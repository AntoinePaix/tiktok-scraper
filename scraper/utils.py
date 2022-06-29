import os

import aiofiles
import httpx


async def download_video(session: httpx.AsyncClient, download_addr_url: str, filename: str, username: str) -> None:
    """Function to download video from tiktok.

    Args:
        download_addr_url (str): Downloaded url link from tiktok website.
        filename (str): Name of the file to download the video.
        username (str): Unique id of the tiktok user.
    """

    full_directory_path = f"downloaded_videos/{username}"
    if not os.path.exists(full_directory_path):
        os.makedirs(full_directory_path)

    files = set(os.listdir(full_directory_path))

    if filename not in files:
        full_path_file = f"{full_directory_path}/{filename}"
        async with aiofiles.open(full_path_file, mode="wb") as file:
            response = await session.get(download_addr_url)
            async for chunk in response.aiter_bytes():
                await file.write(chunk)
            print(f"[+] Download {filename}")

    else:
        print(f"[=] {filename} already downloaded.")
