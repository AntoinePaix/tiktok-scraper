"""Signed requests to TikTok's web API, through a real (patched) Chromium browser.

Most TikTok API endpoints only answer requests signed by the obfuscated `webmssdk.js` script (`X-Bogus`,
`X-Gnarly`, ...). Instead of reproducing the signature, `TikTokBrowser` opens a TikTok page in Chromium and sends
the API requests from inside the page, where TikTok's own script signs them.

It uses patchright, a patched Playwright which removes the main automation leaks. Install it with
`pip install "tiktok-scraper[playwright]"`, then `patchright install chromium`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import tempfile
import urllib.parse
from typing import Any

from .client import TikTokError
from .constants import WEBPAGE_URL

try:
    from patchright.async_api import BrowserContext
    from patchright.async_api import Page
    from patchright.async_api import Playwright
    from patchright.async_api import async_playwright
except ImportError as error:  # pragma: no cover - depends on the installed extras
    raise ImportError(
        'TikTokBrowser needs the "playwright" extra: pip install "tiktok-scraper[playwright]", '
        "then run: patchright install chromium"
    ) from error

logger = logging.getLogger(__name__)

WARM_UP_URL = "https://www.tiktok.com/explore"
SIGNATURE_PARAMS = frozenset({"X-Bogus", "X-Gnarly", "X-Dynosaur", "msToken"})
# Query parameters the web app sends with every API request (endpoint-specific ones are left out).
COMMON_PARAMS = frozenset(
    {
        "WebIdLastTime",
        "aid",
        "app_language",
        "app_name",
        "browser_language",
        "browser_name",
        "browser_online",
        "browser_platform",
        "browser_version",
        "channel",
        "cookie_enabled",
        "data_collection_enabled",
        "device_id",
        "device_platform",
        "focus_state",
        "history_len",
        "is_fullscreen",
        "is_page_visible",
        "odinId",
        "os",
        "region",
        "screen_height",
        "screen_width",
        "tz_name",
        "user_is_login",
        "webcast_language",
    }
)
USER_AGENT_PLATFORMS = {
    "linux": "X11; Linux x86_64",
    "darwin": "Macintosh; Intel Mac OS X 10_15_7",
    "win32": "Windows NT 10.0; Win64; x64",
}
SCREEN_SIZE = {"width": 1920, "height": 1080}
# Headless windows have no browser UI: keep the viewport smaller than the screen, like a real window.
VIEWPORT_SIZE = {"width": 1920, "height": 993}

EMPTY_RESPONSE_RETRIES = 2
EMPTY_RESPONSE_RETRY_DELAY = 3

CAPTCHA_JS = """() => !!document.querySelector('[id*="captcha" i], [class*="captcha" i]')"""

REQUEST_JS = """
async (url) => {
    const response = await fetch(url, {credentials: "include"});
    return {status: response.status, text: await response.text()};
}
"""


def proxy_settings(proxy: str) -> dict[str, str]:
    """Convert a proxy URL (`scheme://user:password@host:port`) to Playwright proxy settings."""
    url = urllib.parse.urlsplit(proxy)
    settings = {"server": f"{url.scheme}://{url.hostname}" + (f":{url.port}" if url.port else "")}
    if url.username:
        settings["username"] = urllib.parse.unquote(url.username)
    if url.password:
        settings["password"] = urllib.parse.unquote(url.password)
    return settings


async def chromium_user_agent(executable_path: str) -> str:
    """User agent of a regular (not headless) Chrome with the same version as the given executable."""
    process = await asyncio.create_subprocess_exec(
        executable_path, "--version", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
    )
    stdout, _ = await process.communicate()
    match = re.search(r"(\d+)\.\d+\.\d+\.\d+", stdout.decode())
    if match is None:
        raise TikTokError(f"Unable to get the version of {executable_path}")
    platform = USER_AGENT_PLATFORMS.get(sys.platform, USER_AGENT_PLATFORMS["linux"])
    # Chrome only reports its major version in the user agent.
    chrome_version = f"{match.group(1)}.0.0.0"
    return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"


class TikTokBrowser:
    """Chromium browser sending signed requests to TikTok's web API. Use it as an async context manager.

    Args:
        headless (bool, optional): Hide the browser window. A visible window looks more like a real user.
        proxy (str, optional): Proxy URL, e.g. `http://user:password@host:8080` or `socks5://host:1080`.
        user_data_dir (str, optional): Browser profile directory, to keep cookies between runs.
            Defaults to a temporary profile.
        channel (str, optional): Browser to use: "chromium" (installed with `patchright install chromium`)
            or "chrome" (Google Chrome installed on the system, harder to detect).
        warm_up_url (str, optional): TikTok page opened at start, to get cookies and common API parameters.
        timeout (float, optional): Timeout of page loads, in seconds.
    """

    def __init__(
        self,
        headless: bool = True,
        proxy: str | None = None,
        user_data_dir: str | None = None,
        channel: str = "chromium",
        warm_up_url: str = WARM_UP_URL,
        timeout: float = 30,
    ) -> None:
        self.headless = headless
        self.proxy = proxy
        self.user_data_dir = user_data_dir
        self.channel = channel
        self.warm_up_url = warm_up_url
        self.timeout = timeout
        self.common_params: dict[str, str] = {}
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._temporary_directory: tempfile.TemporaryDirectory | None = None

    async def __aenter__(self) -> TikTokBrowser:
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def _context_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"headless": self.headless, "channel": self.channel}
        if self.proxy:
            options["proxy"] = proxy_settings(self.proxy)
        if self.headless:
            # Headless Chromium leaks "HeadlessChrome" in its user agent and reports an 800x600 screen.
            executable_path = self._playwright.chromium.executable_path if self.channel == "chromium" else None
            if executable_path:
                options["user_agent"] = await chromium_user_agent(executable_path)
            options["viewport"] = VIEWPORT_SIZE
            options["screen"] = SCREEN_SIZE
        else:
            # A visible window has real screen and window sizes: don't emulate any.
            options["no_viewport"] = True
        return options

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        try:
            user_data_dir = self.user_data_dir
            if user_data_dir is None:
                self._temporary_directory = tempfile.TemporaryDirectory(prefix="tiktok-scraper-")
                user_data_dir = self._temporary_directory.name
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir, **await self._context_options()
            )
            self._context.set_default_timeout(self.timeout * 1000)
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            await self._warm_up()
        except BaseException:
            await self.close()
            raise

    async def _warm_up(self) -> None:
        """Open a TikTok page and copy the common parameters of the first API request signed by the page."""

        def is_signed_api_request(request: Any) -> bool:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.url).query)
            return "/api/" in request.url and "X-Gnarly" in query and "device_id" in query

        async with self._page.expect_request(is_signed_api_request) as request_info:
            await self._page.goto(self.warm_up_url, wait_until="domcontentloaded")
        request = await request_info.value
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.url).query)
        self.common_params = {key: values[0] for key, values in query.items() if key in COMMON_PARAMS}
        logger.debug("Common API parameters: %s", self.common_params)
        await self._wait_for_ms_token()

    async def _wait_for_ms_token(self) -> None:
        """Wait for the `msToken` cookie: TikTok's script adds it to signed requests once it got one."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.timeout
        while loop.time() < deadline:
            if any(cookie["name"] == "msToken" for cookie in await self._context.cookies(WEBPAGE_URL)):
                return
            await asyncio.sleep(0.5)
        logger.warning("No msToken cookie after %s s: signed requests may get empty responses", self.timeout)

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None

    async def is_showing_captcha(self) -> bool:
        return await self._page.evaluate(CAPTCHA_JS, isolated_context=False)

    async def request_json(
        self, url: str, params: dict[str, Any], from_page: str = "video", retries: int = EMPTY_RESPONSE_RETRIES
    ) -> dict[str, Any]:
        """Send a GET request to a TikTok API endpoint from the page, signed by TikTok's own script.

        Args:
            url (str): API URL, e.g. `https://www.tiktok.com/api/comment/list/`.
            params (dict[str, Any]): Endpoint-specific query parameters (the common ones are added).
            from_page (str, optional): Kind of page the request is supposed to come from.
            retries (int, optional): Retries after an empty response (some endpoints only answer a few seconds
                after TikTok's script started).

        Returns:
            dict[str, Any]: JSON response.
        """
        if self._page is None:
            raise TikTokError("The browser is not started")
        query = {**self.common_params, "from_page": from_page, **{key: str(value) for key, value in params.items()}}
        query = {key: value for key, value in query.items() if key not in SIGNATURE_PARAMS}
        path = urllib.parse.urlsplit(urllib.parse.urljoin(WEBPAGE_URL, url)).path

        for attempt in range(retries + 1):
            response = await self._page.evaluate(
                REQUEST_JS, f"{path}?{urllib.parse.urlencode(query)}", isolated_context=False
            )
            if response["status"] != 200:
                raise TikTokError(f"HTTP {response['status']} from {path}")
            if response["text"]:
                return json.loads(response["text"])
            if await self.is_showing_captcha():
                raise TikTokError(
                    "TikTok is showing a CAPTCHA: this browser session was flagged. Wait before retrying, slow down, "
                    "or use another IP address"
                )
            if attempt < retries:
                logger.debug("Empty response from %s, retrying in %s s", path, EMPTY_RESPONSE_RETRY_DELAY)
                await asyncio.sleep(EMPTY_RESPONSE_RETRY_DELAY)
        raise TikTokError(f"Empty response from {path} (the endpoint refused the request)")
