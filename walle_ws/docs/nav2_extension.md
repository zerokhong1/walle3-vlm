# Hướng nâng cấp sang SLAM + Nav2

Bản hiện tại đã đủ tốt để chuyển sang một mini-stack mobile robotics hoàn chỉnh.

## 1. Mục tiêu extension

Nâng project từ mức:

- mô hình + điều khiển + cảm biến + obstacle avoidance phản xạ

lên mức:

- mapping
- localization
- path planning
- navigation goal-based
- behavior tree execution

## 2. Gói nên cài thêm

```bash
sudo apt install -y \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox
```

## 3. Điều kiện tiên quyết trước khi thêm Nav2

Bạn cần chắc chắn các thứ này đã đúng:

- `odom -> base_footprint` có từ diff drive controller
- `base_footprint -> base_link -> sensor frames` có từ robot_state_publisher
- `/scan` ổn định và frame đúng
- robot quay và tiến mượt, không bị trượt quá mức

Nếu 4 điều này chưa ổn, đừng vào Nav2 quá sớm.

## 4. Lộ trình khuyến nghị

### Bước 1 — Làm mapping

Chạy SLAM Toolbox với LiDAR để tạo map 2D.

Kết quả mong đợi:

- có map occupancy grid
- lưu được file `.yaml` + `.pgm`

### Bước 2 — Localization

Dùng map đã lưu để localize robot trong world.

Kết quả mong đợi:

- có transform `map -> odom`
- robot định vị ổn định trong RViz

### Bước 3 — Navigation

Thêm Nav2 để gửi goal và di chuyển tự động.

Kết quả mong đợi:

- click goal trong RViz
- robot tự lập kế hoạch và tránh vật cản

### Bước 4 — Behavior Tree / task layer

Sau khi Nav2 chạy ổn, mới thêm:

- patrol nhiều waypoint
- quay đầu tìm vật thể
- điều khiển đầu theo hướng di chuyển
- state machine hoặc behavior tree cho nhiệm vụ

## 5. Tinh chỉnh cần chú ý

### Footprint

Nav2 cực nhạy với footprint. Hãy dùng footprint gần đúng với body + track covers.

### Laser height và frame

LiDAR nên đặt đủ cao để không quét trúng thân robot.

### Odom quality

Nếu odom nhiễu hoặc sai scale, Nav2 sẽ cho hành vi rất khó hiểu.

### Scan topic QoS

Một số node yêu cầu QoS chuẩn sensor data; nếu không khớp sẽ tưởng là không có sensor.

## 6. Stretch goals rất đáng làm

- thêm camera object detection
- cho đầu quay theo goal heading
- waypoint patrol có biểu cảm tay/đầu
- map nhiều phòng thay vì arena đơn giản
- thay reactive obstacle avoidance bằng planner chuẩn

## 7. Nâng cấp tiếp nếu muốn cực chất

Nếu bạn muốn project đi xa hơn nữa, roadmap đẹp sẽ là:

1. Nav2 chạy ổn định
2. camera perception
3. object pickup workflow (nếu mở rộng tay)
4. behavior tree tasking
5. chuyển code điều khiển từ sim sang real robot base
