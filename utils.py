import os
import threading
from typing import Tuple
from urllib.parse import urlparse

import requests
from colorama import Fore, Style


def generate_location(media_url: str, download_directory: str, extension: str=".mp4") -> Tuple[str, str]:
    video_filename = f"{urlparse(media_url).path.split('/')[-2]}{extension}"
    full_path = os.path.join(download_directory, video_filename)
    return (full_path, video_filename)

def download_media_url(media_url: str, download_directory: str) -> None:
    r = requests.get(media_url, stream=True)
    full_path, video_filename = generate_location(media_url, download_directory)

    files = set(os.listdir(download_directory))
    if video_filename in files:
        print(f"{Fore.CYAN}[=] Filename {video_filename} already downloaded{Style.RESET_ALL}")
    else:
        with open(full_path, 'wb') as f:
            print(f"{Fore.GREEN}[+] Downloading {full_path}{Style.RESET_ALL}")
            for chunk in r.iter_content(1024):
                if chunk:
                    f.write(chunk)

def download_video_background(media_url: str, download_directory: str) -> None:
    thread = threading.Thread(target=download_media_url, name="Video Downloader", args=(media_url, download_directory))
    thread.start()

def extract_tiktok_id_from_url(url:  str) -> str:
    path = urlparse(url).path
    post_id = path.split("/")[-1]
    return post_id
