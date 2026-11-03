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

    def to_dict(self) -> dict[str, Any]:
        """Main fields of the tiktok (`raw` holds everything TikTok returned)."""
        author = self._tiktok_data.get("author") or {}
        # statsV2 holds exact values as strings, stats holds rounded values as integers.
        stats = {**self._tiktok_data.get("stats", {}), **self._tiktok_data.get("statsV2", {})}
        create_time = _to_int(self._tiktok_data.get("createTime"))
        created_at = datetime.datetime.fromtimestamp(create_time, datetime.UTC) if create_time else None
        return {
            "id": self.id,
            "url": self.webpage_url,
            "description": self.description,
            "created_at": created_at.isoformat() if created_at else None,
            "author_username": author.get("uniqueId"),
            "author_nickname": author.get("nickname"),
            "is_slideshow": self.is_slideshow,
            "duration": _to_int(self._tiktok_data.get("video", {}).get("duration")),
            "play_count": _to_int(stats.get("playCount")),
            "like_count": _to_int(stats.get("diggCount")),
            "comment_count": _to_int(stats.get("commentCount")),
            "share_count": _to_int(stats.get("shareCount")),
            "save_count": _to_int(stats.get("collectCount")),
        }


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


@dataclasses.dataclass
class Comment:
    id: str
    video_id: str
    text: str
    created_at: datetime.datetime | None
    like_count: int | None
    reply_count: int | None
    language: str | None
    author_id: str | None
    author_username: str | None
    author_nickname: str | None
    # Id of the comment this one replies to, None for a top-level comment.
    parent_id: str | None

    @classmethod
    def from_api(cls, comment: dict[str, Any]) -> Comment:
        user = comment.get("user") or {}
        create_time = _to_int(comment.get("create_time"))
        parent_id = str(comment.get("reply_id") or "0")
        return cls(
            id=comment["cid"],
            video_id=comment.get("aweme_id", ""),
            text=comment.get("text", ""),
            created_at=datetime.datetime.fromtimestamp(create_time, datetime.UTC) if create_time else None,
            like_count=_to_int(comment.get("digg_count")),
            reply_count=_to_int(comment.get("reply_comment_total")),
            language=comment.get("comment_language"),
            author_id=user.get("uid"),
            author_username=user.get("unique_id"),
            author_nickname=user.get("nickname"),
            parent_id=None if parent_id == "0" else parent_id,
        )

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        return data


@dataclasses.dataclass
class SearchUser:
    """Account found by a search. Use `get_user_metadata(client, user.username)` to get all its metadata."""

    id: str | None
    sec_uid: str | None
    username: str | None
    nickname: str | None
    signature: str | None
    follower_count: int | None

    @classmethod
    def from_api(cls, user_info: dict[str, Any]) -> SearchUser:
        return cls(
            id=user_info.get("uid"),
            sec_uid=user_info.get("sec_uid"),
            username=user_info.get("unique_id"),
            nickname=user_info.get("nickname"),
            signature=user_info.get("signature"),
            follower_count=_to_int(user_info.get("follower_count")),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Hashtag:
    id: str
    name: str
    description: str | None
    video_count: int | None
    view_count: int | None

    @classmethod
    def from_api(cls, challenge_info: dict[str, Any]) -> Hashtag:
        challenge = challenge_info["challenge"]
        # statsV2 holds exact values as strings, stats holds rounded values as integers.
        stats = {**challenge_info.get("stats", {}), **challenge_info.get("statsV2", {})}
        return cls(
            id=challenge["id"],
            name=challenge.get("title", ""),
            description=challenge.get("desc") or None,
            video_count=_to_int(stats.get("videoCount")),
            view_count=_to_int(stats.get("viewCount")),
        )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)
