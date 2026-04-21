"""command_input.py — Chat-style input bar with command history."""

from __future__ import annotations

from collections import deque
from typing import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input


class CommandInput(Widget):
    """Single-line input with Up/Down history and Enter-to-send."""

    DEFAULT_CSS = """
    CommandInput {
        height: 3;
        border: round $accent;
        padding: 0 1;
    }
    Input {
        border: none;
    }
    """

    BINDINGS = [
        Binding("up",   "history_prev", "Previous command", show=False),
        Binding("down", "history_next", "Next command",     show=False),
    ]

    def __init__(
        self,
        on_submit: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._on_submit = on_submit
        self._history: deque[str] = deque(maxlen=50)
        self._hist_idx: int = -1
        self._draft: str = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Send command to WallE… (Enter to send, ↑↓ history)")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        self._history.appendleft(text)
        self._hist_idx = -1
        self._draft = ""
        event.input.value = ""
        self._on_submit(text)

    def action_history_prev(self) -> None:
        inp: Input = self.query_one(Input)
        if not self._history:
            return
        if self._hist_idx == -1:
            self._draft = inp.value
        self._hist_idx = min(self._hist_idx + 1, len(self._history) - 1)
        inp.value = self._history[self._hist_idx]
        inp.cursor_position = len(inp.value)

    def action_history_next(self) -> None:
        inp: Input = self.query_one(Input)
        if self._hist_idx == -1:
            return
        self._hist_idx -= 1
        if self._hist_idx == -1:
            inp.value = self._draft
        else:
            inp.value = self._history[self._hist_idx]
        inp.cursor_position = len(inp.value)
