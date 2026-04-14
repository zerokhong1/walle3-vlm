# WallE3 v2 — VLM-Powered Autonomous Robot

[![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange)](https://gazebosim.org/)
[![Qwen2.5-VL](https://img.shields.io/badge/Qwen2.5--VL-3B%20INT4-red)](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)
[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-purple)](https://ubuntu.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Problem:** A warehouse service robot needs to understand natural language commands
> ("go to the orange box", "find the red box") and navigate autonomously to the correct object —
> without manual waypoint programming.
>
> **Solution:** Integrate a Vision-Language Model (Qwen2.5-VL) running locally on GPU,
> combined with LiDAR safety and camera obstacle detection,
> enabling fully natural-language-controlled robot navigation.

---

## Demo

![Demo](docs/media/demo_v3.gif)

| Gazebo — Arena Simulation | RViz2 — Robot + LiDAR |
|:-------------------------:|:---------------------:|
| ![Gazebo](docs/media/gazebo_screenshot.png) | ![RViz2](docs/media/rviz2_screenshot.png) |

### AI Pipeline — Simulation + LiDAR Map

![Pipeline](docs/media/demo_pipeline.png)

---

## Highlights

- **Natural Language Control** — send commands in English: `"go to the orange box"`, `"find the red box"`
- **Vision-Language Model** — Qwen2.5-VL-3B-Instruct (INT4, ~2GB VRAM) runs locally, analyzes camera frames and generates action plan JSON
- **Dual-loop Architecture** — 50Hz fast loop (LiDAR safety + execution) runs in parallel with VLM inference (~5–8s/frame) on a background thread
- **6-State Machine** — IDLE → PLANNING → SEARCHING → APPROACHING → CONFIRMING → COMPLETED
- **Camera Obstacle Detection** — analyzes bottom-frame region to detect objects below LiDAR scan height
- **Live Camera Feed** — ogre2 camera sensor + NVIDIA EGL, publishes `/camera/image_raw` + `/camera/vlm_annotated`
- **Expressive Robot** — head and arms react to VLM state (wave on arrival, tilt head when approaching)

---

## Technical Challenges & Solutions

### 1. VLM inference too slow for real-time control
**Problem:** Qwen2.5-VL takes ~8 seconds per frame — robot cannot wait idle.

**Solution:** Dual-loop architecture — 50Hz fast loop handles LiDAR safety and executes the current action plan, while VLM runs on a background thread. Robot stays reactive to obstacles while waiting for VLM inference.

### 2. Camera sensor not rendering in headless Gazebo
**Problem:** `gz sim -s` (server-only) does not initialize rendering engine → camera sensor publishes no frames.

**Solution:** Run Gazebo with GUI (`headless:=false`) on DISPLAY:1 (NVIDIA EGL, ogre2). Avoids Mesa/LIBGL_ALWAYS_SOFTWARE which causes segfault with ogre2.

### 3. LiDAR misses low obstacles
**Problem:** 2D LiDAR scans at a fixed height (~0.26m), missing objects lower than the scan plane.

**Solution:** Lower LiDAR mount (`z=-0.05`, scanning at ~0.18m) + add camera obstacle detection analyzing the bottom region of the frame (60–85%), comparing color against a floor sample and Canny edge density → triggers `CAM_AVOID` state.

### 4. Robot stuck in corners
**Problem:** Simple obstacle avoidance logic causes the robot to spin in place in tight corners.

**Solution:** Anti-stuck strategy: wider front sector (±0.30→±0.50 rad), diagonal sectors, reverse-before-turn (back up 0.4s before turning), corner escape heuristic with odometry-based stuck detector.

### 5. Stuck detection disabled during VLM navigation
**Problem:** When `vlm_planner` drives the robot, `wander.py`'s stuck detector does not fire because it only tracks velocity commands it sent itself.

**Solution:** Subscribe to `/diff_drive_base_controller/cmd_vel` to track velocity from any publisher. Use `max(wander_cmd, actual_cmd)` in stuck detection so it works regardless of which node is driving.

---

## System Architecture

```
──────────────── Gazebo Harmonic (NVIDIA EGL, ogre2) ────────────────
   Camera 15Hz          LiDAR 10Hz            IMU 100Hz
────────┬───────────────────┬──────────────────────┬─────────────────
        │    ros_gz_bridge  │                      │
   ─────▼─────         ─────▼─────           ──────▼──────
   /camera/     /scan             /imu
   image_raw
        │
   ─────▼──────────────────────────────────────────────────────
   │              vlm_planner.py  (background thread)          │
   │  Qwen2.5-VL-3B-Instruct INT4 — HuggingFace Transformers  │
   │                                                           │
   │  /user_command ──→ [slow loop ~5-8s]                      │
   │    camera frame → VLM inference → action_plan JSON        │
   │                                                           │
   │  [fast loop 50Hz]                                         │
   │    LiDAR safety check → execute action → publish cmd_vel  │
   ─────────────┬─────────────────────────────────────────────
                │ /vlm/action_plan   /behavior_state
   ─────────────▼──────────────    ──────────────────────────
   │  wander.py (state machine) │  │  expressive.py           │
   │  Priority 0: VLM_TASK      │  │  head/arm reactions      │
   │  Priority 2: CAM_AVOID     │  │  based on behavior state │
   │  Priority 3: LIDAR AVOID   │  │                          │
   │  Priority 4: WANDER        │  ──────────────────────────
   ─────────────┬───────────────
                │ /diff_drive_base_controller/cmd_vel
   ─────────────▼───────────────────────────────────────────
   │                    ros2_control                         │
   │      diff_drive + head_controller + arm_controller      │
   ──────────────────────────────────────────────────────────
```

### VLM Processing Flow

```
User: "go to the orange box"
    │
    ▼ /user_command
vlm_planner receives command → state: PLANNING
    │
    ▼ camera frame (640×480)
Qwen2.5-VL-3B-Instruct inference (~5-8s)
    │
    ▼ action_plan JSON
{
  "target_found": true,
  "target_position": "right",
  "target_distance": "medium",
  "action": { "type": "turn_right", "speed": 0.0, "angular": -0.4 },
  "status": "approaching"
}
    │
    ▼ fast loop (50Hz)
Execute action → /cmd_vel → robot moves
    │
    ▼ /camera/vlm_annotated
Frame + state overlay + target circle → RViz2
```

---

## Project Structure

```
walle3-vlm/
├── run_walle.sh                        # One-command startup
├── walle.rviz                          # RViz2 config (robot + LiDAR + 2 camera feeds)
└── walle_ws/src/
    ├── walle_description/
    │   └── urdf/walle.urdf.xacro       # Robot URDF: camera + LiDAR + IMU + joints
    ├── walle_bringup/
    │   ├── launch/
    │   │   ├── sim.launch.py           # Gazebo + controllers + optional VLM
    │   │   └── vlm.launch.py           # VLM stack only
    │   ├── config/
    │   │   ├── vlm_config.yaml         # VLM model + inference params
    │   │   ├── controllers.yaml        # ros2_control config
    │   │   └── bridge.yaml             # Gazebo ↔ ROS 2 topic bridge
    │   └── worlds/walle_arena.sdf      # Arena 8×8m, ogre2 render engine
    └── walle_demo/walle_demo/
        ├── vlm_planner.py              # VLM planning node (main AI node)
        ├── vlm_utils.py                # VLM backend wrapper (Transformers / Ollama)
        ├── language_interface.py       # Terminal input → /user_command
        ├── wander.py                   # Reactive navigation + camera obstacle detect
        ├── expressive.py               # Head/arm expressive reactions
        └── perception.py               # YOLOv8 fallback (optional)
```

---

## Setup & Run

### Requirements

| Component | Requirement |
|-----------|-------------|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic (gz-sim 8) |
| GPU | NVIDIA (≥8GB VRAM recommended) |
| VRAM | ~2GB (3B INT4) or ~6GB (7B INT4) |
| Python | 3.12+ |

### Quick Start

```bash
# 1. Clone
git clone https://github.com/zerokhong1/walle3-vlm.git
cd walle3-vlm

# 2. Install dependencies
sudo apt install -y \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-cv-bridge ros-jazzy-image-transport ros-jazzy-rviz2

pip install \
  transformers accelerate bitsandbytes qwen-vl-utils \
  torch torchvision opencv-python "numpy<2.0" \
  --break-system-packages

# 3. Build
cd walle_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash

# 4. Run
bash ../run_walle.sh
```

### Send Commands to Robot

```bash
# Via language_interface terminal (opens automatically with VLM stack)
[WallE] > go to the orange box
[WallE] > find the red box

# Or publish directly
ros2 topic pub --once /user_command std_msgs/msg/String \
  "{data: 'go to the orange box'}"
```

### Monitor Topics

```bash
ros2 topic echo /behavior_state        # IDLE / PLANNING / APPROACHING / ESCAPE ...
ros2 topic echo /vlm/action_plan       # action plan JSON
ros2 topic hz /camera/image_raw        # camera rate (~13Hz)
```

---

## Results

| Metric | Value |
|--------|-------|
| VLM inference latency | ~5–8s/frame (3B INT4, RTX 3060 12GB) |
| Fast-loop frequency | 50Hz (LiDAR safety + execution) |
| Camera feed | ~13Hz (640×480, ogre2 + NVIDIA EGL) |
| Obstacle avoidance | LiDAR (≥0.18m) + Camera (low objects) |
| Languages supported | English |
| VRAM usage | ~2GB (3B INT4), Gazebo uses ~6.7GB |
| Corner escape | Reverse 0.8–1.4s + turn 1.5–2.5s |

---

## Roadmap

- [x] Robot URDF + Gazebo simulation (camera + LiDAR + IMU)
- [x] ros2_control (diff_drive + head + arm controllers)
- [x] LiDAR obstacle avoidance
- [x] Qwen2.5-VL Vision-Language Model integration
- [x] Natural language commands (English)
- [x] Dual-loop VLM architecture (50Hz + background inference)
- [x] Camera sensor enabled (ogre2 + NVIDIA EGL)
- [x] VLM annotated camera feed (`/camera/vlm_annotated`)
- [x] Camera-based low obstacle detection
- [x] LIDAR mount optimized (z=-0.05, ~0.18m from ground)
- [x] Anti-stuck: wider sectors, reverse-before-turn, corner escape
- [x] Stuck detection works during VLM navigation
- [ ] Voice input (speech-to-text → `/user_command`)
- [ ] Sim-to-real transfer (physical robot hardware)
- [ ] Edge deployment (Jetson Orin Nano)

---

## Technologies

**Robotics:** ROS 2 Jazzy · Gazebo Harmonic · URDF/Xacro · ros2_control · ros_gz_bridge

**AI/ML:** Qwen2.5-VL-3B-Instruct · HuggingFace Transformers · BitsAndBytes INT4 · OpenCV · YOLOv8

**Languages:** Python 3.12 · XML/SDF · YAML · Bash

**Hardware:** NVIDIA RTX 3060 12GB · GPU EGL rendering (ogre2)

---

## Author

**Cong Thai** — Robotics & AI Developer

---
