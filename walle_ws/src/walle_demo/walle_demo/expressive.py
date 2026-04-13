#!/usr/bin/env python3
"""Expressive motion sequencer — integrated with YOLOv8 detections.

Normal mode : cycles through predefined head/arm poses.
Tracking mode: head follows the highest-confidence detected object in the camera frame.
               Arms raise to a "greeting" pose when a person is detected.
"""

from __future__ import annotations

import json
from typing import List, Optional, Sequence, Tuple

import rclpy
from builtin_interfaces.msg import Duration
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# Image geometry (must match camera URDF: 640×480)
IMAGE_CENTER = 320.0
MAX_HEAD_YAW = 0.65    # rad
DETECTION_TIMEOUT = 2.5  # seconds


class ExpressiveMotion(Node):
    """Publishes periodic joint goals; reacts to YOLO detections for lifelike tracking."""

    def __init__(self) -> None:
        super().__init__('walle_expressive_motion')

        self.declare_parameter('head_topic', '/head_controller/joint_trajectory')
        self.declare_parameter('arm_topic',  '/arm_controller/joint_trajectory')
        self.declare_parameter('period_sec', 3.0)

        head_topic = self.get_parameter('head_topic').get_parameter_value().string_value
        arm_topic  = self.get_parameter('arm_topic').get_parameter_value().string_value
        period_sec = float(self.get_parameter('period_sec').value)

        self.head_pub = self.create_publisher(JointTrajectory, head_topic, 10)
        self.arm_pub  = self.create_publisher(JointTrajectory, arm_topic,  10)

        # ── Pose libraries ──────────────────────────────────────────────────
        # (head_yaw, head_pitch)  — yaw: + left, - right
        self.idle_head_poses: List[Tuple[float, float]] = [
            ( 0.55, -0.08),
            (-0.50,  0.05),
            ( 0.00, -0.18),
            ( 0.35,  0.10),
        ]
        # (left_arm, right_arm)
        self.idle_arm_poses: List[Tuple[float, float]] = [
            ( 0.40, -0.40),
            ( 0.15, -0.15),
            ( 0.52, -0.52),
            ( 0.20, -0.20),
        ]
        # Greeting arm pose (person detected)
        self.GREET_ARMS  = (0.70, -0.70)
        # Curious arm pose  (object detected)
        self.CURIOUS_ARMS = (0.35, -0.10)

        self.index = 0

        # ── Detection state ─────────────────────────────────────────────────
        self._det_label:  Optional[str]   = None
        self._det_cx:     Optional[float] = None   # pixel x of bbox centre
        self._det_conf:   float           = 0.0
        self._det_time:   Optional[Time]  = None
        self._is_person:  bool            = False

        # ── Subscriptions ───────────────────────────────────────────────────
        self.create_subscription(String, '/detections',      self._detection_cb,    10)
        self.create_subscription(String, '/vlm/detections',  self._detection_cb,    10)
        self.create_subscription(String, '/vlm/action_plan', self._vlm_plan_cb,     10)
        self.create_subscription(String, '/behavior_state',  self._behavior_state_cb, 10)

        self._vlm_state = 'IDLE'

        # ── Timers ──────────────────────────────────────────────────────────
        self.startup_timer = self.create_timer(1.5, self._start_sequence)
        self.period_sec    = max(period_sec, 1.0)
        self.motion_timer  = None

        self.get_logger().info('Expressive motion node started (YOLO-integrated).')

    # ── VLM callbacks ───────────────────────────────────────────────────────

    def _behavior_state_cb(self, msg: String) -> None:
        self._vlm_state = msg.data

    def _vlm_plan_cb(self, msg: String) -> None:
        """React to VLM action plan — override arm/head for VLM states."""
        try:
            import json
            plan = json.loads(msg.data)
        except Exception:
            return
        status = plan.get('status', '')
        action = plan.get('action', {})
        if status == 'reached':
            # Celebration: raise both arms + nod head
            self._pub_trajectory(self.arm_pub, ['left_arm_joint', 'right_arm_joint'],
                                 [0.85, -0.85], 1.2)
            self._pub_trajectory(self.head_pub, ['head_yaw_joint', 'head_pitch_joint'],
                                 [0.0, -0.3], 0.8)
        elif status == 'approaching':
            # Lean head forward curiously
            head_yaw = float(action.get('head_yaw', 0.0))
            self._pub_trajectory(self.head_pub, ['head_yaw_joint', 'head_pitch_joint'],
                                 [head_yaw, 0.1], 0.6)

    # ── Detection callback ───────────────────────────────────────────────────

    def _detection_cb(self, msg: String) -> None:
        try:
            dets = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        if not dets:
            return

        # Pick highest-confidence detection; prefer persons
        best = max(dets, key=lambda d: d.get('confidence', 0.0))
        persons = [d for d in dets if d.get('label') == 'person']
        if persons:
            best = max(persons, key=lambda d: d.get('confidence', 0.0))

        bbox = best.get('bbox', [0, 0, 0, 0])
        cx   = (bbox[0] + bbox[2]) / 2.0

        self._det_label  = best.get('label', '')
        self._det_cx     = cx
        self._det_conf   = float(best.get('confidence', 0.0))
        self._det_time   = self.get_clock().now()
        self._is_person  = (self._det_label == 'person')

    # ── Sequence control ─────────────────────────────────────────────────────

    def _start_sequence(self) -> None:
        self.startup_timer.cancel()
        self.startup_timer = None
        self._publish_pose()
        self.motion_timer = self.create_timer(self.period_sec, self._publish_pose)

    def _publish_pose(self) -> None:
        now = self.get_clock().now()

        # Check whether detection is fresh
        tracking = False
        if self._det_time is not None and self._det_cx is not None:
            age = (now - self._det_time).nanoseconds / 1e9
            if age < DETECTION_TIMEOUT:
                tracking = True

        if tracking:
            head, arms = self._tracking_poses()
        else:
            # Idle: reset detection state, cycle poses
            self._det_label = None
            self._det_cx    = None
            head = self.idle_head_poses[self.index % len(self.idle_head_poses)]
            arms = self.idle_arm_poses [self.index % len(self.idle_arm_poses)]
            self.index += 1

        self._pub_trajectory(self.head_pub, ['head_yaw_joint', 'head_pitch_joint'], head, 1.2)
        self._pub_trajectory(self.arm_pub,  ['left_arm_joint', 'right_arm_joint'],  arms, 1.4)

    def _tracking_poses(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Compute head/arm poses that track the detected object."""
        assert self._det_cx is not None

        # Map image x → head yaw: object left of centre → yaw positive (look left)
        offset  = (self._det_cx - IMAGE_CENTER) / IMAGE_CENTER   # -1 … +1
        yaw     = -offset * MAX_HEAD_YAW
        yaw     = max(min(yaw, MAX_HEAD_YAW), -MAX_HEAD_YAW)

        if self._is_person:
            pitch = -0.12   # look slightly down at person
            arms  = self.GREET_ARMS
            self.get_logger().info(
                f'[Expressive] GREETING {self._det_label} '
                f'conf={self._det_conf:.2f} head_yaw={yaw:+.2f}',
                throttle_duration_sec=2.0,
            )
        else:
            pitch = 0.05    # look straight ahead at object
            arms  = self.CURIOUS_ARMS
            self.get_logger().info(
                f'[Expressive] CURIOUS → {self._det_label} '
                f'conf={self._det_conf:.2f} head_yaw={yaw:+.2f}',
                throttle_duration_sec=2.0,
            )

        return (yaw, pitch), arms

    # ── Trajectory publisher ─────────────────────────────────────────────────

    def _pub_trajectory(
        self,
        publisher,
        joint_names: Sequence[str],
        positions: Sequence[float],
        duration_sec: float,
    ) -> None:
        msg = JointTrajectory()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.joint_names  = list(joint_names)

        pt = JointTrajectoryPoint()
        pt.positions        = [float(v) for v in positions]
        pt.time_from_start  = Duration(
            sec    = int(duration_sec),
            nanosec= int((duration_sec % 1.0) * 1e9),
        )
        msg.points = [pt]
        publisher.publish(msg)


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = ExpressiveMotion()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
