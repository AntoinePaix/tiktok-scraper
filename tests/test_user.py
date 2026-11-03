import asyncio
import copy

import pytest

from tiktok_scraper import TikTokError
from tiktok_scraper import get_user_metadata
from tiktok_scraper import iter_user_tiktoks
from tiktok_scraper.constants import STATUS_PRIVATE_ACCOUNT
from tiktok_scraper.constants import STATUS_USER_NOT_FOUND


class FakeClient:
    """Stand-in for `TikTokClient` returning canned responses."""

    def __init__(self, pages=(), universal_data=None):
        self.pages = list(pages)
        self.universal_data = universal_data
        self.queries = []
        self.device_id_resets = 0

    def build_web_query(self, **extra):
        return {key: str(value) for key, value in extra.items()}

    def reset_device_id(self):
        self.device_id_resets += 1

    async def get_api_json(self, url, params, referer):
        self.queries.append(params)
        return self.pages.pop(0)

    async def get_universal_data(self, url):
        return self.universal_data


def make_item(item, video_id, create_time):
    item = copy.deepcopy(item)
    item["id"] = video_id
    item["createTime"] = create_time
    return item


def collect(client):
    async def run():
        return [tiktok.id async for tiktok in iter_user_tiktoks(client, "sec_uid", "https://www.tiktok.com/@user")]

    return asyncio.run(run())


def test_iter_user_tiktoks_paginates_by_create_time(item):
    first_page = [make_item(item, "3", 1_700_000_300), make_item(item, "2", 1_700_000_200)]
    second_page = [make_item(item, "2", 1_700_000_200), make_item(item, "1", 1_700_000_100)]
    client = FakeClient(
        pages=[
            {"itemList": first_page, "hasMorePrevious": True},
            {"itemList": second_page, "hasMorePrevious": False},
        ]
    )

    assert collect(client) == ["3", "2", "1"]
    assert client.queries[1]["cursor"] == str(1_700_000_200 * 1000)
    assert client.queries[0]["type"] == "1"


def test_iter_user_tiktoks_resets_device_id_on_same_page(item):
    page = {"itemList": [make_item(item, "1", 1_700_000_100)], "hasMorePrevious": True}
    client = FakeClient(pages=[page, page, page, page])

    with pytest.raises(TikTokError, match="same page"):
        collect(client)
    assert client.device_id_resets == 3


def test_get_user_metadata(user_info):
    client = FakeClient(universal_data={"webapp.user-detail": {"statusCode": 0, "userInfo": user_info}})

    metadata = asyncio.run(get_user_metadata(client, "@EmmanuelMacron"))

    assert metadata.username == "emmanuelmacron"


@pytest.mark.parametrize(
    ("detail", "message"),
    [
        ({"statusCode": STATUS_USER_NOT_FOUND}, "not found"),
        ({"statusCode": STATUS_PRIVATE_ACCOUNT, "userInfo": {}}, "private"),
        ({}, "Unable to extract"),
    ],
)
def test_get_user_metadata_errors(detail, message):
    client = FakeClient(universal_data={"webapp.user-detail": detail})

    with pytest.raises(TikTokError, match=message):
        asyncio.run(get_user_metadata(client, "user"))
