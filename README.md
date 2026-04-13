# WallE3 — AI-Powered Autonomous Robot with Vision & Reactive Navigation

[![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange)](https://gazebosim.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-green)](https://docs.ultralytics.com/)
[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-purple)](https://ubuntu.com/)

Robot tự hành có khả năng **nhận diện vật thể bằng YOLOv8**, **tránh vật cản bằng LiDAR**, và **phản ứng cảm xúc** theo ngữ cảnh — xây dựng hoàn chỉnh trên ROS 2 + Gazebo.

---

## Demo

| RViz2 — Robot + LiDAR visualization | Gazebo Sim — 3D World |
|:------------------------------------:|:---------------------:|
| ![RViz2](docs/media/rviz2_screenshot.png) | ![Gazebo](docs/media/gazebo_screenshot.png) |

---

## Điểm nổi bật

- **AI Perception** — YOLOv8 real-time object detection trên camera feed, phân loại "person" vs "object" để thay đổi hành vi robot
- **State Machine thông minh** — 4 trạng thái (WANDER → AVOID → ATTENTION → CURIOUS) chuyển đổi theo dữ liệu sensor + AI
- **Sensor Fusion** — kết hợp LiDAR (obstacle avoidance) + Camera (object detection) + IMU trong cùng pipeline ra quyết định
- **Expressive AI** — robot biểu cảm: xoay đầu tracking theo người, giơ tay chào, nghiêng đầu tò mò khi thấy vật thể
- **Full-stack Robotics** — từ URDF modeling → ros2_control → perception → behavior → actuation

---

## Kiến trúc hệ thống

```
─────────────────── Gazebo Harmonic ───────────────────
   LiDAR (10Hz)      Camera (30Hz)      IMU (100Hz)
──────────┬────────────────┬──────────────────┬────────
          │  ros_gz_bridge │                  │
     ─────▼─────    ───────▼───────    ───────▼─────
     │  /scan  │    │ /image_raw  │    │   /imu   │
     ─────┬─────    ───────┬───────    ─────────────
          │                │
          │         ───────▼───────
          │         │perception.py│  ← YOLOv8 inference
          │         │  (AI node)  │
          │         ───────┬───────
          │                │ /detections (JSON)
     ─────▼────────────────▼─────    ────────────────
     │      wander.py            │   │ expressive.py │
     │   (State Machine)         ├───│ (Emotion AI)  │
     │ WANDER→AVOID→ATTENTION    │   │ head tracking │
     │         →CURIOUS          │   │ arm gestures  │
     ──────────────┬─────────────    ────────┬───────
                   │                         │
              /cmd_vel                /joint_trajectory
                   │                         │
           ────────▼─────────────────────────▼───────
           │           ros2_control                  │
           │  diff_drive + joint_trajectory ctrl     │
           ──────────────────────────────────────────
```

### Luồng dữ liệu

```
LiDAR /scan ────────────────────────── wander.py ──→ /cmd_vel ──→ di chuyển
Camera /image ──→ perception.py ──→ /detections ──┤
                    (YOLOv8)                        ├──→ wander.py    (thay đổi state)
                                                    └──→ expressive.py (cảm xúc)
```

---

## AI & Data Pipeline

### YOLOv8 Perception (`perception.py`)

| Thành phần | Chi tiết |
|-----------|---------|
| Model | YOLOv8n (nano) — tối ưu cho real-time inference |
| Input | Camera feed 640×480 @ 30Hz |
| Output | Bounding boxes + class + confidence → JSON |
| Confidence threshold | 0.45 |
| Classes quan tâm | `person`, `bottle`, `cup`, `chair`, `laptop`, `backpack`, ... |

**Xử lý dữ liệu:**
- Nhận ảnh raw từ Gazebo camera qua `cv_bridge` (ROS Image → OpenCV)
- Chạy YOLOv8 inference, lọc detections theo confidence threshold
- Tính `center_x`, `center_y` cho mỗi bbox — dùng cho head tracking
- Publish detection results dạng structured JSON và annotated image

### State Machine — Ra quyết định dựa trên AI + Sensor

```
INIT ──(scan data arrives)──→ WANDER
WANDER ──(LiDAR: obstacle < 0.7m)──→ AVOID
WANDER/AVOID ──(YOLO: person detected)──→ ATTENTION    ← ưu tiên cao nhất
WANDER/AVOID ──(YOLO: object detected)──→ CURIOUS
ATTENTION/CURIOUS ──(timeout 2.5s)──→ WANDER
```

| State | Trigger | Input data | Hành động |
|-------|---------|-----------|-----------|
| **WANDER** | Không có vật cản/detection | LiDAR clear | Đi thẳng 0.2 m/s, corridor balancing |
| **AVOID** | LiDAR < 0.7m phía trước | Sector analysis 3 vùng | Quay về phía có không gian mở |
| **ATTENTION** | YOLOv8 detect "person" | bbox center_x | Dừng lại, xoay đầu tracking theo người |
| **CURIOUS** | YOLOv8 detect object | bbox center_x | Tiến chậm 0.08 m/s, nghiêng đầu nhìn |

### Expressive AI (`expressive.py`)

Robot phản ứng cảm xúc dựa trên AI detection results:

```python
# Head tracking: ánh xạ vị trí detection → góc yaw
yaw = -(center_x - 320.0) / 320.0 * 0.65  # max ±0.65 rad
```

| Ngữ cảnh | Phản ứng đầu | Phản ứng tay |
|----------|-------------|-------------|
| Thấy người (YOLO) | Xoay theo vị trí bbox | Giơ lên chào |
| Thấy vật thể (YOLO) | Nghiêng xuống nhìn | Tư thế tò mò |
| Idle (không detection) | Lắc qua lại tự nhiên | Nghỉ |

---

## Cấu trúc project

```
VinUni_proj/
├── run_walle.sh                    # One-command startup
├── walle.rviz                      # RViz2 visualization config
└── walle_ws/
    └── src/
        ├── walle_description/          # Robot model
        │   └── urdf/walle.urdf.xacro   # Full sensor suite
        ├── walle_bringup/              # Launch & config
        │   ├── launch/sim.launch.py    # Event-sequenced launch
        │   ├── config/
        │   │   ├── controllers.yaml    # ros2_control config
        │   │   └── bridge.yaml         # ROS ↔ Gazebo bridge
        │   └── worlds/walle_arena.sdf  # 8m×8m arena với 20+ vật thể
        └── walle_demo/                 # AI + Behavior nodes
            └── walle_demo/
                ├── perception.py       # YOLOv8 object detection
                ├── wander.py           # State machine + navigation
                └── expressive.py       # Emotion response system
```

## Mô hình Robot

```
base_footprint
└── base_link (differential drive)
    ├── left/right_wheel_link       ← diff_drive_controller
    ├── caster_front/rear_link
    ├── lidar_link                  ← gpu_lidar 10Hz
    ├── imu_link                    ← IMU 100Hz
    └── head_yaw_link               ← joint_trajectory_controller
        └── head_pitch_link
            ├── head_camera_link    ← Camera 30Hz → YOLOv8
            ├── left_arm_link       ← joint_trajectory_controller
            └── right_arm_link
```

---

## Cài đặt & Chạy

### Yêu cầu

| Thành phần | Phiên bản |
|-----------|-----------|
| Ubuntu | 24.04 LTS |
| ROS 2 | Jazzy |
| Gazebo | Harmonic |
| Python | 3.12+ |
| GPU | NVIDIA (khuyến nghị, không bắt buộc) |

### Cài đặt

```bash
# ROS 2 packages
sudo apt-get install -y \
  ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-cv-bridge ros-jazzy-image-transport \
  ros-jazzy-rviz2

# AI dependencies
pip install ultralytics "numpy<2.0" --break-system-packages

# Build
cd ~/VinUni_proj/walle_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Chạy

```bash
# Khởi động toàn bộ (simulation + AI + behavior)
bash ~/VinUni_proj/run_walle.sh

# Hoặc chạy manual
ros2 launch walle_bringup sim.launch.py \
  headless:=true start_demo:=true start_perception:=true
```

### Monitor

```bash
ros2 topic echo /behavior_state    # State machine
ros2 topic echo /detections        # YOLOv8 results
ros2 topic hz /scan                # LiDAR rate
```

---

## Kết quả đạt được

- Robot tự hành ổn định trong arena 8×8m với 20+ vật thể
- YOLOv8 nhận diện real-time: person, bottle, cup, chair, ... với confidence > 0.45
- State machine chuyển trạng thái mượt mà giữa 4 behaviors
- Head tracking theo vị trí detection với latency thấp
- Toàn bộ pipeline chạy trên single machine (CPU inference cho YOLOv8n)

## Roadmap

- [x] Robot URDF + Gazebo simulation
- [x] ros2_control (diff_drive + joint_trajectory)
- [x] LiDAR obstacle avoidance
- [x] YOLOv8 object detection integration
- [x] Behavior state machine (4 states)
- [x] Expressive head/arm tracking
- [ ] SLAM Toolbox — autonomous mapping
- [ ] Nav2 — goal-based navigation
- [ ] Deep RL cho obstacle avoidance thay rule-based
- [ ] Multi-object tracking + re-identification
- [ ] Sim-to-real transfer

---

## Công nghệ sử dụng

**Robotics:** ROS 2 Jazzy, Gazebo Harmonic, URDF/Xacro, ros2_control, ros_gz_bridge

**AI/ML:** YOLOv8 (Ultralytics), OpenCV, cv_bridge

**Languages:** Python 3.12, XML/SDF

**Tools:** Git, Linux (Ubuntu 24.04), Bash scripting, RViz2

---

## Tác giả

**Cong Thai — Robotics & AI Developer**  
VinUniversity
