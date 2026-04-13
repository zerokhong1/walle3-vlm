#!/usr/bin/env python3
"""YOLOv8-based object detection node for the WALL-E robot.

Subscribes to /camera/image_raw, runs YOLOv8 inference, and publishes:
  - /camera/image_detected  (sensor_msgs/Image)  — annotated frame
  - /detections             (std_msgs/String)     — JSON array of detections
"""

from __future__ import annotations

import json
import time
from typing import List, Optional

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String


class YoloPerception(Node):
    """Run YOLOv8 on the robot camera and publish annotated images + detections."""

    def __init__(self) -> None:
        super().__init__('walle_yolo_perception')

        # ── Parameters ──────────────────────────────────────────────────────
        self.declare_parameter('model', 'yolov8n.pt')
        self.declare_parameter('confidence', 0.45)
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('device', 'cpu')   # 'cpu' | '0' (GPU index)

        model_name  = self.get_parameter('model').get_parameter_value().string_value
        self.conf   = float(self.get_parameter('confidence').value)
        img_topic   = self.get_parameter('image_topic').get_parameter_value().string_value
        device      = self.get_parameter('device').get_parameter_value().string_value

        # ── Load YOLOv8 lazily (avoids slowing down launch) ─────────────────
        self.model = None
        self.model_name = model_name
        self.device = device
        self._bridge = CvBridge()

        # ── QoS matching Gazebo sensor stream ───────────────────────────────
        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.sub = self.create_subscription(Image, img_topic, self._image_cb, sensor_qos)
        self.img_pub  = self.create_publisher(Image,  '/camera/image_detected', 10)
        self.det_pub  = self.create_publisher(String, '/detections', 10)

        # Load model in a one-shot timer so the node spins up first
        self._startup_timer = self.create_timer(0.1, self._load_model_once)

        self._model_ready = False
        self._last_fps_log = time.monotonic()
        self._frame_count  = 0

        self.get_logger().info(
            f'YoloPerception node started — model={model_name} conf={self.conf} device={device}'
        )

    # ── Model loading ────────────────────────────────────────────────────────

    def _load_model_once(self) -> None:
        """Load YOLOv8 model on first timer tick, then cancel the timer."""
        self._startup_timer.cancel()   # stop re-firing immediately
        try:
            from ultralytics import YOLO  # noqa: PLC0415
        except ImportError:
            self.get_logger().error(
                'ultralytics is not installed. Run: pip install ultralytics --break-system-packages'
            )
            return

        self.get_logger().info(f'Loading {self.model_name} …')
        try:
            self.model = YOLO(self.model_name)
            # Warm-up pass
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model(dummy, verbose=False, device=self.device)
            self._model_ready = True
            self.get_logger().info('YOLOv8 model ready.')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'Failed to load model: {exc}')
            return

        # (timer already cancelled at top of this method)

    # ── Inference callback ───────────────────────────────────────────────────

    def _image_cb(self, msg: Image) -> None:
        if not self._model_ready:
            return

        # ROS Image → OpenCV BGR
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'cv_bridge error: {exc}')
            return

        # ── Run YOLOv8 ──────────────────────────────────────────────────────
        results = self.model(frame, conf=self.conf, verbose=False, device=self.device)
        result  = results[0]

        # ── Build detection list ─────────────────────────────────────────────
        detections: List[dict] = []
        for box in result.boxes:
            cls_id  = int(box.cls[0])
            label   = result.names[cls_id]
            conf    = float(box.conf[0])
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
            detections.append({
                'label':      label,
                'confidence': round(conf, 3),
                'bbox':       [x1, y1, x2, y2],
            })

        # ── Publish JSON detections ──────────────────────────────────────────
        det_msg = String()
        det_msg.data = json.dumps(detections)
        self.det_pub.publish(det_msg)

        # ── Annotate frame ───────────────────────────────────────────────────
        annotated = self._annotate(frame, detections)

        # ── Publish annotated image ──────────────────────────────────────────
        try:
            out_msg = self._bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
            out_msg.header = msg.header
            self.img_pub.publish(out_msg)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'publish error: {exc}')

        # ── FPS log (every 5 s) ──────────────────────────────────────────────
        self._frame_count += 1
        now = time.monotonic()
        if now - self._last_fps_log >= 5.0:
            fps = self._frame_count / (now - self._last_fps_log)
            n   = len(detections)
            self.get_logger().info(
                f'[YOLO] {fps:.1f} fps | {n} detection(s): '
                + ', '.join(f'{d["label"]} {d["confidence"]:.2f}' for d in detections)
                if detections else f'[YOLO] {fps:.1f} fps | no detections'
            )
            self._frame_count  = 0
            self._last_fps_log = now

    # ── Drawing helper ───────────────────────────────────────────────────────

    @staticmethod
    def _annotate(frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        canvas = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            label = f'{det["label"]} {det["confidence"]:.2f}'

            # Box
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 230, 0), 2)

            # Label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(canvas, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 230, 0), -1)
            cv2.putText(canvas, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

        # Overlay: detection count
        cv2.putText(canvas, f'Objects: {len(detections)}', (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)
        return canvas


def main(args=None) -> None:
    rclpy.init(args=args)
    node = YoloPerception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
