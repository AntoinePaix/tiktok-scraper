import datetime
import urllib.parse

from tiktok_scraper import TikTok
from tiktok_scraper import UserMetadata


def test_tiktok_properties(item):
    tiktok = TikTok(item)

    assert tiktok.id == "7703703665818733857"
    assert tiktok.unique_id == "emmanuelmacron"
    assert tiktok.webpage_url == "https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857"
    assert tiktok.video_filename == "7703703665818733857.mp4"
    assert not tiktok.is_slideshow


def test_video_urls_best_bitrate_first(item):
    urls = TikTok(item).video_urls
    best_bitrate = max(item["video"]["bitrateInfo"], key=lambda info: info["Bitrate"])

    assert urls[0] == best_bitrate["PlayAddr"]["UrlList"][0]
    assert item["video"]["playAddr"] in urls
    assert len(urls) == len(set(urls))


def test_video_urls_skip_broken_formats(item):
    # Unplayable codec and video-only format.
    item["video"]["bitrateInfo"].insert(
        0, {"Bitrate": 10**9, "PlayAddr": {"UrlKey": "x_bytevc2_1080p", "UrlList": ["https://cdn.example/a"]}}
    )
    item["video"]["bitrateInfo"].insert(
        0, {"Bitrate": 10**9, "PlayAddr": {"UrlKey": "x", "UrlList": ["https://cdn.example/media-video-hvc1/"]}}
    )
    urls = TikTok(item).video_urls

    assert "https://cdn.example/a" not in urls
    assert "https://cdn.example/media-video-hvc1/" not in urls
    assert all(urllib.parse.urlparse(url).hostname != "www.tiktok.com" for url in urls)


def test_slideshow(item):
    item["imagePost"] = {"images": []}
    assert TikTok(item).is_slideshow


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

    assert data["created_at"] == "2020-07-06T17:52:54+00:00"
    assert data["follower_count"] == 7710750
