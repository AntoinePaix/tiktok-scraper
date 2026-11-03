import argparse
import asyncio
import json
import logging
import sys
from functools import partial
from typing import Callable

from curl_cffi.requests.exceptions import RequestException

from .client import TikTokClient
from .client import TikTokError
from .constants import DOWNLOAD_DIRECTORY
from .constants import MAX_CONCURRENT_DOWNLOADS
from .downloader import download_user_videos
from .user import get_user_metadata


async def print_user_metadata(client_options: dict, username: str) -> None:
    async with TikTokClient(**client_options) as client:
        metadata = await get_user_metadata(client, username)
    print(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False))


async def download_videos(
    client_options: dict, username: str, output_directory: str, max_concurrent_downloads: int
) -> None:
    async with TikTokClient(**client_options) as client:
        report = await download_user_videos(username, output_directory, max_concurrent_downloads, client)
    print(
        f"Done in {report.directory}: {len(report.downloaded)} downloaded, "
        f"{len(report.already_downloaded)} already downloaded, "
        f"{len(report.skipped_slideshows)} slideshows skipped, {len(report.failed)} failed."
    )


async def print_browser_results(browser_options: dict, iterate: Callable, label: str) -> None:
    """Start a `TikTokBrowser`, then print the results of `iterate(browser)` as JSON lines."""
    try:
        from patchright.async_api import Error as PlaywrightError

        from .browser import TikTokBrowser
    except ImportError as error:
        raise TikTokError(
            'This command needs the "playwright" extra: pip install "tiktok-scraper[playwright]" '
            "(or uv sync --extra playwright), then run: patchright install chromium"
        ) from error

    counter = 0
    try:
        async with TikTokBrowser(**browser_options) as browser:
            async for result in iterate(browser):
                print(json.dumps(result.to_dict(), ensure_ascii=False), flush=True)
                counter += 1
    except PlaywrightError as error:
        if "Executable doesn't exist" in str(error):
            raise TikTokError("Chromium is not installed, run: patchright install chromium") from error
        raise TikTokError(f"Browser error: {error}") from error
    print(f"{counter} {label} scraped.", file=sys.stderr)


async def iter_hashtag_videos_with_info(browser, name: str, limit: int):
    from .hashtag import get_hashtag
    from .hashtag import iter_hashtag_videos

    hashtag = await get_hashtag(browser, name)
    print(
        f"#{hashtag.name} (id {hashtag.id}): {hashtag.video_count} videos, {hashtag.view_count} views", file=sys.stderr
    )
    async for tiktok in iter_hashtag_videos(browser, hashtag, limit=limit):
        yield tiktok


def main() -> None:
    parser = argparse.ArgumentParser(prog="tiktok-scraper")
    parser.add_argument("-v", "--verbose", help="Show debug logs", action="store_true")
    parser.add_argument("--proxy", help="Proxy URL, e.g. http://user:password@host:8080 or socks5h://host:1080")
    parser.add_argument("--timeout", help="Timeout of each request, in seconds", type=float, default=30)
    subparsers = parser.add_subparsers(dest="command", required=True)

    videos_parser = subparsers.add_parser("videos", help="Download all videos of a user")
    videos_parser.add_argument("user", help="Tiktok User Name", type=str)
    videos_parser.add_argument("-o", "--output", help="Output directory", default=DOWNLOAD_DIRECTORY)
    videos_parser.add_argument(
        "-j", "--jobs", help="Number of parallel downloads", type=int, default=MAX_CONCURRENT_DOWNLOADS
    )

    info_parser = subparsers.add_parser("info", help="Print metadata of a user account as JSON")
    info_parser.add_argument("user", help="Tiktok User Name", type=str)

    comments_parser = subparsers.add_parser(
        "comments", help='Print comments of a tiktok as JSON lines (needs the "playwright" extra)'
    )
    comments_parser.add_argument("video", help="Tiktok video URL or id", type=str)
    comments_parser.add_argument("--no-replies", help="Skip replies to comments", action="store_true")
    comments_parser.add_argument("--headed", help="Show the browser window", action="store_true")

    search_parser = subparsers.add_parser(
        "search", help='Search tiktoks (or accounts) by keyword, as JSON lines (needs the "playwright" extra)'
    )
    search_parser.add_argument("keyword", help="Searched keyword, e.g. ukraine", type=str)
    search_parser.add_argument("--users", help="Search accounts instead of tiktoks", action="store_true")
    search_parser.add_argument("-n", "--limit", help="Maximum number of results (default: 50)", type=int, default=50)
    search_parser.add_argument("--headed", help="Show the browser window", action="store_true")

    hashtag_parser = subparsers.add_parser(
        "hashtag", help='List tiktoks of a hashtag, as JSON lines (needs the "playwright" extra)'
    )
    hashtag_parser.add_argument("name", help="Hashtag name, e.g. ukraine", type=str)
    hashtag_parser.add_argument("-n", "--limit", help="Maximum number of results (default: 50)", type=int, default=50)
    hashtag_parser.add_argument(
        "--headless",
        help="Hide the browser window (TikTok often refuses hashtag videos to a headless browser)",
        action="store_true",
    )

    args = parser.parse_args()
    logging.basicConfig(format="%(message)s", level=logging.WARNING)
    logging.getLogger("tiktok_scraper").setLevel(logging.DEBUG if args.verbose else logging.INFO)

    client_options = {"proxy": args.proxy, "timeout": args.timeout}
    try:
        if args.command == "videos":
            asyncio.run(download_videos(client_options, args.user, args.output, args.jobs))
        elif args.command == "info":
            asyncio.run(print_user_metadata(client_options, args.user))
        elif args.command == "comments":
            from .comments import iter_comments

            browser_options = {"proxy": args.proxy, "timeout": args.timeout, "headless": not args.headed}
            iterate = partial(iter_comments, video=args.video, with_replies=not args.no_replies)
            asyncio.run(print_browser_results(browser_options, iterate, "comments"))
        elif args.command == "search":
            from .search import iter_search_users
            from .search import iter_search_videos

            browser_options = {"proxy": args.proxy, "timeout": args.timeout, "headless": not args.headed}
            search = iter_search_users if args.users else iter_search_videos
            iterate = partial(search, keyword=args.keyword, limit=args.limit)
            asyncio.run(print_browser_results(browser_options, iterate, "accounts" if args.users else "tiktoks"))
        elif args.command == "hashtag":
            # A visible window by default: TikTok often refuses hashtag videos to a headless browser.
            browser_options = {"proxy": args.proxy, "timeout": args.timeout, "headless": args.headless}
            iterate = partial(iter_hashtag_videos_with_info, name=args.name, limit=args.limit)
            asyncio.run(print_browser_results(browser_options, iterate, "tiktoks"))
    except (TikTokError, RequestException) as error:
        raise SystemExit(f"[!] {error}") from error
