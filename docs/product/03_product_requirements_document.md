# Product Requirements Document — WallE3 VLM

**Version:** 1.1 | **Status:** Approved | **Date:** April 2026
**Author:** Cong Thai | **Maps to:** BRD v1.0

---

## 1. Product Overview

WallE3 VLM is an autonomous service robot platform that accepts natural-language commands and navigates to visually-described targets in dynamic indoor environments. This PRD defines functional and non-functional requirements for Releases R0–R2.

---

## 2. User Stories Summary

Full user stories with acceptance criteria are in [06_backlog_user_stories.md](06_backlog_user_stories.md). This PRD focuses on the requirement definitions that stories are derived from.

---

## 3. Functional Requirements

### 3.1 Command Interface

**FR-001 — Natural language command reception**
The system shall accept text commands via a terminal interface and via ROS topic `/user_command`.

**FR-002 — Stop keyword fast-path**
The system shall halt all robot motion within 20ms of receiving any stop keyword: `stop`, `dừng`, `dung`, `halt`, `cancel`, `hủy`, `huy`, `thoát`.
This path shall NOT pass through VLM inference.

**FR-003 — Command language support**
The system shall accept commands in Vietnamese and English in the same session without configuration change.

**FR-004 — Command acknowledgment**
Upon receiving a command, the system shall transition planner state to PLANNING within 100ms and publish a `/mission/started` event.

---

### 3.2 Navigation & Planning

**FR-005 — VLM-based visual target identification**
The system shall use a Vision-Language Model to identify named targets (by color, type, shape) in the camera frame and generate a navigation action plan.

**FR-006 — Autonomous navigation to target**
Given an action plan from the VLM, the robot shall navigate toward the identified target using differential drive control.

**FR-007 — Search behavior when target not found**
When the VLM reports target not found, the robot shall execute a systematic search rotation (slow rotation scan) to increase field of view coverage.

**FR-008 — Target reached confirmation**
When the VLM reports `status=reached`, the robot shall stop, play a completion gesture (head nod + arm wave), and transition to COMPLETED state.

**FR-009 — Mission state machine**
The robot shall follow a 6-state machine: IDLE → PLANNING → SEARCHING → APPROACHING → CONFIRMING → COMPLETED. State shall be published on `/planner/state` at ≥ 10 Hz.

---

### 3.3 Safety

**FR-010 — LiDAR obstacle detection**
The system shall continuously monitor a 360° LiDAR scan and trigger an escape maneuver when any obstacle is detected within 0.35m in the front+diagonal sectors.

**FR-011 — Stable escape maneuver**
When an escape is triggered, the robot shall reverse for 1.5s with a fixed turn direction (no oscillation). The escape direction shall be chosen once and held for the full 1.5s window.

**FR-012 — Rear obstacle check during reverse**
When reversing in an escape maneuver, the system shall check rear LiDAR sectors. If rear distance < 0.35m, the robot shall rotate in place instead of reversing.

**FR-013 — Camera low-obstacle detection**
The system shall use camera frame analysis to detect obstacles below the LiDAR scan plane (height < 0.18m) and trigger avoidance.

**FR-014 — Independent stuck watchdog**
An independent watchdog node shall monitor robot progress. If the robot is in APPROACHING or SEARCHING state with < 0.20m displacement over 30s, it shall emit a HIGH safety event. If stuck for 60s, it shall abort the mission and emit a CRITICAL event.

**FR-015 — Priority-arbitrated velocity control**
All velocity commands shall be routed through a priority multiplexer:
- Priority 0 (highest): `/cmd_vel/safety` — escape, stop, stuck recovery
- Priority 1: `/cmd_vel/vlm` — VLM plan execution
- Priority 2 (lowest): `/cmd_vel/wander` — wander behavior

Higher-priority channels shall always override lower-priority channels.

**FR-016 — Contact sensor last-resort safety**
The robot chassis shall include a contact/bumper sensor. Physical contact shall trigger EMERGENCY_STOP and publish a CRITICAL safety event.

---

### 3.4 Telemetry & Observability

**FR-017 — Event contract v1.0**
The system shall publish structured JSON events on 7 topics with fixed schema (see [09_event_contract_v1.md](09_event_contract_v1.md)).

**FR-018 — Mission logging**
All telemetry events shall be written to CSV files in `~/walle_logs/` within 1 second of emission.

**FR-019 — Auto rosbag recording**
On any HIGH or CRITICAL safety event, the system shall automatically start a 60-second rosbag recording capturing 15 topics.

**FR-020 — Structured inference logging**
Every VLM inference shall emit an `/inference/event` with: latency_ms, target_found, confidence, action type.

---

### 3.5 Operator Interface

**FR-021 — Terminal TUI**
The system shall provide a full-screen terminal UI (textual-based) showing: planner state, controller mode, active mux channel, event log, command history, command input.

**FR-022 — RViz2 visualization**
The system shall provide an RViz2 configuration showing: robot model, LiDAR scan, camera feed, odometry.

**FR-023 — One-command startup**
The system shall start all required nodes (simulation, VLM stack, mission logger, mux, watchdog) via a single shell script with world selection (`--world arena|warehouse`).

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-001 — Fast-loop frequency:** Safety + navigation loop shall run at ≥ 50 Hz.

**NFR-002 — VLM inference latency:** Target ≤ 10s per frame on RTX 3060 12 GB (INT4 quantized 3B model).

**NFR-003 — Stop command latency:** ≤ 20ms from command receipt to motor halt (measured at diff-drive controller input).

**NFR-004 — LiDAR scan rate:** ≥ 8 Hz during normal operation including during VLM inference.

**NFR-005 — Camera frame rate:** ≥ 10 Hz at 640×480 px.

### 4.2 Safety

**NFR-006 — Safety channel priority:** Safety channel commands shall reach the diff-drive controller within 2 fast-loop cycles (≤ 40ms) of trigger.

**NFR-007 — Watchdog independence:** The stuck watchdog shall operate as an independent ROS node — failure of vlm_planner or wander shall not affect watchdog operation.

**NFR-008 — No silent failure:** Any VLM inference failure shall be logged as an `/inference/event` with `output_valid=false`. Planner shall not continue executing a stale plan for > 15s.

### 4.3 Reliability

**NFR-009 — Simulation mission success rate:** ≥ 70% over 50 consecutive runs in walle_arena.sdf (R0 target), ≥ 85% (R2 target).

**NFR-010 — Stuck abort rate:** ≤ 20% of missions in simulation (R0), ≤ 10% (R2).

### 4.4 Usability

**NFR-011 — Operator onboarding:** A new user shall complete first successful mission within 30 minutes of reading the README.

**NFR-012 — Build time:** `colcon build` from clean workspace shall complete in ≤ 5 minutes.

### 4.5 Maintainability

**NFR-013 — Telemetry schema versioning:** Event contract version shall be embedded in `/mission/started` payload. Schema changes require version increment.

**NFR-014 — Module isolation:** Modules A, B, C shall communicate only via ROS topics (no shared memory, no direct function calls across module boundaries).

---

## 5. Requirement Traceability (Summary)

| Business Req | Functional Req | Non-Functional Req |
|-------------|---------------|-------------------|
| BR-001 (natural language) | FR-001, FR-002, FR-003, FR-004 | NFR-011 |
| BR-002 (no reprogramming) | FR-005, FR-006, FR-007, FR-008 | NFR-009 |
| BR-003 (safety-first) | FR-010 to FR-016 | NFR-006, NFR-007 |
| BR-004 (operator stop) | FR-002 | NFR-003 |
| BR-005 (observability) | FR-017, FR-018, FR-019, FR-020 | NFR-013 |
| BR-006 (affordable) | FR-005 (local GPU) | NFR-002 |
| BR-007 (30-min onboarding) | FR-021, FR-022, FR-023 | NFR-011 |
| BR-008 (stuck recovery) | FR-014, FR-015 | NFR-007, NFR-010 |

Full traceability in [07_requirements_traceability_matrix.md](07_requirements_traceability_matrix.md).

---

## 6. Change Log

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | Apr 2026 | Initial release | Cong Thai |
| 1.1 | Apr 2026 | Add FR-012 (rear obstacle check), FR-016 (contact sensor) after I-016 root cause analysis | Cong Thai |
