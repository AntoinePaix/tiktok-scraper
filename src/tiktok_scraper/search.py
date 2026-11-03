"""Search TikTok by keyword. Needs a `TikTokBrowser` (the "playwright" extra) to sign API requests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import AsyncIterator

from .constants import SEARCH_USERS_API_URL
from .constants import SEARCH_VIDEOS_API_URL
from .models import SearchUser
from .models import TikTok

if TYPE_CHECKING:
    from .browser import TikTokBrowser

VIDEOS_PER_REQUEST = 12
USERS_PER_REQUEST = 10


async def _paginate_search(
    browser: TikTokBrowser, url: str, keyword: str, list_key: str, count: int
) -> AsyncIterator[dict[str, Any]]:
    cursor = 0
    search_id = None
    while True:
        params = {"keyword": keyword, "offset": cursor, "cursor": cursor, "count": count}
        if search_id:
            # Following pages are tied to the first one by its impression id.
            params["search_id"] = search_id
        data = await browser.request_json(url, params, from_page="search")
        search_id = search_id or (data.get("log_pb") or {}).get("impr_id")

        entries = data.get(list_key) or []
        for entry in entries:
            yield entry

        next_cursor = int(data.get("cursor") or 0)
        if not data.get("has_more") or not entries or next_cursor <= cursor:
            return
        cursor = next_cursor


async def iter_search_videos(browser: TikTokBrowser, keyword: str, limit: int | None = None) -> AsyncIterator[TikTok]:
    """Yield the tiktoks found by a keyword search, in TikTok's ranking order.

    Args:
        browser (TikTokBrowser): Started browser, to sign the API requests.
        keyword (str): Searched keyword, e.g. "ukraine".
        limit (int, optional): Maximum number of tiktoks. Defaults to all the results TikTok returns.
    """
    seen_ids: set[str] = set()
    async for entry in _paginate_search(browser, SEARCH_VIDEOS_API_URL, keyword, "data", VIDEOS_PER_REQUEST):
        # The general search also mixes in other kinds of results (users, sounds...): only keep videos.
        item = entry.get("item")
        if not item or not item.get("id") or item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        yield TikTok(item)
        if limit is not None and len(seen_ids) >= limit:
            return


async def iter_search_users(
    browser: TikTokBrowser, keyword: str, limit: int | None = None
) -> AsyncIterator[SearchUser]:
    """Yield the accounts found by a keyword search.

    Args:
        browser (TikTokBrowser): Started browser, to sign the API requests.
        keyword (str): Searched keyword, e.g. "ukraine".
        limit (int, optional): Maximum number of accounts. Defaults to all the results TikTok returns.
    """
    counter = 0
    async for entry in _paginate_search(browser, SEARCH_USERS_API_URL, keyword, "user_list", USERS_PER_REQUEST):
        if not entry.get("user_info"):
            continue
        yield SearchUser.from_api(entry["user_info"])
        counter += 1
        if limit is not None and counter >= limit:
            return
