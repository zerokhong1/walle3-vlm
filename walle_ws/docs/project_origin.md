# Project Origin

WallE3 started as a 3-day robotics sprint at VinUniversity (Hanoi, Vietnam) with the goal of building a WALL-E-inspired robot in Gazebo using ROS 2 Jazzy.

The original scope covered:

- Robot modeling with URDF/Xacro
- Differential drive kinematics and ros2_control integration
- Gazebo Harmonic simulation with camera, LiDAR, and IMU
- ROS 2 <-> Gazebo topic bridge
- Reactive obstacle avoidance (wander.py)
- Expressive head and arm motion (expressive.py)

The 3-day sprint produced a working simulation with a functional reactive controller. After the sprint, the project was extended with:

- Qwen2.5-VL-3B-Instruct integration for natural language control
- Dual-loop architecture separating VLM inference from the control loop
- YOLOv8 person and object detection
- Camera-based low-obstacle detection
- A 6-state mission planning machine
- Event contract v1.0 for Module B telemetry ingestion
- Reframing as Module A of the WallE3 platform (Modules A, B, C)

The original sprint plan is preserved here for reference. Current project status is documented in the root `README.md`.

---

## Original 3-day sprint plan

### Day 1 — Robot description + simulation backbone

Goals: spawn robot in Gazebo, verify TF tree, joint states, and controller manager.

Tasks:
1. URDF/Xacro skeleton with frames: odom, base_footprint, base_link, lidar_link, imu_link, camera_link, camera_optical_frame
2. Simple world with walls and obstacles
3. gz_ros2_control plugin attached
4. Robot spawned from robot_description
5. joint_state_broadcaster and diff_drive_base_controller activated

Done when: Gazebo opens, robot is stable on the ground, /joint_states and /diff_drive_base_controller/odom are published, cmd_vel moves the robot.

### Day 2 — Sensors + ROS bridge + reactive robotics

Goals: sensor data arriving in ROS 2, first autonomous behavior running.

Tasks:
1. Camera, LiDAR, and IMU sensors added to URDF
2. Topic bridge configured (Gazebo -> ROS 2)
3. wander.py: reads /scan, detects front obstacles, sends TwistStamped
4. expressive.py: periodic head and arm trajectories

Done when: /scan, /imu, and /camera/image_raw are publishing; robot avoids obstacles autonomously.

### Day 3 — Stabilization and documentation

Goals: turn the demo into a reusable robotics framework.

Tasks:
1. Physical tuning: wheel separation, wheel radius, damping, safe distance, turn speed
2. README and package architecture documentation
3. Debug checklist for common failure modes
4. Extension plan for SLAM and Nav2

Done when: workspace is clean, code is readable, simulation is stable, a fresh clone can be built and run from the README.

### Definition of done for the sprint

- Robot spawns stably in Gazebo
- Base moves with diff_drive_controller
- joint_state_broadcaster works
- LiDAR has data
- Camera has image
- IMU has data
- Robot avoids obstacles autonomously
- Head and arm have trajectory demo
- Code is split into logical packages
- README is sufficient for someone to build from scratch
