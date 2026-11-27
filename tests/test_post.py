import asyncio

import pytest

from tokscrape import TikTokError
from tokscrape import get_tiktok
from tokscrape.constants import TikTokStatus


class FakeClient:
    """Stand-in for `TikTokClient` answering the video page with canned rehydration data."""

    def __init__(self, detail):
        self.detail = detail
        self.urls = []

    async def get_universal_data(self, url):
        self.urls.append(url)
        return {"webapp.video-detail": self.detail}


def page(item, status=TikTokStatus.OK, message=""):
    return {"statusCode": status, "statusMsg": message, "itemInfo": {"itemStruct": item}}


@pytest.mark.parametrize(
    "video",
    [
        "https://www.tiktok.com/@theestallion/video/7701398932127059213",
        "https://www.tiktok.com/@theestallion/video/7701398932127059213?lang=fr",
        "https://www.tiktok.com/@theestallion/photo/7701398932127059213",
        "7701398932127059213",
    ],
)
def test_get_tiktok(video_full, video):
    client = FakeClient(page(video_full))

    tiktok = asyncio.run(get_tiktok(client, video))

    assert tiktok.id == "7701398932127059213"
    assert tiktok.location.name == "Zouk Nightclub"
    # Always the /video/ page (it holds the data, slideshows included), whatever the username.
    assert client.urls == ["https://www.tiktok.com/@_/video/7701398932127059213"]


def test_get_tiktok_slideshow(slideshow_item):
    tiktok = asyncio.run(get_tiktok(FakeClient(page(slideshow_item)), slideshow_item["id"]))

    assert tiktok.is_slideshow
    assert tiktok.image_count == 5


@pytest.mark.parametrize(
    ("detail", "message"),
    [
        (page({}, TikTokStatus.ITEM_NOT_FOUND, "item doesn't exist"), "doesn't exist"),
        (page({}, TikTokStatus.PRIVATE_ITEM), "is private"),
        (page({}, TikTokStatus.PRIVATE_ACCOUNT), "private account"),
        (page({}, 10999, "something new"), r"status code 10999: something new"),
        ({}, "unavailable"),
    ],
)
def test_get_tiktok_unavailable(detail, message):
    with pytest.raises(TikTokError, match=message):
        asyncio.run(get_tiktok(FakeClient(detail), "7701398932127059213"))


def test_get_tiktok_invalid_url():
    with pytest.raises(ValueError, match="Unable to extract"):
        asyncio.run(get_tiktok(FakeClient({}), "https://www.tiktok.com/@theestallion"))
