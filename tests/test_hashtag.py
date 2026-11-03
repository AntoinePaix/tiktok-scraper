import asyncio
import copy

import pytest

from tiktok_scraper import Hashtag
from tiktok_scraper import TikTokError
from tiktok_scraper import get_hashtag
from tiktok_scraper import iter_hashtag_videos
from tiktok_scraper.constants import HASHTAG_DETAIL_API_URL
from tiktok_scraper.constants import HASHTAG_VIDEOS_API_URL

DETAIL = {
    "statusCode": 0,
    "challengeInfo": {
        "challenge": {"id": "451042", "title": "ukraine", "desc": ""},
        "stats": {"videoCount": 9600000, "viewCount": 192200000000},
        "statsV2": {"videoCount": "9597506", "viewCount": "192217240529"},
    },
}


class FakeBrowser:
    """Stand-in for `TikTokBrowser`: answers the detail endpoint, then item_list pages by cursor."""

    def __init__(self, pages, detail=DETAIL, headless=False):
        self.pages = pages
        self.detail = detail
        self.headless = headless
        self.requests = []

    async def request_json(self, url, params, from_page="video"):
        self.requests.append((url, params))
        if url == HASHTAG_DETAIL_API_URL:
            return self.detail
        page = self.pages[params["cursor"]]
        if isinstance(page, Exception):
            raise page
        return page


def items(item, *ids):
    return [{**copy.deepcopy(item), "id": video_id} for video_id in ids]


def collect(iterator):
    async def run():
        return [result async for result in iterator]

    return asyncio.run(run())


def test_get_hashtag():
    browser = FakeBrowser({})

    hashtag = asyncio.run(get_hashtag(browser, "#ukraine"))

    assert hashtag == Hashtag(
        id="451042", name="ukraine", description=None, video_count=9597506, view_count=192217240529
    )
    assert browser.requests == [(HASHTAG_DETAIL_API_URL, {"challengeName": "ukraine"})]


def test_get_hashtag_not_found():
    browser = FakeBrowser({}, detail={"statusCode": 10205, "challengeInfo": {}})

    with pytest.raises(TikTokError, match="not found"):
        asyncio.run(get_hashtag(browser, "doesnotexist"))


def test_iter_hashtag_videos_two_steps(item):
    browser = FakeBrowser(
        {
            0: {"itemList": items(item, "1", "2"), "cursor": 30, "hasMore": True},
            30: {"itemList": items(item, "2", "3"), "cursor": 60, "hasMore": False},
        }
    )

    tiktoks = collect(iter_hashtag_videos(browser, "ukraine"))

    assert [tiktok.id for tiktok in tiktoks] == ["1", "2", "3"]
    assert browser.requests[1] == (HASHTAG_VIDEOS_API_URL, {"challengeID": "451042", "count": 30, "cursor": 0})
    assert browser.requests[2][1]["cursor"] == 30


def test_iter_hashtag_videos_with_hashtag_skips_detail(item):
    browser = FakeBrowser({0: {"itemList": items(item, "1", "2", "3"), "cursor": 30, "hasMore": True}})
    hashtag = Hashtag(id="451042", name="ukraine", description=None, video_count=None, view_count=None)

    assert len(collect(iter_hashtag_videos(browser, hashtag, limit=2))) == 2
    assert [url for url, _ in browser.requests] == [HASHTAG_VIDEOS_API_URL]


def test_iter_hashtag_videos_headless_refusal():
    browser = FakeBrowser({0: TikTokError("Empty response from /api/challenge/item_list/")}, headless=True)

    with pytest.raises(TikTokError, match="headless=False"):
        collect(iter_hashtag_videos(browser, "ukraine"))
