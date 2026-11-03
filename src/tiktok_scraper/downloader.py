from __future__ import annotations

import asyncio
import dataclasses
import logging
import os

import aiofiles

from .client import TikTokClient
from .constants import DOWNLOAD_DIRECTORY
from .constants import MAX_CONCURRENT_DOWNLOADS
from .constants import USER_URL_FORMAT
from .models import TikTok
from .user import get_user_info
from .user import iter_user_tiktoks

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DownloadReport:
    """Ids of the tiktoks of a user, sorted by download outcome."""

    directory: str
    downloaded: list[str] = dataclasses.field(default_factory=list)
    already_downloaded: list[str] = dataclasses.field(default_factory=list)
    skipped_slideshows: list[str] = dataclasses.field(default_factory=list)
    failed: list[str] = dataclasses.field(default_factory=list)


async def download_video(client: TikTokClient, url: str, filename: str, directory: str, referer: str) -> bool:
    """Function to download video from tiktok.

    Args:
        client (TikTokClient): Client holding the cookies of the video page.
        url (str): Video url from tiktok website.
        filename (str): Name of the file to download the video.
        directory (str): Directory where to write the video.
        referer (str): Video page URL.

    Returns:
        bool: True if the video has been downloaded.
    """
    full_path_file = os.path.join(directory, filename)
    partial_path_file = f"{full_path_file}.part"
    try:
        async with client.session.stream("GET", url, headers={"Referer": referer}) as response:
            if response.status_code != 200 or not response.headers.get("content-type", "").startswith("video/"):
                logger.debug("Rejected %s (HTTP %s)", url, response.status_code)
                return False
            async with aiofiles.open(partial_path_file, mode="wb") as file:
                async for chunk in response.aiter_content():
                    await file.write(chunk)
    except Exception:
        logger.debug("Failed to download %s", url, exc_info=True)
        if os.path.exists(partial_path_file):
            os.remove(partial_path_file)
        return False

    os.replace(partial_path_file, full_path_file)
    return True


async def get_tiktok_detail(client: TikTokClient, tiktok: TikTok) -> TikTok:
    """Fetch the video page of a tiktok, like yt-dlp does, to get fresh video URLs and their cookies."""
    try:
        universal_data = await client.get_universal_data(tiktok.webpage_url)
    except Exception as error:
        logger.warning("Unable to fetch %s: %s", tiktok.webpage_url, error)
        return tiktok
    item = (universal_data.get("webapp.video-detail") or {}).get("itemInfo", {}).get("itemStruct")
    return TikTok(item) if item and item.get("video") else tiktok


async def process_tiktok(
    client: TikTokClient, tiktok: TikTok, report: DownloadReport, semaphore: asyncio.Semaphore
) -> None:
    async with semaphore:
        if tiktok.is_slideshow:
            logger.info("[-] %s is a slideshow, skipped.", tiktok.id)
            report.skipped_slideshows.append(tiktok.id)
            return
        if os.path.exists(os.path.join(report.directory, tiktok.video_filename)):
            logger.info("[=] %s already downloaded.", tiktok.video_filename)
            report.already_downloaded.append(tiktok.id)
            return

        detailed_tiktok = await get_tiktok_detail(client, tiktok)
        for url in detailed_tiktok.video_urls:
            if await download_video(client, url, tiktok.video_filename, report.directory, referer=tiktok.webpage_url):
                logger.info("[+] Download %s", tiktok.video_filename)
                report.downloaded.append(tiktok.id)
                return
        logger.warning("[!] Unable to download %s", tiktok.video_filename)
        report.failed.append(tiktok.id)


async def download_user_videos(
    username: str,
    output_directory: str = DOWNLOAD_DIRECTORY,
    max_concurrent_downloads: int = MAX_CONCURRENT_DOWNLOADS,
    client: TikTokClient | None = None,
) -> DownloadReport:
    """Main method to download all videos of a TikTok user.

    Args:
        username (str): Tiktok username to scrape.
        output_directory (str, optional): Root directory of the downloaded videos.
        max_concurrent_downloads (int, optional): Number of videos downloaded in parallel.
        client (TikTokClient, optional): Client to use (e.g. configured with a proxy). It is not closed afterwards.
            Defaults to a new client with default options.

    Returns:
        DownloadReport: Outcome of the download of each tiktok.
    """
    if client is None:
        async with TikTokClient() as client:
            return await download_user_videos(username, output_directory, max_concurrent_downloads, client)

    user_info = await get_user_info(client, username)
    user = user_info["user"]
    report = DownloadReport(directory=os.path.join(output_directory, user["uniqueId"]))
    os.makedirs(report.directory, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent_downloads)
    referer = USER_URL_FORMAT.format(username=user["uniqueId"])
    async with asyncio.TaskGroup() as task_group:
        async for tiktok in iter_user_tiktoks(client, user["secUid"], referer):
            task_group.create_task(process_tiktok(client, tiktok, report, semaphore))
    return report
