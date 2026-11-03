"""Scrape a TikTok account, using the same web API as yt-dlp's `TikTokUserIE`."""

from __future__ import annotations

import time
from typing import Any
from typing import AsyncIterator

from .client import TikTokClient
from .client import TikTokError
from .constants import ONE_WEEK_MS
from .constants import STATUS_OK
from .constants import STATUS_PRIVATE_ACCOUNT
from .constants import STATUS_USER_BANNED
from .constants import STATUS_USER_NOT_FOUND
from .constants import TIKTOK_EPOCH_MS
from .constants import USER_ITEM_LIST_API_URL
from .constants import USER_URL_FORMAT
from .models import TikTok
from .models import UserMetadata

MAX_SAME_PAGE_RETRIES = 3


async def get_user_info(client: TikTokClient, username: str) -> dict[str, Any]:
    """Return the raw `userInfo` object (user, stats, statsV2, ...) of a TikTok account."""
    username = username.lstrip("@").lower()
    universal_data = await client.get_universal_data(USER_URL_FORMAT.format(username=username))
    detail = universal_data.get("webapp.user-detail") or {}
    status = detail.get("statusCode", STATUS_OK)

    if status == STATUS_USER_NOT_FOUND:
        raise TikTokError(f"User '{username}' not found")
    if status == STATUS_USER_BANNED:
        raise TikTokError(f"User '{username}' is banned")
    user_info = detail.get("userInfo") or {}
    if not user_info.get("user", {}).get("secUid"):
        if status == STATUS_PRIVATE_ACCOUNT:
            raise TikTokError(f"User '{username}' has a private account")
        raise TikTokError(f"Unable to extract metadata of user '{username}' (status code {status})")
    return user_info


async def get_user_metadata(client: TikTokClient, username: str) -> UserMetadata:
    """Get the metadata (profile and statistics) of a TikTok account."""
    return UserMetadata.from_user_info(await get_user_info(client, username))


async def iter_user_tiktoks(client: TikTokClient, sec_uid: str, referer: str) -> AsyncIterator[TikTok]:
    """Yield every tiktok of an account, newest to oldest.

    Args:
        client (TikTokClient): Client which already visited the user page (to get cookies).
        sec_uid (str): Secondary user id of the account (`UserMetadata.sec_uid`).
        referer (str): User page URL.
    """
    seen_ids: set[str] = set()
    cursor = int(time.time() * 1e3)

    while True:
        for _ in range(MAX_SAME_PAGE_RETRIES):
            query = client.build_web_query(count=15, cursor=cursor, secUid=sec_uid, type=1)
            response = await client.get_api_json(USER_ITEM_LIST_API_URL, query, referer=referer)
            # Avoid an infinite loop caused by a bad device_id (https://github.com/yt-dlp/yt-dlp/issues/14031)
            current_batch = sorted(item["id"] for item in response.get("itemList") or [])
            if not current_batch or current_batch != sorted(seen_ids):
                break
            client.reset_device_id()
        else:
            raise TikTokError("TikTok API keeps sending the same page")

        items = response.get("itemList") or []
        for item in items:
            if item.get("id") and item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                yield TikTok(item)

        old_cursor = cursor
        cursor = int(items[-1]["createTime"]) * 1000 if items else 0
        if not cursor or old_cursor == cursor:
            # User may not have posted within this ~1 week lookback, so manually adjust cursor.
            cursor = old_cursor - ONE_WEEK_MS
        # In case 'hasMorePrevious' is wrong, break if we have gone back before TikTok existed.
        if cursor < TIKTOK_EPOCH_MS or not response.get("hasMorePrevious"):
            return
