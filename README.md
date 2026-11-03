# TikTok Scraper

A basic tiktok scraper to download videos and account metadata.

It talks to TikTok the same way [yt-dlp](https://github.com/yt-dlp/yt-dlp) does: the user page rehydration
data gives the account `secUid`, then the `api/creator/item_list/` web API is paginated by timestamp cursor.
Requests impersonate a real Chrome browser with [curl_cffi](https://github.com/lexiforest/curl_cffi), so no
headless browser is needed.

## How to install:

Requires [uv](https://docs.astral.sh/uv/).

``` bash
git clone git@github.com:AntoinePaix/tiktok-scraper.git
cd tiktok-scraper
uv sync
```

### Without uv

Plain `pip` works too:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .            # the project and its dependencies
pip install --group dev     # optional: pytest and ruff (needs pip >= 25.1)
```

Then run the commands below without the `uv run` prefix, e.g. `tiktok-scraper info charlidamelio`.

pip ignores `uv.lock` and installs the latest versions allowed by `pyproject.toml`. To get the exact locked
versions, export them once with `uv export --format requirements.txt > requirements.txt`, then run
`pip install -r requirements.txt`.

## How to use:

```bash
# Download all videos of a user into downloaded_videos/<user>/
uv run tiktok-scraper videos charlidamelio

# Same, into another directory with 8 parallel downloads
uv run tiktok-scraper videos charlidamelio -o videos -j 8

# Print account metadata (profile + statistics) as JSON
uv run tiktok-scraper info charlidamelio
```

Global options go before the command:

```bash
uv run tiktok-scraper -v videos charlidamelio                                # show debug logs
uv run tiktok-scraper --proxy http://user:password@host:8080 info charlidamelio
uv run tiktok-scraper --proxy socks5h://127.0.0.1:1080 --timeout 60 videos charlidamelio
```

Without `--proxy`, the `https_proxy`, `all_proxy` and `no_proxy` environment variables are used.

From Python, print user infos:

```python
import asyncio
import json

from tiktok_scraper import TikTokClient
from tiktok_scraper import get_user_metadata


async def main():
    async with TikTokClient() as client:
        metadata = await get_user_metadata(client, "charlidamelio")

    # Single fields
    print(f"{metadata.nickname} (@{metadata.username})")
    print(f"{metadata.follower_count} followers, {metadata.video_count} videos, {metadata.heart_count} likes")

    # All fields, as JSON
    print(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False))


asyncio.run(main())
```

Available fields: `id`, `sec_uid`, `username`, `nickname`, `signature`, `verified`, `private_account`,
`created_at`, `avatar_url`, `bio_link`, `region`, `language`, `follower_count`, `following_count`,
`heart_count`, `video_count`, `digg_count`, `friend_count`.

List tiktoks and download videos:

```python
import asyncio

from tiktok_scraper import TikTokClient
from tiktok_scraper import download_user_videos
from tiktok_scraper import get_user_metadata
from tiktok_scraper import iter_user_tiktoks


async def main():
    async with TikTokClient() as client:
        metadata = await get_user_metadata(client, "charlidamelio")
        print(metadata.follower_count, metadata.video_count)

        async for tiktok in iter_user_tiktoks(
            client, metadata.sec_uid, referer="https://www.tiktok.com/@charlidamelio"
        ):
            print(tiktok.id, tiktok.description)

    report = await download_user_videos("charlidamelio")
    print(f"{len(report.downloaded)} videos downloaded, {len(report.failed)} failed")


asyncio.run(main())
```

The library logs progress with the `logging` module under the `tiktok_scraper` logger.

### Client options (proxy, cookies, ...)

Every request goes through a `TikTokClient`, so options are given when creating it:

```python
import asyncio

from tiktok_scraper import TikTokClient
from tiktok_scraper import download_user_videos
from tiktok_scraper import get_user_metadata


async def main():
    async with TikTokClient(
        proxy="http://user:password@host:8080",  # or "socks5h://host:1080"
        cookies={"sessionid": "..."},  # optional: browser cookies, to be logged in
        impersonate="chrome",  # browser fingerprint: "chrome", "safari", "firefox"...
        timeout=60,  # seconds, per request
        retry=2,  # any other curl_cffi AsyncSession option is passed through
    ) as client:
        metadata = await get_user_metadata(client, "charlidamelio")
        report = await download_user_videos("charlidamelio", client=client)


asyncio.run(main())
```

| Option | Default | Description |
|---|---|---|
| `proxy` | `None` | Proxy URL for every request (pages, API and video downloads). Use `http://` for an HTTP proxy, even for https sites. |
| `cookies` | `None` | Extra cookies set on `.tiktok.com`, e.g. `sessionid` copied from a logged-in browser. |
| `impersonate` | `"chrome"` | Browser fingerprint impersonated by [curl_cffi](https://curl-cffi.readthedocs.io/). |
| `timeout` | `30` | Timeout of each request, in seconds. |
| `**session_options` | | Any other `curl_cffi.requests.AsyncSession` option, e.g. `retry`, `verify`, `interface`. |

`download_user_videos` uses the client you pass and doesn't close it. Without one, it creates a client with
default options.

## Development:

```bash
uv run pytest                 # run tests (offline, no request to TikTok)
uv run ruff check --fix .     # lint and sort imports
uv run ruff format .          # format
```
