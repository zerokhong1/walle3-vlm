#!/usr/bin/env python3
"""Reactive obstacle-avoidance wander controller — integrated with YOLOv8 + VLM override.

Behavior priority (highest → lowest):
  0. VLM_TASK     — vlm_planner issued an action plan → execute VLM command
  1. ATTENTION    — person detected by camera  → stop + rotate to face person
  2. CURIOUS      — interesting object detected → slow approach
  2.5 CAM_AVOID   — camera sees low obstacle LIDAR missed → turn away
  3. AVOID        — LiDAR obstacle ahead       → turn away
  4. WANDER       — open space                 → cruise forward

Low-obstacle fix (Option 3):
  - LIDAR mount lowered in URDF: z=0.03 → z=-0.05 (scans at ~0.18 m from ground)
  - Camera-based obstacle detection: analyzes bottom 25% of frame for objects
    that are below the LIDAR scan plane using edge density + color divergence.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np
import rclpy
import rclpy.duration
from geometry_msgs.msg import TwistStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import Image as ImageMsg
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

# ── Detection categories ────────────────────────────────────────────────────
PERSON_CLASSES  = {'person'}
CURIOUS_CLASSES = {'bottle', 'cup', 'sports ball', 'chair', 'teddy bear',
                   'cat', 'dog', 'backpack', 'suitcase'}

# Image geometry (must match camera URDF: 640×480)
IMAGE_WIDTH  = 640.0
IMAGE_CENTER = IMAGE_WIDTH / 2.0

DETECTION_TIMEOUT = 2.5   # seconds before a detection is considered stale

# Camera obstacle thresholds
_CAM_COLOR_DIFF_THRESH = 28.0   # mean pixel diff vs floor sample
_CAM_EDGE_DENSITY_THRESH = 0.06  # fraction of edge pixels in ROI
_CAM_FRAME_MAX_AGE = 1.2         # seconds; stale frame → skip camera check


@dataclass
class ScanState:
    ranges: List[float]
    angle_min: float
    angle_increment: float
    range_min: float
    range_max: float


@dataclass
class DetectionHit:
    label: str
    confidence: float
    center_x: float        # pixel x of bbox centre (0 = left, IMAGE_WIDTH = right)
    timestamp: Time = field(default_factory=Time)


class ReactiveWander(Node):
    """Drive forward when clear; react to YOLO detections with priority behaviours."""

    def __init__(self) -> None:
        super().__init__('walle_reactive_wander')

        # ── Parameters ─────────────────────────────────────────────────────
        self.declare_parameter('cmd_topic', '/diff_drive_base_controller/cmd_vel')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('safe_distance', 0.65)
        self.declare_parameter('cruise_speed', 0.22)
        self.declare_parameter('turn_speed', 1.05)
        self.declare_parameter('control_rate_hz', 10.0)

        cmd_topic       = self.get_parameter('cmd_topic').get_parameter_value().string_value
        scan_topic      = self.get_parameter('scan_topic').get_parameter_value().string_value
        self.safe_distance  = float(self.get_parameter('safe_distance').value)
        self.cruise_speed   = float(self.get_parameter('cruise_speed').value)
        self.turn_speed     = float(self.get_parameter('turn_speed').value)
        control_rate_hz     = float(self.get_parameter('control_rate_hz').value)

        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        img_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=2,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        # ── Publishers / Subscribers ────────────────────────────────────────
        self.cmd_pub      = self.create_publisher(TwistStamped, cmd_topic, 10)
        self.state_pub    = self.create_publisher(String, '/behavior_state', 10)
        self.scan_sub     = self.create_subscription(LaserScan, scan_topic, self._scan_cb, qos)
        self.img_sub      = self.create_subscription(ImageMsg, '/camera/image_raw',
                                                      self._image_cb, img_qos)
        self.det_sub      = self.create_subscription(String, '/detections',      self._detection_cb, 10)
        self.vlm_det_sub  = self.create_subscription(String, '/vlm/detections',  self._detection_cb, 10)
        self.vlm_plan_sub = self.create_subscription(String, '/vlm/action_plan', self._vlm_plan_cb,  10)
        self.timer        = self.create_timer(1.0 / max(control_rate_hz, 1.0), self._control_loop)

        # ── State ───────────────────────────────────────────────────────────
        self.scan_state: Optional[ScanState] = None
        self.turn_until     = self.get_clock().now()
        self.turn_direction = 1.0
        self.bias           = 0.0
        self.last_log_time  = self.get_clock().now()

        self.person_hit:  Optional[DetectionHit] = None
        self.curious_hit: Optional[DetectionHit] = None

        # VLM override — when vlm_planner is active, yield control
        self._vlm_active  = False
        self._vlm_timeout = self.get_clock().now()

        # Camera obstacle detection state
        self._cam_frame: Optional[np.ndarray] = None
        self._cam_stamp: Optional[Time]        = None
        self._floor_sample: Optional[np.ndarray] = None  # cached floor color BGR

        self.get_logger().info(
            'Reactive wander node started (YOLO + VLM + camera low-obstacle detection).'
        )

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _scan_cb(self, msg: LaserScan) -> None:
        self.scan_state = ScanState(
            ranges=list(msg.ranges),
            angle_min=msg.angle_min,
            angle_increment=msg.angle_increment,
            range_min=msg.range_min,
            range_max=msg.range_max,
        )

    def _image_cb(self, msg: ImageMsg) -> None:
        """Store latest camera frame as BGR numpy array."""
        try:
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, 3)
            # Bridge publishes rgb8 → convert to BGR for OpenCV
            if msg.encoding in ('rgb8', 'RGB8'):
                frame = frame[:, :, ::-1].copy()
            else:
                frame = frame.copy()
            self._cam_frame = frame
            self._cam_stamp = self.get_clock().now()
        except Exception:
            pass

    def _vlm_plan_cb(self, msg: String) -> None:
        """When VLM planner publishes a plan, yield control for up to 5 s."""
        try:
            plan = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        status = plan.get('status', 'searching')
        if status in ('reached', 'not_found', 'completed'):
            self._vlm_active = False
        else:
            self._vlm_active  = True
            self._vlm_timeout = self.get_clock().now() + rclpy.duration.Duration(seconds=5)

    def _detection_cb(self, msg: String) -> None:
        try:
            dets = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        now = self.get_clock().now()
        self.person_hit  = None
        self.curious_hit = None

        for det in dets:
            label  = det.get('label', '')
            conf   = float(det.get('confidence', 0.0))
            bbox   = det.get('bbox', [0, 0, 0, 0])
            cx     = (bbox[0] + bbox[2]) / 2.0

            if label in PERSON_CLASSES and conf >= 0.5:
                if self.person_hit is None or conf > self.person_hit.confidence:
                    self.person_hit = DetectionHit(label, conf, cx, now)

            elif label in CURIOUS_CLASSES and conf >= 0.40 and self.person_hit is None:
                if self.curious_hit is None or conf > self.curious_hit.confidence:
                    self.curious_hit = DetectionHit(label, conf, cx, now)

    # ── Camera obstacle detection ────────────────────────────────────────────

    def _check_camera_low_obstacle(self) -> Tuple[bool, str]:
        """
        Detect low obstacles (below LIDAR scan height) using camera.

        Method:
        1. Sample floor color from the very bottom corners of the frame
           (corners are rarely occluded by obstacles).
        2. Analyze a center-bottom ROI (60-85% from top, center 70% width) —
           this region corresponds to the ground 0.3-1.5 m in front of the robot.
        3. If ROI has high color divergence from floor AND high edge density →
           there is a physical object in the path that LIDAR misses.

        Returns (obstacle_detected, side_of_obstacle: 'left'|'right'|'center').
        """
        if self._cam_frame is None:
            return False, 'center'

        # Skip stale frames
        if self._cam_stamp is not None:
            age = (self.get_clock().now() - self._cam_stamp).nanoseconds / 1e9
            if age > _CAM_FRAME_MAX_AGE:
                return False, 'center'

        frame = self._cam_frame
        h, w  = frame.shape[:2]

        # ── 1. Floor color sample (bottom corners, 30×15 px each) ──────────
        corner_l = frame[h - 15:h,      :30 ].astype(np.float32)
        corner_r = frame[h - 15:h,  w - 30:w].astype(np.float32)
        floor_mean = np.concatenate([corner_l, corner_r], axis=1).mean(axis=(0, 1))

        # ── 2. ROI: bottom-center zone ──────────────────────────────────────
        y0 = int(h * 0.60)
        y1 = int(h * 0.85)
        x0 = int(w * 0.15)
        x1 = int(w * 0.85)
        roi = frame[y0:y1, x0:x1]

        # ── 3. Color divergence from floor ──────────────────────────────────
        diff = float(np.abs(roi.astype(np.float32) - floor_mean).mean())

        # ── 4. Edge density in ROI ───────────────────────────────────────────
        gray  = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 110)
        edge_density = float(np.count_nonzero(edges)) / max(edges.size, 1)

        obstacle_detected = (diff > _CAM_COLOR_DIFF_THRESH) and \
                            (edge_density > _CAM_EDGE_DENSITY_THRESH)

        if not obstacle_detected:
            return False, 'center'

        # ── 5. Determine which side the obstacle is on ───────────────────────
        mid       = roi.shape[1] // 2
        left_diff  = float(np.abs(roi[:, :mid].astype(np.float32) - floor_mean).mean())
        right_diff = float(np.abs(roi[:, mid:].astype(np.float32) - floor_mean).mean())
        side = 'right' if right_diff > left_diff else 'left'

        return True, side

    # ── Main control loop ────────────────────────────────────────────────────

    def _control_loop(self) -> None:
        now = self.get_clock().now()

        # ── Priority 0: VLM task active — yield control to vlm_planner ──────
        if self._vlm_active:
            if now < self._vlm_timeout:
                self._pub_state('VLM_TASK')
                return
            self._vlm_active = False

        # ── Priority 1: ATTENTION (person detected) ─────────────────────────
        if self.person_hit is not None:
            age = (now - self.person_hit.timestamp).nanoseconds / 1e9
            if age < DETECTION_TIMEOUT:
                self._do_attention(self.person_hit)
                self._pub_state('ATTENTION')
                return
            self.person_hit = None

        # ── Priority 2: CURIOUS (interesting object) ────────────────────────
        if self.curious_hit is not None:
            age = (now - self.curious_hit.timestamp).nanoseconds / 1e9
            if age < DETECTION_TIMEOUT:
                self._do_curious(self.curious_hit)
                self._pub_state('CURIOUS')
                return
            self.curious_hit = None

        # ── Priority 2.5: Camera low-obstacle (objects below LIDAR plane) ───
        # Only check when not already turning away from something
        if now >= self.turn_until:
            cam_obs, cam_side = self._check_camera_low_obstacle()
            if cam_obs:
                # Turn AWAY from the obstacle side
                turn_sign = -1.0 if cam_side == 'right' else 1.0
                dur = random.uniform(0.7, 1.2)
                self.turn_until   = now + Duration(seconds=dur)
                self.turn_direction = turn_sign
                self.publish_cmd(0.0, turn_sign * self.turn_speed * 0.75)
                self._maybe_log(
                    f'[CAM] Low obstacle on {cam_side} (below LIDAR) → '
                    f'turning {"left" if turn_sign > 0 else "right"} {dur:.1f}s'
                )
                self._pub_state('CAM_AVOID')
                return

        # ── Priority 3 & 4: LiDAR-based AVOID / WANDER ──────────────────────
        if self.scan_state is None:
            self.publish_cmd(0.0, 0.35)
            self._pub_state('INIT')
            return

        if now < self.turn_until:
            self.publish_cmd(0.0, self.turn_direction * self.turn_speed)
            self._pub_state('AVOID')
            return

        front = self._sector_min(-0.30, 0.30)
        left  = self._sector_min(0.30, 1.20)
        right = self._sector_min(-1.20, -0.30)

        if front < self.safe_distance:
            self.turn_direction = 1.0 if left > right else -1.0
            duration_sec = random.uniform(0.9, 1.6)
            self.turn_until = now + Duration(seconds=duration_sec)
            self.bias = random.uniform(-0.12, 0.12)
            self.publish_cmd(0.0, self.turn_direction * self.turn_speed)
            self._maybe_log(
                f'Obstacle ahead ({front:.2f} m) — turning '
                f'{"left" if self.turn_direction > 0 else "right"} {duration_sec:.1f}s'
            )
            self._pub_state('AVOID')
            return

        # WANDER
        corridor = self._normalize(right) - self._normalize(left)
        angular  = max(min(0.8 * corridor + self.bias, 0.65), -0.65)
        linear   = self.cruise_speed
        if front < self.safe_distance * 1.6:
            linear *= 0.6
        if min(left, right) < self.safe_distance * 0.8:
            linear *= 0.75

        self.bias *= 0.98
        if random.random() < 0.03:
            self.bias = random.uniform(-0.18, 0.18)

        self.publish_cmd(linear, angular)
        self._pub_state('WANDER')

    # ── YOLO-driven behaviours ───────────────────────────────────────────────

    def _do_attention(self, hit: DetectionHit) -> None:
        """Stop and rotate to face the detected person."""
        offset  = (hit.center_x - IMAGE_CENTER) / IMAGE_CENTER   # -1 … +1
        angular = -offset * self.turn_speed * 0.55
        angular = max(min(angular, self.turn_speed), -self.turn_speed)
        self.publish_cmd(0.0, angular)
        self._maybe_log(
            f'[YOLO] ATTENTION — {hit.label} conf={hit.confidence:.2f} '
            f'cx={hit.center_x:.0f}px → angular={angular:+.2f}'
        )

    def _do_curious(self, hit: DetectionHit) -> None:
        """Slowly approach an interesting object while steering toward it."""
        offset  = (hit.center_x - IMAGE_CENTER) / IMAGE_CENTER
        angular = -offset * 0.45
        linear  = self.cruise_speed * 0.45
        self.publish_cmd(linear, angular)
        self._maybe_log(
            f'[YOLO] CURIOUS — {hit.label} conf={hit.confidence:.2f} '
            f'→ approach linear={linear:.2f} angular={angular:+.2f}'
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _sector_min(self, angle_start: float, angle_end: float) -> float:
        state = self.scan_state
        assert state is not None
        if not state.ranges:
            return state.range_max

        i0 = int((angle_start - state.angle_min) / state.angle_increment)
        i1 = int((angle_end   - state.angle_min) / state.angle_increment)
        i0 = max(0, min(i0, len(state.ranges) - 1))
        i1 = max(0, min(i1, len(state.ranges) - 1))
        if i0 > i1:
            i0, i1 = i1, i0

        valid = [v for v in state.ranges[i0:i1 + 1]
                 if math.isfinite(v) and state.range_min < v < state.range_max]
        return min(valid) if valid else state.range_max

    @staticmethod
    def _normalize(value: float, clip_max: float = 2.5) -> float:
        return min(max(value, 0.0), clip_max) / clip_max

    def publish_cmd(self, linear_x: float, angular_z: float) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x  = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        self.cmd_pub.publish(msg)

    def _pub_state(self, state: str) -> None:
        self.state_pub.publish(String(data=state))

    def _maybe_log(self, text: str) -> None:
        now = self.get_clock().now()
        if (now - self.last_log_time).nanoseconds > 2_000_000_000:
            self.get_logger().info(text)
            self.last_log_time = now


def main(args: Optional[List[str]] = None) -> None:
    rclpy.init(args=args)
    node = ReactiveWander()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.publish_cmd(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
