import pytest

pytest.importorskip("patchright")

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
