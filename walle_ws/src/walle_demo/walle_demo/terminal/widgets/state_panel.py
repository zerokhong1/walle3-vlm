"""state_panel.py — Top status bar showing robot state fields."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..ros_bridge import RobotState

_STATE_COLOR = {
    "IDLE":        "dim",
    "PLANNING":    "yellow",
    "SEARCHING":   "cyan",
    "APPROACHING": "blue",
    "CONFIRMING":  "magenta",
    "COMPLETED":   "green",
}

_MODE_COLOR = {
    "VLM_TASK":      "blue",
    "CAM_AVOID":     "yellow",
    "LIDAR_AVOID":   "yellow",
    "WANDER":        "dim",
    "EMERGENCY_STOP": "red bold",
}

_CHANNEL_COLOR = {
    "SAFETY": "red bold",
    "VLM":    "blue",
    "WANDER": "dim",
    "idle":   "dim",
}


def _color(value: str, mapping: dict) -> str:
    style = mapping.get(value, "white")
    return f"[{style}]{value}[/{style}]"


class StatePanel(Widget):
    """Displays planner state, controller mode, active channel, last command."""

    DEFAULT_CSS = """
    StatePanel {
        height: 5;
        border: round $accent;
        padding: 0 1;
    }
    """

    robot_state: reactive[RobotState] = reactive(RobotState, recompose=True)

    def compose(self) -> ComposeResult:
        s = self.robot_state
        planner = _color(s.planner_state, _STATE_COLOR)
        mode = _color(s.controller_mode, _MODE_COLOR)
        channel = _color(s.active_channel, _CHANNEL_COLOR)
        cmd = s.last_command or "—"

        yield Static(
            f"  Planner : {planner}\n"
            f"  Mode    : {mode}\n"
            f"  Channel : {channel}\n"
            f"  Command : [italic]{cmd}[/italic]",
            markup=True,
        )
