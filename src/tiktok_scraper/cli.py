import argparse
import asyncio
import json
import logging
import sys

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


async def print_comments(proxy: str | None, timeout: float, video: str, with_replies: bool, headless: bool) -> None:
    try:
        from patchright.async_api import Error as PlaywrightError

        from .browser import TikTokBrowser
        from .comments import iter_comments
    except ImportError as error:
        raise TikTokError(
            'The comments command needs the "playwright" extra: pip install "tiktok-scraper[playwright]" '
            "(or uv sync --extra playwright), then run: patchright install chromium"
        ) from error

    counter = 0
    try:
        async with TikTokBrowser(headless=headless, proxy=proxy, timeout=timeout) as browser:
            async for comment in iter_comments(browser, video, with_replies=with_replies):
                print(json.dumps(comment.to_dict(), ensure_ascii=False), flush=True)
                counter += 1
    except PlaywrightError as error:
        if "Executable doesn't exist" in str(error):
            raise TikTokError("Chromium is not installed, run: patchright install chromium") from error
        raise TikTokError(f"Browser error: {error}") from error
    print(f"{counter} comments scraped.", file=sys.stderr)


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
            asyncio.run(print_comments(args.proxy, args.timeout, args.video, not args.no_replies, not args.headed))
    except (TikTokError, RequestException) as error:
        raise SystemExit(f"[!] {error}") from error
