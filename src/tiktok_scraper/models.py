from __future__ import annotations

import dataclasses
import datetime
import urllib.parse
from typing import Any

from .constants import VIDEO_URL_FORMAT


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class TikTok:
    def __init__(self, tiktok_data: dict[str, Any]) -> None:
        self._tiktok_data = tiktok_data

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}(id='{self.id}', description='{self.description}')>"

    @property
    def raw(self) -> dict[str, Any]:
        return self._tiktok_data

    @property
    def id(self) -> str:
        return self._tiktok_data["id"]

    @property
    def description(self) -> str:
        return self._tiktok_data.get("desc", "")

    @property
    def create_time(self) -> int:
        return int(self._tiktok_data["createTime"])

    @property
    def unique_id(self) -> str:
        return self._tiktok_data["author"]["uniqueId"]

    @property
    def webpage_url(self) -> str:
        return VIDEO_URL_FORMAT.format(username=self.unique_id, video_id=self.id)

    @property
    def is_slideshow(self) -> bool:
        return "imagePost" in self._tiktok_data

    @property
    def video_format(self) -> str:
        return self._tiktok_data.get("video", {}).get("format") or "mp4"

    @property
    def video_filename(self) -> str:
        return f"{self.id}.{self.video_format}"

    @property
    def video_urls(self) -> list[str]:
        """Candidate video URLs, best first (same priority as yt-dlp's web formats)."""
        video = self._tiktok_data.get("video", {})
        urls = []

        bitrate_infos = sorted(video.get("bitrateInfo") or [], key=lambda info: info.get("Bitrate", 0), reverse=True)
        for bitrate_info in bitrate_infos:
            play_addr = bitrate_info.get("PlayAddr") or {}
            # bytevc2 is bytedance's own h266/vvc codec, as-of-yet unplayable.
            if "bytevc2" in (play_addr.get("UrlKey") or ""):
                continue
            for url in play_addr.get("UrlList") or []:
                # Some bytevc1 formats are video-only.
                if urllib.parse.urlparse(url).path.endswith("/media-video-hvc1/"):
                    continue
                urls.append(url)

        urls.extend(url for url in (video.get("playAddr"), video.get("downloadAddr")) if url)

        # Filter out broken formats, see https://github.com/yt-dlp/yt-dlp/issues/11034
        urls = [url for url in urls if urllib.parse.urlparse(url).hostname != "www.tiktok.com"]
        return list(dict.fromkeys(urls))


@dataclasses.dataclass
class UserMetadata:
    id: str
    sec_uid: str
    username: str
    nickname: str
    signature: str
    verified: bool
    private_account: bool
    created_at: datetime.datetime | None
    avatar_url: str | None
    bio_link: str | None
    region: str | None
    language: str | None
    follower_count: int | None
    following_count: int | None
    heart_count: int | None
    video_count: int | None
    digg_count: int | None
    friend_count: int | None

    @classmethod
    def from_user_info(cls, user_info: dict[str, Any]) -> UserMetadata:
        user = user_info["user"]
        # statsV2 holds exact values as strings, stats holds rounded values as integers.
        stats = {**user_info.get("stats", {}), **user_info.get("statsV2", {})}
        create_time = _to_int(user.get("createTime"))
        return cls(
            id=user["id"],
            sec_uid=user["secUid"],
            username=user["uniqueId"],
            nickname=user.get("nickname", ""),
            signature=user.get("signature", ""),
            verified=bool(user.get("verified")),
            private_account=bool(user.get("privateAccount")),
            created_at=datetime.datetime.fromtimestamp(create_time, datetime.UTC) if create_time else None,
            avatar_url=user.get("avatarLarger"),
            bio_link=(user.get("bioLink") or {}).get("link"),
            region=user.get("region"),
            language=user.get("language"),
            follower_count=_to_int(stats.get("followerCount")),
            following_count=_to_int(stats.get("followingCount")),
            heart_count=_to_int(stats.get("heartCount", stats.get("heart"))),
            video_count=_to_int(stats.get("videoCount")),
            digg_count=_to_int(stats.get("diggCount")),
            friend_count=_to_int(stats.get("friendCount")),
        )

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        return data
