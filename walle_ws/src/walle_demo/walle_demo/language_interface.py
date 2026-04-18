#!/usr/bin/env python3
"""Language Interface — nhận lệnh từ user qua terminal / ROS topic.

Publish:
  /user_command (std_msgs/String)

Dùng:
  ros2 run walle_demo language_interface          # interactive terminal
  ros2 topic pub --once /user_command std_msgs/msg/String "{data: 'tìm ghế'}"
"""

from __future__ import annotations

import sys
import threading
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# ── Built-in command aliases ──────────────────────────────────────────────────

ALIASES = {
    # Vietnamese shortcuts
    'dừng':        'stop',
    'dừng lại':    'stop',
    'chào':        'wave hello',
    'tìm':         'search for objects around you',
    'mô tả':       'describe what you see',
    # English shortcuts
    'stop':        'stop all movement immediately',
    'hello':       'wave hello and greet',
    'look':        'describe what you see in front of you',
    'help':        None,   # special: print help
}

HELP_TEXT = """
╔══════════════════════════════════════════════════════╗
║         WallE3 v2 — Language Interface               ║
╠══════════════════════════════════════════════════════╣
║  Nhập lệnh bằng tiếng Việt hoặc English:            ║
║                                                      ║
║  "đi tới chai nước xanh"                            ║
║  "có gì ở phía trước?"                              ║
║  "tìm ghế"                                          ║
║  "chào" / "wave hello"                              ║
║  "dừng lại" / "stop"                                ║
║  "mô tả" — mô tả scene hiện tại                     ║
║                                                      ║
║  Ctrl+C để thoát                                    ║
╚══════════════════════════════════════════════════════╝
"""


class LanguageInterface(Node):
    """Publish user commands to /user_command topic."""

    def __init__(self) -> None:
        super().__init__('walle_language_interface')

        self.cmd_pub = self.create_publisher(String, '/user_command', 10)

        # Subscribe to planner/state and scene to give user feedback
        self.create_subscription(String, '/planner/state',       self._state_cb,  10)
        self.create_subscription(String, '/vlm/scene_description', self._scene_cb, 10)

        self._last_state = 'IDLE'
        self._last_scene = ''

        # Start terminal input in background thread
        t = threading.Thread(target=self._terminal_loop, daemon=True)
        t.start()

        self.get_logger().info('Language interface ready. Type commands in the terminal.')
        print(HELP_TEXT)

    # ── Feedback callbacks ────────────────────────────────────────────────────

    def _state_cb(self, msg: String) -> None:
        state = msg.data
        if state != self._last_state:
            print(f'\n[Robot] State → {state}')
            self._last_state = state

    def _scene_cb(self, msg: String) -> None:
        scene = msg.data
        if scene and scene != self._last_scene:
            print(f'[Robot] Scene: {scene}')
            self._last_scene = scene

    # ── Terminal input loop ───────────────────────────────────────────────────

    def _terminal_loop(self) -> None:
        print('> ', end='', flush=True)
        for line in sys.stdin:
            cmd = line.strip()
            if not cmd:
                print('> ', end='', flush=True)
                continue

            # Resolve alias
            resolved = ALIASES.get(cmd.lower())
            if resolved is None and cmd.lower() in ALIASES:
                # 'help' special case
                print(HELP_TEXT)
                print('> ', end='', flush=True)
                continue
            if resolved:
                cmd = resolved

            self._publish(cmd)
            print(f'[Sent] "{cmd}"')
            print('> ', end='', flush=True)

    def _publish(self, cmd: str) -> None:
        self.cmd_pub.publish(String(data=cmd))
        self.get_logger().info(f'Published command: "{cmd}"')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LanguageInterface()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
