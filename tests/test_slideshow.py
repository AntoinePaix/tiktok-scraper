import asyncio
import copy

from tiktok_scraper.downloader import DownloadReport
from tiktok_scraper.downloader import process_tiktok
from tiktok_scraper.models import TikTok

IMAGES = {
    "https://cdn.example/1a.jpeg": b"first image",
    "https://cdn.example/2a.jpeg": b"second image",
}
AUDIO = {"https://cdn.example/sound": b"soundtrack"}


class FakeResponse:
    def __init__(self, url):
        self.status_code = 200 if url in IMAGES or url in AUDIO else 404
        self.headers = {"content-type": "image/jpeg" if url in IMAGES else "audio/mp4"}
        self.body = IMAGES.get(url) or AUDIO.get(url) or b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_content(self):
        yield self.body


class FakeSession:
    def __init__(self):
        self.urls = []

    def stream(self, method, url, headers=None):
        self.urls.append(url)
        return FakeResponse(url)


class FakeClient:
    def __init__(self):
        self.session = FakeSession()


def slideshow(item):
    item = copy.deepcopy(item)
    item["imagePost"] = {
        "images": [
            # The first URL of the first image is dead: the second one must be used.
            {"imageURL": {"urlList": ["https://cdn.example/dead.jpeg", "https://cdn.example/1a.jpeg"]}},
            {"imageURL": {"urlList": ["https://cdn.example/2a.jpeg"]}},
        ],
    }
    item["music"] = {"playUrl": "https://cdn.example/sound"}
    return TikTok.from_api(item)


def run(client, tiktok, report):
    asyncio.run(process_tiktok(client, tiktok, report, asyncio.Semaphore(1)))


def test_slideshow_downloads_images_and_soundtrack(item, tmp_path):
    tiktok = slideshow(item)
    report = DownloadReport(directory=str(tmp_path))

    run(FakeClient(), tiktok, report)

    assert report.downloaded == [tiktok.id]
    assert report.slideshows == [tiktok.id]
    folder = tmp_path / tiktok.id
    assert sorted(path.name for path in folder.iterdir()) == ["1.jpg", "2.jpg", "music.m4a"]
    assert (folder / "1.jpg").read_bytes() == b"first image"
    assert (folder / "2.jpg").read_bytes() == b"second image"
    assert (folder / "music.m4a").read_bytes() == b"soundtrack"
    # Nothing left next to the videos.
    assert [path.name for path in tmp_path.iterdir()] == [tiktok.id]


def test_slideshow_already_downloaded(item, tmp_path):
    tiktok = slideshow(item)
    run(FakeClient(), tiktok, DownloadReport(directory=str(tmp_path)))

    client = FakeClient()
    report = DownloadReport(directory=str(tmp_path))
    run(client, tiktok, report)

    assert report.already_downloaded == [tiktok.id]
    assert client.session.urls == []
