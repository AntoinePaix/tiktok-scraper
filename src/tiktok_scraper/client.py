"""HTTP client mimicking the way yt-dlp talks to TikTok (see `yt_dlp/extractor/tiktok.py`)."""

from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import string
from typing import Any

from curl_cffi.requests import AsyncSession

from .constants import IMPERSONATE_TARGET
from .constants import UNIVERSAL_DATA_SCRIPT_ID
from .constants import WEBPAGE_URL


class TikTokError(Exception):
    pass


def generate_device_id() -> str:
    return str(random.randint(7250000000000000000, 7325099899999994577))


def generate_blockbuster_headers(min_headers: int = 2, max_headers: int = 8) -> dict[str, str]:
    """Randomize the HTTP header fingerprint to bust HTTP 403 blockage (same trick as yt-dlp)."""

    def random_letters(minimum: int, maximum: int) -> str:
        # Omit vowels so we don't generate valid header names like 'authorization', etc.
        return "".join(random.choices("bcdfghjklmnpqrstvwxz", k=random.randint(minimum, maximum)))

    return {random_letters(8, 24): random_letters(16, 32) for _ in range(random.randint(min_headers, max_headers))}


def _attribute_of_element(html: str, element_id: str, attribute: str = "class") -> str | None:
    tag = re.search(rf'<[^>]+\bid=["\']{re.escape(element_id)}["\'][^>]*>', html)
    if tag is None:
        return None
    value = re.search(rf'\b{attribute}=["\']([^"\']*)["\']', tag.group(0))
    return value.group(1) if value else None


def extract_universal_data(webpage: str) -> dict[str, Any]:
    match = re.search(rf'<script[^>]+\bid="{UNIVERSAL_DATA_SCRIPT_ID}"[^>]*>(.*?)</script>', webpage, re.DOTALL)
    if match is None:
        return {}
    try:
        return json.loads(match.group(1)).get("__DEFAULT_SCOPE__") or {}
    except json.JSONDecodeError:
        return {}


class TikTokClient:
    """Async TikTok web client. Use it as an async context manager to share cookies between requests.

    Args:
        proxy (str, optional): Proxy URL for every request, e.g. `http://user:password@host:8080` or
            `socks5h://host:1080` (use `http://` for an HTTP proxy, even for https sites). Without it, libcurl
            uses the `https_proxy`, `all_proxy` and `no_proxy` environment variables.
        cookies (dict[str, str], optional): Extra cookies for `.tiktok.com`, e.g. `{"sessionid": "..."}` to be
            logged in.
        impersonate (str, optional): Browser fingerprint impersonated by curl_cffi, e.g. "chrome" or "safari".
        timeout (float, optional): Timeout of each request, in seconds.
        **session_options: Any other `curl_cffi.requests.AsyncSession` option (`retry`, `verify`, `interface`...).
    """

    def __init__(
        self,
        proxy: str | None = None,
        cookies: dict[str, str] | None = None,
        impersonate: str = IMPERSONATE_TARGET,
        timeout: float = 30,
        **session_options: Any,
    ) -> None:
        self.session = AsyncSession(proxy=proxy, impersonate=impersonate, timeout=timeout, **session_options)
        for name, value in (cookies or {}).items():
            self.session.cookies.set(name, value, domain=".tiktok.com")
        self.device_id = generate_device_id()

    async def __aenter__(self) -> TikTokClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    def reset_device_id(self) -> None:
        self.device_id = generate_device_id()

    def build_web_query(self, from_page: str = "user", **extra: Any) -> dict[str, str]:
        """Query parameters sent by the TikTok web app (copied from yt-dlp's `TikTokUserIE`)."""
        query = {
            "aid": "1988",
            "app_language": "en",
            "app_name": "tiktok_web",
            "browser_language": "en-US",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": "5.0 (Windows)",
            "channel": "tiktok_web",
            "cookie_enabled": "true",
            "device_id": self.device_id,
            "device_platform": "web_pc",
            "focus_state": "true",
            "from_page": from_page,
            "history_len": "2",
            "is_fullscreen": "false",
            "is_page_visible": "true",
            "language": "en",
            "os": "windows",
            "priority_region": "",
            "referer": "",
            "region": "US",
            "screen_height": "1080",
            "screen_width": "1920",
            "tz_name": "UTC",
            "verifyFp": f"verify_{''.join(random.choices(string.hexdigits, k=7))}",
            "webcast_language": "en",
        }
        ms_tokens = [cookie.value for cookie in self.session.cookies.jar if cookie.name == "msToken"]
        if ms_tokens:
            query["msToken"] = ms_tokens[-1]
        query.update({key: str(value) for key, value in extra.items()})
        return query

    def _solve_challenge_and_set_cookies(self, webpage: str) -> list[str]:
        """Solve TikTok's proof-of-work JS challenge (port of yt-dlp's native implementation)."""
        encoded_challenge = _attribute_of_element(webpage, "cs")
        if not encoded_challenge:
            if "Please wait..." in webpage:
                raise TikTokError("Unable to extract challenge data")
            raise TikTokError("Unexpected response from webpage request")

        challenge = json.loads(base64.b64decode(f"{encoded_challenge}==="))
        expected_digest = base64.b64decode(challenge["v"]["c"])
        base_hash = hashlib.sha256(base64.b64decode(challenge["v"]["a"]))

        for i in range(1_000_001):
            test_hash = base_hash.copy()
            test_hash.update(str(i).encode())
            if test_hash.digest() == expected_digest:
                challenge["d"] = base64.b64encode(str(i).encode()).decode()
                break
        else:
            raise TikTokError("Unable to solve JS challenge")

        cookie_names = []
        wci_cookie_name = _attribute_of_element(webpage, "wci")
        if not wci_cookie_name:
            raise TikTokError("Unable to extract challenge cookie name")
        wci_cookie_value = base64.b64encode(json.dumps(challenge, separators=(",", ":")).encode()).decode()
        self.session.cookies.set(wci_cookie_name, wci_cookie_value, domain=".tiktok.com")
        cookie_names.append(wci_cookie_name)

        rci_cookie_name = _attribute_of_element(webpage, "rci")
        rci_cookie_value = _attribute_of_element(webpage, "rs")
        if rci_cookie_name and rci_cookie_value:
            self.session.cookies.set(rci_cookie_name, rci_cookie_value, domain=".tiktok.com")
            cookie_names.append(rci_cookie_name)

        return cookie_names

    async def get_webpage(self, url: str) -> str:
        response = await self.session.get(url, headers=generate_blockbuster_headers())
        response.raise_for_status()
        if response.url.rstrip("/").endswith("/login"):
            raise TikTokError("TikTok is requiring login for access to this content")
        return response.text

    async def get_universal_data(self, url: str) -> dict[str, Any]:
        """Download a TikTok webpage and return its rehydration data, solving the JS challenge if needed."""
        webpage = await self.get_webpage(url)
        universal_data = extract_universal_data(webpage)
        if not universal_data:
            cookie_names = self._solve_challenge_and_set_cookies(webpage)
            webpage = await self.get_webpage(url)
            # Challenge cookies should expire immediately after the webpage request.
            for cookie_name in cookie_names:
                self.session.cookies.delete(cookie_name, domain=".tiktok.com")
            universal_data = extract_universal_data(webpage)
        if not universal_data:
            raise TikTokError("Unable to extract universal data for rehydration")
        return universal_data

    async def get_api_json(self, url: str, params: dict[str, str], referer: str = WEBPAGE_URL) -> dict[str, Any]:
        response = await self.session.get(url, params=params, headers={"Referer": referer})
        response.raise_for_status()
        if not response.content:
            raise TikTokError(f"Empty response from {url} (request probably needs a signature or login cookies)")
        return response.json()
