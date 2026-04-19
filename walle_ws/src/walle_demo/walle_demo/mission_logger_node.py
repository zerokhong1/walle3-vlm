#!/usr/bin/env python3
"""mission_logger_node.py — WallE3 Mission Analytics Logger (schema v1.0)

Subscribes to event contract v1.0 topics from walle3-vlm and writes CSV logs
compatible with the walle3-mission-analytics data model.

Deploy: copy to walle_ws/src/walle_demo/walle_demo/ and add to setup.py entry_points.
Usage:  ros2 run walle_demo mission_logger_node

Parameters (ros2 param or launch file):
  log_dir           (str) : directory for CSV output  (default: ~/walle_logs)
  flush_interval_s  (int) : seconds between flushes   (default: 30)
  robot_id          (str) : robot identifier           (default: walle3)
  site_id           (str) : site identifier            (default: default)

Event contract v1.0 topics consumed:
  /mission/started      JSON: {mission_id, mission_type, user_command, timestamp, robot_id, site_id, schema_version}
  /mission/completed    JSON: {mission_id, success, duration_s, intervention_count, reason}
  /planner/state        plain string: IDLE|PLANNING|SEARCHING|APPROACHING|CONFIRMING|COMPLETED
  /controller/mode      plain string: VLM_TASK|CAM_AVOID|LIDAR_AVOID|WANDER|EMERGENCY_STOP
  /safety/event         JSON: {event_type, severity, timestamp}
  /inference/event      JSON: {model, latency_ms, input_tokens, output_valid, confidence}
"""

import csv
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False
    print("WARNING: rclpy not available. Running in STUB mode.")


# ── Helpers ────────────────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def short_id(prefix: str = "") -> str:
    return prefix + uuid.uuid4().hex[:8]


# ── CSV writer ─────────────────────────────────────────────────────────────────

class CSVLogger:
    SCHEMAS = {
        "fact_missions": [
            "mission_id", "robot_id", "site_id", "operator_id",
            "start_ts", "end_ts", "duration_s", "outcome", "failure_reason",
            "target_description", "target_type", "command_language",
            "retry_count", "total_states", "inference_count",
            "safety_event_count", "shift",
        ],
        "fact_mission_events": [
            "event_id", "mission_id", "robot_id", "site_id",
            "timestamp", "category", "event_type", "severity",
            "duration_s", "payload_json",
        ],
        "fact_safety_events": [
            "event_id", "mission_id", "robot_id", "site_id",
            "timestamp", "event_type", "severity",
            "distance_m", "source", "duration_s", "resolved",
        ],
        "fact_inference_events": [
            "event_id", "mission_id", "robot_id", "timestamp",
            "duration_ms", "target_found", "confidence",
            "retry_number", "gpu_temp_c", "gpu_memory_mb", "outcome",
        ],
    }

    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        self.log_dir = log_dir
        self._lock = threading.Lock()
        self._buffers = {t: [] for t in self.SCHEMAS}
        self._writers: dict = {}
        self._files: dict = {}
        self._init_files()

    def _init_files(self):
        for table, cols in self.SCHEMAS.items():
            path = os.path.join(self.log_dir, f"{table}.csv")
            write_header = not os.path.exists(path)
            f = open(path, "a", newline="", encoding="utf-8")
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if write_header:
                w.writeheader()
            self._files[table] = f
            self._writers[table] = w

    def append(self, table: str, row: dict):
        with self._lock:
            self._buffers[table].append(row)

    def flush(self):
        with self._lock:
            for table, rows in self._buffers.items():
                if rows:
                    self._writers[table].writerows(rows)
                    self._files[table].flush()
                    self._buffers[table] = []

    def close(self):
        self.flush()
        for f in self._files.values():
            f.close()


# ── In-flight mission state ────────────────────────────────────────────────────

class MissionTracker:
    def __init__(self):
        self.mission_id:      str   = ""
        self.start_ts:        str   = ""
        self.start_epoch:     float = 0.0
        self.safety_count:    int   = 0
        self.inference_count: int   = 0
        self.total_states:    int   = 0
        self.last_command:    str   = ""

    def start(self, mission_id: str, command: str):
        self.mission_id      = mission_id
        self.start_ts        = utc_now()
        self.start_epoch     = time.time()
        self.safety_count    = 0
        self.inference_count = 0
        self.total_states    = 0
        self.last_command    = command

    def active(self) -> bool:
        return bool(self.mission_id)

    @staticmethod
    def _shift() -> str:
        h = datetime.now().hour
        if 6 <= h < 14:
            return "morning"
        elif 14 <= h < 22:
            return "afternoon"
        return "night"


# ── ROS 2 node ────────────────────────────────────────────────────────────────

if ROS2_AVAILABLE:
    class MissionLoggerNode(Node):

        def __init__(self):
            super().__init__("mission_logger_node")

            self.declare_parameter("log_dir",          os.path.expanduser("~/walle_logs"))
            self.declare_parameter("flush_interval_s", 30)
            self.declare_parameter("robot_id",         "walle3")
            self.declare_parameter("site_id",          "default")

            log_dir        = self.get_parameter("log_dir").value
            flush_interval = self.get_parameter("flush_interval_s").value
            self.robot_id  = self.get_parameter("robot_id").value
            self.site_id   = self.get_parameter("site_id").value

            self.csv     = CSVLogger(log_dir)
            self.tracker = MissionTracker()

            # State change deduplication (log only on transition, not every publish)
            self._last_planner_state:    str = ""
            self._last_controller_mode:  str = ""

            # Event contract v1.0 subscriptions
            self.create_subscription(String, "/mission/started",   self._on_mission_started,   10)
            self.create_subscription(String, "/mission/completed", self._on_mission_completed, 10)
            self.create_subscription(String, "/planner/state",     self._on_planner_state,     10)
            self.create_subscription(String, "/controller/mode",   self._on_controller_mode,   10)
            self.create_subscription(String, "/safety/event",      self._on_safety_event,      10)
            self.create_subscription(String, "/inference/event",   self._on_inference_event,   10)

            self.create_timer(float(flush_interval), self._flush_timer)
            self.get_logger().info(
                f"MissionLoggerNode started. log_dir={log_dir} "
                f"robot={self.robot_id} site={self.site_id}"
            )

        # ── /mission/started ──────────────────────────────────────────────────
        # Payload: {mission_id, mission_type, user_command, timestamp,
        #           robot_id, site_id, schema_version}

        def _on_mission_started(self, msg: String):
            try:
                ev = json.loads(msg.data)
            except json.JSONDecodeError:
                return
            mission_id = ev.get("mission_id", short_id("msn_"))
            command    = ev.get("user_command", "")
            self.tracker.start(mission_id, command)
            self.csv.append("fact_mission_events", {
                "event_id":    short_id("evt_"),
                "mission_id":  mission_id,
                "robot_id":    self.robot_id,
                "site_id":     self.site_id,
                "timestamp":   utc_now(),
                "category":    "MISSION_LIFECYCLE",
                "event_type":  "MISSION_START",
                "severity":    "INFO",
                "duration_s":  None,
                "payload_json": json.dumps({"user_command": command}),
            })
            self.get_logger().info(f"[LOGGER] Mission started: {mission_id} cmd={command!r}")

        # ── /mission/completed ────────────────────────────────────────────────
        # Payload: {mission_id, success, duration_s, intervention_count, reason}

        def _on_mission_completed(self, msg: String):
            try:
                ev = json.loads(msg.data)
            except json.JSONDecodeError:
                return
            if not self.tracker.active():
                return

            success  = ev.get("success", False)
            outcome  = "SUCCESS" if success else "FAILED"
            reason   = ev.get("reason", "")
            duration = ev.get("duration_s", round(time.time() - self.tracker.start_epoch, 1))

            self.csv.append("fact_missions", {
                "mission_id":         self.tracker.mission_id,
                "robot_id":           self.robot_id,
                "site_id":            self.site_id,
                "operator_id":        "",
                "start_ts":           self.tracker.start_ts,
                "end_ts":             utc_now(),
                "duration_s":         duration,
                "outcome":            outcome,
                "failure_reason":     reason if not success else "",
                "target_description": self.tracker.last_command,
                "target_type":        "object",
                "command_language":   "en",
                "retry_count":        ev.get("intervention_count", self.tracker.safety_count),
                "total_states":       self.tracker.total_states,
                "inference_count":    self.tracker.inference_count,
                "safety_event_count": self.tracker.safety_count,
                "shift":              MissionTracker._shift(),
            })
            self.csv.append("fact_mission_events", {
                "event_id":    short_id("evt_"),
                "mission_id":  self.tracker.mission_id,
                "robot_id":    self.robot_id,
                "site_id":     self.site_id,
                "timestamp":   utc_now(),
                "category":    "MISSION_LIFECYCLE",
                "event_type":  "MISSION_END",
                "severity":    "INFO",
                "duration_s":  duration,
                "payload_json": json.dumps({"outcome": outcome, "reason": reason}),
            })
            self.get_logger().info(
                f"[LOGGER] Mission completed: {self.tracker.mission_id} "
                f"outcome={outcome} duration={duration}s"
            )
            self.tracker.mission_id = ""

        # ── /planner/state (plain string) ─────────────────────────────────────
        # Log only on state transition to avoid flooding at 50 Hz.

        def _on_planner_state(self, msg: String):
            state = msg.data.strip()
            if not state or not self.tracker.active():
                return
            if state == self._last_planner_state:
                return
            self._last_planner_state = state
            self.tracker.total_states += 1
            self.csv.append("fact_mission_events", {
                "event_id":    short_id("evt_"),
                "mission_id":  self.tracker.mission_id,
                "robot_id":    self.robot_id,
                "site_id":     self.site_id,
                "timestamp":   utc_now(),
                "category":    "PLANNER_STATE",
                "event_type":  f"STATE_{state}",
                "severity":    "INFO",
                "duration_s":  None,
                "payload_json": "{}",
            })

        # ── /controller/mode (plain string) ───────────────────────────────────
        # Log only on mode transition to avoid flooding at 10 Hz.

        def _on_controller_mode(self, msg: String):
            mode = msg.data.strip()
            if not mode or not self.tracker.active():
                return
            if mode == self._last_controller_mode:
                return
            self._last_controller_mode = mode
            severity = "HIGH" if mode == "EMERGENCY_STOP" else "INFO"
            self.csv.append("fact_mission_events", {
                "event_id":    short_id("evt_"),
                "mission_id":  self.tracker.mission_id,
                "robot_id":    self.robot_id,
                "site_id":     self.site_id,
                "timestamp":   utc_now(),
                "category":    "CONTROLLER_MODE",
                "event_type":  f"MODE_{mode}",
                "severity":    severity,
                "duration_s":  None,
                "payload_json": "{}",
            })

        # ── /safety/event ─────────────────────────────────────────────────────
        # Payload: {event_type, severity, timestamp}

        def _on_safety_event(self, msg: String):
            try:
                ev = json.loads(msg.data)
            except json.JSONDecodeError:
                return
            self.tracker.safety_count += 1
            self.csv.append("fact_safety_events", {
                "event_id":   short_id("evt_"),
                "mission_id": self.tracker.mission_id,
                "robot_id":   self.robot_id,
                "site_id":    self.site_id,
                "timestamp":  utc_now(),
                "event_type": ev.get("event_type", "unknown"),
                "severity":   ev.get("severity", "INFO"),
                "distance_m": None,
                "source":     "lidar" if ev.get("event_type") == "collision_risk" else "odometry",
                "duration_s": None,
                "resolved":   1,
            })

        # ── /inference/event ──────────────────────────────────────────────────
        # Payload: {model, latency_ms, input_tokens, output_valid, confidence}

        def _on_inference_event(self, msg: String):
            try:
                ev = json.loads(msg.data)
            except json.JSONDecodeError:
                return
            self.tracker.inference_count += 1
            output_valid = ev.get("output_valid", True)
            self.csv.append("fact_inference_events", {
                "event_id":      short_id("evt_"),
                "mission_id":    self.tracker.mission_id,
                "robot_id":      self.robot_id,
                "timestamp":     utc_now(),
                "duration_ms":   ev.get("latency_ms", 0),
                "target_found":  1 if ev.get("target_found") else 0,
                "confidence":    ev.get("confidence", 0.0),
                "retry_number":  self.tracker.inference_count - 1,
                "gpu_temp_c":    None,
                "gpu_memory_mb": None,
                "outcome":       "SUCCESS" if output_valid else "PARSE_ERROR",
            })

        # ── Internal ──────────────────────────────────────────────────────────

        def _flush_timer(self):
            self.csv.flush()
            self.get_logger().debug("CSV flushed.")

        def destroy_node(self):
            self.csv.close()
            super().destroy_node()


def main(args=None):
    if not ROS2_AVAILABLE:
        print("rclpy not available. This node requires ROS 2.")
        return
    rclpy.init(args=args)
    node = MissionLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
