"""Scrape TikTok: download videos, get account metadata, comments, hashtag videos and keyword search results."""

from importlib.metadata import version

from .client import TikTokClient
from .client import TikTokError
from .comments import iter_comments
from .comments import iter_replies
from .downloader import DownloadReport
from .downloader import download_user_videos
from .hashtag import get_hashtag
from .hashtag import iter_hashtag_videos
from .models import Comment
from .models import Hashtag
from .models import SearchUser
from .models import TikTok
from .models import UserMetadata
from .search import iter_search_users
from .search import iter_search_videos
from .user import get_user_info
from .user import get_user_metadata
from .user import iter_user_tiktoks

__version__ = version("tiktok-scraper")

__all__ = [
    "Comment",
    "DownloadReport",
    "Hashtag",
    "SearchUser",
    "TikTok",
    "TikTokClient",
    "TikTokError",
    "UserMetadata",
    "download_user_videos",
    "get_hashtag",
    "get_user_info",
    "get_user_metadata",
    "iter_comments",
    "iter_hashtag_videos",
    "iter_replies",
    "iter_search_users",
    "iter_search_videos",
    "iter_user_tiktoks",
]
