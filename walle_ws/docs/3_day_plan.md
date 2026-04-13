# Kế hoạch triển khai 3 ngày

## Day 1 — Robot Description + Simulation Backbone

### Mục tiêu

Dựng robot chạy được trong Gazebo và thấy được TF / joint state / controller manager.

### Việc phải hoàn thành

1. Dựng skeleton robot bằng URDF/Xacro.
2. Chốt frame chuẩn:
   - `odom`
   - `base_footprint`
   - `base_link`
   - `lidar_link`
   - `imu_link`
   - `camera_link`
   - `camera_optical_frame`
3. Tạo world đơn giản có tường và obstacle.
4. Gắn `gz_ros2_control`.
5. Spawn robot từ `robot_description`.
6. Activate `joint_state_broadcaster` và `diff_drive_base_controller`.

### Kết quả cuối ngày

- Gazebo mở được.
- Robot đứng ổn định trên mặt đất.
- Có `/joint_states`.
- Có `/diff_drive_base_controller/odom`.
- Gửi `cmd_vel` được thì robot chạy.

### Kiến thức học được

- URDF / Xacro
- links / joints / inertial / collision / visual
- TF tree
- ros2_control cơ bản
- controller manager
- khái niệm differential drive

---

## Day 2 — Sensors + ROS Bridge + Reactive Robotics

### Mục tiêu

Có LiDAR / camera / IMU đi vào ROS 2 và viết node tự hành phản xạ đầu tiên.

### Việc phải hoàn thành

1. Gắn camera sensor.
2. Gắn LiDAR sensor.
3. Gắn IMU sensor.
4. Bridge các topic từ Gazebo sang ROS 2.
5. Viết node `wander.py`:
   - đọc `/scan`
   - phát hiện obstacle phía trước
   - quyết định rẽ trái / phải
   - gửi `TwistStamped`
6. Viết node `expressive.py` để gửi trajectory cho đầu và tay.

### Kết quả cuối ngày

- Xem được `/scan` và `/imu`.
- Xem được `/camera/image_raw` bằng `rqt_image_view`.
- Robot tự chạy tránh vật cản.
- Đầu và tay có chuyển động “có hồn”.

### Kiến thức học được

- perception pipeline cơ bản
- QoS cho sensor data
- bridge ROS ↔ Gazebo
- kiến trúc node publisher/subscriber
- vòng điều khiển phản xạ
- joint trajectory controller

---

## Day 3 — Chất lượng hóa dự án + Chuẩn bị lên Nav2/SLAM

### Mục tiêu

Biến project từ “demo chạy được” thành “bộ khung học robotics nghiêm túc”.

### Việc phải hoàn thành

1. Tinh chỉnh:
   - wheel separation
   - wheel radius
   - damping / friction
   - safe distance
   - tốc độ quay và tiến
2. Ghi README + sơ đồ package.
3. Viết checklist debug:
   - robot rung
   - controller không active
   - bridge không lên topic
   - sensor có data nhưng RViz không hiện frame
4. Chuẩn bị extension cho:
   - SLAM Toolbox
   - Nav2
   - behavior tree
   - camera perception
5. Nếu còn thời gian:
   - thêm map + localization
   - hoặc thêm waypoint patrol

### Kết quả cuối ngày

- Workspace rõ ràng, có cấu trúc.
- Code Python sạch, đọc được.
- Robot mô phỏng ổn định hơn.
- Có lộ trình nâng cấp lên navigation stack.

### Kiến thức học được

- tuning mô phỏng
- software architecture cho robotics project
- khả năng chuyển từ reactive robotics sang deliberative robotics
- tư duy chuẩn hóa package để sau này dùng cho robot thật

---

## Definition of Done cho sprint 3 ngày

Project được xem là đạt nếu thỏa các điều kiện sau:

- robot spawn ổn định trong Gazebo
- base chạy được bằng `diff_drive_controller`
- `joint_state_broadcaster` hoạt động
- LiDAR có dữ liệu
- camera có ảnh
- IMU có dữ liệu
- robot tự tránh vật cản bằng node Python
- đầu và tay có trajectory demo
- code được chia package hợp lý
- README đủ để một người khác build lại
