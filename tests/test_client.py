import asyncio
import base64
import hashlib
import json

import pytest

from tiktok_scraper import TikTokClient
from tiktok_scraper import TikTokError
from tiktok_scraper.client import extract_universal_data


@pytest.fixture
def client():
    client = TikTokClient()
    yield client
    asyncio.run(client.close())


def test_client_options():
    client = TikTokClient(proxy="socks5h://127.0.0.1:1080", cookies={"sessionid": "secret"}, retry=2)
    try:
        assert client.session.proxies == {"all": "socks5h://127.0.0.1:1080"}
        assert client.session.cookies.get("sessionid", domain=".tiktok.com") == "secret"
    finally:
        asyncio.run(client.close())


def test_extract_universal_data():
    webpage = (
        '<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
        '{"__DEFAULT_SCOPE__": {"webapp.user-detail": {"statusCode": 0}}}</script></html>'
    )
    assert extract_universal_data(webpage) == {"webapp.user-detail": {"statusCode": 0}}


@pytest.mark.parametrize(
    "webpage",
    [
        "<html>Please wait...</html>",
        '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">{not json</script>',
    ],
)
def test_extract_universal_data_missing(webpage):
    assert extract_universal_data(webpage) == {}


def test_build_web_query(client):
    client.session.cookies.set("msToken", "token", domain=".tiktok.com")
    query = client.build_web_query(count=15, secUid="abc")

    assert query["device_id"] == client.device_id
    assert query["msToken"] == "token"
    assert query["count"] == "15"
    assert query["secUid"] == "abc"


def test_solve_challenge(client):
    base = b"challenge-base"
    answer = 4242
    challenge = {
        "v": {
            "a": base64.b64encode(base).decode(),
            "c": base64.b64encode(hashlib.sha256(base + str(answer).encode()).digest()).decode(),
        }
    }
    encoded_challenge = base64.b64encode(json.dumps(challenge).encode()).decode().rstrip("=")
    webpage = (
        f'<p id="cs" class="{encoded_challenge}"></p><p id="wci" class="_wafchallengeid"></p>'
        '<p id="rci" class="waforiginalreid"></p><p id="rs" class="original"></p>'
    )

    cookie_names = client._solve_challenge_and_set_cookies(webpage)

    assert cookie_names == ["_wafchallengeid", "waforiginalreid"]
    solved = json.loads(base64.b64decode(client.session.cookies.get("_wafchallengeid")))
    assert base64.b64decode(solved["d"]) == str(answer).encode()
    assert client.session.cookies.get("waforiginalreid") == "original"


def test_solve_challenge_without_challenge(client):
    with pytest.raises(TikTokError):
        client._solve_challenge_and_set_cookies("<html>Please wait...</html>")
