"""Data models for what is scraped from TikTok, validated with pydantic.

Each model is built from TikTok's JSON by its `from_api()` (or `from_user_info()`) class method, which maps
TikTok's field names to ours. Pydantic then validates the values and converts them to the declared types,
e.g. the counts of `statsV2`, which TikTok sends as strings, to integers.
"""

from __future__ import annotations

import datetime
import urllib.parse
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import PrivateAttr

from tiktok_scraper.constants import VIDEO_URL_FORMAT


def _stats(data: dict[str, Any], stats_key: str = "stats", stats_v2_key: str = "statsV2") -> dict[str, Any]:
    """Counts of an object: statsV2 holds exact values as strings, stats holds rounded values as integers."""
    return {**(data.get(stats_key) or {}), **(data.get(stats_v2_key) or {})}


class Model(BaseModel):
    def to_dict(self) -> dict[str, Any]:
        """Fields as JSON-compatible values (datetimes as ISO 8601 strings in UTC)."""
        return self.model_dump(mode="json")


class Music(Model):
    """Sound of a tiktok: the music of a video, or the soundtrack of a slideshow."""

    id: str | None = None
    title: str | None = None
    author: str | None = None
    album: str | None = None
    duration: int | None = None  # seconds
    is_original: bool | None = None  # a sound recorded by the author, not a published track
    url: str | None = None  # audio file
    cover_url: str | None = None
    video_count: int | None = None  # videos using this sound, search results only

    @classmethod
    def from_api(cls, music: dict[str, Any]) -> Music:
        """Build the music of a tiktok, from the `music` of an item of TikTok's web API."""
        return cls(
            id=music.get("id") or None,
            title=music.get("title") or None,
            author=music.get("authorName") or None,
            album=music.get("album") or None,
            duration=music.get("duration") or None,
            is_original=music.get("original"),
            url=music.get("playUrl") or None,
            cover_url=music.get("coverLarge") or music.get("coverMedium") or None,
        )

    @classmethod
    def from_search(cls, music_info: dict[str, Any]) -> Music:
        """Build a sound found by `api/search/music/full/`, whose `music_info` uses the mobile app's format."""

        def first_url(url_object: dict[str, Any] | None) -> str | None:
            return next(iter((url_object or {}).get("url_list") or []), None)

        return cls(
            id=music_info.get("id_str") or str(music_info.get("id") or "") or None,
            title=music_info.get("title") or None,
            author=music_info.get("author") or None,
            album=music_info.get("album") or None,
            duration=music_info.get("duration") or None,
            is_original=music_info.get("is_original_sound"),
            url=first_url(music_info.get("play_url")),
            cover_url=first_url(music_info.get("cover_large")) or first_url(music_info.get("cover_medium")),
            video_count=music_info.get("user_count"),
        )


class Location(Model):
    """Place tagged on a tiktok."""

    id: str | None = None
    name: str
    address: str | None = None
    city: str | None = None

    @classmethod
    def from_api(cls, poi: dict[str, Any]) -> Location:
        return cls(
            id=poi.get("id") or None,
            name=poi["name"],
            address=poi.get("address") or None,
            city=poi.get("city") or None,
        )


class TikTok(Model):
    """A tiktok: a video, or a slideshow of images with a soundtrack."""

    id: str
    url: str
    description: str = ""
    created_at: datetime.datetime | None = None  # UTC
    author_id: str | None = None
    author_username: str | None = None
    author_nickname: str | None = None
    author_sec_uid: str | None = None
    author_verified: bool | None = None
    is_slideshow: bool = False
    image_count: int = 0  # images of a slideshow
    duration: int | None = None  # seconds, videos only
    width: int | None = None
    height: int | None = None
    cover_url: str | None = None
    origin_cover_url: str | None = None  # full size cover
    dynamic_cover_url: str | None = None  # animated cover
    language: str | None = None  # language of the description
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)  # usernames mentioned in the description
    location: Location | None = None
    is_ad: bool = False
    duet_enabled: bool | None = None
    stitch_enabled: bool | None = None
    play_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    share_count: int | None = None
    save_count: int | None = None
    repost_count: int | None = None
    music: Music | None = None

    _raw: dict[str, Any] = PrivateAttr(default_factory=dict)

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> TikTok:
        """Build a tiktok from an item of TikTok's web API (`itemList`, `itemStruct`...)."""
        author = item.get("author") or {}
        video = item.get("video") or {}
        stats = _stats(item)
        text_extra = item.get("textExtra") or []
        hashtags = [extra["hashtagName"] for extra in text_extra if extra.get("hashtagName")]
        hashtags += [challenge["title"] for challenge in item.get("challenges") or [] if challenge.get("title")]
        poi = item.get("poi") or {}

        tiktok = cls(
            id=item["id"],
            url=VIDEO_URL_FORMAT.format(username=author.get("uniqueId") or "_", video_id=item["id"]),
            description=item.get("desc") or "",
            created_at=item.get("createTime") or None,
            author_id=author.get("id") or None,
            author_username=author.get("uniqueId") or None,
            author_nickname=author.get("nickname") or None,
            author_sec_uid=author.get("secUid") or None,
            author_verified=author.get("verified"),
            is_slideshow="imagePost" in item,
            image_count=len((item.get("imagePost") or {}).get("images") or []),
            # Slideshows have a video object too, with a duration, width and height of 0.
            duration=video.get("duration") or None,
            width=video.get("width") or None,
            height=video.get("height") or None,
            cover_url=video.get("cover") or None,
            origin_cover_url=video.get("originCover") or None,
            dynamic_cover_url=video.get("dynamicCover") or None,
            language=item.get("textLanguage") or None,
            hashtags=list(dict.fromkeys(hashtags)),
            mentions=list(dict.fromkeys(extra["userUniqueId"] for extra in text_extra if extra.get("userUniqueId"))),
            location=Location.from_api(poi) if poi.get("name") else None,
            is_ad=bool(item.get("isAd")),
            duet_enabled=item.get("duetEnabled"),
            stitch_enabled=item.get("stitchEnabled"),
            play_count=stats.get("playCount"),
            like_count=stats.get("diggCount"),
            comment_count=stats.get("commentCount"),
            share_count=stats.get("shareCount"),
            save_count=stats.get("collectCount"),
            repost_count=stats.get("repostCount"),
            music=Music.from_api(item["music"]) if item.get("music") else None,
        )
        tiktok._raw = item
        return tiktok

    @property
    def raw(self) -> dict[str, Any]:
        """Everything TikTok returned for this tiktok."""
        return self._raw

    @property
    def video_filename(self) -> str:
        return f"{self.id}.{(self._raw.get('video') or {}).get('format') or 'mp4'}"

    @property
    def video_urls(self) -> list[str]:
        """Candidate video URLs, best first (same priority as yt-dlp's web formats)."""
        video = self._raw.get("video") or {}
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

    @property
    def image_urls(self) -> list[list[str]]:
        """Candidate URLs of each image of a slideshow, in order (empty for a video)."""
        images = (self._raw.get("imagePost") or {}).get("images") or []
        return [image.get("imageURL", {}).get("urlList") or [] for image in images]

    @property
    def image_filenames(self) -> list[str]:
        """File names of the images of a slideshow, numbered from 1, inside its folder (named after its id)."""
        return [f"{index}.jpg" for index in range(1, len(self.image_urls) + 1)]

    @property
    def audio_url(self) -> str | None:
        """URL of the soundtrack (the slideshow's sound, or the video's music)."""
        return self.music.url if self.music else None

    @property
    def audio_filename(self) -> str:
        """File name of the soundtrack of a slideshow, inside its folder (named after its id)."""
        return "music.m4a"


class UserMetadata(Model):
    id: str
    sec_uid: str
    username: str
    nickname: str = ""
    signature: str = ""
    verified: bool = False
    private_account: bool = False
    created_at: datetime.datetime | None = None  # UTC
    avatar_url: str | None = None
    bio_link: str | None = None
    region: str | None = None
    language: str | None = None
    follower_count: int | None = None
    following_count: int | None = None
    heart_count: int | None = None
    video_count: int | None = None
    digg_count: int | None = None
    friend_count: int | None = None

    @classmethod
    def from_user_info(cls, user_info: dict[str, Any]) -> UserMetadata:
        user = user_info["user"]
        stats = _stats(user_info)
        return cls(
            id=user["id"],
            sec_uid=user["secUid"],
            username=user["uniqueId"],
            nickname=user.get("nickname") or "",
            signature=user.get("signature") or "",
            verified=bool(user.get("verified")),
            private_account=bool(user.get("privateAccount")),
            created_at=user.get("createTime") or None,
            avatar_url=user.get("avatarLarger") or None,
            bio_link=(user.get("bioLink") or {}).get("link") or None,
            region=user.get("region") or None,
            language=user.get("language") or None,
            follower_count=stats.get("followerCount"),
            following_count=stats.get("followingCount"),
            heart_count=stats.get("heartCount", stats.get("heart")),
            video_count=stats.get("videoCount"),
            digg_count=stats.get("diggCount"),
            friend_count=stats.get("friendCount"),
        )


class Comment(Model):
    id: str
    video_id: str = ""
    text: str = ""
    created_at: datetime.datetime | None = None  # UTC
    like_count: int | None = None
    reply_count: int | None = None
    language: str | None = None
    author_id: str | None = None
    author_username: str | None = None
    author_nickname: str | None = None
    # Id of the comment this one replies to, None for a top-level comment.
    parent_id: str | None = None

    @classmethod
    def from_api(cls, comment: dict[str, Any]) -> Comment:
        user = comment.get("user") or {}
        parent_id = str(comment.get("reply_id") or "0")
        return cls(
            id=comment["cid"],
            video_id=comment.get("aweme_id") or "",
            text=comment.get("text") or "",
            created_at=comment.get("create_time") or None,
            like_count=comment.get("digg_count"),
            reply_count=comment.get("reply_comment_total"),
            language=comment.get("comment_language") or None,
            author_id=user.get("uid") or None,
            author_username=user.get("unique_id") or None,
            author_nickname=user.get("nickname") or None,
            parent_id=None if parent_id == "0" else parent_id,
        )


class SearchUser(Model):
    """Account found by a search. Use `get_user_metadata(client, user.username)` to get all its metadata."""

    id: str | None = None
    sec_uid: str | None = None
    username: str | None = None
    nickname: str | None = None
    signature: str | None = None
    follower_count: int | None = None

    @classmethod
    def from_api(cls, user_info: dict[str, Any]) -> SearchUser:
        return cls(
            id=user_info.get("uid") or None,
            sec_uid=user_info.get("sec_uid") or None,
            username=user_info.get("unique_id") or None,
            nickname=user_info.get("nickname") or None,
            signature=user_info.get("signature") or None,
            follower_count=user_info.get("follower_count"),
        )


class Hashtag(Model):
    id: str
    name: str = ""
    description: str | None = None
    video_count: int | None = None
    view_count: int | None = None

    @classmethod
    def from_api(cls, challenge_info: dict[str, Any]) -> Hashtag:
        challenge = challenge_info["challenge"]
        stats = _stats(challenge_info)
        return cls(
            id=challenge["id"],
            name=challenge.get("title") or "",
            description=challenge.get("desc") or None,
            video_count=stats.get("videoCount"),
            view_count=stats.get("viewCount"),
        )
