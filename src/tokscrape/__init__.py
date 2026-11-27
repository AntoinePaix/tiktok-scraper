"""Scrape TikTok: download videos, get account metadata, comments, hashtag videos and keyword search results."""

from importlib.metadata import version

from tokscrape.client import TikTokClient
from tokscrape.client import TikTokError
from tokscrape.comments import iter_comments
from tokscrape.comments import iter_replies
from tokscrape.downloader import DownloadReport
from tokscrape.downloader import download_tiktok
from tokscrape.downloader import download_user_videos
from tokscrape.hashtag import get_hashtag
from tokscrape.hashtag import iter_hashtag_videos
from tokscrape.models import Comment
from tokscrape.models import Hashtag
from tokscrape.models import Location
from tokscrape.models import Music
from tokscrape.models import SearchUser
from tokscrape.models import TikTok
from tokscrape.models import UserMetadata
from tokscrape.post import get_tiktok
from tokscrape.search import iter_search_music
from tokscrape.search import iter_search_photos
from tokscrape.search import iter_search_users
from tokscrape.search import iter_search_videos
from tokscrape.user import get_user_info
from tokscrape.user import get_user_metadata
from tokscrape.user import iter_user_tiktoks

__version__ = version("tokscrape")

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
