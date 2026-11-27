import datetime
import json
import urllib.parse

import pydantic
import pytest

from tiktok_scraper import TikTok
from tiktok_scraper import UserMetadata


def test_tiktok_properties(item):
    tiktok = TikTok.from_api(item)

    assert tiktok.id == "7703703665818733857"
    assert tiktok.author_username == "emmanuelmacron"
    assert tiktok.url == "https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857"
    assert tiktok.video_filename == "7703703665818733857.mp4"
    assert not tiktok.is_slideshow


def test_video_urls_best_bitrate_first(item):
    urls = TikTok.from_api(item).video_urls
    best_bitrate = max(item["video"]["bitrateInfo"], key=lambda info: info["Bitrate"])

    assert urls[0] == best_bitrate["PlayAddr"]["UrlList"][0]
    assert item["video"]["playAddr"] in urls
    assert len(urls) == len(set(urls))


def test_video_urls_skip_broken_formats(item):
    # Unplayable codec and video-only format.
    item["video"]["bitrateInfo"].insert(
        0,
        {
            "Bitrate": 10**9,
            "PlayAddr": {"UrlKey": "x_bytevc2_1080p", "UrlList": ["https://cdn.example/a"]},  # gitleaks:allow
        },
    )
    item["video"]["bitrateInfo"].insert(
        0,
        {"Bitrate": 10**9, "PlayAddr": {"UrlKey": "x", "UrlList": ["https://cdn.example/media-video-hvc1/"]}},
    )
    urls = TikTok.from_api(item).video_urls

    assert "https://cdn.example/a" not in urls
    assert "https://cdn.example/media-video-hvc1/" not in urls
    assert all(urllib.parse.urlparse(url).hostname != "www.tiktok.com" for url in urls)


def test_slideshow(item):
    item["imagePost"] = {"images": []}
    assert TikTok.from_api(item).is_slideshow


def test_slideshow_files(item):
    item["imagePost"] = {
        "images": [
            {"imageURL": {"urlList": ["https://cdn.example/1a.jpeg", "https://cdn.example/1b.jpeg"]}},
            {"imageURL": {"urlList": ["https://cdn.example/2a.jpeg"]}},
        ],
    }
    item["music"] = {"playUrl": "https://cdn.example/sound"}
    tiktok = TikTok.from_api(item)

    assert tiktok.image_urls == [
        ["https://cdn.example/1a.jpeg", "https://cdn.example/1b.jpeg"],
        ["https://cdn.example/2a.jpeg"],
    ]
    assert tiktok.image_filenames == ["1.jpg", "2.jpg"]
    assert tiktok.audio_url == "https://cdn.example/sound"
    assert tiktok.audio_filename == "music.m4a"


def test_video_has_no_images(item):
    assert TikTok.from_api(item).image_urls == []
    assert TikTok.from_api(item).image_filenames == []


def test_user_metadata_prefers_exact_stats(user_info):
    metadata = UserMetadata.from_user_info(user_info)

    assert metadata.username == "emmanuelmacron"
    assert metadata.sec_uid.startswith("MS4wLjABAAAA")
    assert metadata.verified
    assert metadata.follower_count == 7710750
    assert metadata.heart_count == 93367785
    assert metadata.video_count == 454
    assert metadata.created_at == datetime.datetime(2020, 7, 6, 17, 52, 54, tzinfo=datetime.UTC)


def test_user_metadata_without_stats_v2(user_info):
    del user_info["statsV2"]
    metadata = UserMetadata.from_user_info(user_info)

    assert metadata.follower_count == 7700000
    assert metadata.bio_link is None


def test_user_metadata_to_dict(user_info):
    data = UserMetadata.from_user_info(user_info).to_dict()

    assert data["created_at"] == "2020-07-06T17:52:54Z"
    assert data["follower_count"] == 7710750


def test_tiktok_from_api_video(video_full):
    tiktok = TikTok.from_api(video_full)

    assert tiktok.url == "https://www.tiktok.com/@theestallion/video/7701398932127059213"
    assert tiktok.created_at == datetime.datetime(2026, 10, 27, 17, 21, 43, tzinfo=datetime.UTC)
    assert (tiktok.author_id, tiktok.author_verified) == ("6748929703376536581", True)
    assert (tiktok.duration, tiktok.width, tiktok.height) == (13, 720, 1280)
    assert tiktok.cover_url == video_full["video"]["cover"]
    assert tiktok.origin_cover_url == video_full["video"]["originCover"]
    assert tiktok.dynamic_cover_url == video_full["video"]["dynamicCover"]
    assert tiktok.hashtags == ["hottieween"]
    assert tiktok.mentions == ["uncle.waffles"]
    assert tiktok.location.name == "Zouk Nightclub"
    assert tiktok.location.city == "Las Vegas"
    assert tiktok.language == "en"
    assert (tiktok.duet_enabled, tiktok.stitch_enabled, tiktok.is_ad) == (True, True, False)
    # statsV2 sends the counts as strings: they are validated as integers.
    assert video_full["statsV2"]["playCount"] == "3300000"
    assert tiktok.play_count == 3_300_000
    assert tiktok.repost_count == 0
    assert tiktok.music.is_original
    assert tiktok.audio_url == video_full["music"]["playUrl"]
    assert tiktok.raw is video_full


def test_tiktok_from_api_slideshow(slideshow_item):
    tiktok = TikTok.from_api(slideshow_item)

    assert tiktok.is_slideshow
    assert tiktok.image_count == 5
    # The video object of a slideshow has a duration, width and height of 0.
    assert (tiktok.duration, tiktok.width, tiktok.height) == (None, None, None)
    assert tiktok.music.title == "Thin Ice"
    assert tiktok.music.album == "Tina Tuesday Freestyles"
    assert tiktok.mentions == ["cirquedusoleil"]
    assert tiktok.location is None


def test_hashtags_from_text_extra_and_challenges(item):
    item["textExtra"] = [{"type": 1, "hashtagName": "news"}, {"type": 0, "userUniqueId": "someone"}]
    item["challenges"] = [{"id": "1", "title": "news"}, {"id": "2", "title": "ukraine"}]

    tiktok = TikTok.from_api(item)

    assert tiktok.hashtags == ["news", "ukraine"]
    assert tiktok.mentions == ["someone"]


def test_tiktok_to_dict_is_json_ready(video_full):
    data = TikTok.from_api(video_full).to_dict()

    assert data["created_at"] == "2026-10-27T17:21:43Z"
    assert data["location"]["name"] == "Zouk Nightclub"
    assert data["music"]["title"] == "original sound"
    json.dumps(data)


def test_invalid_count_is_rejected(item):
    item["statsV2"] = {"playCount": "a lot"}

    with pytest.raises(pydantic.ValidationError, match="play_count"):
        TikTok.from_api(item)
