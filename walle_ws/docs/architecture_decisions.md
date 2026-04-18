# Architecture Decisions

Key design decisions made during development of WallE3 Module A, and the reasoning behind them.

---

## Dual-loop VLM architecture

**Decision:** Separate VLM inference (slow) from the control loop (fast) using a background thread.

**Context:** Qwen2.5-VL-3B-Instruct INT4 takes approximately 7–12 seconds per inference on an RTX 3060. A single-loop design that blocked on inference would make the robot unresponsive to obstacles for that entire duration.

**Implementation:** The fast loop runs at 50 Hz and executes the current plan from `self._plan` (a shared dict protected by a lock). The slow loop sleeps, checks timing, and calls `VLMInterface.plan()` in a background thread. When inference completes, the result is written to `self._plan` atomically. The fast loop also applies LiDAR safety overrides independently of VLM output.

**Trade-off:** The robot continues executing a stale plan while a new inference is in progress. Temporal filtering (majority vote over a 3-frame window on `target_position`) reduces oscillation from inference noise.

---

## Priority-based behavior arbitration in wander.py

**Decision:** Use explicit numeric priorities rather than a behavior tree or state machine in the reactive controller.

**Context:** The reactive controller (`wander.py`) handles multiple simultaneous signals: VLM plan, YOLO detections, camera obstacles, LiDAR readings, and stuck detection. A full behavior tree would add framework overhead and indirection for what is ultimately a simple priority list.

**Implementation:** The `_control_loop` function checks conditions in order and returns early at the first match. Priority 0 (VLM_TASK) defers to the planner; priority 2.5 (CAM_AVOID) catches low obstacles the LiDAR misses; priority 3 (ESCAPE) overrides even VLM planning when the stuck detector fires.

**Trade-off:** Adding a new behavior requires careful placement in the priority chain. This is acceptable given the small number of behaviors in the MVP.

---

## /behavior_state split into /planner/state + /controller/mode

**Decision:** Replace the single `/behavior_state` topic with two semantically distinct topics.

**Context:** The original `/behavior_state` mixed planner lifecycle states (IDLE, PLANNING, SEARCHING, APPROACHING, CONFIRMING, COMPLETED) with controller mode states (VLM_TASK, CAM_AVOID, AVOID, WANDER). Module B analytics could not cleanly separate mission progress from instantaneous controller behavior because they were in the same string-valued topic.

**Implementation:**
- `/planner/state` is published by `vlm_planner.py` only and carries the 6-state mission lifecycle.
- `/controller/mode` is published by `wander.py` (and by `vlm_planner.py` for EMERGENCY_STOP) and carries the 5-mode controller state: VLM_TASK, CAM_AVOID, LIDAR_AVOID, WANDER, EMERGENCY_STOP.

**Trade-off:** `expressive.py` and `language_interface.py` subscribed to `/behavior_state` for different reasons: expressive needed mission state to trigger celebration; language_interface needed it for user feedback. Both now subscribe to `/planner/state`, which carries the mission lifecycle. A future version may give language_interface a composite view of both topics.

---

## On-device VLM inference (no cloud)

**Decision:** Run VLM inference entirely on the robot's local GPU.

**Context:** Sending camera frames to a cloud API introduces network latency, depends on connectivity, and creates privacy concerns (raw camera data leaving the device). For a mall service robot, this is a significant barrier.

**Implementation:** `vlm_utils.py` wraps HuggingFace Transformers with BitsAndBytes INT4 quantization. The 3B model uses ~2 GB VRAM and runs on hardware as modest as an RTX 3060 12 GB.

**Trade-off:** On-device inference is slower (~7 s/frame for 3B vs. < 1 s for cloud APIs). This is acceptable for wayfinding tasks where the target object does not change rapidly. It would not be acceptable for conversational Q&A or real-time tracking.

---

## Camera low-obstacle detection without depth sensor

**Decision:** Use color deviation from a floor sample and Canny edge density to detect obstacles below the LiDAR scan plane, rather than adding a depth camera.

**Context:** The LiDAR is mounted at ~0.18 m from the ground. Objects lower than this (shopping bags, small dogs, low stools) are invisible to it. A depth camera would solve this cleanly but adds hardware cost and integration complexity.

**Implementation:** The bottom corners of each frame are sampled as a floor color reference. The center ROI (rows 60–85%, columns 15–85%) is compared against this reference. If both color difference and edge density exceed thresholds, `CAM_AVOID` is triggered. The side with greater color deviation determines the turn direction.

**Trade-off:** The detection is sensitive to lighting changes and unusual floor textures. The thresholds (`_CAM_COLOR_DIFF_THRESH`, `_CAM_EDGE_DENSITY_THRESH`) must be calibrated per deployment site. A depth camera or stereo pair would give higher recall with fewer false positives.

---

## Event contract v1.0

**Decision:** Define a stable JSON schema for telemetry events published to `/mission/started`, `/mission/completed`, `/safety/event`, and `/inference/event`.

**Context:** Module B (walle3-mission-analytics) needs to ingest raw events from Module A and compute KPIs. A single unstructured topic would require Module B to reverse-engineer the schema with every code change.

**Implementation:** Each event topic carries a JSON string payload with a fixed set of fields. The schema version (`v1.0`) is embedded in `/mission/started` payloads. Breaking changes require a version bump and a migration note in the analytics repository.

**Trade-off:** Using `std_msgs/String` with JSON rather than custom ROS message types avoids message definition dependencies between repositories, at the cost of losing compile-time type safety. This is acceptable for telemetry events that are consumed by analytics pipelines rather than real-time controllers.
