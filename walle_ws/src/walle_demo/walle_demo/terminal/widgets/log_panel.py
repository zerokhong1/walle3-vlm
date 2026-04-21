"""log_panel.py — Scrollable log panel that displays ROS event stream."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog

_TYPE_STYLE: dict[str, str] = {
    "cmd":    "bold cyan",
    "state":  "bold white",
    "plan":   "blue",
    "infer":  "dim",
    "safety": "bold yellow",
    "mission": "bold green",
}

_SEVERITY_OVERRIDE: dict[str, str] = {
    "CRITICAL": "bold red",
    "HIGH":     "bold yellow",
    "MEDIUM":   "yellow",
    "LOW":      "dim",
}


class LogPanel(Widget):
    """Auto-scrolling log of all ROS events received by the bridge."""

    DEFAULT_CSS = """
    LogPanel {
        border: round $accent;
    }
    RichLog {
        height: 1fr;
        scrollbar-gutter: stable;
    }
    """

    MAX_LINES: ClassVar[int] = 500

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=False, markup=True, max_lines=self.MAX_LINES)

    def push(self, entry: dict) -> None:
        log: RichLog = self.query_one(RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        text = entry.get("text", "")
        etype = entry.get("type", "state")
        severity = entry.get("severity", "")

        if severity and severity in _SEVERITY_OVERRIDE:
            style = _SEVERITY_OVERRIDE[severity]
        else:
            style = _TYPE_STYLE.get(etype, "white")

        log.write(f"[dim]{ts}[/dim]  [{style}]{text}[/{style}]")
