"""Smoke tests of the command-line interface (same tests in every repo with a CLI)."""

import re

import pytest
from typer.testing import CliRunner

from tiktok_scraper import __version__
from tiktok_scraper.cli import app

runner = CliRunner()

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def plain_output(result) -> str:
    """Output without colour codes: Typer forces coloured help when GITHUB_ACTIONS is set."""
    return ANSI_ESCAPE.sub("", result.output)


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert plain_output(result).strip() == f"tiktok-scraper {__version__}"


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in (
        "videos",
        "info",
        "tiktok",
        "comments",
        "search",
        "hashtag",
    ):
        assert command in plain_output(result)


@pytest.mark.parametrize("command", ["videos", "info", "tiktok", "comments", "search", "hashtag"])
def test_command_help(command):
    result = runner.invoke(app, [command, "--help"])
    assert result.exit_code == 0
    assert "--proxy" in plain_output(result)
