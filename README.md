# TikTok Scraper

A basic tiktok scraper to download videos, account metadata and comments.

Videos and metadata are scraped the same way [yt-dlp](https://github.com/yt-dlp/yt-dlp) does: the user page
rehydration data gives the account `secUid`, then the `api/creator/item_list/` web API is paginated by timestamp
cursor. Requests impersonate a real Chrome browser with [curl_cffi](https://github.com/lexiforest/curl_cffi), so no
browser is needed.

Other TikTok API endpoints (comments, ...) only answer requests signed by TikTok's obfuscated JavaScript. For those,
the optional `playwright` extra opens a TikTok page in a Chromium browser and sends the requests from inside the
page, where TikTok's own script signs them (see [Browser endpoints](#browser-endpoints-comments)).

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

### Browser endpoints (comments)

The `playwright` extra installs [patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python), a
patched Playwright which removes the main automation leaks, then a Chromium build:

```bash
uv sync --extra playwright           # or: pip install -e ".[playwright]"
uv run patchright install chromium   # downloads Chromium into ~/.cache/ms-playwright
```

## How to use:

```bash
# Download all videos of a user into downloaded_videos/<user>/
uv run tiktok-scraper videos charlidamelio

# Same, into another directory with 8 parallel downloads
uv run tiktok-scraper videos charlidamelio -o videos -j 8

# Print account metadata (profile + statistics) as JSON
uv run tiktok-scraper info charlidamelio

# Print comments and replies of a tiktok as JSON lines (needs the "playwright" extra)
uv run tiktok-scraper comments https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857 > comments.jsonl
uv run tiktok-scraper comments 7703703665818733857 --no-replies   # top-level comments only
uv run tiktok-scraper comments 7703703665818733857 --headed       # show the browser window
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

### Comments (browser)

```python
import asyncio

from tiktok_scraper import iter_comments
from tiktok_scraper.browser import TikTokBrowser


async def main():
    async with TikTokBrowser(proxy="http://user:password@host:8080") as browser:
        async for comment in iter_comments(browser, "https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857"):
            indent = "    " if comment.parent_id else ""  # replies come right after their comment
            print(f"{indent}@{comment.author_username}: {comment.text} ({comment.like_count} likes)")


asyncio.run(main())
```

`Comment` fields: `id`, `video_id`, `text`, `created_at`, `like_count`, `reply_count`, `language`, `author_id`,
`author_username`, `author_nickname`, `parent_id` (`None` for a top-level comment).

`TikTokBrowser` options:

| Option | Default | Description |
|---|---|---|
| `headless` | `True` | Hide the browser window. A visible window looks more like a real user. |
| `proxy` | `None` | Proxy URL, e.g. `http://user:password@host:8080` or `socks5://host:1080`. |
| `user_data_dir` | temporary | Browser profile directory, to keep cookies between runs. |
| `channel` | `"chromium"` | `"chromium"`, or `"chrome"` to use Google Chrome installed on the system (harder to detect). |
| `timeout` | `30` | Timeout of page loads, in seconds. |

In headless mode, the browser is patched to look like a regular Chrome: user agent without `HeadlessChrome`, and a
real screen size. At start, it opens `https://www.tiktok.com/explore` and waits for TikTok's script to get its
`msToken`, which takes a few seconds.

Any other web API endpoint can be called the same way, the common parameters (`device_id`, ...) are added:

```python
data = await browser.request_json(
    "https://www.tiktok.com/api/comment/list/", {"aweme_id": "...", "count": 20, "cursor": 0}
)
```

Known limitations:

- TikTok counts more comments than it returns to a logged-out browser (hidden or filtered comments): a comment
  with `reply_count == 3` may come with only 1 reply.
- Signing requests in a browser goes against TikTok's terms of service: keep request volumes reasonable.

## Development:

```bash
uv run pytest                 # run tests (offline, no request to TikTok)
uv run ruff check --fix .     # lint and sort imports
uv run ruff format .          # format
```
