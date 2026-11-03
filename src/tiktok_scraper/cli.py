import argparse
import asyncio
import json
import logging

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

    args = parser.parse_args()
    logging.basicConfig(format="%(message)s", level=logging.WARNING)
    logging.getLogger("tiktok_scraper").setLevel(logging.DEBUG if args.verbose else logging.INFO)

    client_options = {"proxy": args.proxy, "timeout": args.timeout}
    try:
        if args.command == "videos":
            asyncio.run(download_videos(client_options, args.user, args.output, args.jobs))
        elif args.command == "info":
            asyncio.run(print_user_metadata(client_options, args.user))
    except (TikTokError, RequestException) as error:
        raise SystemExit(f"[!] {error}") from error
