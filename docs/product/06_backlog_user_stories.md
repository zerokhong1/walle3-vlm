# Backlog & User Stories — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026 | **Prioritization:** MoSCoW

---

## Sprint 1 — Safety Foundation (Must Have)

### US-001 — Stop command fast-path

**As** Anh Minh (operator),
**I want** the robot to stop immediately when I type "stop" or "dừng",
**so that** I have reliable emergency control at all times.

**Acceptance Criteria:**
- [ ] Robot halts within 20ms of command receipt
- [ ] Stop path does NOT invoke VLM inference
- [ ] Motor velocity is set to (0, 0) and confirmed at diff-drive controller
- [ ] `/planner/state` publishes IDLE within 1 fast-loop tick
- [ ] Stop keywords: stop, dừng, dung, halt, cancel, hủy, huy, thoát, thoat

**Story Points:** 5
**Maps to:** FR-002, BR-004
**Status:** Done ✅ (I-011)

---

### US-002 — LiDAR obstacle avoidance

**As** Anh Khoa (safety officer),
**I want** the robot to automatically avoid obstacles detected by LiDAR,
**so that** it never collides with people or objects.

**Acceptance Criteria:**
- [ ] LiDAR scans 360° at ≥ 8 Hz continuously
- [ ] Front sector (±30°) + diagonal sectors checked at 50 Hz
- [ ] If any sector < 0.35m, escape triggers within 1 fast-loop tick
- [ ] Escape maneuver is stable: 1.5s reverse + turn, no oscillation
- [ ] Rear is checked before reversing; if rear < 0.35m, rotate in place
- [ ] `/safety/event` published with event_type=collision_risk, severity=high

**Story Points:** 8
**Maps to:** FR-010, FR-011, FR-012, BR-003
**Status:** Done ✅ (I-016 partial — LiDAR now 360°, sector widened)

---

### US-003 — Priority velocity arbitration

**As** Chị Lan (supervisor),
**I want** safety commands to always override navigation commands,
**so that** VLM navigation can never prevent an emergency stop.

**Acceptance Criteria:**
- [ ] cmd_vel_mux routes 3 channels: /cmd_vel/safety (P0) > /cmd_vel/vlm (P1) > /cmd_vel/wander (P2)
- [ ] Safety channel always wins when message < 250ms old
- [ ] Active channel published to /mux/active_channel
- [ ] No race condition possible between channels (separate topics)

**Story Points:** 5
**Maps to:** FR-015, BR-003
**Status:** Done ✅ (I-006)

---

### US-004 — Stuck watchdog

**As** Chị Lan (supervisor),
**I want** the robot to detect when it's stuck and alert me,
**so that** I know when intervention is needed without walking the floor.

**Acceptance Criteria:**
- [ ] Watchdog runs as independent node (not inside vlm_planner)
- [ ] Monitors /planner/state and /diff_drive_base_controller/odom at 1 Hz
- [ ] If in APPROACHING or SEARCHING with < 0.20m displacement for 30s: emit HIGH safety event
- [ ] If stuck for 60s: emit CRITICAL event + abort mission
- [ ] False positive rate < 5% in open space (no obstacles)

**Story Points:** 5
**Maps to:** FR-014, BR-008
**Status:** Done ✅ (I-007)

---

## Sprint 2 — Core Navigation (Must Have)

### US-005 — Natural language command

**As** Anh Minh (operator),
**I want** to type a command like "đi tới thùng màu cam" and have the robot navigate to it,
**so that** I don't need to program waypoints.

**Acceptance Criteria:**
- [ ] Command published on /user_command as std_msgs/String
- [ ] Robot transitions IDLE → PLANNING → SEARCHING within 5s of command
- [ ] VLM processes camera frame to identify named target
- [ ] Robot navigates toward target when found
- [ ] Mission started event published with command text, mission_id, timestamp

**Story Points:** 13
**Maps to:** FR-001, FR-004, FR-005, FR-006, BR-001
**Status:** Done ✅

---

### US-006 — Search behavior when target not found

**As** Anh Minh (operator),
**I want** the robot to actively search when it can't see the target,
**so that** it finds objects that are not directly in its initial field of view.

**Acceptance Criteria:**
- [ ] When VLM returns status=not_found, robot executes slow rotation scan (angular=0.30 rad/s)
- [ ] Forward speed = 0 when obstacle within 0.60m (OBSTACLE_SLOW_DIST)
- [ ] Search rotation covers 360° before mission abort
- [ ] Search state published on /planner/state as SEARCHING

**Story Points:** 5
**Maps to:** FR-007, BR-002
**Status:** Done ✅

---

### US-007 — Mission completion gesture

**As** Anh Minh (operator),
**I want** the robot to signal when it has found the target,
**so that** I know it has arrived without watching the terminal.

**Acceptance Criteria:**
- [ ] When VLM returns status=reached: robot stops (safety channel), head nods, arms wave
- [ ] State transitions CONFIRMING → COMPLETED → IDLE
- [ ] /mission/completed event published with success=true, duration_s, reason=target_reached

**Story Points:** 3
**Maps to:** FR-008, FR-009
**Status:** Done ✅

---

### US-008 — Mission event logging

**As** Chị Lan (supervisor),
**I want** every mission to generate structured log data,
**so that** I can analyze success rates, intervention counts, and durations.

**Acceptance Criteria:**
- [ ] /mission/started published at command receipt
- [ ] /mission/completed published at mission end (success or abort)
- [ ] All events written to CSV in ~/walle_logs/ within 1s of emission
- [ ] CSV schema is stable (no field renames without schema_version increment)

**Story Points:** 5
**Maps to:** FR-017, FR-018, BR-005
**Status:** Done ✅

---

## Sprint 3 — Observability & Recovery (Should Have)

### US-009 — Auto rosbag on safety event

**As** Anh Khoa (safety officer),
**I want** the system to automatically record sensor data when a HIGH or CRITICAL safety event occurs,
**so that** I have evidence for post-incident analysis.

**Acceptance Criteria:**
- [ ] rosbag_trigger subscribes to /safety/event
- [ ] On HIGH or CRITICAL: starts ros2 bag record with 15 topics
- [ ] Records for 60s, extends by 30s on new events (max 120s)
- [ ] Bags saved to ~/walle_bags/safety_{event_type}_{timestamp}/
- [ ] Rosbag start logged as INFO with bag path

**Story Points:** 5
**Maps to:** FR-019, BR-005
**Status:** Done ✅

---

### US-010 — Terminal TUI

**As** Anh Minh (operator),
**I want** a full-screen terminal interface showing robot state, event log, and command input,
**so that** I can monitor and control the robot from a single screen.

**Acceptance Criteria:**
- [ ] TUI shows: planner state, controller mode, active channel, last command
- [ ] Event log auto-scrolls, color-coded by event type (safety=yellow/red, mission=green)
- [ ] Command input supports ↑↓ history (50 commands), Enter to send
- [ ] Ctrl+C quits cleanly; Ctrl+L clears log
- [ ] TUI does not block ROS callbacks (asyncio + background spin thread)

**Story Points:** 8
**Maps to:** FR-021, BR-007
**Status:** Done ✅

---

### US-011 — One-command startup

**As** Anh Hùng (IT),
**I want** to start the entire robot system with one command,
**so that** setup is reproducible and requires no manual node launching.

**Acceptance Criteria:**
- [ ] `bash run_walle.sh` starts: Gazebo, RViz2, VLM stack, mission logger
- [ ] `bash run_walle.sh --world warehouse` starts warehouse world with correct spawn position
- [ ] Script handles cleanup of old processes before starting
- [ ] Script prints status: PID of each component, readiness check for controllers

**Story Points:** 3
**Maps to:** FR-023, BR-007
**Status:** Done ✅

---

### US-012 — Camera low-obstacle detection

**As** Anh Khoa (safety officer),
**I want** the robot to avoid obstacles that are too low for LiDAR to detect,
**so that** low pallets and debris don't cause collisions.

**Acceptance Criteria:**
- [ ] Camera frame bottom zone analyzed for floor color deviation
- [ ] If color diff > threshold AND edge density > threshold: CAM_AVOID triggered
- [ ] CAM_AVOID publishes escape via safety channel (priority 0)
- [ ] False positive rate < 10% on flat open floor

**Story Points:** 5
**Maps to:** FR-013, BR-003
**Status:** Done ✅

---

## Sprint 4 — Warehouse Scenario (Should Have)

### US-013 — Warehouse world simulation

**As** Anh Minh (operator),
**I want** to test the robot in a realistic warehouse environment,
**so that** simulation results are relevant to actual deployment conditions.

**Acceptance Criteria:**
- [ ] walle_warehouse.sdf: 20×15m, 4 storage racks, 6 low pallets, carton boxes, forklift
- [ ] Low pallets (h=0.15m) test camera obstacle detection
- [ ] Robot spawns in Zone A (1.0, 7.5, 0.0) facing Zone B
- [ ] Warehouse launch: `ros2 launch walle_bringup sim_warehouse.launch.py`

**Story Points:** 8
**Maps to:** BR-002
**Status:** Done ✅

---

### US-014 — Contact sensor safety net

**As** Anh Khoa (safety officer),
**I want** the robot to detect physical contact as a last-resort safety mechanism,
**so that** even if LiDAR fails, a collision triggers an emergency stop.

**Acceptance Criteria:**
- [ ] Contact sensor defined on base_link in URDF
- [ ] Physical contact publishes to /bumper topic
- [ ] Contact event triggers EMERGENCY_STOP and CRITICAL safety event
- [ ] Contact event logged with timestamp for audit trail

**Story Points:** 5
**Maps to:** FR-016, BR-003
**Status:** In Progress 🔄 (sensor added to URDF; subscriber pending)

---

## Backlog — Future Sprints (Could Have / Won't Have)

| ID | Story | Priority | Target Release |
|----|-------|----------|---------------|
| US-015 | Voice command input (speech-to-text) | Could | R2 |
| US-016 | Spatial memory for known obstacles | Could | R3 |
| US-017 | Confidence threshold enforcement (refuse low-confidence plans) | Could | R2 |
| US-018 | Fleet dashboard (Module B integration) | Could | R3 |
| US-019 | Sim-to-real transfer checklist | Could | R3 |
| US-020 | Multi-language voice output (robot speaks confirmation) | Won't | R4 |
| US-021 | Autonomous return-to-charging station | Won't | R4 |
| US-022 | WMS API integration (receive tasks from warehouse system) | Won't | R4 |

---

## Story Points Summary

| Sprint | Stories | Points | Status |
|--------|---------|--------|--------|
| Sprint 1 (Safety Foundation) | US-001 to US-004 | 23 | Complete |
| Sprint 2 (Core Navigation) | US-005 to US-008 | 26 | Complete |
| Sprint 3 (Observability) | US-009 to US-012 | 21 | Complete |
| Sprint 4 (Warehouse) | US-013 to US-014 | 13 | Mostly complete |
| **Total R0-R1** | **14 stories** | **83 points** | |
