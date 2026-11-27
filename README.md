# tiktok-scraper

[![CI](https://github.com/AntoinePaix/tiktok-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/AntoinePaix/tiktok-scraper/actions/workflows/ci.yml)

`tiktok-scraper` is a Python package and command-line tool that downloads TikTok videos, account metadata,
comments, hashtag videos and keyword search results.

- Videos and account metadata without a browser: requests with [curl_cffi](https://github.com/lexiforest/curl_cffi),
  impersonating a real Chrome browser
- Comments, search and hashtags through an optional browser (`playwright` extra), where TikTok's own script signs
  the requests
- Parallel video downloads with live [rich](https://github.com/Textualize/rich) progress bars; videos already
  downloaded are skipped
- HTTP(S) and SOCKS proxies
- Command `tiktok-scraper`, or `python -m tiktok_scraper`, or use it as a library

Requires Python 3.11 or later.

## Installation

Pick one of the options below. They all install the `tiktok-scraper` command.

### With uv

```bash
# As a tool, available everywhere:
uv tool install git+https://github.com/AntoinePaix/tiktok-scraper

# Or from a clone (runs from the project's own virtual environment):
git clone https://github.com/AntoinePaix/tiktok-scraper
cd tiktok-scraper
uv sync
uv run tiktok-scraper --help
```

### With pip

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install git+https://github.com/AntoinePaix/tiktok-scraper
```

pip ignores `uv.lock` and installs the latest versions allowed by `pyproject.toml`. To get the exact locked
versions, export them once with `uv export --format requirements.txt > requirements.txt`, then run
`pip install -r requirements.txt`.

### Optional: comments, search and hashtags (browser)

The `playwright` extra installs [patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python), a patched
Playwright which removes the main automation leaks, then a Chromium build:

```bash
uv sync --extra playwright           # or: pip install "tiktok-scraper[playwright] @ git+https://github.com/AntoinePaix/tiktok-scraper"
uv run patchright install chromium   # downloads Chromium into ~/.cache/ms-playwright
```

## Usage

```bash
# Download all videos of a user into downloaded_videos/<user>/
tiktok-scraper videos charlidamelio

# Same, into another directory with 8 parallel downloads
tiktok-scraper videos charlidamelio -o videos -c 8

# Only the 20 last published tiktoks, without the progress bars (plain log lines)
tiktok-scraper videos charlidamelio -n 20 --no-progress

# Print account metadata (profile + statistics) as JSON
tiktok-scraper info charlidamelio

# Print comments and replies of a tiktok as JSON lines (needs the "playwright" extra)
tiktok-scraper comments https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857 > comments.jsonl
tiktok-scraper comments 7703703665818733857 --no-replies   # top-level comments only
tiktok-scraper comments 7703703665818733857 --headed       # show the browser window

# Search tiktoks, or accounts, by keyword as JSON lines (needs the "playwright" extra)
tiktok-scraper search ukraine > ukraine.jsonl     # first 50 tiktoks
tiktok-scraper search ukraine -n 200              # first 200 tiktoks
tiktok-scraper search ukraine --users -n 10       # first 10 accounts

# List tiktoks of a hashtag as JSON lines (needs the "playwright" extra, opens a browser window)
tiktok-scraper hashtag ukraine -n 200 > ukraine.jsonl
```

From a clone installed with `uv sync`, prefix the commands with `uv run`. Results go to stdout, logs and progress to
stderr. The exit code is `1` on a TikTok or network error.

### Common options

Same options, with the same names, in every command (and in the other scraper repos):

| Option | Default | Description |
| --- | --- | --- |
| `-o`, `--output` | `downloaded_videos` | Download root folder (`videos`) |
| `-c`, `--concurrency` | `4` | Parallel downloads (`videos`) |
| `-x`, `--proxy` | | Proxy URL (see [Proxies](#proxies)) |
| `--impersonate` | `chrome` | curl_cffi browser fingerprint (`videos`, `info`) |
| `--timeout` | `30` | Timeout of each request, in seconds |
| `-v`, `--verbose` | | Show debug logs |
| `-q`, `--quiet` | | Only show warnings and errors |
| `--version` | | Show the version and exit |

Options specific to tiktok-scraper:

| Option | Default | Description |
| --- | --- | --- |
| `-n`, `--limit` | all (`videos`), 50 (others) | Maximum number of tiktoks, comments or accounts |
| `--progress / --no-progress` | on | Live progress bars, when stderr is a terminal (`videos`) |
| `--replies / --no-replies` | on | Also list replies to comments (`comments`) |
| `--users` | off | Search accounts instead of tiktoks (`search`) |
| `--headless / --headed` | headless, headed for `hashtag` | Hide the browser window, or show it |

## Proxies

```bash
tiktok-scraper info charlidamelio -x http://user:password@host:8080
tiktok-scraper videos charlidamelio -x socks5h://127.0.0.1:1080 --timeout 60
TIKTOK_PROXY=http://host:8080 tiktok-scraper info charlidamelio
```

- **Formats**: `http://`, `https://`, `socks5://` or `socks5h://` URLs, with optional `user:password@`. Use
  `http://` for an HTTP proxy, even for https sites.
- **Environment variables**: `TIKTOK_PROXY` sets the same option as `--proxy`. Without any proxy option, the
  `https_proxy`, `all_proxy` and `no_proxy` variables are used.
- The proxy is used for every request: pages, API, video downloads and the browser.

## Output

- `videos` writes one `<video id>.mp4` per tiktok into `<output>/<user>/`. Each slideshow (photo post) gets its
  own folder named after its id, with its images and its music: `<output>/<user>/<id>/1.jpg`, `2.jpg`...,
  `music.m4a`.
- `info` prints a JSON object: `id`, `sec_uid`, `username`, `nickname`, `signature`, `verified`, `private_account`,
  `created_at`, `avatar_url`, `bio_link`, `region`, `language`, `follower_count`, `following_count`,
  `heart_count`, `video_count`, `digg_count`, `friend_count`.
- `comments` prints one JSON object per line: `id`, `video_id`, `text`, `created_at`, `like_count`, `reply_count`,
  `language`, `author_id`, `author_username`, `author_nickname`, `parent_id` (`null` for a top-level comment).
  Replies come right after their comment.
- `search` and `hashtag` print one JSON object per tiktok (`id`, `url`, `description`, `created_at`,
  `author_username`, `play_count`, `like_count`, ...), or per account with `--users` (`id`, `sec_uid`, `username`,
  `nickname`, `signature`, `follower_count`).

## Library use

Account metadata, tiktoks and video downloads:

```python
import asyncio
import json

from tiktok_scraper import TikTokClient
from tiktok_scraper import download_user_videos
from tiktok_scraper import get_user_metadata
from tiktok_scraper import iter_user_tiktoks


async def main():
    async with TikTokClient() as client:
        metadata = await get_user_metadata(client, "charlidamelio")
        print(f"{metadata.nickname} (@{metadata.username}): {metadata.follower_count} followers")
        print(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False))

        async for tiktok in iter_user_tiktoks(
            client, metadata.sec_uid, referer="https://www.tiktok.com/@charlidamelio"
        ):
            print(tiktok.id, tiktok.description)

        report = await download_user_videos("charlidamelio", client=client)
        print(f"{len(report.downloaded)} videos downloaded, {len(report.failed)} failed")


asyncio.run(main())
```

Every request goes through a `TikTokClient`, so options are given when creating it:

| Option | Default | Description |
| --- | --- | --- |
| `proxy` | `None` | Proxy URL for every request (pages, API and video downloads) |
| `cookies` | `None` | Extra cookies set on `.tiktok.com`, e.g. `sessionid` copied from a logged-in browser |
| `impersonate` | `"chrome"` | Browser fingerprint impersonated by [curl_cffi](https://curl-cffi.readthedocs.io/) |
| `timeout` | `30` | Timeout of each request, in seconds |
| `**session_options` | | Any other `curl_cffi.requests.AsyncSession` option, e.g. `retry`, `verify`, `interface` |

`download_user_videos` uses the client you pass and doesn't close it; without one, it creates a client with default
options. Pass a `tiktok_scraper.progress.ProgressBars` as its `progress=` argument to get the same bars as the
command (any object implementing the `Observer` protocol works).

Comments, search and hashtags, with the `playwright` extra:

```python
import asyncio

from tiktok_scraper import get_hashtag
from tiktok_scraper import iter_comments
from tiktok_scraper import iter_hashtag_videos
from tiktok_scraper import iter_search_users
from tiktok_scraper import iter_search_videos
from tiktok_scraper.browser import TikTokBrowser


async def main():
    async with TikTokBrowser(proxy="http://user:password@host:8080") as browser:
        async for comment in iter_comments(browser, "https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857"):
            indent = "    " if comment.parent_id else ""  # replies come right after their comment
            print(f"{indent}@{comment.author_username}: {comment.text} ({comment.like_count} likes)")

        async for tiktok in iter_search_videos(browser, "ukraine", limit=100):
            print(tiktok.webpage_url, tiktok.to_dict()["play_count"])

        async for user in iter_search_users(browser, "ukraine", limit=10):
            print(user.username, user.follower_count)

    # TikTok often refuses hashtag videos to a headless browser: use a visible window.
    async with TikTokBrowser(headless=False) as browser:
        hashtag = await get_hashtag(browser, "ukraine")
        print(hashtag.id, hashtag.video_count, hashtag.view_count)
        async for tiktok in iter_hashtag_videos(browser, hashtag, limit=100):
            print(tiktok.webpage_url)


asyncio.run(main())
```

`TikTokBrowser` options:

| Option | Default | Description |
| --- | --- | --- |
| `headless` | `True` | Hide the browser window. A visible window looks more like a real user. |
| `proxy` | `None` | Proxy URL, e.g. `http://user:password@host:8080` or `socks5://host:1080` |
| `user_data_dir` | temporary | Browser profile directory, to keep cookies between runs |
| `channel` | `"chromium"` | `"chromium"`, or `"chrome"` to use Google Chrome installed on the system (harder to detect) |
| `timeout` | `30` | Timeout of page loads, in seconds |

Errors raise `tiktok_scraper.TikTokError`. The library logs with the `logging` module under the `tiktok_scraper`
logger.

### Adding an endpoint

Any web API endpoint can be called with `TikTokBrowser.request_json`. It adds the common parameters
(`device_id`, ...), lets TikTok's script add the signatures, and retries empty responses twice:

```python
data = await browser.request_json(
    "https://www.tiktok.com/api/search/user/full/",
    {"keyword": "ukraine", "offset": 0, "cursor": 0, "count": 10},
    from_page="search",
)
```

To find an endpoint and its parameters, open the matching TikTok page in your browser, filter the Network tab of the
developer tools on `/api/`, and keep the parameters that are not common ones (`keyword`, `cursor`, ...).

## How it works

- **Videos and metadata** are scraped the same way [yt-dlp](https://github.com/yt-dlp/yt-dlp) does: the user page
  rehydration data gives the account `secUid`, then the `api/creator/item_list/` web API is paginated by timestamp
  cursor. Each video page is then fetched for fresh video URLs and their cookies.
- **Comments, search and hashtags** use API endpoints that only answer requests signed by TikTok's obfuscated
  JavaScript. `TikTokBrowser` opens `https://www.tiktok.com/explore` in Chromium, waits for TikTok's script to get
  its `msToken`, then sends the requests from inside the page, where TikTok's own script signs them.
- **Hashtags** take two steps: `get_hashtag` gets the hashtag id from its name (`api/challenge/detail/`), then
  `iter_hashtag_videos` lists its tiktoks from that id (`api/challenge/item_list/`).
- In headless mode, the browser is patched to look like a regular Chrome: user agent without `HeadlessChrome`, and a
  real screen size.

## Limitations

- TikTok counts more comments than it returns to a logged-out browser (hidden or filtered comments): a comment with
  `reply_count == 3` may come with only 1 reply.
- Hashtag videos are often refused (empty response) to a headless browser, even with the patches: the `hashtag`
  command opens a visible window by default (`--headless` to hide it). On a server without a display, run it in a
  virtual one: `xvfb-run tiktok-scraper hashtag ukraine`.
- A hashtag's feed also contains videos without the hashtag in their description: TikTok's ranking, not a bug.
- When TikTok shows a CAPTCHA, requests fail with a `TikTokError` saying so. The scraper doesn't solve CAPTCHAs:
  wait, slow down, or change IP address.
- This is unofficial and may break whenever TikTok changes its website. Signing requests in a browser goes against
  TikTok's terms of service: keep request volumes reasonable.

## Development

The four scraper repos (snapchat-cli, tiktok-scraper, vinted-api, scraping-classement-atout-france) share the same
tooling: [uv](https://docs.astral.sh/uv/), [ruff](https://docs.astral.sh/ruff/), [pytest](https://docs.pytest.org/),
[pre-commit](https://pre-commit.com/) and the same GitHub Actions pipeline.

```bash
uv sync --all-extras                # project + dev tools (pytest, ruff, pre-commit)
uv run pre-commit install           # once: run the hooks on every commit

uv run pytest                       # offline tests
uv run pytest -m live               # smoke tests against the real website
uv run ruff check --fix . && uv run ruff format .
uv run pre-commit run --all-files   # every hook, as the CI does
```

Without uv: `pip install -e ".[playwright]" --group dev` (`--group` needs pip 25.1+), then run the same commands without
the `uv run` prefix.

- **Pre-commit hooks**: they block `.env` files, `.har` captures and `token.json` files, scan for secrets with
  gitleaks, refuse files over 1 MB, check YAML and TOML files, fix trailing whitespace and final newlines, run
  `ruff check --fix` and `ruff format`, and keep `uv.lock` in sync with `pyproject.toml`.
- **CI** (`.github/workflows/ci.yml`): on every push to `main` and every pull request, one job runs all the
  pre-commit hooks, and another runs the offline tests on Python 3.11, 3.12, 3.13 and 3.14.
- **Code style**: ruff with 120-character lines, one import per line and absolute imports only (see
  `pyproject.toml`).

### Repository layout

```
.github/workflows/ci.yml   lint (pre-commit) + tests on Python 3.11 to 3.14
src/tiktok_scraper/
├── cli.py          # command line (typer): videos, info, comments, search, hashtag
├── client.py       # HTTP client: curl_cffi, page rehydration data
├── user.py         # account metadata and tiktoks of a user
├── downloader.py   # parallel video downloads
├── progress.py     # rich progress bars
├── browser.py      # TikTokBrowser: requests signed by TikTok's script (playwright extra)
├── comments.py     # comments and replies (browser)
├── search.py       # keyword search (browser)
├── hashtag.py      # hashtag videos (browser)
├── models.py       # TikTok / UserMetadata / Comment / Hashtag data structures
└── constants.py    # URLs and defaults
tests/              # pytest suite, JSON fixtures, live smoke tests
```

## License

[MIT](LICENSE)
