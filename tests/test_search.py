import asyncio
import copy
import json
from pathlib import Path

from tiktok_scraper.constants import SEARCH_MUSIC_API_URL
from tiktok_scraper.constants import SEARCH_USERS_API_URL
from tiktok_scraper.constants import SEARCH_VIDEOS_API_URL
from tiktok_scraper.models import Music
from tiktok_scraper.search import iter_search_music
from tiktok_scraper.search import iter_search_users
from tiktok_scraper.search import iter_search_videos


class FakeBrowser:
    """Stand-in for `TikTokBrowser` returning canned API responses, by cursor."""

    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    async def request_json(self, url, params, from_page="video"):
        self.requests.append((url, params, from_page))
        return self.pages[params["cursor"]]


def video(item, video_id):
    item = copy.deepcopy(item)
    item["id"] = video_id
    return {"type": 1, "item": item}


def collect(iterator):
    async def run():
        return [result async for result in iterator]

    return asyncio.run(run())


def test_iter_search_videos_paginates_with_search_id(item):
    browser = FakeBrowser(
        {
            0: {
                "data": [video(item, "1"), {"type": 4, "user_list": []}, video(item, "2")],
                "cursor": 12,
                "has_more": 1,
                "log_pb": {"impr_id": "search-id"},
            },
            12: {"data": [video(item, "2"), video(item, "3")], "cursor": 24, "has_more": 0},
        },
    )

    tiktoks = collect(iter_search_videos(browser, "ukraine"))

    assert [tiktok.id for tiktok in tiktoks] == ["1", "2", "3"]
    url, first_params, from_page = browser.requests[0]
    assert (url, from_page) == (SEARCH_VIDEOS_API_URL, "search")
    assert first_params["keyword"] == "ukraine" and "search_id" not in first_params
    assert browser.requests[1][1]["search_id"] == "search-id"
    assert browser.requests[1][1]["offset"] == 12


def test_iter_search_videos_limit(item):
    browser = FakeBrowser({0: {"data": [video(item, str(i)) for i in range(12)], "cursor": 12, "has_more": 1}})

    assert len(collect(iter_search_videos(browser, "ukraine", limit=5))) == 5
    assert len(browser.requests) == 1


def test_iter_search_users():
    user_info = {
        "uid": "1",
        "sec_uid": "MS4",
        "unique_id": "ukraine.ua",
        "nickname": "Ukraine",
        "follower_count": 1400000,
    }
    browser = FakeBrowser({0: {"user_list": [{"user_info": user_info}, {}], "cursor": 10, "has_more": 0}})

    users = collect(iter_search_users(browser, "ukraine"))

    assert [user.username for user in users] == ["ukraine.ua"]
    assert users[0].follower_count == 1400000
    assert browser.requests[0][0] == SEARCH_USERS_API_URL


def test_tiktok_to_dict(item):
    data = collect(iter_search_videos(FakeBrowser({0: {"data": [video(item, "1")], "has_more": 0}}), "x"))[0].to_dict()

    assert data["id"] == "1"
    assert data["url"] == "https://www.tiktok.com/@emmanuelmacron/video/1"
    assert data["play_count"] == item["stats"]["playCount"]
    assert data["created_at"].endswith("Z")


MUSIC_SEARCH = json.loads((Path(__file__).parent / "fixtures" / "music_search.json").read_text())


def test_music_from_search():
    music = Music.from_search(MUSIC_SEARCH["data"][0]["music_info"])

    assert music.id == "6766128122128500738"
    assert (music.title, music.author, music.album) == ("Paris", "Else", "Paris")
    assert music.duration == 60
    assert music.is_original is False
    assert music.video_count == 1401567
    assert music.url.startswith("https://") and music.cover_url.startswith("https://")


def test_iter_search_music_paginates():
    first_page = copy.deepcopy(MUSIC_SEARCH)
    second_page = {"data": [MUSIC_SEARCH["data"][0], {"other": {}}], "cursor": 20, "has_more": 0}
    browser = FakeBrowser({0: first_page, 10: second_page})

    sounds = collect(iter_search_music(browser, "paris"))

    # The repeated sound and the entry without music_info are skipped.
    assert [sound.author for sound in sounds] == ["Else", "Theo Degler", "Nono La Grinta"]
    url, params, from_page = browser.requests[0]
    assert (url, from_page, params["keyword"]) == (SEARCH_MUSIC_API_URL, "search", "paris")
    assert browser.requests[1][1]["cursor"] == 10


def test_iter_search_music_limit():
    browser = FakeBrowser({0: MUSIC_SEARCH})

    assert len(collect(iter_search_music(browser, "paris", limit=2))) == 2
