"""app.py — WallE Terminal TUI built with textual 8.x."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static

from .ros_bridge import RosBridge, RobotState, WalleBridge
from .widgets.command_input import CommandInput
from .widgets.log_panel import LogPanel
from .widgets.state_panel import StatePanel

_CSS_PATH = Path(__file__).parent / "walle_terminal.tcss"


class WalleTerminalApp(App):
    """Full-screen TUI for sending commands and monitoring WallE3 v2."""

    CSS_PATH = _CSS_PATH

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_log", "Clear log"),
    ]

    TITLE = "WallE3 v2 — Terminal"

    def __init__(self) -> None:
        super().__init__()
        self._bridge_manager = RosBridge()
        self._node: WalleBridge | None = None

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(
            " WallE3 v2  |  VLM-Powered Robot Terminal ",
            id="header",
        )
        yield StatePanel(id="state-panel")
        yield LogPanel(id="log-panel")
        yield CommandInput(on_submit=self._handle_command, id="cmd-input")
        yield Static(
            " Ctrl+C quit  |  Ctrl+L clear  |  ↑↓ history  |  Enter send",
            id="footer",
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        loop = asyncio.get_event_loop()
        self._node = self._bridge_manager.start(loop)
        self.set_interval(0.1, self._poll_queues)

    def on_unmount(self) -> None:
        self._bridge_manager.stop()

    # ── Polling ───────────────────────────────────────────────────────────────

    async def _poll_queues(self) -> None:
        if self._node is None:
            return

        log_panel: LogPanel = self.query_one("#log-panel", LogPanel)
        state_panel: StatePanel = self.query_one("#state-panel", StatePanel)

        # Drain log queue (up to 20 entries per tick to stay responsive)
        for _ in range(20):
            try:
                entry = self._node.log_queue.get_nowait()
                log_panel.push(entry)
            except asyncio.QueueEmpty:
                break

        # Take only latest state update (drain, keep last)
        last_state: RobotState | None = None
        while True:
            try:
                last_state = self._node.state_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        if last_state is not None:
            state_panel.robot_state = last_state

    # ── Actions ───────────────────────────────────────────────────────────────

    def _handle_command(self, text: str) -> None:
        if self._node:
            self._node.send_command(text)

    def action_clear_log(self) -> None:
        from textual.widgets import RichLog
        log_panel: LogPanel = self.query_one("#log-panel", LogPanel)
        log_panel.query_one(RichLog).clear()

    def action_quit(self) -> None:
        self._bridge_manager.stop()
        self.exit()


def main() -> None:
    app = WalleTerminalApp()
    app.run()


if __name__ == "__main__":
    main()
