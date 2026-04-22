# WallE3 v2 — VLM-Powered Autonomous Robot

[![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange)](https://gazebosim.org/)
[![Qwen2.5-VL](https://img.shields.io/badge/Qwen2.5--VL-3B%20INT4-red)](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)
[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-purple)](https://ubuntu.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Problem:** A service robot needs to understand natural language commands
> ("go to the orange box", "find the red chair") and navigate autonomously to
> the correct object — without manual waypoint programming.
>
> **Solution:** Integrate a Vision-Language Model (Qwen2.5-VL-3B) running
> locally on GPU, combined with a priority-arbitrated safety layer and
> an independent monitoring stack, enabling fully natural-language-controlled
> robot navigation with real-time telemetry.

This is **Module A** of the WallE3 platform. Module B (`walle3-mission-analytics`)
ingests telemetry from this module and computes mission KPIs. Module C
(`walle3-ops-simulator`) generates synthetic training scenarios.

---

## Demo

![Demo](docs/media/demo_v3.gif)

| Gazebo — Arena Simulation | RViz2 — Robot + LiDAR |
|:-------------------------:|:---------------------:|
| ![Gazebo](docs/media/gazebo_screenshot.png) | ![RViz2](docs/media/rviz2_screenshot.png) |

### AI Pipeline

![Pipeline](docs/media/demo_pipeline.png)

---

## Architecture

### Node graph

```
User terminal
    │ /user_command
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    vlm_planner.py                           │
│                                                             │
│  Slow loop (~0.2 Hz, background thread):                    │
│    camera frame → Qwen2.5-VL-3B INT4 → action_plan JSON    │
│                                                             │
│  Fast loop (50 Hz):                                         │
│    LiDAR safety → execute plan → publish /cmd_vel/vlm       │
│    obstacle < 0.35m → escape 1.5s → publish /cmd_vel/safety │
│    "stop"/"dừng" → immediate halt via /cmd_vel/safety       │
└─────────┬──────────────┬────────────────────────────────────┘
          │              │
/cmd_vel/vlm    /planner/state  /mission/started  /safety/event
          │              │      /mission/completed /inference/event
          ▼              ▼
┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐
│  wander.py   │  │ stuck_watchdog   │  │ mission_logger  │
│              │  │                  │  │ (→ CSV + Module B│
│ LIDAR_AVOID →│  │ 30s warn         │  └─────────────────┘
│ /cmd_vel/    │  │ 60s abort        │
│ safety       │  └──────────────────┘  ┌─────────────────┐
│              │                        │ rosbag_trigger  │
│ WANDER →     │                        │ HIGH/CRITICAL → │
│ /cmd_vel/    │                        │ ~/walle_bags/   │
│ wander       │                        └─────────────────┘
└─────┬────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                     cmd_vel_mux.py                          │
│                                                             │
│  /cmd_vel/safety  priority 0  timeout 0.25 s               │
│  /cmd_vel/vlm     priority 1  timeout 0.15 s               │
│  /cmd_vel/wander  priority 2  timeout 0.25 s               │
│                                                             │
│  → /diff_drive_base_controller/cmd_vel  (50 Hz)            │
└─────────────────────────────────────────────────────────────┘
```

### Why priority arbitration matters

Previously, `vlm_planner` (50 Hz) and `wander` (10 Hz) both published
directly to the diff-drive controller. The last writer always won — meaning
wander's LIDAR_AVOID and CAM_AVOID escape commands were silently overwritten
by VLM plan execution at 50 Hz. The robot appeared stuck because it was
receiving conflicting commands 50 times per second.

`cmd_vel_mux` resolves this: the safety channel is reserved exclusively for
obstacle escapes and emergency stops. It always overrides VLM navigation.
VLM navigation overrides basic wandering.

### Dual-loop VLM architecture

```
Fast loop 50 Hz ─────────────────────────────────────────────────
  LiDAR check → escape? → execute last plan → publish cmd_vel
  Stop keyword detected? → immediate halt (no VLM needed)

Slow loop ~0.2 Hz (background thread) ───────────────────────────
  Wait inference_interval (5 s default)
  Capture camera frame → Qwen2.5-VL inference (~8–12 s)
  Write result to self._plan (plan_lock)
  Fast loop picks up new plan on next tick
```

Qwen2.5-VL inference takes 8–12 s on an RTX 3060 12 GB (3B INT4). The
dual-loop allows the robot to stay reactive to obstacles and commands
throughout the inference window.

---

## Event contract v1.0

All telemetry topics use `std_msgs/String` with JSON payloads. Schema
version is embedded in `/mission/started`. Module B ingests these topics.

| Topic | Publisher | Payload fields |
|-------|-----------|---------------|
| `/planner/state` | vlm_planner | plain string: `IDLE\|PLANNING\|SEARCHING\|APPROACHING\|CONFIRMING\|COMPLETED` |
| `/controller/mode` | vlm_planner, wander | plain string: `VLM_TASK\|CAM_AVOID\|LIDAR_AVOID\|WANDER\|EMERGENCY_STOP` |
| `/mux/active_channel` | cmd_vel_mux | plain string: `SAFETY\|VLM\|WANDER\|idle` |
| `/mission/started` | vlm_planner | `{mission_id, mission_type, user_command, timestamp, robot_id, site_id, schema_version}` |
| `/mission/completed` | vlm_planner, stuck_watchdog | `{mission_id, success, duration_s, intervention_count, reason}` |
| `/safety/event` | vlm_planner, wander, stuck_watchdog | `{event_type, severity, timestamp}` |
| `/inference/event` | vlm_planner | `{model, latency_ms, input_tokens, output_valid, target_found, confidence}` |

---

## Node reference

| Node | File | Role |
|------|------|------|
| `vlm_planner` | `vlm_planner.py` | VLM inference + mission state machine + fast safety loop |
| `wander` | `wander.py` | Reactive obstacle avoidance (LIDAR + camera) |
| `cmd_vel_mux` | `cmd_vel_mux.py` | Priority arbitration for `/cmd_vel` (safety > vlm > wander) |
| `stuck_watchdog` | `stuck_watchdog_node.py` | Independent watchdog: warn at 30s, abort at 60s |
| `rosbag_trigger` | `rosbag_trigger_node.py` | Auto-record 60s bag on HIGH/CRITICAL safety event |
| `mission_logger` | `mission_logger_node.py` | Write telemetry events to CSV fact tables (Module B) |
| `expressive` | `expressive.py` | Head/arm reactions driven by `/planner/state` |
| `language_interface` | `language_interface.py` | Terminal → `/user_command` |

---

## Project structure

```
walle3-vlm/
├── run_walle.sh                         # One-command startup (Gazebo + VLM + logger)
├── record_demo.sh                       # Record demo GIF via ffmpeg screen capture
├── walle.rviz                           # RViz2 config
└── walle_ws/src/
    ├── walle_description/
    │   └── urdf/walle.urdf.xacro        # Robot model: camera + LiDAR + IMU
    ├── walle_bringup/
    │   ├── launch/
    │   │   ├── sim.launch.py            # Gazebo + controllers + wander/mux/watchdog
    │   │   └── vlm.launch.py            # VLM stack: planner + mux + watchdog + logger
    │   ├── config/
    │   │   ├── vlm_config.yaml          # VLM model params + inference interval
    │   │   ├── controllers.yaml         # ros2_control config
    │   │   └── bridge.yaml              # Gazebo ↔ ROS 2 bridge
    │   └── worlds/walle_arena.sdf       # 8×8m arena, ogre2 renderer
    └── walle_demo/walle_demo/
        ├── vlm_planner.py               # VLM planning + fast safety loop
        ├── vlm_utils.py                 # Transformers / Ollama backend wrapper
        ├── wander.py                    # Reactive navigation controller
        ├── cmd_vel_mux.py               # cmd_vel priority arbitration
        ├── stuck_watchdog_node.py       # Independent stuck detector
        ├── rosbag_trigger_node.py       # Auto-record on safety events
        ├── mission_logger_node.py       # Telemetry → CSV (Module B integration)
        ├── language_interface.py        # Terminal input → /user_command
        └── expressive.py               # Head/arm animations
```

---

## Setup

### Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic (gz-sim 8) |
| GPU | NVIDIA (≥8 GB VRAM recommended) |
| VRAM | ~2 GB (3B INT4); Gazebo uses ~6.7 GB |
| Python | 3.12+ |

### Install

```bash
git clone https://github.com/zerokhong1/walle3-vlm.git
cd walle3-vlm

# ROS 2 dependencies
sudo apt install -y \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-cv-bridge ros-jazzy-image-transport ros-jazzy-rviz2

# Python / AI dependencies
pip install \
  transformers accelerate bitsandbytes qwen-vl-utils \
  torch torchvision opencv-python "numpy<2.0" \
  --break-system-packages

# Build
cd walle_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
```

### Run

```bash
bash run_walle.sh
```

The script starts Gazebo, RViz2, the VLM stack, and the mission logger.
VLM model loading takes ~20 s. The robot is ready when you see
`[VLM] Model loaded` in the terminal.

---

## Usage

### Send commands

```bash
# Via language_interface (opens automatically)
[WallE] > go to the orange box
[WallE] > find the red chair

# Stop immediately (bypasses VLM, <1 tick latency)
[WallE] > stop
[WallE] > dừng

# Or publish directly
ros2 topic pub --once /user_command std_msgs/msg/String \
  "{data: 'go to the orange box'}"
```

Stop keywords: `stop`, `dừng`, `dung`, `halt`, `cancel`, `hủy`, `huy`.
These bypass the VLM pipeline entirely — the robot halts within one
fast-loop tick (~20 ms).

### Monitor

```bash
ros2 topic echo /planner/state          # mission lifecycle
ros2 topic echo /controller/mode        # controller behavior
ros2 topic echo /mux/active_channel     # which cmd_vel channel is winning
ros2 topic echo /safety/event           # collision, stuck events
ros2 topic echo /vlm/action_plan        # VLM output JSON

# Rosbag auto-records to ~/walle_bags/ on HIGH/CRITICAL safety events
ls ~/walle_bags/

# CSV telemetry (Mission Analytics / Module B)
ls ~/walle_logs/
```

### Record a demo GIF

```bash
# With simulation already running
./record_demo.sh --sim-already-up

# Full auto (starts simulation + records + converts)
./record_demo.sh
```

---

## Performance

| Metric | Value |
|--------|-------|
| VLM inference latency | ~8–12 s/frame (3B INT4, RTX 3060 12 GB) |
| Fast-loop frequency | 50 Hz |
| Stop command latency | < 20 ms (bypasses VLM) |
| Camera feed | ~13 Hz (640×480, ogre2 + NVIDIA EGL) |
| Emergency escape duration | 1.5 s (stable reverse + turn) |
| Stuck detection | warn 30 s · abort 60 s · threshold 20 cm |
| VRAM usage | ~2 GB model · ~6.7 GB Gazebo |

---

## Known issues

See [ISSUES.md](ISSUES.md) for the full issue catalog with severity,
root-cause analysis, and triage order.

Issues resolved in the current codebase:

| ID | Issue | Resolution |
|----|-------|-----------|
| I-003 | `/behavior_state` mixed signals | Split into `/planner/state` + `/controller/mode` |
| I-004 | Event contract v1.0 not published | All 6 topics implemented with full JSON schema |
| I-005 | No observability for debugging | Structured `[INFER]` logs + `rosbag_trigger_node` |
| I-006 | Priority race between VLM and safety | `cmd_vel_mux` with 3-channel priority arbitration |
| I-007 | No independent stuck detector | `stuck_watchdog_node` (warn 30s / abort 60s) |
| I-011 | Stop command went through VLM loop | Fast-path stop: < 20 ms via `/cmd_vel/safety` |

Open issues (S0–S1): I-001, I-002, I-008, I-009, I-010, I-012, I-014.

---

## Roadmap

- [x] Robot URDF + Gazebo simulation (camera + LiDAR + IMU)
- [x] ros2_control (diff_drive + head + arm controllers)
- [x] LiDAR obstacle avoidance + camera low-obstacle detection
- [x] Qwen2.5-VL Vision-Language Model (local GPU, INT4)
- [x] Dual-loop architecture (50 Hz safety + background VLM inference)
- [x] 6-state mission planner (IDLE → PLANNING → … → COMPLETED)
- [x] Event contract v1.0 + Mission Analytics integration (Module B)
- [x] cmd_vel priority mux (safety > VLM > wander)
- [x] Independent stuck watchdog (30s warn / 60s abort)
- [x] Fast-path stop command (< 20 ms, bypass VLM)
- [x] Auto rosbag recording on safety events
- [ ] Confidence threshold enforcement (I-010)
- [ ] Spatial memory for known obstacles (I-008)
- [ ] Voice input (speech-to-text → `/user_command`)
- [ ] Sim-to-real transfer

---

## Technologies

**Robotics:** ROS 2 Jazzy · Gazebo Harmonic · URDF/Xacro · ros2_control · ros_gz_bridge

**AI/ML:** Qwen2.5-VL-3B-Instruct · HuggingFace Transformers · BitsAndBytes INT4 · OpenCV · YOLOv8 *(planned low-obstacle detection fallback — `fallback_to_yolo=false` in config)*

**Languages:** Python 3.12 · XML/SDF · YAML · Bash

**Hardware:** NVIDIA RTX 3060 12 GB · GPU EGL rendering (ogre2)

---

## Robotics Business Analyst Engineer Portfolio Fit

WallE3 VLM is not only a robotics prototype — it is a BA/engineering case study demonstrating how a robotics use case is translated from business problem to deployable technical requirements, telemetry, KPIs, safety controls, and ROI analysis.

| Competency | Evidence in this project |
|-----------|--------------------------|
| Market/use-case analysis | Warehouse + mall locate-and-fetch, target users, ROI/TCO assumptions ([docs/business/market_use_case_analysis.md](docs/business/market_use_case_analysis.md)) |
| Business requirements | BRD with 8 requirements, business context, stakeholders, constraints ([docs/product/02_business_requirements_document.md](docs/product/02_business_requirements_document.md)) |
| Technical requirements | PRD with 23 functional + 14 non-functional requirements ([docs/product/03_product_requirements_document.md](docs/product/03_product_requirements_document.md)) |
| User stories & acceptance criteria | 14-story MoSCoW backlog mapped to requirements ([docs/product/06_backlog_user_stories.md](docs/product/06_backlog_user_stories.md)) |
| Process modeling | Current-state vs future-state workflow analysis + Mermaid diagrams ([docs/business/workflow_analysis.md](docs/business/workflow_analysis.md)) |
| KPI design | 8 operational KPIs mapped to ROS 2 telemetry topics ([docs/product/08_kpi_dashboard_spec.md](docs/product/08_kpi_dashboard_spec.md)) |
| Data analytics | SQL queries + Python KPI analysis + dashboard PNG ([analytics/](analytics/)) |
| Safety governance | FMEA-lite (12 failure modes), priority mux, watchdog, 6-scenario UAT safety tests |
| Compliance mapping | ISO 3691-4, ISO 13849-1 gap analysis ([docs/safety/compliance_mapping.md](docs/safety/compliance_mapping.md)) |
| Deployment planning | Site survey checklist, pilot rollout plan ([docs/deployment/](docs/deployment/)) |
| ROI analysis | ROI/TCO one-pager + SQL ROI query ([docs/product/17_roi_tco_one_pager.md](docs/product/17_roi_tco_one_pager.md)) |
| Architecture decisions | 4 ADRs with context, alternatives, and tradeoffs ([docs/adr/](docs/adr/)) |

**Status:** Simulation MVP and BA/engineering documentation complete. Physical pilot would require site-specific safety validation, hardware testing, compliance review, and stakeholder approval.

---

## Author

**Cong Thai** — VinUniversity · Robotics & AI Developer
