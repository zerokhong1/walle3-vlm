#!/usr/bin/env python3
"""rosbag_trigger_node.py — Auto-record rosbag on safety events (I-005).

Subscribes to /safety/event. On HIGH or CRITICAL severity, starts a 60 s
rosbag recording of all diagnostic topics. Files go to ~/walle_bags/.

A new HIGH/CRITICAL event during an active recording extends the window by
30 s, capped at 120 s total, so a stuck loop produces a single long bag
rather than many small fragments.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

_RECORD_TOPICS = [
    '/camera/image_raw',
    '/scan',
    '/planner/state',
    '/controller/mode',
    '/mux/active_channel',
    '/cmd_vel/safety',
    '/cmd_vel/vlm',
    '/cmd_vel/wander',
    '/vlm/action_plan',
    '/safety/event',
    '/inference/event',
    '/mission/started',
    '/mission/completed',
    '/diff_drive_base_controller/odom',
    '/diff_drive_base_controller/cmd_vel',
]

_BAG_DIR         = os.path.expanduser('~/walle_bags')
_RECORD_SECS     = 60
_MAX_RECORD_SECS = 120
_EXTEND_SECS     = 30
_TRIGGER_SEVS    = frozenset({'high', 'critical', 'HIGH', 'CRITICAL'})


class RosbagTrigger(Node):
    def __init__(self) -> None:
        super().__init__('rosbag_trigger')
        os.makedirs(_BAG_DIR, exist_ok=True)

        self.create_subscription(String, '/safety/event', self._safety_cb, 10)
        self.create_timer(1.0, self._check_stop)

        self._proc:         Optional[subprocess.Popen] = None
        self._record_until: float = 0.0
        self._bag_start:    float = 0.0

        self.get_logger().info(f'RosbagTrigger ready → {_BAG_DIR}')

    def _safety_cb(self, msg: String) -> None:
        try:
            ev = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if ev.get('severity', '') not in _TRIGGER_SEVS:
            return

        now     = time.monotonic()
        ev_type = ev.get('event_type', 'unknown')

        if self._proc is not None and self._proc.poll() is None:
            new_until = min(now + _EXTEND_SECS, self._bag_start + _MAX_RECORD_SECS)
            if new_until > self._record_until:
                self._record_until = new_until
                self.get_logger().info(
                    f'[BAG] Extended to +{self._record_until - now:.0f}s (event={ev_type})'
                )
        else:
            self._record_until = now + _RECORD_SECS
            self._bag_start    = now
            self._start_bag(ev_type)

    def _start_bag(self, trigger: str) -> None:
        ts   = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        path = os.path.join(_BAG_DIR, f'safety_{trigger}_{ts}')
        cmd  = ['ros2', 'bag', 'record', '-o', path] + _RECORD_TOPICS
        self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.get_logger().info(f'[BAG] Recording → {path} (trigger={trigger})')

    def _check_stop(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            return
        if time.monotonic() >= self._record_until:
            self._proc.terminate()
            self._proc = None
            self.get_logger().info('[BAG] Recording stopped.')

    def destroy_node(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RosbagTrigger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
