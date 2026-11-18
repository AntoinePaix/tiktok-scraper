"""Live progress bars for the video downloads, drawn with rich."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Protocol

from rich.console import Console
from rich.console import Group
from rich.live import Live
from rich.progress import BarColumn
from rich.progress import DownloadColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import TaskID
from rich.progress import TextColumn
from rich.progress import TransferSpeedColumn


class Observer(Protocol):
    """What the downloader reports its progress to; see `ProgressBars`."""

    def queued(self) -> None: ...
    def started(self, name: str, size: int | None) -> None: ...
    def advanced(self, name: str, count: int) -> None: ...
    def finished(self, name: str) -> None: ...


class ConsoleHandler(logging.Handler):
    """Write log lines through a rich console, so they appear above its live bars."""

    def __init__(self, console: Console):
        super().__init__()
        self.console = console

    def emit(self, record: logging.LogRecord) -> None:
        self.console.print(self.format(record), markup=False, highlight=False, emoji=False)


class ProgressBars:
    """One bar per video being downloaded, and a total of the videos done out of those queued.

        with ProgressBars() as bars:
            await download_user_videos("someone", progress=bars)

    The bars are drawn on stderr and removed when the block is left. `usable` tells whether
    the console can draw them: it cannot when the output is piped or sent to a file.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console(stderr=True)
        self.files = Progress(
            TextColumn("  {task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        )
        self.total = Progress(
            TextColumn("  [bold]Total"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("videos"),
        )
        self._total_task = self.total.add_task("total", total=0)
        self._tasks: dict[str, TaskID] = {}
        self._live = Live(Group(self.files, self.total), console=self.console, transient=True)

    @property
    def usable(self) -> bool:
        return self.console.is_terminal and not self.console.is_dumb_terminal

    def log_handler(self) -> logging.Handler:
        """A logging handler whose lines do not break the bars."""
        return ConsoleHandler(self.console)

    def __enter__(self) -> ProgressBars:
        self._live.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._live.stop()

    def queued(self) -> None:
        """One more video is waiting to be downloaded."""
        task = self.total.tasks[self._total_task]
        self.total.update(self._total_task, total=(task.total or 0) + 1)

    def started(self, name: str, size: int | None) -> None:
        """A download begins, or begins again after a failure; `size` is in bytes if known."""
        if name in self._tasks:
            self.files.reset(self._tasks[name], total=size)
        else:
            self._tasks[name] = self.files.add_task(name, total=size)

    def advanced(self, name: str, count: int) -> None:
        """`count` more bytes of the file were written."""
        if name in self._tasks:
            self.files.advance(self._tasks[name], count)

    def finished(self, name: str) -> None:
        """The video is done with, downloaded or not."""
        if name in self._tasks:
            self.files.remove_task(self._tasks.pop(name))
        self.total.advance(self._total_task)
