#!/usr/bin/env python3
"""cmd_vel_mux.py — Priority arbitration for /cmd_vel (I-006).

Three channels, fixed priority (lower index = higher priority):

  0  /cmd_vel/safety   EMERGENCY_STOP, LIDAR_AVOID, CAM_AVOID, escape
  1  /cmd_vel/vlm      VLM_TASK normal plan execution
  2  /cmd_vel/wander   WANDER, ATTENTION, CURIOUS

The mux selects the highest-priority channel that received a message
within its timeout window, then forwards it to the diff-drive controller
at 50 Hz. Publishes the active channel name to /mux/active_channel.

Timeout rationale:
  safety : 0.25 s — wander runs at 10 Hz (100 ms/msg), need ≥2 cycles
  vlm    : 0.15 s — vlm_planner runs at 50 Hz (20 ms/msg), 7 cycles
  wander : 0.25 s — wander runs at 10 Hz, need ≥2 cycles
"""

from __future__ import annotations

import time
from typing import Optional

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from std_msgs.msg import String

_CHANNELS = [
    ('/cmd_vel/safety', 'SAFETY', 0.25),
    ('/cmd_vel/vlm',    'VLM',    0.15),
    ('/cmd_vel/wander', 'WANDER', 0.25),
]


class CmdVelMux(Node):
    def __init__(self) -> None:
        super().__init__('cmd_vel_mux')

        self._out_pub  = self.create_publisher(
            TwistStamped, '/diff_drive_base_controller/cmd_vel', 10)
        self._name_pub = self.create_publisher(String, '/mux/active_channel', 10)

        self._msgs:  dict[str, Optional[TwistStamped]] = {ch: None for ch, _, _ in _CHANNELS}
        self._times: dict[str, float]                  = {ch: 0.0  for ch, _, _ in _CHANNELS}

        for ch, _, _ in _CHANNELS:
            self.create_subscription(
                TwistStamped, ch,
                lambda msg, c=ch: self._cb(c, msg),
                10,
            )

        self.create_timer(1.0 / 50.0, self._mux_loop)
        self._last_active = ''
        self._last_pub_t  = 0.0
        self.get_logger().info('cmd_vel_mux ready (safety > vlm > wander)')

    def _cb(self, channel: str, msg: TwistStamped) -> None:
        self._msgs[channel]  = msg
        self._times[channel] = time.monotonic()

    def _mux_loop(self) -> None:
        now = time.monotonic()
        winner: Optional[TwistStamped] = None
        active  = 'idle'

        for ch, name, timeout in _CHANNELS:
            msg = self._msgs[ch]
            if msg is not None and (now - self._times[ch]) < timeout:
                winner = msg
                active = name
                break

        if winner is not None:
            out = TwistStamped()
            out.header.stamp    = self.get_clock().now().to_msg()
            out.header.frame_id = winner.header.frame_id
            out.twist           = winner.twist
            self._out_pub.publish(out)

        if active != self._last_active:
            self.get_logger().info(f'[MUX] active channel: {self._last_active} → {active}')
            self._last_active = active

        if now - self._last_pub_t > 2.0:
            self._name_pub.publish(String(data=active))
            self._last_pub_t = now


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CmdVelMux()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
