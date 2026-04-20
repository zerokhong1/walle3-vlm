#!/usr/bin/env python3
"""Reactive obstacle-avoidance wander controller — integrated with YOLOv8 + VLM override.

Publishes /controller/mode (contract v1.0):
  VLM_TASK      — vlm_planner issued an action plan → execute VLM command
  CAM_AVOID     — camera sees low obstacle LiDAR missed → reverse + turn
  LIDAR_AVOID   — LiDAR obstacle or stuck escape maneuver
  WANDER        — open space cruise, person/object detection, or init
  EMERGENCY_STOP — not used here (emitted by vlm_planner on hard stop)

Internal behavior priority (highest → lowest):
  0. VLM_TASK     — vlm_planner issued an action plan
  1. ATTENTION    — person detected by camera  → stop + rotate to face person
  2. CURIOUS      — interesting object detected → slow approach
  2.5 CAM_AVOID   — camera sees low obstacle LiDAR missed → reverse + turn
  3. ESCAPE       — stuck detector triggered (no movement despite cmd) → emergency escape
  4. AVOID        — LiDAR obstacle ahead → reverse + turn
  5. WANDER       — open space → cruise forward

Anti-stuck fixes:
  - Front sector widened: ±0.30 → ±0.50 rad (catches diagonal obstacles)
  - Diagonal sectors: front-left and front-right at ±30°–±60° with lower threshold
  - REVERSE before TURN: back up 0.4s before turning (clears wedged robots)
  - Stuck detector: odom/cmd_vel cross-check; if moving cmd but no position
    change for > 2.5s → emergency reverse + random large turn
  - Corner escape: if front + both sides blocked → full reverse
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
from nav_msgs.msg import Odometry
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

IMAGE_WIDTH  = 640.0
IMAGE_CENTER = IMAGE_WIDTH / 2.0
DETECTION_TIMEOUT = 2.5

# Camera obstacle thresholds (lowered for better small-object detection)
_CAM_COLOR_DIFF_THRESH  = 18.0   # was 28.0 — more sensitive
_CAM_EDGE_DENSITY_THRESH = 0.04  # was 0.06 — more sensitive
_CAM_FRAME_MAX_AGE       = 1.2

# Stuck detection
_STUCK_CMD_THRESH   = 0.04   # m/s — minimum cmd to count as "moving command"
_STUCK_VEL_THRESH   = 0.03   # m/s — maximum actual speed to count as "not moving"
_STUCK_TIMEOUT_SEC  = 2.0    # seconds before declaring stuck (was 2.5)


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
    center_x: float
    timestamp: Time = field(default_factory=Time)


class ReactiveWander(Node):
    def __init__(self) -> None:
        super().__init__('walle_reactive_wander')

        # ── Parameters ─────────────────────────────────────────────────────
        self.declare_parameter('cmd_topic',       '/diff_drive_base_controller/cmd_vel')
        self.declare_parameter('scan_topic',      '/scan')
        self.declare_parameter('safe_distance',   0.65)
        self.declare_parameter('cruise_speed',    0.22)
        self.declare_parameter('turn_speed',      1.05)
        self.declare_parameter('control_rate_hz', 10.0)

        cmd_topic       = self.get_parameter('cmd_topic').get_parameter_value().string_value
        scan_topic      = self.get_parameter('scan_topic').get_parameter_value().string_value
        self.safe_dist  = float(self.get_parameter('safe_distance').value)
        self.cruise_spd = float(self.get_parameter('cruise_speed').value)
        self.turn_spd   = float(self.get_parameter('turn_speed').value)
        rate_hz         = float(self.get_parameter('control_rate_hz').value)

        be_qos = QoSProfile(
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
        # I-006: split into two mux channels
        self.safety_cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel/safety', 10)
        self.nav_cmd_pub    = self.create_publisher(TwistStamped, '/cmd_vel/wander', 10)
        self.mode_pub   = self.create_publisher(String, '/controller/mode', 10)
        self.safety_pub = self.create_publisher(String, '/safety/event', 10)

        self.create_subscription(LaserScan,    scan_topic,                              self._scan_cb,      be_qos)
        self.create_subscription(ImageMsg,     '/camera/image_raw',                     self._image_cb,     img_qos)
        self.create_subscription(Odometry,     '/diff_drive_base_controller/odom',      self._odom_cb,      be_qos)
        self.create_subscription(TwistStamped, '/diff_drive_base_controller/cmd_vel',   self._cmdvel_cb,    be_qos)
        self.create_subscription(String, '/detections',      self._detection_cb, 10)
        self.create_subscription(String, '/vlm/detections',  self._detection_cb, 10)
        self.create_subscription(String, '/vlm/action_plan', self._vlm_plan_cb,  10)

        self.timer = self.create_timer(1.0 / max(rate_hz, 1.0), self._control_loop)

        # ── LiDAR state ─────────────────────────────────────────────────────
        self.scan_state: Optional[ScanState] = None

        # ── Motion state ────────────────────────────────────────────────────
        self.turn_until     = self.get_clock().now()
        self.turn_direction = 1.0
        self.reverse_until  = self.get_clock().now()   # NEW: reverse phase
        self.bias           = 0.0
        self.last_log_time  = self.get_clock().now()

        # ── Detection state ─────────────────────────────────────────────────
        self.person_hit:  Optional[DetectionHit] = None
        self.curious_hit: Optional[DetectionHit] = None

        # ── VLM override ────────────────────────────────────────────────────
        self._vlm_active  = False
        self._vlm_timeout = self.get_clock().now()

        # ── Camera obstacle detection ───────────────────────────────────────
        self._cam_frame: Optional[np.ndarray] = None
        self._cam_stamp: Optional[Time]        = None

        # ── Stuck detection ─────────────────────────────────────────────────
        self._odom_vx: float        = 0.0
        self._cmd_vx:  float        = 0.0    # velocity wander commands
        self._actual_cmd_vx: float  = 0.0    # velocity from ANY publisher (incl. vlm_planner)
        self._stuck_since: Optional[Time] = None
        self._escaping: bool        = False  # True while in escape maneuver

        self.get_logger().info(
            'Reactive wander (anti-stuck v2): wider sectors, reverse-before-turn, stuck detector.'
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

    def _odom_cb(self, msg: Odometry) -> None:
        vx = msg.twist.twist.linear.x
        vy = msg.twist.twist.linear.y
        self._odom_vx = math.sqrt(vx * vx + vy * vy)

    def _cmdvel_cb(self, msg: TwistStamped) -> None:
        """Track actual commanded velocity from ANY publisher (wander OR vlm_planner)."""
        self._actual_cmd_vx = abs(msg.twist.linear.x)

    def _image_cb(self, msg: ImageMsg) -> None:
        try:
            frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(
                msg.height, msg.width, 3)
            if msg.encoding in ('rgb8', 'RGB8'):
                frame = frame[:, :, ::-1].copy()
            else:
                frame = frame.copy()
            self._cam_frame = frame
            self._cam_stamp = self.get_clock().now()
        except Exception:
            pass

    def _vlm_plan_cb(self, msg: String) -> None:
        try:
            plan = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        status = plan.get('status', 'searching')
        if status in ('reached', 'not_found', 'completed'):
            self._vlm_active = False
        else:
            self._vlm_active  = True
            self._vlm_timeout = self.get_clock().now() + rclpy.duration.Duration(seconds=15)

    def _detection_cb(self, msg: String) -> None:
        try:
            dets = json.loads(msg.data)
        except json.JSONDecodeError:
            return
        now = self.get_clock().now()
        self.person_hit  = None
        self.curious_hit = None
        for det in dets:
            label = det.get('label', '')
            conf  = float(det.get('confidence', 0.0))
            bbox  = det.get('bbox', [0, 0, 0, 0])
            cx    = (bbox[0] + bbox[2]) / 2.0
            if label in PERSON_CLASSES and conf >= 0.5:
                if self.person_hit is None or conf > self.person_hit.confidence:
                    self.person_hit = DetectionHit(label, conf, cx, now)
            elif label in CURIOUS_CLASSES and conf >= 0.40 and self.person_hit is None:
                if self.curious_hit is None or conf > self.curious_hit.confidence:
                    self.curious_hit = DetectionHit(label, conf, cx, now)

    # ── Camera low-obstacle detection ────────────────────────────────────────

    def _check_camera_low_obstacle(self) -> Tuple[bool, str]:
        if self._cam_frame is None:
            return False, 'center'
        if self._cam_stamp is not None:
            age = (self.get_clock().now() - self._cam_stamp).nanoseconds / 1e9
            if age > _CAM_FRAME_MAX_AGE:
                return False, 'center'

        frame = self._cam_frame
        h, w  = frame.shape[:2]

        corner_l   = frame[h - 15:h,     :30].astype(np.float32)
        corner_r   = frame[h - 15:h, w - 30:w].astype(np.float32)
        floor_mean = np.concatenate([corner_l, corner_r], axis=1).mean(axis=(0, 1))

        y0 = int(h * 0.60); y1 = int(h * 0.85)
        x0 = int(w * 0.15); x1 = int(w * 0.85)
        roi  = frame[y0:y1, x0:x1]
        diff = float(np.abs(roi.astype(np.float32) - floor_mean).mean())

        gray  = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 110)
        edge_density = float(np.count_nonzero(edges)) / max(edges.size, 1)

        if not (diff > _CAM_COLOR_DIFF_THRESH and edge_density > _CAM_EDGE_DENSITY_THRESH):
            return False, 'center'

        mid        = roi.shape[1] // 2
        left_diff  = float(np.abs(roi[:, :mid].astype(np.float32) - floor_mean).mean())
        right_diff = float(np.abs(roi[:, mid:].astype(np.float32) - floor_mean).mean())
        side = 'right' if right_diff > left_diff else 'left'
        return True, side

    # ── Stuck detection ───────────────────────────────────────────────────────

    def _update_stuck(self, now: Time) -> bool:
        """Return True if robot is stuck.

        Uses _actual_cmd_vx (tracks ANY publisher incl. vlm_planner) so stuck
        detection works even when VLM is driving.
        """
        effective_cmd = max(self._cmd_vx, self._actual_cmd_vx)
        if effective_cmd < _STUCK_CMD_THRESH:
            self._stuck_since = None
            return False

        if self._odom_vx < _STUCK_VEL_THRESH:
            if self._stuck_since is None:
                self._stuck_since = now
            else:
                elapsed = (now - self._stuck_since).nanoseconds / 1e9
                if elapsed > _STUCK_TIMEOUT_SEC:
                    return True
        else:
            self._stuck_since = None

        return False

    # ── Main control loop ────────────────────────────────────────────────────

    def _control_loop(self) -> None:
        now = self.get_clock().now()

        # ── Priority 0: VLM task ─────────────────────────────────────────────
        if self._vlm_active:
            if now < self._vlm_timeout:
                self._cmd_vx = 0.0
                # vlm_planner publishes at 50 Hz — any escape from wander (10 Hz)
                # would be immediately overwritten. Let vlm_planner's internal
                # escape state (1.5 s stable reverse+turn) handle stuck recovery.
                self._pub_mode('VLM_TASK')
                return
            else:
                self._vlm_active = False

        # ── Priority 1: ATTENTION ────────────────────────────────────────────
        if self.person_hit is not None:
            age = (now - self.person_hit.timestamp).nanoseconds / 1e9
            if age < DETECTION_TIMEOUT:
                self._do_attention(self.person_hit)
                self._pub_mode('WANDER')
                return
            self.person_hit = None

        # ── Priority 2: CURIOUS ──────────────────────────────────────────────
        if self.curious_hit is not None:
            age = (now - self.curious_hit.timestamp).nanoseconds / 1e9
            if age < DETECTION_TIMEOUT:
                self._do_curious(self.curious_hit)
                self._pub_mode('WANDER')
                return
            self.curious_hit = None

        # ── Priority 2.5: Camera low-obstacle ───────────────────────────────
        if now >= self.turn_until and now >= self.reverse_until:
            cam_obs, cam_side = self._check_camera_low_obstacle()
            if cam_obs:
                turn_sign = -1.0 if cam_side == 'right' else 1.0
                self._start_avoid(now, turn_sign, reason=f'[CAM_AVOID] Low obstacle {cam_side}')
                self._pub_mode('CAM_AVOID')
                # Motion executed via safety channel in next reverse/turn ticks
                return

        # ── Priority 3: Stuck detector ───────────────────────────────────────
        if self._update_stuck(now):
            self._stuck_since = None
            self.get_logger().warn('STUCK detected — triggering escape maneuver')
            self._trigger_escape(now)

        # ── Priority 4 & 5: LiDAR AVOID / WANDER ───────────────────────────
        if self.scan_state is None:
            self.publish_cmd(0.0, 0.35)
            self._pub_mode('WANDER')
            return

        # Reverse phase — safety channel: overrides VLM nav in mux
        if now < self.reverse_until:
            self.publish_safety(-0.18, 0.0)
            self._pub_mode('LIDAR_AVOID')
            return

        # Turn phase — safety channel
        if now < self.turn_until:
            spd = self.turn_spd * (1.3 if self._escaping else 1.0)
            self.publish_safety(0.0, self.turn_direction * spd)
            self._pub_mode('LIDAR_AVOID')
            return

        self._escaping = False  # escape maneuver complete

        # ── Sector analysis (wider + diagonal) ──────────────────────────────
        front       = self._sector_min(-0.50, 0.50)    # was ±0.30 — now wider ±0.50
        front_left  = self._sector_min(0.50, 1.05)     # NEW: front-left diagonal
        front_right = self._sector_min(-1.05, -0.50)   # NEW: front-right diagonal
        left        = self._sector_min(1.05, 1.80)
        right       = self._sector_min(-1.80, -1.05)

        # Corner trap: all directions blocked → full reverse + large turn
        if (front < self.safe_dist and
                front_left < self.safe_dist * 0.8 and
                front_right < self.safe_dist * 0.8):
            turn_sign = 1.0 if left > right else -1.0
            self._trigger_escape(now, turn_sign, large=True)
            self._maybe_log(f'[CORNER TRAP] front={front:.2f} → full escape')
            self._pub_mode('LIDAR_AVOID')
            return

        # Diagonal obstacle → pre-emptive steer
        if front_left < self.safe_dist * 0.85 and front_right >= self.safe_dist * 0.85:
            self._start_avoid(now, -1.0, reason=f'Diag-left {front_left:.2f}m')
            self._pub_mode('LIDAR_AVOID')
            return
        if front_right < self.safe_dist * 0.85 and front_left >= self.safe_dist * 0.85:
            self._start_avoid(now, 1.0, reason=f'Diag-right {front_right:.2f}m')
            self._pub_mode('LIDAR_AVOID')
            return

        # Front obstacle
        if front < self.safe_dist:
            turn_sign = 1.0 if front_left > front_right else -1.0
            self._start_avoid(now, turn_sign,
                              reason=f'Obstacle ahead {front:.2f}m')
            self._pub_mode('LIDAR_AVOID')
            return

        # ── WANDER ──────────────────────────────────────────────────────────
        corridor = self._normalize(right) - self._normalize(left)
        angular  = max(min(0.8 * corridor + self.bias, 0.65), -0.65)
        linear   = self.cruise_spd
        if front < self.safe_dist * 1.6:
            linear *= 0.6
        if min(left, right) < self.safe_dist * 0.8:
            linear *= 0.75

        self.bias *= 0.98
        if random.random() < 0.03:
            self.bias = random.uniform(-0.18, 0.18)

        self.publish_cmd(linear, angular)
        self._pub_mode('WANDER')

    # ── Avoid helpers ─────────────────────────────────────────────────────────

    def _start_avoid(self, now: Time, turn_sign: float, reason: str = '') -> None:
        """Reverse 0.4s then turn. Much more effective than pure rotation."""
        self.turn_direction = turn_sign
        # Reverse first
        rev_dur = random.uniform(0.35, 0.55)
        self.reverse_until = now + Duration(seconds=rev_dur)
        # Then turn
        turn_dur = random.uniform(0.9, 1.6)
        self.turn_until = self.reverse_until + Duration(seconds=turn_dur)
        self.bias = random.uniform(-0.12, 0.12)
        if reason:
            self._maybe_log(f'{reason} → reverse {rev_dur:.1f}s + turn {turn_dur:.1f}s')

    def _trigger_escape(self, now: Time, turn_sign: Optional[float] = None,
                        large: bool = False) -> None:
        """Emergency escape: reverse then large turn. Uses same reverse_until/turn_until
        mechanism as _start_avoid — no separate broken phase tracking."""
        self.turn_direction = turn_sign if turn_sign is not None else \
                              (1.0 if random.random() > 0.5 else -1.0)
        rev_dur  = random.uniform(0.8, 1.4)
        turn_dur = random.uniform(1.5, 2.5) if large else random.uniform(1.0, 1.8)
        self.reverse_until = now + Duration(seconds=rev_dur)
        self.turn_until    = self.reverse_until + Duration(seconds=turn_dur)
        self._escaping     = True
        self._maybe_log(
            f'[ESCAPE] reverse {rev_dur:.1f}s + turn {turn_dur:.1f}s '
            f'{"(large)" if large else ""}'
        )
        self._pub_safety_event('stuck', 'medium')

    # ── YOLO behaviours ───────────────────────────────────────────────────────

    def _do_attention(self, hit: DetectionHit) -> None:
        offset  = (hit.center_x - IMAGE_CENTER) / IMAGE_CENTER
        angular = -offset * self.turn_spd * 0.55
        angular = max(min(angular, self.turn_spd), -self.turn_spd)
        self.publish_cmd(0.0, angular)
        self._maybe_log(f'[YOLO] ATTENTION — {hit.label} conf={hit.confidence:.2f}')

    def _do_curious(self, hit: DetectionHit) -> None:
        offset  = (hit.center_x - IMAGE_CENTER) / IMAGE_CENTER
        self.publish_cmd(self.cruise_spd * 0.45, -offset * 0.45)
        self._maybe_log(f'[YOLO] CURIOUS — {hit.label} conf={hit.confidence:.2f}')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sector_min(self, angle_start: float, angle_end: float) -> float:
        state = self.scan_state
        if state is None:
            return float('inf')
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

    def _make_twist(self, linear_x: float, angular_z: float) -> TwistStamped:
        msg = TwistStamped()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x  = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        return msg

    def publish_cmd(self, linear_x: float, angular_z: float) -> None:
        """Navigation-priority command → /cmd_vel/wander (priority 2 in mux)."""
        self._cmd_vx = abs(linear_x)
        self.nav_cmd_pub.publish(self._make_twist(linear_x, angular_z))

    def publish_safety(self, linear_x: float, angular_z: float) -> None:
        """Safety-priority command → /cmd_vel/safety (priority 0 in mux)."""
        self._cmd_vx = abs(linear_x)
        self.safety_cmd_pub.publish(self._make_twist(linear_x, angular_z))

    def _pub_mode(self, mode: str) -> None:
        self.mode_pub.publish(String(data=mode))

    def _pub_safety_event(self, event_type: str, severity: str) -> None:
        payload = json.dumps({
            'event_type': event_type,
            'severity':   severity,
            'timestamp':  self.get_clock().now().nanoseconds / 1e9,
        })
        self.safety_pub.publish(String(data=payload))

    def _maybe_log(self, text: str) -> None:
        now = self.get_clock().now()
        if (now - self.last_log_time).nanoseconds > 2_000_000_000:
            self.get_logger().info(text)
            self.last_log_time = now


def main(args=None) -> None:
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
