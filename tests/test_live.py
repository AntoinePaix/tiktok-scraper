"""Live smoke tests against tiktok.com, deselected by default: run them with `pytest -m live`."""

import asyncio

import pytest

from tokscrape import TikTokClient
from tokscrape import get_user_metadata

pytestmark = pytest.mark.live


async def _metadata():
    async with TikTokClient() as client:
        return await get_user_metadata(client, "charlidamelio")


def test_live_user_metadata():
    metadata = asyncio.run(_metadata())
    assert metadata.username == "charlidamelio"
    assert metadata.sec_uid
    assert metadata.follower_count > 0
