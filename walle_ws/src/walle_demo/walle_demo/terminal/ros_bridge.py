"""ros_bridge.py — Thread-safe bridge between rclpy and the textual asyncio loop.

A background OS thread runs rclpy.spin(). Incoming ROS messages are pushed
into asyncio queues so the TUI can await them without blocking.
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


@dataclass
class RobotState:
    planner_state: str = "IDLE"
    controller_mode: str = "WANDER"
    active_channel: str = "idle"
    last_command: str = ""
    last_plan: dict = field(default_factory=dict)
    last_safety: dict = field(default_factory=dict)
    last_inference: dict = field(default_factory=dict)


class WalleBridge(Node):
    """ROS 2 node that bridges topics into asyncio-safe queues."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__("walle_terminal_bridge")
        self._loop = loop
        self.state = RobotState()
        self._lock = threading.Lock()

        # Queues for streaming log panels (maxsize prevents unbounded growth)
        self.log_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)
        self.state_queue: asyncio.Queue[RobotState] = asyncio.Queue(maxsize=100)

        self._sub_planner = self.create_subscription(
            String, "/planner/state", self._on_planner_state, 10
        )
        self._sub_mode = self.create_subscription(
            String, "/controller/mode", self._on_controller_mode, 10
        )
        self._sub_channel = self.create_subscription(
            String, "/mux/active_channel", self._on_active_channel, 10
        )
        self._sub_plan = self.create_subscription(
            String, "/vlm/action_plan", self._on_action_plan, 10
        )
        self._sub_safety = self.create_subscription(
            String, "/safety/event", self._on_safety_event, 10
        )
        self._sub_infer = self.create_subscription(
            String, "/inference/event", self._on_inference_event, 10
        )
        self._sub_mission_start = self.create_subscription(
            String, "/mission/started", self._on_mission_started, 10
        )
        self._sub_mission_end = self.create_subscription(
            String, "/mission/completed", self._on_mission_completed, 10
        )

        self._cmd_pub = self.create_publisher(String, "/user_command", 10)

    # ── Publishers ────────────────────────────────────────────────────────────

    def send_command(self, text: str) -> None:
        msg = String()
        msg.data = text.strip()
        self._cmd_pub.publish(msg)
        with self._lock:
            self.state.last_command = text.strip()
        self._push_log({"type": "cmd", "text": text.strip()})
        self._push_state()

    # ── Subscribers ───────────────────────────────────────────────────────────

    def _on_planner_state(self, msg: String) -> None:
        with self._lock:
            self.state.planner_state = msg.data.strip()
        self._push_log({"type": "state", "text": f"[STATE] {msg.data.strip()}"})
        self._push_state()

    def _on_controller_mode(self, msg: String) -> None:
        with self._lock:
            self.state.controller_mode = msg.data.strip()
        self._push_state()

    def _on_active_channel(self, msg: String) -> None:
        with self._lock:
            self.state.active_channel = msg.data.strip()
        self._push_state()

    def _on_action_plan(self, msg: String) -> None:
        try:
            plan = json.loads(msg.data)
        except json.JSONDecodeError:
            plan = {"raw": msg.data}
        with self._lock:
            self.state.last_plan = plan
        action = plan.get("action", "?")
        target = plan.get("target", "")
        self._push_log({"type": "plan", "text": f"[PLAN] action={action} target={target}"})
        self._push_state()

    def _on_safety_event(self, msg: String) -> None:
        try:
            ev = json.loads(msg.data)
        except json.JSONDecodeError:
            ev = {"raw": msg.data}
        with self._lock:
            self.state.last_safety = ev
        severity = ev.get("severity", "info").upper()
        etype = ev.get("event_type", "unknown")
        self._push_log({"type": "safety", "severity": severity, "text": f"[SAFETY:{severity}] {etype}"})
        self._push_state()

    def _on_inference_event(self, msg: String) -> None:
        try:
            ev = json.loads(msg.data)
        except json.JSONDecodeError:
            ev = {"raw": msg.data}
        with self._lock:
            self.state.last_inference = ev
        latency = ev.get("latency_ms", 0)
        found = ev.get("target_found", False)
        conf = ev.get("confidence", 0.0)
        self._push_log({
            "type": "infer",
            "text": f"[INFER] {latency:.0f}ms  found={found}  conf={conf:.2f}",
        })

    def _on_mission_started(self, msg: String) -> None:
        try:
            ev = json.loads(msg.data)
        except json.JSONDecodeError:
            ev = {"raw": msg.data}
        cmd = ev.get("user_command", "?")
        self._push_log({"type": "mission", "text": f"[MISSION START] \"{cmd}\""})

    def _on_mission_completed(self, msg: String) -> None:
        try:
            ev = json.loads(msg.data)
        except json.JSONDecodeError:
            ev = {"raw": msg.data}
        success = ev.get("success", False)
        reason = ev.get("reason", "?")
        dur = ev.get("duration_s", 0)
        status = "OK" if success else "FAIL"
        self._push_log({
            "type": "mission",
            "text": f"[MISSION {status}] {reason}  ({dur:.1f}s)",
        })

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _push_log(self, entry: dict) -> None:
        try:
            self._loop.call_soon_threadsafe(self.log_queue.put_nowait, entry)
        except asyncio.QueueFull:
            pass  # drop oldest — TUI is reading too slowly

    def _push_state(self) -> None:
        import copy
        with self._lock:
            snapshot = copy.copy(self.state)
        try:
            self._loop.call_soon_threadsafe(self.state_queue.put_nowait, snapshot)
        except asyncio.QueueFull:
            pass


class RosBridge:
    """Manages rclpy init and the background spin thread."""

    def __init__(self) -> None:
        self._node: Optional[WalleBridge] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self, loop: asyncio.AbstractEventLoop) -> WalleBridge:
        if not rclpy.ok():
            rclpy.init()
        self._node = WalleBridge(loop)
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self._node

    def _spin(self) -> None:
        while self._running and rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.05)

    def stop(self) -> None:
        self._running = False
        if self._node:
            self._node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
