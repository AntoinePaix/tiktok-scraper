import asyncio
import datetime

import pytest

from tiktok_scraper import Comment
from tiktok_scraper import iter_comments
from tiktok_scraper.comments import extract_video_id
from tiktok_scraper.constants import COMMENTS_API_URL
from tiktok_scraper.constants import REPLIES_API_URL

VIDEO_ID = "7703703665818733857"


def api_comment(comment_id, text, reply_count=0, reply_id="0"):
    return {
        "cid": comment_id,
        "aweme_id": VIDEO_ID,
        "text": text,
        "create_time": 1793685419,
        "digg_count": 5,
        "reply_comment_total": reply_count,
        "reply_id": reply_id,
        "comment_language": "fr",
        "user": {"uid": "42", "unique_id": "someone", "nickname": "Someone"},
    }


class FakeBrowser:
    """Stand-in for `TikTokBrowser` returning canned API responses."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    async def request_json(self, url, params, from_page="video"):
        self.requests.append((url, params))
        key = (url, params.get("comment_id"), params["cursor"])
        return self.responses[key]


def collect(browser, **kwargs):
    async def run():
        return [comment async for comment in iter_comments(browser, VIDEO_ID, **kwargs)]

    return asyncio.run(run())


@pytest.mark.parametrize(
    "video",
    [
        VIDEO_ID,
        f"https://www.tiktok.com/@emmanuelmacron/video/{VIDEO_ID}?lang=fr",
        f"https://www.tiktok.com/@a/photo/{VIDEO_ID}",
    ],
)
def test_extract_video_id(video):
    assert extract_video_id(video) == VIDEO_ID


def test_extract_video_id_invalid():
    with pytest.raises(ValueError):
        extract_video_id("https://www.tiktok.com/@emmanuelmacron")


def test_comment_from_api():
    comment = Comment.from_api(api_comment("1", "Bonjour", reply_count=2))

    assert comment.id == "1"
    assert comment.parent_id is None
    assert comment.reply_count == 2
    assert comment.author_username == "someone"
    assert comment.created_at == datetime.datetime.fromtimestamp(1793685419, datetime.UTC)
    assert comment.to_dict()["created_at"] == comment.created_at.isoformat()


def test_reply_from_api():
    assert Comment.from_api(api_comment("2", "Re", reply_id="1")).parent_id == "1"


@pytest.fixture
def browser():
    return FakeBrowser(
        {
            (COMMENTS_API_URL, None, 0): {
                "comments": [api_comment("1", "first", reply_count=2), api_comment("2", "second")],
                "has_more": 1,
                "cursor": 2,
            },
            (COMMENTS_API_URL, None, 2): {"comments": [api_comment("3", "third")], "has_more": 0, "cursor": 3},
            (REPLIES_API_URL, "1", 0): {
                "comments": [api_comment("1a", "reply", reply_id="1"), api_comment("1b", "reply", reply_id="1")],
                "has_more": 0,
                "cursor": 2,
            },
        }
    )


def test_iter_comments_with_replies(browser):
    comments = collect(browser)

    assert [comment.id for comment in comments] == ["1", "1a", "1b", "2", "3"]
    assert browser.requests[0] == (COMMENTS_API_URL, {"aweme_id": VIDEO_ID, "count": 50, "cursor": 0})
    assert browser.requests[1][1]["item_id"] == VIDEO_ID


def test_iter_comments_without_replies(browser):
    comments = collect(browser, with_replies=False)

    assert [comment.id for comment in comments] == ["1", "2", "3"]
    assert all(url == COMMENTS_API_URL for url, _ in browser.requests)


def test_iter_comments_stops_when_cursor_does_not_move():
    browser = FakeBrowser(
        {(COMMENTS_API_URL, None, 0): {"comments": [api_comment("1", "first")], "has_more": 1, "cursor": 0}}
    )

    assert [comment.id for comment in collect(browser)] == ["1"]
