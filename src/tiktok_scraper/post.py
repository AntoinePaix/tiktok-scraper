"""Get one tiktok from its URL or id, from its page like yt-dlp's `TikTokIE` (no browser needed)."""

from __future__ import annotations

import re

from tiktok_scraper.client import TikTokClient
from tiktok_scraper.client import TikTokError
from tiktok_scraper.constants import VIDEO_URL_FORMAT
from tiktok_scraper.constants import TikTokStatus
from tiktok_scraper.models import TikTok


def extract_video_id(video: str) -> str:
    """Return the id of a tiktok from its id or URL (e.g. https://www.tiktok.com/@user/video/7019344847035288837)."""
    if video.isdigit():
        return video
    match = re.search(r"/(?:video|photo)/(\d+)", video)
    if match is None:
        raise ValueError(f"Unable to extract tiktok id from: {video}")
    return match.group(1)


async def get_tiktok(client: TikTokClient, video: str) -> TikTok:
    """Get one tiktok (a video or a slideshow) with all its fields.

    Args:
        client (TikTokClient): Client to use.
        video (str): Tiktok URL (`/video/<id>` or `/photo/<id>`) or id.

    Raises:
        TikTokError: The tiktok doesn't exist, is private, or is otherwise unavailable.
    """
    video_id = extract_video_id(video)
    # The page answers by id whatever the username, and only `/video/` pages hold the data, slideshows included.
    universal_data = await client.get_universal_data(VIDEO_URL_FORMAT.format(username="_", video_id=video_id))
    detail = universal_data.get("webapp.video-detail") or {}
    status = detail.get("statusCode", TikTokStatus.OK)
    item = (detail.get("itemInfo") or {}).get("itemStruct") or {}

    if status == TikTokStatus.ITEM_NOT_FOUND:
        raise TikTokError(f"Tiktok {video_id} doesn't exist (deleted, or wrong id)")
    if status == TikTokStatus.PRIVATE_ITEM:
        raise TikTokError(f"Tiktok {video_id} is private")
    if status == TikTokStatus.PRIVATE_ACCOUNT:
        raise TikTokError(f"Tiktok {video_id} belongs to a private account")
    if status != TikTokStatus.OK or not item.get("id"):
        message = detail.get("statusMsg") or "no data"
        raise TikTokError(f"Tiktok {video_id} is unavailable (status code {status}: {message})")
    return TikTok.from_api(item)
