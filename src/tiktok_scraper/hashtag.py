"""List the tiktoks of a hashtag. Needs a `TikTokBrowser` (the "playwright" extra) to sign API requests.

TikTok often refuses hashtag videos to a headless browser: prefer `TikTokBrowser(headless=False)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import AsyncIterator

from .client import TikTokError
from .constants import HASHTAG_DETAIL_API_URL
from .constants import HASHTAG_VIDEOS_API_URL
from .constants import STATUS_OK
from .models import Hashtag
from .models import TikTok

if TYPE_CHECKING:
    from .browser import TikTokBrowser

VIDEOS_PER_REQUEST = 30


async def get_hashtag(browser: TikTokBrowser, name: str) -> Hashtag:
    """Get the id and statistics of a hashtag.

    Args:
        browser (TikTokBrowser): Started browser, to sign the API requests.
        name (str): Hashtag name, with or without "#", e.g. "ukraine".
    """
    name = name.lstrip("#")
    data = await browser.request_json(HASHTAG_DETAIL_API_URL, {"challengeName": name}, from_page="hashtag")
    challenge_info = data.get("challengeInfo") or {}
    if data.get("statusCode", STATUS_OK) != STATUS_OK or not challenge_info.get("challenge", {}).get("id"):
        raise TikTokError(f"Hashtag '#{name}' not found (status code {data.get('statusCode')})")
    return Hashtag.from_api(challenge_info)


async def iter_hashtag_videos(
    browser: TikTokBrowser, hashtag: str | Hashtag, limit: int | None = None
) -> AsyncIterator[TikTok]:
    """Yield the tiktoks of a hashtag, in TikTok's ranking order.

    Args:
        browser (TikTokBrowser): Started browser, preferably with a visible window (`headless=False`).
        hashtag (str | Hashtag): Hashtag name (e.g. "ukraine"), or a `Hashtag` from `get_hashtag`.
        limit (int, optional): Maximum number of tiktoks. Defaults to all the results TikTok returns.
    """
    if not isinstance(hashtag, Hashtag):
        hashtag = await get_hashtag(browser, hashtag)

    seen_ids: set[str] = set()
    cursor = 0
    while True:
        params = {"challengeID": hashtag.id, "count": VIDEOS_PER_REQUEST, "cursor": cursor}
        try:
            data = await browser.request_json(HASHTAG_VIDEOS_API_URL, params, from_page="hashtag")
        except TikTokError as error:
            if browser.headless and "Empty response" in str(error):
                raise TikTokError(
                    "TikTok refused hashtag videos to this headless browser: retry with TikTokBrowser(headless=False)"
                ) from error
            raise

        items = data.get("itemList") or []
        for item in items:
            if item.get("id") and item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                yield TikTok(item)
                if limit is not None and len(seen_ids) >= limit:
                    return

        next_cursor = int(data.get("cursor") or 0)
        if not data.get("hasMore") or not items or next_cursor <= cursor:
            return
        cursor = next_cursor
