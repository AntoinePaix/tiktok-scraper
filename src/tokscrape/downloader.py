from __future__ import annotations

import asyncio
import dataclasses
import logging
import os

import aiofiles
import aiofiles.os

from tokscrape.client import TikTokClient
from tokscrape.constants import DOWNLOAD_DIRECTORY
from tokscrape.constants import MAX_CONCURRENT_DOWNLOADS
from tokscrape.constants import USER_URL_FORMAT
from tokscrape.models import TikTok
from tokscrape.post import get_tiktok
from tokscrape.progress import Observer
from tokscrape.user import get_user_info
from tokscrape.user import iter_user_tiktoks

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DownloadReport:
    """Ids of the tiktoks of a user, sorted by download outcome."""

    directory: str
    downloaded: list[str] = dataclasses.field(default_factory=list)
    already_downloaded: list[str] = dataclasses.field(default_factory=list)
    failed: list[str] = dataclasses.field(default_factory=list)
    # Subset of the ids above which are slideshows (images and a soundtrack, not a video).
    slideshows: list[str] = dataclasses.field(default_factory=list)


async def download_video(
    client: TikTokClient,
    url: str,
    filename: str,
    directory: str,
    referer: str,
    progress: Observer | None = None,
    content_type: str = "video/",
    progress_name: str | None = None,
) -> bool:
    """Function to download a file (video, slideshow image or soundtrack) from tiktok.

    Args:
        client (TikTokClient): Client holding the cookies of the video page.
        url (str): File url from tiktok website.
        filename (str): Name of the file to download.
        directory (str): Directory where to write the file.
        referer (str): Video page URL.
        progress (Observer, optional): Told when the download starts and advances.
        content_type (str, optional): Expected prefix of the response content type, e.g. "image/".
        progress_name (str, optional): Name shown by `progress`. Defaults to `filename`.

    Returns:
        bool: True if the file has been downloaded.
    """
    progress_name = progress_name or filename
    full_path_file = os.path.join(directory, filename)
    partial_path_file = f"{full_path_file}.part"
    try:
        async with client.session.stream("GET", url, headers={"Referer": referer}) as response:
            if response.status_code != 200 or not response.headers.get("content-type", "").startswith(content_type):
                logger.debug("Rejected %s (HTTP %s)", url, response.status_code)
                return False
            if progress:
                size = response.headers.get("content-length")
                progress.started(progress_name, int(size) if size else None)
            async with aiofiles.open(partial_path_file, mode="wb") as file:
                async for chunk in response.aiter_content():
                    await file.write(chunk)
                    if progress:
                        progress.advanced(progress_name, len(chunk))
    except Exception:
        logger.debug("Failed to download %s", url, exc_info=True)
        if await aiofiles.os.path.exists(partial_path_file):
            await aiofiles.os.remove(partial_path_file)
        return False

    await aiofiles.os.replace(partial_path_file, full_path_file)
    return True


async def get_tiktok_detail(client: TikTokClient, tiktok: TikTok) -> TikTok:
    """Fetch the video page of a tiktok, like yt-dlp does, to get fresh video URLs and their cookies."""
    try:
        return await get_tiktok(client, tiktok.id)
    except Exception as error:
        logger.warning("Unable to fetch %s: %s", tiktok.url, error)
        return tiktok


async def download_first(
    client: TikTokClient,
    urls: list[str],
    filename: str,
    directory: str,
    referer: str,
    progress: Observer | None,
    content_type: str,
    progress_name: str,
) -> bool:
    """Download a file from the first of `urls` that works."""
    for url in urls:
        if await download_video(client, url, filename, directory, referer, progress, content_type, progress_name):
            return True
    return False


def slideshow_files(tiktok: TikTok) -> list[str]:
    """Files of a complete slideshow download: every image, and the soundtrack if it has one."""
    return tiktok.image_filenames + ([tiktok.audio_filename] if tiktok.audio_url else [])


async def download_slideshow(
    client: TikTokClient,
    tiktok: TikTok,
    directory: str,
    progress: Observer | None,
    progress_name: str,
) -> bool:
    """Download the images of a slideshow, then its soundtrack.

    Returns:
        bool: True if every image has been downloaded (a missing soundtrack is only logged).
    """
    detailed_tiktok = None
    all_images = True
    for index, filename in enumerate(tiktok.image_filenames):
        if await aiofiles.os.path.exists(os.path.join(directory, filename)):
            continue
        args = (filename, directory, tiktok.url, progress, "image/", progress_name)
        if await download_first(client, tiktok.image_urls[index], *args):
            continue
        # The URLs of the listing may have expired: retry with fresh ones from the video page.
        detailed_tiktok = detailed_tiktok or await get_tiktok_detail(client, tiktok)
        fresh_urls = detailed_tiktok.image_urls[index] if index < len(detailed_tiktok.image_urls) else []
        if not await download_first(client, fresh_urls, *args):
            logger.warning("[!] Unable to download %s/%s", tiktok.id, filename)
            all_images = False

    audio_path = os.path.join(directory, tiktok.audio_filename)
    if tiktok.audio_url and not await aiofiles.os.path.exists(audio_path):
        args = (tiktok.audio_filename, directory, tiktok.url, progress, "audio/", progress_name)
        if not await download_first(client, [tiktok.audio_url], *args):
            logger.warning("[!] Unable to download the soundtrack of %s", tiktok.id)
    return all_images


async def process_tiktok(
    client: TikTokClient,
    tiktok: TikTok,
    report: DownloadReport,
    semaphore: asyncio.Semaphore,
    progress: Observer | None = None,
) -> None:
    progress_name = f"{tiktok.id} (slideshow)" if tiktok.is_slideshow else tiktok.video_filename
    async with semaphore:
        try:
            if tiktok.is_slideshow:
                report.slideshows.append(tiktok.id)
                # One folder per slideshow, named after its id: its images and its music.
                directory = os.path.join(report.directory, tiktok.id)
                files = [os.path.join(directory, filename) for filename in slideshow_files(tiktok)]
                if all([await aiofiles.os.path.exists(path) for path in files]):
                    logger.info("[=] %s already downloaded.", progress_name)
                    report.already_downloaded.append(tiktok.id)
                    return
                await aiofiles.os.makedirs(directory, exist_ok=True)
                if await download_slideshow(client, tiktok, directory, progress, progress_name):
                    logger.info("[+] Download %s: %s images", progress_name, len(tiktok.image_filenames))
                    report.downloaded.append(tiktok.id)
                else:
                    report.failed.append(tiktok.id)
                return

            if await aiofiles.os.path.exists(os.path.join(report.directory, tiktok.video_filename)):
                logger.info("[=] %s already downloaded.", tiktok.video_filename)
                report.already_downloaded.append(tiktok.id)
                return

            detailed_tiktok = await get_tiktok_detail(client, tiktok)
            for url in detailed_tiktok.video_urls:
                if await download_video(
                    client,
                    url,
                    tiktok.video_filename,
                    report.directory,
                    tiktok.url,
                    progress,
                ):
                    logger.info("[+] Download %s", tiktok.video_filename)
                    report.downloaded.append(tiktok.id)
                    return
            logger.warning("[!] Unable to download %s", tiktok.video_filename)
            report.failed.append(tiktok.id)
        finally:
            if progress:
                progress.finished(progress_name)


async def download_user_videos(
    username: str,
    output_directory: str = DOWNLOAD_DIRECTORY,
    max_concurrent_downloads: int = MAX_CONCURRENT_DOWNLOADS,
    client: TikTokClient | None = None,
    limit: int | None = None,
    progress: Observer | None = None,
) -> DownloadReport:
    """Main method to download the videos of a TikTok user.

    Args:
        username (str): Tiktok username to scrape.
        output_directory (str, optional): Root directory of the downloaded videos.
        max_concurrent_downloads (int, optional): Number of videos downloaded in parallel.
        client (TikTokClient, optional): Client to use (e.g. configured with a proxy). It is not closed afterwards.
            Defaults to a new client with default options.
        limit (int, optional): Only the `limit` last published tiktoks (already downloaded ones included).
            Defaults to all. Each slideshow is saved in its own folder named after its id: `<id>/1.jpg`,
            `<id>/2.jpg`... and its music as `<id>/music.m4a`.
        progress (Observer, optional): Told about each tiktok queued, started, advanced and finished, e.g. a
            `tokscrape.progress.ProgressBars` for a live progress bar.

    Returns:
        DownloadReport: Outcome of the download of each tiktok.
    """
    if client is None:
        async with TikTokClient() as client:
            return await download_user_videos(
                username,
                output_directory,
                max_concurrent_downloads,
                client,
                limit,
                progress,
            )

    user_info = await get_user_info(client, username)
    user = user_info["user"]
    report = DownloadReport(directory=os.path.join(output_directory, user["uniqueId"]))
    os.makedirs(report.directory, exist_ok=True)

    semaphore = asyncio.Semaphore(max_concurrent_downloads)
    referer = USER_URL_FORMAT.format(username=user["uniqueId"])
    async with asyncio.TaskGroup() as task_group:
        async for tiktok in iter_user_tiktoks(client, user["secUid"], referer, limit=limit):
            if progress:
                progress.queued()
            task_group.create_task(process_tiktok(client, tiktok, report, semaphore, progress))
    return report


async def download_tiktok(
    tiktok: TikTok,
    output_directory: str = DOWNLOAD_DIRECTORY,
    client: TikTokClient | None = None,
    progress: Observer | None = None,
) -> DownloadReport:
    """Download one tiktok into `output_directory/<user>/`, like `download_user_videos` does for each of a user's.

    A video is saved as `<id>.mp4`, a slideshow in a `<id>/` folder with its images and its music.

    Args:
        tiktok (TikTok): Tiktok to download, e.g. from `get_tiktok`.
        output_directory (str, optional): Root directory of the downloads.
        client (TikTokClient, optional): Client to use. It is not closed afterwards. Defaults to a new client.
        progress (Observer, optional): Told about the download, e.g. a `ProgressBars`.

    Returns:
        DownloadReport: Outcome of the download (`downloaded`, `already_downloaded` or `failed`).
    """
    if client is None:
        async with TikTokClient() as client:
            return await download_tiktok(tiktok, output_directory, client, progress)

    report = DownloadReport(directory=os.path.join(output_directory, tiktok.author_username or "_"))
    os.makedirs(report.directory, exist_ok=True)
    if progress:
        progress.queued()
    await process_tiktok(client, tiktok, report, asyncio.Semaphore(1), progress)
    return report
