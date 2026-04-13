#!/usr/bin/env python3
"""VLM Perception — thay thế YOLOv8 bằng Qwen2.5-VL cho scene understanding.

Chạy song song với perception.py (YOLOv8 làm fallback).
Publish scene description + structured detections với ngôn ngữ tự nhiên.

Subscribe:
  /camera/image_raw          — camera feed

Publish:
  /vlm/detections            — JSON detections (richer than YOLO)
  /vlm/scene                 — plain-text scene description
  /camera/vlm_annotated      — annotated frame (bounding boxes + text)
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String

try:
    from cv_bridge import CvBridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# ── Perception-specific VLM prompt ────────────────────────────────────────────

PERCEPTION_PROMPT = """Phân tích ảnh camera của robot và trả lời JSON:
{
  "scene": "<mô tả toàn cảnh ngắn, tiếng Việt>",
  "objects": [
    {
      "description": "<mô tả vật thể>",
      "type": "<category: person/bottle/cup/chair/box/unknown/...>",
      "position": "left/center/right",
      "distance_estimate": "near/medium/far",
      "notable": true/false
    }
  ],
  "obstacles": "<mô tả vật cản phía trước hoặc 'không có'>",
  "navigable": true/false,
  "lighting": "bright/normal/dark"
}
Chỉ trả lời JSON hợp lệ."""

# Màu cho mỗi loại object
TYPE_COLORS = {
    'person':  (0, 255, 100),
    'bottle':  (0, 180, 255),
    'cup':     (0, 220, 255),
    'chair':   (255, 180, 0),
    'box':     (200, 100, 255),
    'unknown': (180, 180, 180),
}


class VLMPerception(Node):
    """VLM-based perception node — scene understanding với natural language."""

    def __init__(self) -> None:
        super().__init__('walle_vlm_perception')

        # ── Parameters ─────────────────────────────────────────────────────
        self.declare_parameter('model_backend',       'transformers')
        self.declare_parameter('model_name',          'Qwen/Qwen2.5-VL-7B-Instruct')
        self.declare_parameter('quantize_4bit',       True)
        self.declare_parameter('language',            'vi')
        self.declare_parameter('inference_interval',  3.0)   # seconds between inferences

        cfg = {
            'model_backend':  self.get_parameter('model_backend').value,
            'model_name':     self.get_parameter('model_name').value,
            'quantize_4bit':  self.get_parameter('quantize_4bit').value,
            'language':       self.get_parameter('language').value,
        }
        self._interval = float(self.get_parameter('inference_interval').value)

        # ── QoS ────────────────────────────────────────────────────────────
        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        # ── Publishers ──────────────────────────────────────────────────────
        self.det_pub   = self.create_publisher(String, '/vlm/detections', 10)
        self.scene_pub = self.create_publisher(String, '/vlm/scene', 10)
        self.img_pub   = self.create_publisher(Image,  '/camera/vlm_annotated', 10)

        # ── Subscribers ─────────────────────────────────────────────────────
        self._bridge   = CvBridge() if _HAS_BRIDGE else None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self.create_subscription(Image, '/camera/image_raw', self._image_cb, sensor_qos)

        # ── VLM ─────────────────────────────────────────────────────────────
        self._vlm: Any   = None
        self._vlm_ready  = False
        self._last_infer = 0.0

        t_load = threading.Thread(target=self._load_vlm, args=(cfg,), daemon=True)
        t_load.start()

        t_infer = threading.Thread(target=self._infer_loop, daemon=True)
        t_infer.start()

        self.get_logger().info('VLM Perception node started. Loading model...')

    # ── Model load ────────────────────────────────────────────────────────────

    def _load_vlm(self, cfg: Dict[str, Any]) -> None:
        from walle_demo.vlm_utils import VLMInterface
        self._vlm = VLMInterface(cfg, logger=lambda m: self.get_logger().info(m))
        self._vlm_ready = self._vlm.ready

    # ── Image callback ────────────────────────────────────────────────────────

    def _image_cb(self, msg: Image) -> None:
        if not self._bridge:
            return
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, 'bgr8')
            with self._frame_lock:
                self._frame = frame
        except Exception:
            pass

    # ── Inference loop ────────────────────────────────────────────────────────

    def _infer_loop(self) -> None:
        while rclpy.ok():
            time.sleep(0.2)
            if not self._vlm_ready:
                continue

            now = time.monotonic()
            if now - self._last_infer < self._interval:
                continue
            self._last_infer = now

            with self._frame_lock:
                frame = self._frame.copy() if self._frame is not None else None
            if frame is None:
                continue

            result = self._vlm.describe_scene(frame)
            self._publish_results(frame, result)

    # ── Output ────────────────────────────────────────────────────────────────

    def _publish_results(self, frame: np.ndarray, result: Dict[str, Any]) -> None:
        # Publish scene text
        scene = result.get('scene', '')
        self.scene_pub.publish(String(data=scene))

        # Build detection list (compatible with /detections format for wander.py)
        objects: List[Dict[str, Any]] = result.get('objects', [])
        compat_dets = []
        for obj in objects:
            pos = obj.get('position', 'center')
            cx = {'left': 160.0, 'center': 320.0, 'right': 480.0}.get(pos, 320.0)
            compat_dets.append({
                'label':       obj.get('type', 'unknown'),
                'confidence':  0.80 if obj.get('notable', False) else 0.60,
                'bbox':        [int(cx - 60), 160, int(cx + 60), 320],
                'description': obj.get('description', ''),
                'distance':    obj.get('distance_estimate', 'unknown'),
            })
        self.det_pub.publish(String(data=json.dumps(compat_dets)))

        # Annotate frame
        annotated = self._annotate(frame, result)
        if self._bridge:
            try:
                msg = self._bridge.cv2_to_imgmsg(annotated, 'bgr8')
                self.img_pub.publish(msg)
            except Exception:
                pass

        self.get_logger().info(
            f'[VLM Perception] scene="{scene[:60]}" | {len(objects)} object(s)',
            throttle_duration_sec=5.0,
        )

    @staticmethod
    def _annotate(frame: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        canvas = frame.copy()
        h, w   = canvas.shape[:2]

        # Scene overlay (top bar)
        scene = result.get('scene', '')[:80]
        cv2.rectangle(canvas, (0, 0), (w, 30), (30, 30, 30), -1)
        cv2.putText(canvas, scene, (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 255, 200), 1, cv2.LINE_AA)

        # Object markers (position-based columns)
        for i, obj in enumerate(result.get('objects', [])):
            pos   = obj.get('position', 'center')
            color = TYPE_COLORS.get(obj.get('type', 'unknown'), (180, 180, 180))
            col_x = {'left': w // 6, 'center': w // 2, 'right': 5 * w // 6}.get(pos, w // 2)

            label = f'{obj.get("type","?")} ({obj.get("distance_estimate","?")})'
            desc  = obj.get('description', '')[:40]

            y_base = 60 + i * 48
            cv2.circle(canvas, (col_x, y_base), 18, color, -1)
            cv2.putText(canvas, label, (col_x - 50, y_base + 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)
            cv2.putText(canvas, desc, (col_x - 50, y_base + 46),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (200, 200, 200), 1, cv2.LINE_AA)

        # Navigable indicator
        nav = result.get('navigable', True)
        nav_text = "CLEAR" if nav else "BLOCKED"
        nav_color = (0, 230, 0) if nav else (0, 50, 230)
        cv2.putText(canvas, nav_text, (w - 90, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, nav_color, 2, cv2.LINE_AA)

        return canvas


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VLMPerception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
