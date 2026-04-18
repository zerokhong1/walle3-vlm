# WallE3 — Module A: Robot

**Edge-product layer: natural-language-controlled service robot running Vision-Language Models fully on-device.**

ROS 2 Jazzy / Gazebo Harmonic / Qwen2.5-VL-3B-Instruct INT4 / Python 3.12 / Ubuntu 24.04

---

## Platform context

This repository is **Module A** of a three-module platform:

| Module | Repository | Role |
|---|---|---|
| **A. Robot** (this repo) | `walle3-vlm` | Edge product — robot running VLM on-device |
| **B. Mission Analytics** | `walle3-mission-analytics` | Fleet observability, KPI dashboard |
| **C. Ops Simulator** | `walle3-ops-simulator` | Capacity planning, pre-sales tooling |

Module A receives user commands, executes them via VLM + safety loop, and emits telemetry events consumed by Module B. It is not a standalone demo — the full value is understood across all three modules.

---

## Architecture

```
User terminal (language_interface)
        |
        | /user_command
        v
VLM Planner (vlm_planner.py)          — slow loop ~0.2 Hz, background thread
  - Qwen2.5-VL-3B-Instruct INT4
  - 6-state machine: IDLE -> PLANNING -> SEARCHING -> APPROACHING -> CONFIRMING -> COMPLETED
  - Publishes: /planner/state  /vlm/action_plan  /vlm/scene_description
  - Fast loop 50 Hz: execute plan + LiDAR safety override

Reactive Controller (wander.py)        — 10 Hz control loop
  - Priority arbitration: VLM_TASK > CAM_AVOID > LIDAR_AVOID > WANDER
  - LiDAR obstacle sectors (wide + diagonal)
  - Camera low-obstacle detection (color diff + edge density)
  - Stuck detector: odom/cmd_vel cross-check, emergency escape
  - Publishes: /controller/mode  /safety/event

Perception (perception.py)             — YOLOv8n, optional
  - Person detection -> ATTENTION behavior in wander
  - Object detection -> CURIOUS behavior

Expressive Motion (expressive.py)      — reacts to /planner/state + detections
  - Head tracks detected objects
  - Arms react to person / object / celebration

VLM Perception (vlm_perception.py)    — optional, shares GPU with planner
  - Scene understanding, detection output compatible with wander

        |
        v
ros2_control (100 Hz)
  - diff_drive_base_controller  (wheel_separation: 0.39m, wheel_radius: 0.095m)
  - head_controller             (head_yaw_joint, head_pitch_joint)
  - arm_controller              (left_arm_joint, right_arm_joint)
```

### Dual-loop design

The fast loop (50 Hz) executes the current VLM plan and applies LiDAR safety overrides without waiting for the next VLM inference. The slow loop (~0.2 Hz) runs VLM inference in a background thread. This decoupling ensures the robot responds to obstacles at control frequency even when VLM inference takes 7–12 seconds per frame.

---

## Topic contract v1.0

These topics form the stable interface between Module A and Module B. Do not change topic names or payload schema without a version bump.

### State topics

| Topic | Type | Values | Publisher |
|---|---|---|---|
| `/planner/state` | String | `IDLE` `PLANNING` `SEARCHING` `APPROACHING` `CONFIRMING` `COMPLETED` | vlm_planner |
| `/controller/mode` | String | `VLM_TASK` `CAM_AVOID` `LIDAR_AVOID` `WANDER` `EMERGENCY_STOP` | wander / vlm_planner |

### Event topics (JSON payloads)

**`/mission/started`**
```json
{
  "mission_id":     "<uuid>",
  "mission_type":   "vlm_navigation",
  "user_command":   "<raw text>",
  "timestamp":      1234567890.123,
  "robot_id":       "walle3",
  "site_id":        "default",
  "schema_version": "v1.0"
}
```

**`/mission/completed`**
```json
{
  "mission_id":         "<uuid>",
  "success":            true,
  "duration_s":         42.5,
  "intervention_count": 2,
  "reason":             "target_reached"
}
```

**`/safety/event`**
```json
{
  "event_type": "collision_risk | stuck | manual_stop",
  "severity":   "high | medium | low",
  "timestamp":  1234567890.123
}
```

**`/inference/event`**
```json
{
  "model":        "Qwen/Qwen2.5-VL-3B-Instruct",
  "latency_ms":   7234.1,
  "input_tokens": 0,
  "output_valid": true,
  "confidence":   0.87
}
```

`/operator/override` is defined in the contract schema but not yet published (no operator interface implemented).

---

## System requirements

| Component | Requirement |
|---|---|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic (gz-sim 8) |
| GPU | NVIDIA with >= 4 GB VRAM (8 GB recommended) |
| VRAM | ~2 GB for 3B INT4, ~6 GB for 7B INT4 |
| Python | 3.12 |
| Display | X11 with GNOME for camera rendering (EGL) |

---

## Install dependencies

```bash
# ROS 2 packages
sudo apt install -y \
  ros-jazzy-ros-gz \
  ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-cv-bridge \
  ros-jazzy-image-transport \
  ros-jazzy-rviz2

# Python — VLM inference
pip install \
  transformers accelerate bitsandbytes \
  qwen-vl-utils torch torchvision \
  opencv-python "numpy<2.0" \
  --break-system-packages

# Python — YOLOv8 (optional, for person/object detection)
pip install ultralytics --break-system-packages
```

---

## Build

```bash
cd ~/VinUni_proj/walle_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## Run

### Full simulation stack

```bash
# Gazebo + controllers + wander + expressive + VLM
ros2 launch walle_bringup sim.launch.py \
  start_demo:=true \
  start_vlm:=true \
  headless:=false
```

Launch arguments:

| Argument | Default | Description |
|---|---|---|
| `start_demo` | false | Start wander + expressive nodes |
| `start_perception` | false | Start YOLOv8 perception node |
| `start_vlm` | false | Start VLM planner + language interface |
| `headless` | true | Run Gazebo without GUI |
| `x`, `y`, `z` | 0, 0, 0.3 | Initial robot spawn position |

### VLM stack only (simulation already running)

```bash
ros2 launch walle_bringup vlm.launch.py \
  start_vlm_perception:=false
```

### Send commands

```bash
# Via interactive terminal (opens with VLM stack)
[WallE] > go to the orange barrel
[WallE] > find the red box
[WallE] > stop

# Or publish directly
ros2 topic pub --once /user_command std_msgs/msg/String \
  "{data: 'go to the orange barrel'}"
```

---

## Monitor

```bash
# Mission lifecycle
ros2 topic echo /planner/state

# Controller mode
ros2 topic echo /controller/mode

# Event contract
ros2 topic echo /mission/started
ros2 topic echo /mission/completed
ros2 topic echo /safety/event
ros2 topic echo /inference/event

# VLM output
ros2 topic echo /vlm/scene_description
ros2 topic echo /vlm/action_plan

# Camera rates
ros2 topic hz /camera/image_raw
ros2 topic hz /camera/vlm_annotated
```

---

## Configuration

File: `src/walle_bringup/config/vlm_config.yaml`

```yaml
walle_vlm_planner:
  ros__parameters:
    model_backend: "transformers"      # "transformers" or "ollama"
    model_name: "Qwen/Qwen2.5-VL-3B-Instruct"
    quantize_4bit: true                # INT4 quantization, ~2 GB VRAM
    language: "en"                     # "en" or "vi"
    inference_interval_sec: 5.0        # seconds between VLM calls
    vlm_timeout_sec: 12.0
    max_speed: 0.25                    # m/s hard cap
```

The 7B model (`Qwen2.5-VL-7B-Instruct`) requires ~6 GB VRAM but reduces inference latency from ~7 s to ~1.5 s per frame.

---

## Repository structure

```
walle_ws/
├── README.md
├── docs/
│   ├── project_origin.md          # Original 3-day sprint plan (historical)
│   └── architecture_decisions.md  # Key design decisions and trade-offs
└── src/
    ├── walle_description/
    │   └── urdf/walle.urdf.xacro  # Robot: camera + LiDAR + IMU, diff drive base
    ├── walle_bringup/
    │   ├── launch/
    │   │   ├── sim.launch.py      # Full simulation + all nodes
    │   │   └── vlm.launch.py      # VLM stack only
    │   ├── config/
    │   │   ├── vlm_config.yaml    # VLM model and inference parameters
    │   │   ├── controllers.yaml   # ros2_control controller parameters
    │   │   └── bridge.yaml        # ROS <-> Gazebo topic bridge
    │   └── worlds/
    │       └── walle_arena.sdf    # 8x8m arena, ogre2 renderer
    └── walle_demo/
        └── walle_demo/
            ├── vlm_planner.py     # VLM brain: dual-loop, 6-state machine, event contract
            ├── vlm_perception.py  # Parallel scene understanding (optional)
            ├── vlm_utils.py       # VLM backend wrapper (Transformers / Ollama)
            ├── language_interface.py  # Terminal input -> /user_command
            ├── wander.py          # Reactive nav: LiDAR + camera obstacle detection
            ├── expressive.py      # Head/arm reactions by state and detection
            └── perception.py      # YOLOv8 fallback detection (optional)
```

---

## Node reference

| Node | Executable | Key subscriptions | Key publications |
|---|---|---|---|
| `walle_vlm_planner` | `vlm_planner` | `/camera/image_raw` `/scan` `/user_command` | `/planner/state` `/controller/mode` `/vlm/action_plan` `/mission/*` `/safety/event` `/inference/event` |
| `walle_reactive_wander` | `wander` | `/scan` `/camera/image_raw` `/vlm/action_plan` `/detections` | `/controller/mode` `/safety/event` `/diff_drive_base_controller/cmd_vel` |
| `walle_expressive_motion` | `expressive` | `/planner/state` `/detections` `/vlm/action_plan` | `/head_controller/joint_trajectory` `/arm_controller/joint_trajectory` |
| `walle_language_interface` | `language_interface` | `/planner/state` `/vlm/scene_description` | `/user_command` |
| `walle_yolo_perception` | `perception` | `/camera/image_raw` | `/detections` `/camera/image_detected` |
| `walle_vlm_perception` | `vlm_perception` | `/camera/image_raw` | `/vlm/detections` `/vlm/scene` |

---

## Low-obstacle detection

LiDAR is mounted at z = -0.05 from base_link (~0.18 m from ground), covering objects from that height upward. Objects lower than the LiDAR plane (bags, small animals, low furniture) are detected by the camera layer.

The camera ROI (bottom 60–85% of frame, center 70% width) is analyzed for color deviation from a floor sample taken at the bottom corners of each frame. If both color difference and Canny edge density exceed their thresholds, the controller switches to `CAM_AVOID`.

Thresholds (tunable in `wander.py`):
- `_CAM_COLOR_DIFF_THRESH`: 18.0 — color deviation from floor mean
- `_CAM_EDGE_DENSITY_THRESH`: 0.04 — fraction of edge pixels in ROI

---

## Roadmap

| Item | Status | Target |
|---|---|---|
| Robot URDF + Gazebo simulation | Done | |
| ros2_control (diff drive + head + arm) | Done | |
| LiDAR obstacle avoidance | Done | |
| YOLOv8 detection fallback | Done | |
| Qwen2.5-VL integration | Done | |
| Natural language commands (EN/VI) | Done | |
| Dual-loop VLM architecture | Done | |
| Camera sensor (ogre2 + NVIDIA EGL) | Done | |
| VLM annotated camera feed | Done | |
| Low-obstacle camera detection | Done | |
| Anti-stuck (wider sectors, reverse, corner escape) | Done | |
| Split `/behavior_state` -> `/planner/state` + `/controller/mode` | Done | Q2 2026 |
| Event contract v1.0 publisher | Done | Q2 2026 |
| Confidence-threshold fallback (re-query user) | Planned | Q3 2026 |
| Voice input (Vietnamese STT) | Planned | Q1 2027 |
| Sim-to-real transfer on WallE3 hardware | Planned | Q4 2026 |
| Multi-robot coordination | Planned | 2027 |

---

## Safety and privacy

- VLM inference is fully on-device. No camera frames are sent to external servers.
- Raw frames are discarded after processing and are not stored.
- LiDAR emergency stop activates at 0.35 m front distance; speed is reduced at 0.60 m.
- Speed is hard-capped at 0.25 m/s in `vlm_config.yaml`.
- A physical emergency stop button is required on any production hardware deployment.
- Compliance target: PDPA Vietnam.

---

## Tech stack

**Robotics:** ROS 2 Jazzy / Gazebo Harmonic / URDF-Xacro / ros2_control / ros_gz_bridge

**AI/ML:** Qwen2.5-VL-3B-Instruct / HuggingFace Transformers / BitsAndBytes INT4 / OpenCV / YOLOv8

**Languages:** Python 3.12 / XML-SDF / YAML

**Hardware target:** NVIDIA RTX 3060 12 GB / GPU EGL rendering (ogre2)

---

## Related repositories

- [walle3-mission-analytics](https://github.com/zerokhong1/walle3-mission-analytics) — telemetry ingestion, KPI dictionary, SQL model, dashboard specifications
- [walle3-ops-simulator](https://github.com/zerokhong1/walle3-ops-simulator) — deployment simulator, capacity planning, ROI estimator
