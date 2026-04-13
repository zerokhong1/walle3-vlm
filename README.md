# WallE3 v2 — VLM-Powered Autonomous Robot

[![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange)](https://gazebosim.org/)
[![Qwen2.5-VL](https://img.shields.io/badge/Qwen2.5--VL-3B%20INT4-red)](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)
[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-purple)](https://ubuntu.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Bài toán:** Robot service trong nhà kho / nhà máy cần hiểu lệnh tự nhiên của công nhân Việt Nam
> ("đi tới thùng màu cam", "tìm hộp đỏ") và tự hành đến đúng vật thể — không cần lập trình waypoint thủ công.
>
> **Giải pháp:** Tích hợp Vision-Language Model (Qwen2.5-VL) chạy local trên GPU,
> kết hợp LiDAR safety và camera obstacle detection, điều khiển robot hoàn toàn bằng ngôn ngữ tự nhiên tiếng Việt/English.

---

## Demo

<!-- 🎥 **[Video Demo](https://youtube.com/...)** — Xem robot nhận lệnh tiếng Việt và tự hành trong Gazebo -->

| Gazebo — Arena Simulation | RViz2 — Robot + LiDAR |
|:-------------------------:|:---------------------:|
| ![Gazebo](docs/media/gazebo_screenshot.png) | ![RViz2](docs/media/rviz2_screenshot.png) |

### AI Pipeline — Simulation + LiDAR Map

![Pipeline](docs/media/demo_pipeline.png)

---

## Điểm nổi bật

- **Natural Language Control** — gửi lệnh tiếng Việt/English: `"đi tới thùng màu cam"`, `"find the red box"`
- **Vision-Language Model** — Qwen2.5-VL-3B-Instruct (INT4, ~2GB VRAM) chạy local, phân tích camera frame và sinh action plan JSON
- **Dual-loop Architecture** — vòng lặp nhanh 50Hz (LiDAR safety + execution) song song VLM inference (~8s/frame) trên background thread
- **State Machine 6 trạng thái** — IDLE → PLANNING → SEARCHING → APPROACHING → CONFIRMING → COMPLETED
- **Camera Obstacle Detection** — phân tích bottom-frame để phát hiện vật cản thấp hơn tầm quét LIDAR
- **Live Camera Feed** — camera sensor ogre2 + NVIDIA EGL, publish `/camera/image_raw` + `/camera/vlm_annotated`
- **Expressive Robot** — đầu/tay phản ứng theo trạng thái VLM (vươn tay khi đến đích, nghiêng đầu khi tiếp cận)

---

## Thách thức kỹ thuật & Cách giải quyết

### 1. VLM inference quá chậm cho real-time control
**Vấn đề:** Qwen2.5-VL mất ~8 giây mỗi frame — robot không thể đứng im chờ.

**Giải pháp:** Thiết kế dual-loop architecture — fast loop 50Hz xử lý LiDAR safety và execute action plan, trong khi VLM chạy trên background thread. Robot vẫn reactive với vật cản trong khi chờ VLM inference.

### 2. Camera sensor không render trong Gazebo headless
**Vấn đề:** `gz sim -s` (server-only) không khởi tạo rendering engine → camera sensor không publish frame.

**Giải pháp:** Chạy Gazebo với GUI (`headless:=false`) trên DISPLAY:1 (NVIDIA EGL, ogre2), không dùng Mesa/LIBGL_ALWAYS_SOFTWARE để tránh segfault với ogre2.

### 3. LiDAR không phát hiện vật cản thấp
**Vấn đề:** LiDAR 2D quét ở độ cao cố định (~0.26m), bỏ sót vật thể thấp hơn tầm quét.

**Giải pháp:** Hạ LIDAR mount (`z=-0.05`, quét ở ~0.18m) + thêm camera obstacle detection phân tích vùng dưới frame (60–85%), so sánh màu sắc với floor sample và Canny edge density → state `CAM_AVOID`.

### 4. Xử lý tiếng Việt trong VLM prompt
**Vấn đề:** Các VLM phổ biến không xử lý tốt lệnh tiếng Việt có dấu.

**Giải pháp:** Chọn Qwen2.5-VL vì hỗ trợ multilingual tốt, thiết kế prompt template song ngữ với structured JSON output để đảm bảo action plan luôn parseable.

### 5. Robot bị kẹt ở góc tường
**Vấn đề:** Logic tránh vật cản đơn giản khiến robot xoay tại chỗ ở góc hẹp, không thoát được.

**Giải pháp:** Implement anti-stuck strategy: mở rộng front sector (±0.30→±0.50 rad), thêm diagonal sectors, reverse-before-turn (lùi 0.4s trước khi quay), corner escape heuristic với stuck detector qua odometry.

---

## Kiến trúc hệ thống

```
────────────────── Gazebo Harmonic (NVIDIA EGL, ogre2) ──────────────────
   Camera 15Hz          LiDAR 10Hz            IMU 100Hz
────────┬───────────────────┬──────────────────────┬──────────────────────
        │    ros_gz_bridge  │                      │
   ─────▼─────         ─────▼─────           ──────▼──────
   /camera/     /scan             /imu
   image_raw
        │
   ─────▼──────────────────────────────────────────────────────
   │              vlm_planner.py  (background thread)          │
   │  Qwen2.5-VL-3B-Instruct INT4 — HuggingFace Transformers  │
   │                                                           │
   │  /user_command ──→ [slow loop ~8s]                        │
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

### Luồng xử lý VLM

```
User: "đi tới thùng màu cam"
    │
    ▼ /user_command
vlm_planner nhận lệnh → state: PLANNING
    │
    ▼ camera frame (640×480)
Qwen2.5-VL-3B-Instruct inference (~8s)
    │
    ▼ action_plan JSON
{
  "action": "turn_right",
  "target": "thùng màu cam",
  "target_position": "right",
  "linear_speed": 0.2,
  "angular_speed": 0.4,
  "message": "Phát hiện thùng cam bên phải, đang tiếp cận"
}
    │
    ▼ fast loop (50Hz)
Execute action → /cmd_vel → robot di chuyển
    │
    ▼ /camera/vlm_annotated
Frame + state overlay + target indicator → RViz2
```

---

## Cấu trúc project

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
        ├── vlm_perception.py           # Parallel scene understanding
        ├── vlm_utils.py                # VLM backend wrapper (Transformers / Ollama)
        ├── language_interface.py       # Terminal input → /user_command
        ├── wander.py                   # Reactive navigation + camera obstacle detect
        ├── expressive.py               # Head/arm expressive reactions
        └── perception.py               # YOLOv8 fallback (optional)
```

---

## Cài đặt & Chạy

### Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|---------|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic (gz-sim 8) |
| GPU | NVIDIA (≥8GB VRAM khuyến nghị) |
| VRAM | ~2GB (3B INT4) hoặc ~6GB (7B INT4) |
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

### Gửi lệnh cho robot

```bash
# Qua terminal language_interface (tự động mở khi VLM stack chạy)
[WallE] > đi tới thùng màu cam
[WallE] > find the red box

# Hoặc publish trực tiếp
ros2 topic pub --once /user_command std_msgs/msg/String \
  "{data: 'đi tới thùng màu cam'}"
```

### Monitor

```bash
ros2 topic echo /behavior_state        # IDLE / PLANNING / APPROACHING / ESCAPE ...
ros2 topic echo /vlm/scene_description # VLM mô tả scene
ros2 topic echo /vlm/action_plan       # action plan JSON
ros2 topic hz /camera/image_raw        # camera rate (~13Hz)
```

---

## Kết quả & Đánh giá

| Metric | Giá trị |
|--------|---------|
| VLM inference latency | ~8s/frame (3B INT4, RTX 3060 12GB) |
| Fast-loop frequency | 50Hz (LiDAR safety + execution) |
| Camera feed | ~13Hz (640×480, ogre2 + NVIDIA EGL) |
| Obstacle avoidance | LiDAR (≥0.18m) + Camera (vật thấp hơn) |
| Ngôn ngữ hỗ trợ | Tiếng Việt, English |
| VRAM usage | ~2GB (3B INT4), Gazebo chiếm ~6.7GB |
| Corner escape | Reverse 0.8–1.4s + turn 1.5–2.5s |

---

## Roadmap

- [x] Robot URDF + Gazebo simulation (camera + LiDAR + IMU)
- [x] ros2_control (diff_drive + head + arm controllers)
- [x] LiDAR obstacle avoidance
- [x] Qwen2.5-VL Vision-Language Model integration
- [x] Natural language commands (Vietnamese/English)
- [x] Dual-loop VLM architecture (50Hz + background inference)
- [x] Camera sensor enabled (ogre2 + NVIDIA EGL)
- [x] VLM annotated camera feed (`/camera/vlm_annotated`)
- [x] Camera-based low obstacle detection
- [x] LIDAR mount optimized (z=-0.05, ~0.18m from ground)
- [x] Anti-stuck: wider sectors, reverse-before-turn, corner escape
- [ ] Voice input (speech-to-text → `/user_command`)
- [ ] Sim-to-real transfer (khi có hardware robot thật)
- [ ] Edge deployment (Jetson Orin Nano)

---

## Công nghệ sử dụng

**Robotics:** ROS 2 Jazzy · Gazebo Harmonic · URDF/Xacro · ros2_control · ros_gz_bridge

**AI/ML:** Qwen2.5-VL-3B-Instruct · HuggingFace Transformers · BitsAndBytes INT4 · OpenCV · YOLOv8

**Languages:** Python 3.12 · XML/SDF · YAML · Bash

**Hardware:** NVIDIA RTX 3060 12GB · GPU EGL rendering (ogre2)

---

## Tác giả

**Cong Thai** — Robotics & AI Developer · VinUniversity

<!-- - 📧 Email: your.email@vinuni.edu.vn -->
<!-- - 💼 LinkedIn: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile) -->

---

## License

MIT License — xem file [LICENSE](LICENSE) để biết chi tiết.
