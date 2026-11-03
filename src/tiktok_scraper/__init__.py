"""Scrape TikTok accounts: download videos and get account metadata."""

from importlib.metadata import version

from .client import TikTokClient
from .client import TikTokError
from .downloader import DownloadReport
from .downloader import download_user_videos
from .models import TikTok
from .models import UserMetadata
from .user import get_user_info
from .user import get_user_metadata
from .user import iter_user_tiktoks

__version__ = version("tiktok-scraper")

__all__ = [
    "DownloadReport",
    "TikTok",
    "TikTokClient",
    "TikTokError",
    "UserMetadata",
    "download_user_videos",
    "get_user_info",
    "get_user_metadata",
    "iter_user_tiktoks",
]
