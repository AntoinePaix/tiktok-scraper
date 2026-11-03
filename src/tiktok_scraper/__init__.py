"""Scrape TikTok accounts: download videos, get account metadata and comments."""

from importlib.metadata import version

from .client import TikTokClient
from .client import TikTokError
from .comments import iter_comments
from .comments import iter_replies
from .downloader import DownloadReport
from .downloader import download_user_videos
from .models import Comment
from .models import TikTok
from .models import UserMetadata
from .user import get_user_info
from .user import get_user_metadata
from .user import iter_user_tiktoks

__version__ = version("tiktok-scraper")

__all__ = [
    "Comment",
    "DownloadReport",
    "TikTok",
    "TikTokClient",
    "TikTokError",
    "UserMetadata",
    "download_user_videos",
    "get_user_info",
    "get_user_metadata",
    "iter_comments",
    "iter_replies",
    "iter_user_tiktoks",
]
