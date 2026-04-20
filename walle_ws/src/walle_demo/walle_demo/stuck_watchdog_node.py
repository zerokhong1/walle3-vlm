#!/usr/bin/env python3
"""stuck_watchdog_node.py — Independent stuck detector (I-007).

Monitors /planner/state + odometry independently of vlm_planner and wander.
If APPROACHING or SEARCHING for > 30 s with < 20 cm displacement → warn.
If > 60 s → publish mission abort and safety critical event.

This is intentionally a separate node so it survives crashes in other nodes
and can be included or excluded from the launch without code changes.
"""

from __future__ import annotations

import json
import math
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String

_STUCK_STATES   = frozenset({'APPROACHING', 'SEARCHING'})
_WARN_SECS      = 30.0
_ABORT_SECS     = 60.0
_DISP_THRESH    = 0.20   # metres — less than this means stuck


class StuckWatchdog(Node):
    def __init__(self) -> None:
        super().__init__('stuck_watchdog')

        self._safety_pub  = self.create_publisher(String, '/safety/event',      10)
        self._mission_pub = self.create_publisher(String, '/mission/completed',  10)

        self.create_subscription(String,   '/planner/state',                   self._state_cb, 10)
        self.create_subscription(Odometry, '/diff_drive_base_controller/odom', self._odom_cb,  10)
        self.create_timer(1.0, self._check)

        self._state      = 'IDLE'
        self._entry_t    = 0.0
        self._entry_x    = 0.0
        self._entry_y    = 0.0
        self._odom_x     = 0.0
        self._odom_y     = 0.0
        self._warned     = False
        self._aborted    = False

        self.get_logger().info(
            f'StuckWatchdog ready (warn={_WARN_SECS:.0f}s abort={_ABORT_SECS:.0f}s '
            f'disp_thresh={_DISP_THRESH:.2f}m)'
        )

    def _state_cb(self, msg: String) -> None:
        state = msg.data.strip()
        if state == self._state:
            return
        self._state = state
        if state in _STUCK_STATES:
            self._entry_t = time.monotonic()
            self._entry_x = self._odom_x
            self._entry_y = self._odom_y
            self._warned  = False
            self._aborted = False

    def _odom_cb(self, msg: Odometry) -> None:
        self._odom_x = msg.pose.pose.position.x
        self._odom_y = msg.pose.pose.position.y

    def _displacement(self) -> float:
        dx = self._odom_x - self._entry_x
        dy = self._odom_y - self._entry_y
        return math.sqrt(dx * dx + dy * dy)

    def _check(self) -> None:
        if self._state not in _STUCK_STATES:
            return

        elapsed = time.monotonic() - self._entry_t
        disp    = self._displacement()

        if disp >= _DISP_THRESH:
            self._entry_t = time.monotonic()
            self._entry_x = self._odom_x
            self._entry_y = self._odom_y
            self._warned  = False
            self._aborted = False
            return

        if elapsed > _ABORT_SECS and not self._aborted:
            self._aborted = True
            self.get_logger().error(
                f'[WATCHDOG] ABORT: {self._state} stuck for {elapsed:.0f}s '
                f'disp={disp:.3f}m < {_DISP_THRESH}m — publishing mission abort'
            )
            self._pub_safety('stuck_abort', 'critical')
            self._pub_mission_abort()

        elif elapsed > _WARN_SECS and not self._warned:
            self._warned = True
            self.get_logger().warn(
                f'[WATCHDOG] STUCK: {self._state} for {elapsed:.0f}s '
                f'disp={disp:.3f}m < {_DISP_THRESH}m'
            )
            self._pub_safety('stuck', 'high')

    def _pub_safety(self, event_type: str, severity: str) -> None:
        self._safety_pub.publish(String(data=json.dumps({
            'event_type': event_type,
            'severity':   severity,
            'timestamp':  self.get_clock().now().nanoseconds / 1e9,
        })))

    def _pub_mission_abort(self) -> None:
        self._mission_pub.publish(String(data=json.dumps({
            'mission_id':         'unknown',
            'success':            False,
            'duration_s':         _ABORT_SECS,
            'intervention_count': 0,
            'reason':             'stuck_timeout_60s',
        })))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StuckWatchdog()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
