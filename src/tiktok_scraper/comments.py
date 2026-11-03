"""Scrape the comments of a tiktok. Needs a `TikTokBrowser` (the "playwright" extra) to sign API requests."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Any
from typing import AsyncIterator

from .constants import COMMENTS_API_URL
from .constants import REPLIES_API_URL
from .models import Comment

if TYPE_CHECKING:
    from .browser import TikTokBrowser

COMMENTS_PER_REQUEST = 50
REPLIES_PER_REQUEST = 50


def extract_video_id(video: str) -> str:
    """Return the id of a tiktok from its id or URL (e.g. https://www.tiktok.com/@user/video/7019344847035288837)."""
    if video.isdigit():
        return video
    match = re.search(r"/(?:video|photo)/(\d+)", video)
    if match is None:
        raise ValueError(f"Unable to extract tiktok id from: {video}")
    return match.group(1)


async def _paginate(
    browser: TikTokBrowser, url: str, params: dict[str, Any], count: int
) -> AsyncIterator[dict[str, Any]]:
    cursor = 0
    while True:
        data = await browser.request_json(url, {**params, "count": count, "cursor": cursor})
        comments = data.get("comments") or []
        for comment in comments:
            yield comment

        next_cursor = int(data.get("cursor") or 0)
        if not data.get("has_more") or not comments or next_cursor <= cursor:
            return
        cursor = next_cursor


async def iter_replies(browser: TikTokBrowser, video_id: str, comment_id: str) -> AsyncIterator[Comment]:
    """Yield the replies to a comment."""
    params = {"item_id": video_id, "comment_id": comment_id}
    async for reply in _paginate(browser, REPLIES_API_URL, params, REPLIES_PER_REQUEST):
        yield Comment.from_api(reply)


async def iter_comments(browser: TikTokBrowser, video: str, with_replies: bool = True) -> AsyncIterator[Comment]:
    """Yield the comments of a tiktok, each followed by its replies.

    Args:
        browser (TikTokBrowser): Started browser, to sign the API requests.
        video (str): Tiktok id or URL.
        with_replies (bool, optional): Also yield the replies to each comment.
    """
    video_id = extract_video_id(video)
    async for data in _paginate(browser, COMMENTS_API_URL, {"aweme_id": video_id}, COMMENTS_PER_REQUEST):
        comment = Comment.from_api(data)
        yield comment
        if with_replies and comment.reply_count:
            async for reply in iter_replies(browser, video_id, comment.id):
                yield reply
