"""Command-line interface: ``tiktok-scraper videos|info|comments|search|hashtag ...``."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Annotated

import typer
from curl_cffi.requests.exceptions import RequestException
from rich.console import Console
from rich.logging import RichHandler

from tiktok_scraper import __version__
from tiktok_scraper.client import IMPERSONATE_TARGET
from tiktok_scraper.client import TikTokClient
from tiktok_scraper.client import TikTokError
from tiktok_scraper.constants import DOWNLOAD_DIRECTORY
from tiktok_scraper.constants import MAX_CONCURRENT_DOWNLOADS
from tiktok_scraper.downloader import download_user_videos
from tiktok_scraper.progress import ProgressBars
from tiktok_scraper.user import get_user_metadata

console = Console(stderr=True)
app = typer.Typer(
    help="Download TikTok videos, account metadata, comments, hashtag videos and search results.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Options shared by every command (same names in all the scraper repos).
ProxyOpt = Annotated[
    str | None,
    typer.Option(
        "--proxy",
        "-x",
        envvar="TIKTOK_PROXY",
        help=(
            "Proxy URL, e.g. http://user:pass@host:8080 or socks5h://host:1080. "
            "Without it, the HTTPS_PROXY / ALL_PROXY environment variables apply."
        ),
        rich_help_panel="Network",
    ),
]
TimeoutOpt = Annotated[
    float,
    typer.Option("--timeout", min=1, help="Timeout of each request, in seconds.", rich_help_panel="Network"),
]
ImpersonateOpt = Annotated[
    str,
    typer.Option("--impersonate", help="curl_cffi browser fingerprint.", rich_help_panel="Network"),
]
VerboseOpt = Annotated[int, typer.Option("--verbose", "-v", count=True, help="Show debug logs.")]
QuietOpt = Annotated[bool, typer.Option("--quiet", "-q", help="Only show warnings and errors.")]

# Options of the browser commands.
LimitOpt = Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of results.")]
HeadlessOpt = Annotated[
    bool,
    typer.Option("--headless/--headed", help="Hide the browser window, or show it.", rich_help_panel="Browser"),
]


def _setup_logging(verbose: int, quiet: bool, log_console: Console = console) -> None:
    level = logging.WARNING if quiet else logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=log_console, show_path=False)],
        force=True,
    )
    logging.getLogger("tiktok_scraper").setLevel(level)


def _execute(coro) -> None:
    try:
        asyncio.run(coro)
    except (TikTokError, RequestException) as error:
        console.print(f"[red]✗[/] {error}")
        raise typer.Exit(1) from error
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted[/]")
        raise typer.Exit(130) from None


async def _print_user_metadata(client_options: dict, username: str) -> None:
    async with TikTokClient(**client_options) as client:
        metadata = await get_user_metadata(client, username)
    print(json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False))


async def _download_videos(
    client_options: dict,
    username: str,
    output: Path,
    concurrency: int,
    limit: int | None,
    progress: ProgressBars | None,
) -> None:
    async with TikTokClient(**client_options) as client:
        with progress or contextlib.nullcontext():
            report = await download_user_videos(username, str(output), concurrency, client, limit, progress)
    console.print(
        f"[green]✓[/] {report.directory}: {len(report.downloaded)} downloaded, "
        f"{len(report.already_downloaded)} already downloaded, "
        f"{len(report.skipped_slideshows)} slideshows skipped, {len(report.failed)} failed.",
    )


async def _print_browser_results(browser_options: dict, iterate: Callable, label: str) -> None:
    """Start a `TikTokBrowser`, then print the results of `iterate(browser)` as JSON lines."""
    try:
        from patchright.async_api import Error as PlaywrightError

        from tiktok_scraper.browser import TikTokBrowser
    except ImportError as error:
        raise TikTokError(
            'This command needs the "playwright" extra: pip install "tiktok-scraper[playwright]" '
            "(or uv sync --extra playwright), then run: patchright install chromium",
        ) from error

    counter = 0
    try:
        async with TikTokBrowser(**browser_options) as browser:
            async for result in iterate(browser):
                print(json.dumps(result.to_dict(), ensure_ascii=False), flush=True)
                counter += 1
    except PlaywrightError as error:
        if "Executable doesn't exist" in str(error):
            raise TikTokError("Chromium is not installed, run: patchright install chromium") from error
        raise TikTokError(f"Browser error: {error}") from error
    console.print(f"[green]✓[/] {counter} {label} scraped.")


async def _iter_hashtag_videos_with_info(browser, name: str, limit: int):
    from tiktok_scraper.hashtag import get_hashtag
    from tiktok_scraper.hashtag import iter_hashtag_videos

    hashtag = await get_hashtag(browser, name)
    console.print(f"#{hashtag.name} (id {hashtag.id}): {hashtag.video_count} videos, {hashtag.view_count} views")
    async for tiktok in iter_hashtag_videos(browser, hashtag, limit=limit):
        yield tiktok


@app.command()
def videos(
    user: Annotated[str, typer.Argument(help="TikTok user name.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Download root folder.", rich_help_panel="Output"),
    ] = Path(DOWNLOAD_DIRECTORY),
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", min=1, max=64, help="Parallel downloads.", rich_help_panel="Network"),
    ] = MAX_CONCURRENT_DOWNLOADS,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", min=1, help="Only the N last published tiktoks (default: all)."),
    ] = None,
    progress: Annotated[
        bool,
        typer.Option(
            "--progress/--no-progress",
            help="Show live progress bars (on a terminal).",
            rich_help_panel="Output",
        ),
    ] = True,
    proxy: ProxyOpt = None,
    timeout: TimeoutOpt = 30,
    impersonate: ImpersonateOpt = IMPERSONATE_TARGET,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Download the videos of a user, newest first, into OUTPUT/<user>/."""
    # Live bars need a terminal; otherwise, and with --no-progress, progress is plain log lines.
    bars = ProgressBars(console) if progress else None
    if bars and not bars.usable:
        bars = None
    _setup_logging(verbose, quiet)
    client_options = {"proxy": proxy, "timeout": timeout, "impersonate": impersonate}
    _execute(_download_videos(client_options, user, output, concurrency, limit, bars))


@app.command()
def info(
    user: Annotated[str, typer.Argument(help="TikTok user name.")],
    proxy: ProxyOpt = None,
    timeout: TimeoutOpt = 30,
    impersonate: ImpersonateOpt = IMPERSONATE_TARGET,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Print the metadata of a user account (profile + statistics) as JSON."""
    _setup_logging(verbose, quiet)
    client_options = {"proxy": proxy, "timeout": timeout, "impersonate": impersonate}
    _execute(_print_user_metadata(client_options, user))


@app.command()
def comments(
    video: Annotated[str, typer.Argument(help="TikTok video URL or id.")],
    replies: Annotated[bool, typer.Option("--replies/--no-replies", help="Also list replies to comments.")] = True,
    headless: HeadlessOpt = True,
    proxy: ProxyOpt = None,
    timeout: TimeoutOpt = 30,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Print the comments of a tiktok as JSON lines (needs the "playwright" extra)."""
    from tiktok_scraper.comments import iter_comments

    _setup_logging(verbose, quiet)
    browser_options = {"proxy": proxy, "timeout": timeout, "headless": headless}
    iterate = partial(iter_comments, video=video, with_replies=replies)
    _execute(_print_browser_results(browser_options, iterate, "comments"))


@app.command()
def search(
    keyword: Annotated[str, typer.Argument(help="Searched keyword, e.g. ukraine.")],
    users: Annotated[bool, typer.Option("--users", help="Search accounts instead of tiktoks.")] = False,
    limit: LimitOpt = 50,
    headless: HeadlessOpt = True,
    proxy: ProxyOpt = None,
    timeout: TimeoutOpt = 30,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """Search tiktoks (or accounts) by keyword, as JSON lines (needs the "playwright" extra)."""
    from tiktok_scraper.search import iter_search_users
    from tiktok_scraper.search import iter_search_videos

    _setup_logging(verbose, quiet)
    browser_options = {"proxy": proxy, "timeout": timeout, "headless": headless}
    iterate = partial(iter_search_users if users else iter_search_videos, keyword=keyword, limit=limit)
    _execute(_print_browser_results(browser_options, iterate, "accounts" if users else "tiktoks"))


@app.command()
def hashtag(
    name: Annotated[str, typer.Argument(help="Hashtag name, e.g. ukraine.")],
    limit: LimitOpt = 50,
    # A visible window by default: TikTok often refuses hashtag videos to a headless browser.
    headless: HeadlessOpt = False,
    proxy: ProxyOpt = None,
    timeout: TimeoutOpt = 30,
    verbose: VerboseOpt = 0,
    quiet: QuietOpt = False,
) -> None:
    """List the tiktoks of a hashtag, as JSON lines (needs the "playwright" extra)."""
    _setup_logging(verbose, quiet)
    browser_options = {"proxy": proxy, "timeout": timeout, "headless": headless}
    iterate = partial(_iter_hashtag_videos_with_info, name=name, limit=limit)
    _execute(_print_browser_results(browser_options, iterate, "tiktoks"))


def _version(value: bool) -> None:
    if value:
        typer.echo(f"tiktok-scraper {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit."),
    ] = False,
) -> None:
    pass


def main() -> None:
    app()
