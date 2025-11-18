import time
from typing import Any

from rich.spinner import Spinner
from textual.timer import Timer
from textual.widgets import Static


class SpinnerWidget(Static):
    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._spinner: Spinner = Spinner(name)
        self.update_timer: Timer

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1 / 15, self.update_spinner, pause=False)

    def update_spinner(self) -> None:
        self.update(self._spinner.render(time.monotonic()))

    def resume(self) -> None:
        self.update_timer.resume()
        self.update_spinner()

    def pause(self) -> None:
        self.update_timer.pause()
        self.update_spinner()
