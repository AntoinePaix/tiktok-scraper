import asyncio
import urllib.parse

import pytest

pytest.importorskip("patchright")

from tiktok_scraper import TikTokError  # noqa: E402
from tiktok_scraper import browser as browser_module  # noqa: E402
from tiktok_scraper.browser import proxy_settings  # noqa: E402


@pytest.mark.parametrize(
    ("proxy", "expected"),
    [
        ("http://host:8080", {"server": "http://host:8080"}),
        ("socks5://127.0.0.1:1080", {"server": "socks5://127.0.0.1:1080"}),
        (
            "http://user:p%40ss@host:8080",
            {"server": "http://host:8080", "username": "user", "password": "p@ss"},
        ),
    ],
)
def test_proxy_settings(proxy, expected):
    assert proxy_settings(proxy) == expected


class FakePage:
    """Stand-in for a Playwright page: answers `evaluate` with canned API responses."""

    def __init__(self, responses, captcha=False):
        self.responses = list(responses)
        self.captcha = captcha
        self.urls = []

    async def evaluate(self, script, arg=None, isolated_context=True):
        if script == browser_module.CAPTCHA_JS:
            return self.captcha
        self.urls.append(arg)
        return self.responses.pop(0)


@pytest.fixture
def browser(monkeypatch):
    monkeypatch.setattr(browser_module, "EMPTY_RESPONSE_RETRY_DELAY", 0)
    browser = browser_module.TikTokBrowser()
    browser.common_params = {"aid": "1988", "device_id": "123"}
    return browser


def test_request_json_adds_common_params(browser):
    browser._page = FakePage([{"status": 200, "text": '{"ok": 1}'}])

    data = asyncio.run(browser.request_json("https://www.tiktok.com/api/x/", {"msToken": "old", "count": 5}))

    assert data == {"ok": 1}
    path, query = browser._page.urls[0].split("?")
    assert path == "/api/x/"
    # Common params added, signature params left to TikTok's script.
    expected = {"aid": ["1988"], "device_id": ["123"], "from_page": ["video"], "count": ["5"]}
    assert urllib.parse.parse_qs(query) == expected


def test_request_json_retries_empty_responses(browser):
    browser._page = FakePage([{"status": 200, "text": ""}, {"status": 200, "text": '{"ok": 1}'}])

    assert asyncio.run(browser.request_json("/api/x/", {})) == {"ok": 1}


def test_request_json_gives_up_after_retries(browser):
    browser._page = FakePage([{"status": 200, "text": ""}] * 3)

    with pytest.raises(TikTokError, match="Empty response"):
        asyncio.run(browser.request_json("/api/x/", {}))
    assert len(browser._page.urls) == 3


def test_request_json_detects_captcha(browser):
    browser._page = FakePage([{"status": 200, "text": ""}], captcha=True)

    with pytest.raises(TikTokError, match="CAPTCHA"):
        asyncio.run(browser.request_json("/api/x/", {}))
    assert len(browser._page.urls) == 1
