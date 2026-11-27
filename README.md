# tokscrape

[![CI](https://github.com/AntoinePaix/tokscrape/actions/workflows/ci.yml/badge.svg)](https://github.com/AntoinePaix/tokscrape/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tokscrape)](https://pypi.org/project/tokscrape/)

`tokscrape` is a Python package and command-line tool that downloads TikTok videos, account metadata,
comments, hashtag videos and keyword search results.

- Videos and account metadata without a browser: requests with [curl_cffi](https://github.com/lexiforest/curl_cffi),
  impersonating a real Chrome browser
- Comments, search and hashtags through an optional browser (`playwright` extra), where TikTok's own script signs
  the requests
- Parallel video downloads with live [rich](https://github.com/Textualize/rich) progress bars; videos already
  downloaded are skipped
- HTTP(S) and SOCKS proxies
- Command `tokscrape`, or `python -m tokscrape`, or use it as a library

Requires Python 3.11 or later.

## Installation

Pick one of the options below. They all install the `tokscrape` command.

### With uv

```bash
# As a tool, available everywhere, from PyPI:
uv tool install tokscrape

# Or from a clone (runs from the project's own virtual environment):
git clone https://github.com/AntoinePaix/tokscrape
cd tokscrape
uv sync
uv run tokscrape --help
```

### With pip

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install tokscrape
```

The development version, not released yet: `pip install git+https://github.com/AntoinePaix/tokscrape`.

pip ignores `uv.lock` and installs the latest versions allowed by `pyproject.toml`. To get the exact locked
versions, export them once with `uv export --format requirements.txt > requirements.txt`, then run
`pip install -r requirements.txt`.

### Optional: comments, search and hashtags (browser)

The `playwright` extra installs [patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python), a patched
Playwright which removes the main automation leaks, then a Chromium build:

```bash
uv sync --extra playwright           # or: pip install "tokscrape[playwright]"
uv run patchright install chromium   # downloads Chromium into ~/.cache/ms-playwright
```

## Usage

```bash
# Download all videos of a user into downloaded_videos/<user>/
tokscrape videos charlidamelio

# Same, into another directory with 8 parallel downloads
tokscrape videos charlidamelio -o videos -c 8

# Only the 20 last published tiktoks, without the progress bars (plain log lines)
tokscrape videos charlidamelio -n 20 --no-progress

# Print account metadata (profile + statistics) as JSON
tokscrape info charlidamelio

# Print one tiktok (video or slideshow) as JSON, from its URL or id; --download also saves it
tokscrape tiktok https://www.tiktok.com/@europeanspaceagency/video/7695112242110418209
tokscrape tiktok 7695112242110418209 --download

# Print comments and replies of a tiktok as JSON lines (needs the "playwright" extra)
tokscrape comments https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857 > comments.jsonl
tokscrape comments 7703703665818733857 --no-replies   # top-level comments only
tokscrape comments 7703703665818733857 --headed       # show the browser window

# Search tiktoks, or accounts, by keyword as JSON lines (needs the "playwright" extra)
tokscrape search ukraine > ukraine.jsonl     # first 50 tiktoks
tokscrape search ukraine -n 200              # first 200 tiktoks
tokscrape search ukraine --users -n 10       # first 10 accounts
tokscrape search paris --music -n 20         # first 20 sounds
tokscrape search nasa --photos -n 20         # first 20 photo posts (slideshows)

# List tiktoks of a hashtag as JSON lines (needs the "playwright" extra, opens a browser window)
tokscrape hashtag ukraine -n 200 > ukraine.jsonl
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

Options specific to tokscrape:

| Option | Default | Description |
| --- | --- | --- |
| `-n`, `--limit` | all (`videos`), 50 (others) | Maximum number of tiktoks, comments, accounts or sounds |
| `--progress / --no-progress` | on | Live progress bars, when stderr is a terminal (`videos`) |
| `--replies / --no-replies` | on | Also list replies to comments (`comments`) |
| `--users` | off | Search accounts instead of tiktoks (`search`) |
| `--music` | off | Search sounds instead of tiktoks (`search`) |
| `--photos` | off | Search photo posts (slideshows) only, like the website's Photo tab (`search`) |
| `--headless / --headed` | headless, headed for `hashtag` | Hide the browser window, or show it |

## Proxies

```bash
tokscrape info charlidamelio -x http://user:password@host:8080
tokscrape videos charlidamelio -x socks5h://127.0.0.1:1080 --timeout 60
TIKTOK_PROXY=http://host:8080 tokscrape info charlidamelio
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
- `tiktok` prints one tiktok as a JSON object (same fields as below). With `--download`, it is saved like `videos`
  does: `<output>/<user>/<id>.mp4`, or the `<output>/<user>/<id>/` folder of a slideshow.
- `comments` prints one JSON object per line: `id`, `video_id`, `text`, `created_at`, `like_count`, `reply_count`,
  `language`, `author_id`, `author_username`, `author_nickname`, `parent_id` (`null` for a top-level comment).
  Replies come right after their comment.
- `search` and `hashtag` print one JSON object per tiktok, or per account with `--users` (`id`, `sec_uid`,
  `username`, `nickname`, `signature`, `follower_count`), or per sound with `--music` (same fields as a tiktok's
  `music` below, plus `video_count`, the number of videos using it). With `--photos`, every tiktok is a slideshow.
  A tiktok has:
  - `id`, `url`, `description`, `created_at`, `language`, `hashtags`, `mentions`, `location` (`id`, `name`,
    `address`, `city`, or `null`)
  - `author_id`, `author_username`, `author_nickname`, `author_sec_uid`, `author_verified`
  - `is_slideshow`, `image_count`, `duration` (seconds, `null` for a slideshow), `width`, `height`, `cover_url`,
    `origin_cover_url` (full size), `dynamic_cover_url` (animated)
  - `play_count`, `like_count`, `comment_count`, `share_count`, `save_count`, `repost_count`
  - `is_ad`, `duet_enabled`, `stitch_enabled`
  - `music` (`id`, `title`, `author`, `album`, `duration`, `is_original`, `url`, `cover_url`, or `null`)
- Dates are ISO 8601 in UTC, e.g. `2026-10-27T17:21:43Z`.

## Library use

Results are [pydantic](https://docs.pydantic.dev/) models (`TikTok`, `Music`, `Location`, `UserMetadata`,
`Comment`, `SearchUser`, `Hashtag`), validated when built from TikTok's JSON: their fields are typed (counts are
`int`, dates are `datetime` in UTC). `to_dict()` gives JSON-ready values (same as `model_dump(mode="json")`), and
`tiktok.raw` keeps everything TikTok returned for a tiktok.

Account metadata, tiktoks and video downloads:

```python
import asyncio
import json

from tokscrape import TikTokClient
from tokscrape import download_tiktok
from tokscrape import download_user_videos
from tokscrape import get_tiktok
from tokscrape import get_user_metadata
from tokscrape import iter_user_tiktoks


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

        # One tiktok, from its URL or id (raises TikTokError if it was deleted or is private)
        tiktok = await get_tiktok(client, "https://www.tiktok.com/@europeanspaceagency/video/7695112242110418209")
        print(tiktok.description, tiktok.play_count, tiktok.music.title if tiktok.music else None)
        await download_tiktok(tiktok, client=client)


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
options. Pass a `tokscrape.progress.ProgressBars` as its `progress=` argument to get the same bars as the
command (any object implementing the `Observer` protocol works).

Comments, search and hashtags, with the `playwright` extra:

```python
import asyncio

from tokscrape import get_hashtag
from tokscrape import iter_comments
from tokscrape import iter_hashtag_videos
from tokscrape import iter_search_music
from tokscrape import iter_search_photos
from tokscrape import iter_search_users
from tokscrape import iter_search_videos
from tokscrape.browser import TikTokBrowser


async def main():
    async with TikTokBrowser(proxy="http://user:password@host:8080") as browser:
        async for comment in iter_comments(browser, "https://www.tiktok.com/@emmanuelmacron/video/7703703665818733857"):
            indent = "    " if comment.parent_id else ""  # replies come right after their comment
            print(f"{indent}@{comment.author_username}: {comment.text} ({comment.like_count} likes)")

        async for tiktok in iter_search_videos(browser, "ukraine", limit=100):
            print(tiktok.url, tiktok.play_count, tiktok.hashtags)

        async for user in iter_search_users(browser, "ukraine", limit=10):
            print(user.username, user.follower_count)

        async for sound in iter_search_music(browser, "paris", limit=10):
            print(sound.title, sound.author, sound.video_count)

        async for slideshow in iter_search_photos(browser, "nasa", limit=10):
            print(slideshow.url, slideshow.image_count)

    # TikTok often refuses hashtag videos to a headless browser: use a visible window.
    async with TikTokBrowser(headless=False) as browser:
        hashtag = await get_hashtag(browser, "ukraine")
        print(hashtag.id, hashtag.video_count, hashtag.view_count)
        async for tiktok in iter_hashtag_videos(browser, hashtag, limit=100):
            print(tiktok.url)


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

Errors raise `tokscrape.TikTokError`. The library logs with the `logging` module under the `tokscrape`
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
  virtual one: `xvfb-run tokscrape hashtag ukraine`.
- A hashtag's feed also contains videos without the hashtag in their description: TikTok's ranking, not a bug.
- Sound search (`--music`) uses an endpoint the website has but no longer shows (no "Sounds" tab): it may disappear.
  Places can't be searched on the web, unlike in the app; a tiktok's place is in its `location` field.
- When TikTok shows a CAPTCHA, requests fail with a `TikTokError` saying so. The scraper doesn't solve CAPTCHAs:
  wait, slow down, or change IP address.
- This is unofficial and may break whenever TikTok changes its website. Signing requests in a browser goes against
  TikTok's terms of service: keep request volumes reasonable.

## Development

The four scraper repos (snapchat-cli, tokscrape, vinted-api, scraping-classement-atout-france) share the same
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
- **Releases** (`.github/workflows/release.yml`): pushing a version tag such as `v0.5.0` checks it matches the
  version in `pyproject.toml`, runs the tests, builds the package, publishes it to
  [PyPI](https://pypi.org/project/tokscrape/) and creates a GitHub release with the wheel, the sdist and the list
  of commits since the previous tag.

### Releasing

Versions follow `MAJOR.MINOR.PATCH`: bump `minor` for new features or breaking changes (while the version is
`0.x`), `patch` for fixes only.

```bash
uv version --bump minor                          # e.g. 0.4.0 -> 0.5.0, in pyproject.toml and uv.lock
git commit -am "Release 0.5.0"
git tag v0.5.0
git push origin main v0.5.0                       # the release workflow publishes to PyPI and GitHub
```

Release candidates test the whole chain on PyPI first: pip only installs them when asked explicitly
(`pip install tokscrape==0.5.0rc1`), and they are marked as pre-releases on GitHub.

```bash
uv version 0.5.0rc1                               # then commit, tag v0.5.0rc1 and push as above
```

The package is named `tokscrape` because `tiktok-scraper` is taken on PyPI by another project (which also
installs a `tiktok_scraper` module and a `tiktok-scraper` command).

PyPI publishing uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/): no token is stored, PyPI
trusts the release workflow itself. It is configured once on pypi.org, in the project's *Settings > Publishing*
(or *Your account > Publishing > Add a new pending publisher* before the first upload), GitHub tab:

| Field | Value |
| --- | --- |
| PyPI Project Name | `tokscrape` |
| Owner | `AntoinePaix` |
| Repository name | `tokscrape` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

### Repository layout

```
.github/workflows/ci.yml        lint (pre-commit) + tests on Python 3.11 to 3.14
.github/workflows/release.yml   PyPI + GitHub release on a version tag (v*)
src/tokscrape/
├── cli.py          # command line (typer): videos, info, tiktok, comments, search, hashtag
├── client.py       # HTTP client: curl_cffi, page rehydration data
├── user.py         # account metadata and tiktoks of a user
├── post.py         # one tiktok from its URL or id
├── downloader.py   # parallel video downloads
├── progress.py     # rich progress bars
├── browser.py      # TikTokBrowser: requests signed by TikTok's script (playwright extra)
├── comments.py     # comments and replies (browser)
├── search.py       # keyword search (browser)
├── hashtag.py      # hashtag videos (browser)
├── models.py       # pydantic models: TikTok, Music, Location, UserMetadata, Comment, SearchUser, Hashtag
└── constants.py    # URLs and defaults
tests/              # pytest suite, JSON fixtures, live smoke tests
```

## License

[MIT](LICENSE)
