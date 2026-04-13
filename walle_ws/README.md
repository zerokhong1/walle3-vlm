# WALL-E inspired Gazebo project (ROS 2 Jazzy + Gazebo Harmonic)

Đây là một workspace ROS 2 hoàn chỉnh để mô phỏng một robot **lấy cảm hứng từ WALL-E** trong Gazebo.

Mục tiêu của bộ khung này không phải dựng một bản sao hoạt hình 100%, mà là tạo ra một project **có thể học robotics thật sự** trong 3 ngày, với đủ các lớp quan trọng:

- robot modeling bằng URDF/Xacro
- cơ học và khớp nối
- ros2_control + controller manager
- mobile base kiểu differential drive
- cảm biến camera / LiDAR / IMU
- bridge ROS 2 ↔ Gazebo
- TF / joint states / odometry
- hành vi tự hành phản xạ tránh vật cản
- expressive joints cho đầu và tay

## Kiến trúc package

```text
walle_ws/
├── README.md
├── docs/
│   ├── 3_day_plan.md
│   └── nav2_extension.md
└── src/
    ├── walle_description/
    │   └── urdf/walle.urdf.xacro
    ├── walle_bringup/
    │   ├── launch/sim.launch.py
    │   ├── config/controllers.yaml
    │   ├── config/bridge.yaml
    │   └── worlds/walle_arena.sdf
    └── walle_demo/
        └── walle_demo/
            ├── wander.py
            └── expressive.py
```

## Điểm quan trọng về mô hình

Trong sprint 3 ngày, phần **di chuyển bằng track thật** được giản lược thành:

- hình dáng bên ngoài giống base bánh xích của WALL-E
- điều khiển động học bên dưới dùng **differential drive** với 2 bánh chủ động

Lý do là vì cách này cho trải nghiệm học tập tốt hơn nhiều trong thời gian ngắn:

- dễ ổn định trong Gazebo
- dễ đưa vào `diff_drive_controller`
- dễ chuyển sang robot thật sau này
- vẫn giữ được silhouette kiểu WALL-E

## Cài phụ thuộc

Máy mục tiêu khuyến nghị:

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic

Cài các gói chính:

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-desktop \
  ros-jazzy-ros-gz \
  ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-xacro \
  ros-jazzy-rviz2 \
  ros-jazzy-rqt-image-view
```

## Build

```bash
mkdir -p ~/walle_ws/src
cd ~/walle_ws/src
# copy hoặc git clone thư mục project này vào đây

cd ~/walle_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Chạy mô phỏng

### 1) Chạy simulation cơ bản

```bash
source /opt/ros/jazzy/setup.bash
source ~/walle_ws/install/setup.bash
ros2 launch walle_bringup sim.launch.py
```

### 2) Chạy simulation kèm demo tự hành

```bash
source /opt/ros/jazzy/setup.bash
source ~/walle_ws/install/setup.bash
ros2 launch walle_bringup sim.launch.py start_demo:=true
```

## Điều khiển tay bằng terminal

Controller `diff_drive_base_controller` nhận `TwistStamped` ở topic:

```text
/diff_drive_base_controller/cmd_vel
```

Ví dụ đi thẳng:

```bash
ros2 topic pub --rate 10 /diff_drive_base_controller/cmd_vel geometry_msgs/msg/TwistStamped \
"{
  header: {frame_id: 'base_footprint'},
  twist: {
    linear:  {x: 0.2, y: 0.0, z: 0.0},
    angular: {x: 0.0, y: 0.0, z: 0.0}
  }
}"
```

Ví dụ quay trái:

```bash
ros2 topic pub --rate 10 /diff_drive_base_controller/cmd_vel geometry_msgs/msg/TwistStamped \
"{
  header: {frame_id: 'base_footprint'},
  twist: {
    linear:  {x: 0.0, y: 0.0, z: 0.0},
    angular: {x: 0.0, y: 0.0, z: 0.8}
  }
}"
```

## Các topic đáng kiểm tra

```bash
ros2 topic list
ros2 topic echo /joint_states
ros2 topic echo /diff_drive_base_controller/odom
ros2 topic echo /scan
ros2 topic echo /imu
ros2 topic hz /camera/image_raw
```

## Xem camera

```bash
rqt_image_view /camera/image_raw
```

## Tóm tắt từng package

### `walle_description`

Chứa URDF/Xacro của robot:

- thân robot kiểu WALL-E
- đầu 2 bậc tự do: yaw + pitch
- 2 tay đơn giản
- base di chuyển differential drive
- cảm biến camera, lidar, imu
- cấu hình `ros2_control`

### `walle_bringup`

Chứa:

- world SDF
- launch mô phỏng
- controller YAML
- bridge YAML ROS ↔ Gazebo

### `walle_demo`

Chứa 2 node Python:

- `wander.py`: đọc LiDAR và tránh vật cản theo phản xạ
- `expressive.py`: phát trajectory để đầu và tay chuyển động định kỳ

## Checklist học robotics theo project này

Sau khi chạy được project, bạn nên đi lần lượt theo thứ tự:

1. Mở `walle.urdf.xacro` và hiểu từng link/joint.
2. Quan sát TF tree và `joint_states`.
3. Kiểm tra cách `gz_ros2_control` nối Gazebo với controller manager.
4. Đọc `controllers.yaml` để hiểu `diff_drive_controller` và `joint_trajectory_controller`.
5. Kiểm tra `bridge.yaml` để hiểu dữ liệu cảm biến đi từ Gazebo sang ROS 2.
6. Đọc `wander.py` để thấy vòng lặp perception → decision → control.
7. Mở `expressive.py` để thấy cách gửi trajectory vào controller.
8. Tự chỉnh kích thước robot, góc khớp, tốc độ, safe distance.
9. Thử thay obstacle avoidance bằng wall-following hoặc waypoint follower.
10. Xem `docs/nav2_extension.md` để nâng cấp sang mapping + navigation.

## Mục tiêu đầu ra sau 3 ngày

Sau 3 ngày, bạn nên đạt được các năng lực sau:

- tự dựng robot từ URDF/Xacro
- spawn robot trong Gazebo
- nối controller và điều khiển được base / joints
- thêm cảm biến và đọc topic ROS 2
- viết node Python phản xạ đơn giản
- hiểu pipeline cơ bản của một robot di động hoàn chỉnh

## Nâng cấp đề xuất

Bản hiện tại là bản nền rất tốt để nâng lên:

- SLAM Toolbox
- Nav2
- robot_localization
- camera-based perception
- task planner / behavior tree
- MoveIt cho tay gắp nếu mở rộng arm

Chi tiết có trong `docs/nav2_extension.md`.
