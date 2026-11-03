import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"


@pytest.fixture
def item() -> dict[str, Any]:
    """Tiktok from `api/creator/item_list/`, trimmed to the fields used by the scraper."""
    return json.loads((FIXTURES_DIRECTORY / "item.json").read_text())


@pytest.fixture
def user_info() -> dict[str, Any]:
    """`webapp.user-detail.userInfo` from a user page rehydration data."""
    return {
        "user": {
            "id": "6846411051911660549",
            "uniqueId": "emmanuelmacron",
            "nickname": "Emmanuel Macron",
            "avatarLarger": "https://p16-common-sign.tiktokcdn-eu.com/avatar.jpeg",
            "signature": "Président de la République française.",
            "createTime": 1594057974,
            "verified": True,
            "secUid": "MS4wLjABAAAA26OwyIlDhn9hpedKCILgG_p4QuxvKXbBQ43lFzJPj3PRbbdx_FMDJTGfYy1Ay-sT",
            "privateAccount": False,
        },
        "stats": {
            "followerCount": 7700000,
            "followingCount": 0,
            "heart": 93400000,
            "heartCount": 93400000,
            "videoCount": 454,
            "diggCount": 0,
            "friendCount": 0,
        },
        "statsV2": {
            "followerCount": "7710750",
            "followingCount": "0",
            "heart": "93367785",
            "heartCount": "93367785",
            "videoCount": "454",
            "diggCount": "0",
            "friendCount": "0",
        },
    }
