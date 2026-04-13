#!/usr/bin/env python3
"""VLM Planner — bộ não VLM của WallE3 v2.

Dual-loop architecture:
  Fast loop  (50 Hz): thực thi plan hiện tại + LiDAR safety override
  Slow loop  (~0.5 Hz): VLM inference trong background thread

State machine: IDLE → PLANNING → SEARCHING → APPROACHING → CONFIRMING → COMPLETED

Subscribe:
  /camera/image_raw          — camera feed
  /user_command              — lệnh từ user (text)
  /scan                      — LiDAR (safety layer)

Publish:
  /vlm/action_plan           — JSON action plan
  /vlm/scene_description     — mô tả scene
  /behavior_state            — state machine state
  /diff_drive_base_controller/cmd_vel
"""

from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import rclpy
from builtin_interfaces.msg import Duration as DurationMsg
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

try:
    from cv_bridge import CvBridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# ── States ────────────────────────────────────────────────────────────────────

STATES = ['IDLE', 'PLANNING', 'SEARCHING', 'APPROACHING', 'CONFIRMING', 'COMPLETED']

# ── LiDAR safety thresholds ───────────────────────────────────────────────────

OBSTACLE_STOP_DIST  = 0.35   # m — emergency stop
OBSTACLE_SLOW_DIST  = 0.60   # m — slow down

# ── Default VLM config ────────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "model_backend":       "transformers",
    "model_name":          "Qwen/Qwen2.5-VL-7B-Instruct",
    "quantize_4bit":       True,
    "language":            "vi",
    "inference_interval_sec": 2.0,
    "vlm_timeout_sec":     10.0,
    "fallback_to_yolo":    True,
    "max_speed":           0.25,
    "angular_max":         0.80,
}


@dataclass
class ScanState:
    ranges: List[float]
    angle_min: float
    angle_increment: float
    range_min: float
    range_max: float


class VLMPlanner(Node):
    """Main VLM planner node — dual-loop, threaded VLM inference."""

    def __init__(self) -> None:
        super().__init__('walle_vlm_planner')

        # ── Parameters ─────────────────────────────────────────────────────
        self.declare_parameter('model_backend', DEFAULT_CONFIG['model_backend'])
        self.declare_parameter('model_name',    DEFAULT_CONFIG['model_name'])
        self.declare_parameter('quantize_4bit', DEFAULT_CONFIG['quantize_4bit'])
        self.declare_parameter('language',      DEFAULT_CONFIG['language'])
        self.declare_parameter('inference_interval_sec', DEFAULT_CONFIG['inference_interval_sec'])
        self.declare_parameter('vlm_timeout_sec',        DEFAULT_CONFIG['vlm_timeout_sec'])
        self.declare_parameter('max_speed',              DEFAULT_CONFIG['max_speed'])

        cfg: Dict[str, Any] = {
            'model_backend':          self.get_parameter('model_backend').value,
            'model_name':             self.get_parameter('model_name').value,
            'quantize_4bit':          self.get_parameter('quantize_4bit').value,
            'language':               self.get_parameter('language').value,
            'inference_interval_sec': self.get_parameter('inference_interval_sec').value,
            'vlm_timeout_sec':        self.get_parameter('vlm_timeout_sec').value,
        }
        self._max_speed   = float(self.get_parameter('max_speed').value)
        self._infer_interval = float(cfg['inference_interval_sec'])

        # ── QoS ────────────────────────────────────────────────────────────
        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        # ── Publishers ──────────────────────────────────────────────────────
        self.cmd_pub   = self.create_publisher(
            TwistStamped, '/diff_drive_base_controller/cmd_vel', 10)
        self.state_pub = self.create_publisher(String, '/behavior_state', 10)
        self.plan_pub  = self.create_publisher(String, '/vlm/action_plan', 10)
        self.scene_pub = self.create_publisher(String, '/vlm/scene_description', 10)
        self.ann_pub   = self.create_publisher(Image, '/camera/vlm_annotated', 10)
        self.head_pub  = self.create_publisher(
            JointTrajectory, '/head_controller/joint_trajectory', 10)
        self.arm_pub   = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10)

        # ── Subscribers ─────────────────────────────────────────────────────
        self.create_subscription(Image,     '/camera/image_raw', self._image_cb,   sensor_qos)
        self.create_subscription(LaserScan, '/scan',             self._scan_cb,    sensor_qos)
        self.create_subscription(String,    '/user_command',     self._command_cb, 10)

        # ── Internal state ──────────────────────────────────────────────────
        self._bridge       = CvBridge() if _HAS_BRIDGE else None
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock   = threading.Lock()
        self._scan: Optional[ScanState] = None
        self._scan_lock    = threading.Lock()

        self._state        = 'IDLE'
        self._command      = ''
        self._plan: Dict[str, Any] = {}
        self._plan_lock    = threading.Lock()

        self._vlm: Any     = None      # VLMInterface, loaded in thread
        self._vlm_ready    = False

        # Search rotation bookkeeping
        self._search_angle_covered = 0.0
        self._last_search_t        = time.monotonic()

        # Slow-loop timing
        self._last_infer_t = 0.0

        # ── Timers ──────────────────────────────────────────────────────────
        self.fast_timer = self.create_timer(0.02, self._fast_loop)      # 50 Hz

        # ── Background threads ───────────────────────────────────────────────
        t_load = threading.Thread(target=self._load_vlm, args=(cfg,), daemon=True)
        t_load.start()

        t_infer = threading.Thread(target=self._vlm_loop, daemon=True)
        t_infer.start()

        self.get_logger().info('VLM Planner node started. Loading model...')

    # ── Model loading (background) ────────────────────────────────────────────

    def _load_vlm(self, cfg: Dict[str, Any]) -> None:
        from walle_demo.vlm_utils import VLMInterface
        self._vlm = VLMInterface(cfg, logger=lambda m: self.get_logger().info(m))
        self._vlm_ready = self._vlm.ready
        if self._vlm_ready:
            self.get_logger().info('[VLM] Model ready — accepting commands.')
        else:
            self.get_logger().error('[VLM] Model failed to load! Check VRAM / model path.')

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _image_cb(self, msg: Image) -> None:
        if self._bridge is None:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, 'bgr8')
            with self._frame_lock:
                self._latest_frame = frame
        except Exception:
            pass

    def _scan_cb(self, msg: LaserScan) -> None:
        with self._scan_lock:
            self._scan = ScanState(
                ranges=list(msg.ranges),
                angle_min=msg.angle_min,
                angle_increment=msg.angle_increment,
                range_min=msg.range_min,
                range_max=msg.range_max,
            )

    def _command_cb(self, msg: String) -> None:
        cmd = msg.data.strip()
        if not cmd:
            return
        self.get_logger().info(f'[VLM] Command received: "{cmd}"')
        self._command = cmd
        self._state   = 'PLANNING'
        self._last_infer_t = 0.0   # trigger immediate inference

    # ── Fast loop: 50 Hz ──────────────────────────────────────────────────────

    def _fast_loop(self) -> None:
        # LiDAR safety check
        front_min = self._front_distance()
        if front_min < OBSTACLE_STOP_DIST and self._state not in ('IDLE', 'COMPLETED'):
            self._pub_cmd(0.0, 0.5)   # back-off turn
            self._pub_state('AVOID')
            return

        if self._state == 'IDLE':
            self._pub_state('IDLE')
            return

        if self._state == 'COMPLETED':
            self._trigger_celebration()
            self._state = 'IDLE'
            return

        # Execute current plan
        with self._plan_lock:
            plan = dict(self._plan)

        if not plan:
            # Still waiting for first VLM plan
            self._pub_state(self._state)
            return

        self._execute_plan(plan, front_min)

    def _execute_plan(self, plan: Dict[str, Any], front_min: float) -> None:
        action = plan.get('action', {})
        a_type  = action.get('type', 'stop')
        speed   = float(action.get('speed', 0.0))
        angular = float(action.get('angular', 0.0))

        # Safety clamp
        speed = min(speed, self._max_speed)
        if front_min < OBSTACLE_SLOW_DIST:
            speed *= 0.4

        self._pub_cmd(speed, angular)

        # Head / arm
        head_yaw   = float(action.get('head_yaw', 0.0))
        head_pitch = float(action.get('head_pitch', 0.0))
        arm_l      = float(action.get('arm_left', 0.0))
        arm_r      = float(action.get('arm_right', 0.0))
        self._pub_head(head_yaw, head_pitch)
        self._pub_arms(arm_l, arm_r)

        # State mapping
        status = plan.get('status', 'searching')
        if status == 'reached':
            self._state = 'CONFIRMING'
        elif status == 'approaching':
            self._state = 'APPROACHING'
        elif status == 'not_found':
            self._state = 'SEARCHING'

        # Publish plan + state
        self.plan_pub.publish(String(data=json.dumps(plan)))
        self._pub_state(self._state)

        # Scene description
        scene_text = plan.get('scene', '')
        if scene_text:
            self.scene_pub.publish(String(data=scene_text))

        # Annotated camera frame
        with self._frame_lock:
            frame = self._latest_frame.copy() if self._latest_frame is not None else None
        if frame is not None and self._bridge:
            annotated = self._annotate_frame(frame, plan, self._state)
            try:
                ann_msg = self._bridge.cv2_to_imgmsg(annotated, 'bgr8')
                ann_msg.header.stamp = self.get_clock().now().to_msg()
                self.ann_pub.publish(ann_msg)
            except Exception:
                pass

        # Confirmation transition
        if self._state == 'CONFIRMING':
            self.get_logger().info(f'[VLM] REACHED target! "{plan.get("message", "")}"')
            self._state = 'COMPLETED'

    # ── Slow loop: VLM inference (background thread) ──────────────────────────

    def _vlm_loop(self) -> None:
        while rclpy.ok():
            time.sleep(0.1)
            if not self._vlm_ready or self._state == 'IDLE':
                continue

            now = time.monotonic()
            if now - self._last_infer_t < self._infer_interval:
                continue

            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is None:
                continue

            self._last_infer_t = now

            plan = self._vlm.plan(frame, self._command)
            with self._plan_lock:
                self._plan = plan

    # ── LiDAR helpers ─────────────────────────────────────────────────────────

    def _front_distance(self) -> float:
        with self._scan_lock:
            scan = self._scan
        if scan is None:
            return 99.0
        return self._sector_min(scan, -0.30, 0.30)

    @staticmethod
    def _sector_min(scan: ScanState, a_start: float, a_end: float) -> float:
        if not scan.ranges:
            return scan.range_max
        i0 = int((a_start - scan.angle_min) / scan.angle_increment)
        i1 = int((a_end   - scan.angle_min) / scan.angle_increment)
        i0 = max(0, min(i0, len(scan.ranges) - 1))
        i1 = max(0, min(i1, len(scan.ranges) - 1))
        if i0 > i1:
            i0, i1 = i1, i0
        valid = [v for v in scan.ranges[i0:i1 + 1]
                 if math.isfinite(v) and scan.range_min < v < scan.range_max]
        return min(valid) if valid else scan.range_max

    # ── Publishers ────────────────────────────────────────────────────────────

    def _pub_cmd(self, linear: float, angular: float) -> None:
        msg = TwistStamped()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x  = float(linear)
        msg.twist.angular.z = float(angular)
        self.cmd_pub.publish(msg)

    def _pub_state(self, state: str) -> None:
        self.state_pub.publish(String(data=state))

    def _pub_head(self, yaw: float, pitch: float) -> None:
        self._pub_trajectory(self.head_pub,
                             ['head_yaw_joint', 'head_pitch_joint'],
                             [yaw, pitch], 0.8)

    def _pub_arms(self, left: float, right: float) -> None:
        self._pub_trajectory(self.arm_pub,
                             ['left_arm_joint', 'right_arm_joint'],
                             [left, right], 1.0)

    def _pub_trajectory(self, pub, joints, positions, dur_sec: float) -> None:
        msg = JointTrajectory()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.joint_names  = list(joints)
        pt = JointTrajectoryPoint()
        pt.positions       = [float(p) for p in positions]
        pt.time_from_start = DurationMsg(
            sec=int(dur_sec), nanosec=int((dur_sec % 1) * 1e9))
        msg.points = [pt]
        pub.publish(msg)

    @staticmethod
    def _annotate_frame(frame: np.ndarray, plan: Dict[str, Any], state: str) -> np.ndarray:
        """Draw VLM decision overlay on camera frame."""
        canvas = frame.copy()
        h, w   = canvas.shape[:2]

        # State colors
        STATE_COLORS = {
            'IDLE':        (120, 120, 120),
            'PLANNING':    (255, 200,   0),
            'SEARCHING':   (255, 140,   0),
            'APPROACHING': ( 50, 200,  50),
            'CONFIRMING':  (  0, 255, 200),
            'COMPLETED':   (  0, 255,   0),
        }
        color = STATE_COLORS.get(state, (200, 200, 200))

        # Top bar: state + command
        cv2.rectangle(canvas, (0, 0), (w, 36), (20, 20, 20), -1)
        cv2.rectangle(canvas, (0, 0), (6, 36), color, -1)
        state_label = f'[VLM] {state}'
        cv2.putText(canvas, state_label, (14, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

        # Scene description
        scene = plan.get('scene', '')[:70]
        if scene:
            cv2.rectangle(canvas, (0, 36), (w, 62), (30, 30, 30), -1)
            cv2.putText(canvas, scene, (8, 54),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 255, 200), 1, cv2.LINE_AA)

        # Target indicator
        target_found = plan.get('target_found', False)
        target_pos   = plan.get('target_position', 'unknown')
        if target_found:
            pos_x = {'left': w // 4, 'center': w // 2, 'right': 3 * w // 4}.get(target_pos, w // 2)
            cv2.circle(canvas, (pos_x, h // 2), 30, (0, 255, 100), 3)
            cv2.putText(canvas, 'TARGET', (pos_x - 28, h // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2, cv2.LINE_AA)
            # Direction arrow
            arrow_dx = {'left': -60, 'center': 0, 'right': 60}.get(target_pos, 0)
            cv2.arrowedLine(canvas, (w // 2, h - 50), (w // 2 + arrow_dx, h - 90),
                            (0, 255, 100), 3, tipLength=0.4)

        # Bottom bar: action
        action = plan.get('action', {})
        a_type  = action.get('type', '')
        speed   = action.get('speed', 0.0)
        angular = action.get('angular', 0.0)
        status  = plan.get('status', '')
        msg     = plan.get('message', '')[:50]

        cv2.rectangle(canvas, (0, h - 50), (w, h), (20, 20, 20), -1)
        action_str = f'action: {a_type}  speed: {speed:.2f} m/s  angular: {angular:.2f} rad/s'
        cv2.putText(canvas, action_str, (8, h - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, msg, (8, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180, 180, 180), 1, cv2.LINE_AA)

        return canvas

    def _trigger_celebration(self) -> None:
        """Head nod + wave arms when target reached."""
        self._pub_head(0.0, -0.25)
        self._pub_arms(0.80, -0.80)
        self._pub_cmd(0.0, 0.0)
        self.get_logger().info('[VLM] Celebration! Target reached.')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VLMPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._pub_cmd(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
