import asyncio
import os

from rich.console import Console

from tiktok_scraper.downloader import download_video
from tiktok_scraper.progress import ProgressBars


class RecordingObserver:
    """Observer that records the calls made to it."""

    def __init__(self):
        self.events = []

    def queued(self):
        self.events.append(("queued",))

    def started(self, name, size):
        self.events.append(("started", name, size))

    def advanced(self, name, count):
        self.events.append(("advanced", name, count))

    def finished(self, name):
        self.events.append(("finished", name))


class FakeResponse:
    def __init__(self, chunks, status_code=200, content_type="video/mp4", content_length=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        if content_length is not None:
            self.headers["content-length"] = str(content_length)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_content(self):
        for chunk in self.chunks:
            yield chunk


class FakeSession:
    def __init__(self, response):
        self._response = response

    def stream(self, method, url, headers=None):
        return self._response


class FakeClient:
    def __init__(self, response):
        self.session = FakeSession(response)


def test_download_video_reports_progress(tmp_path):
    chunks = [b"aaaa", b"bbbbbb"]
    client = FakeClient(FakeResponse(chunks, content_length=10))
    observer = RecordingObserver()

    ok = asyncio.run(download_video(client, "https://cdn/x.mp4", "123.mp4", str(tmp_path), "ref", observer))

    assert ok is True
    assert os.path.getsize(tmp_path / "123.mp4") == 10
    assert observer.events == [
        ("started", "123.mp4", 10),
        ("advanced", "123.mp4", 4),
        ("advanced", "123.mp4", 6),
    ]


def test_download_video_rejected_reports_nothing(tmp_path):
    client = FakeClient(FakeResponse([b"x"], content_type="text/html"))
    observer = RecordingObserver()

    ok = asyncio.run(download_video(client, "https://cdn/x", "123.mp4", str(tmp_path), "ref", observer))

    assert ok is False
    assert observer.events == []
    assert not (tmp_path / "123.mp4").exists()


def test_progress_bars_track_totals():
    # A forced-terminal console so the bars are "usable" and render without a real TTY.
    bars = ProgressBars(console=Console(force_terminal=True))
    with bars:
        bars.queued()
        bars.queued()
        bars.started("a.mp4", 100)
        bars.advanced("a.mp4", 40)
        bars.finished("a.mp4")  # downloaded
        bars.finished("b.mp4")  # skipped, never started

    total = bars.total.tasks[bars._total_task]
    assert total.total == 2
    assert total.completed == 2
    assert bars._tasks == {}  # every file task removed when finished


def test_progress_bars_unusable_without_terminal():
    bars = ProgressBars(console=Console(force_terminal=False))
    assert bars.usable is False
