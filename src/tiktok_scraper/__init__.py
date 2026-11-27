"""Scrape TikTok: download videos, get account metadata, comments, hashtag videos and keyword search results."""

from importlib.metadata import version

from tiktok_scraper.client import TikTokClient
from tiktok_scraper.client import TikTokError
from tiktok_scraper.comments import iter_comments
from tiktok_scraper.comments import iter_replies
from tiktok_scraper.downloader import DownloadReport
from tiktok_scraper.downloader import download_tiktok
from tiktok_scraper.downloader import download_user_videos
from tiktok_scraper.hashtag import get_hashtag
from tiktok_scraper.hashtag import iter_hashtag_videos
from tiktok_scraper.models import Comment
from tiktok_scraper.models import Hashtag
from tiktok_scraper.models import Location
from tiktok_scraper.models import Music
from tiktok_scraper.models import SearchUser
from tiktok_scraper.models import TikTok
from tiktok_scraper.models import UserMetadata
from tiktok_scraper.post import get_tiktok
from tiktok_scraper.search import iter_search_music
from tiktok_scraper.search import iter_search_photos
from tiktok_scraper.search import iter_search_users
from tiktok_scraper.search import iter_search_videos
from tiktok_scraper.user import get_user_info
from tiktok_scraper.user import get_user_metadata
from tiktok_scraper.user import iter_user_tiktoks

__version__ = version("tiktok-scraper")

__all__ = [
    "Comment",
    "DownloadReport",
    "Hashtag",
    "Location",
    "Music",
    "SearchUser",
    "TikTok",
    "TikTokClient",
    "TikTokError",
    "UserMetadata",
    "download_tiktok",
    "download_user_videos",
    "get_hashtag",
    "get_tiktok",
    "get_user_info",
    "get_user_metadata",
    "iter_comments",
    "iter_hashtag_videos",
    "iter_replies",
    "iter_search_music",
    "iter_search_photos",
    "iter_search_users",
    "iter_search_videos",
    "iter_user_tiktoks",
]
