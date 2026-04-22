# Issue Catalog — WallE3 VLM

**Format:** ID | Severity | Summary | Root Cause | Resolution | Status
**Severity:** S0=Critical (RPN≥40 or person-risk veto) | S1=High | S2=Medium | S3=Low

---

## Resolved Issues

| ID | Severity | Issue | Root Cause | Resolution | Commit |
|----|----------|-------|------------|------------|--------|
| I-003 | S1 | `/behavior_state` mixed controller and planner signals | Single topic dual-purpose | Split into `/planner/state` + `/controller/mode` | — |
| I-004 | S1 | Event contract v1.0 not published to any topic | No publishers wired | All 7 topics implemented with full JSON schema | — |
| I-005 | S2 | No structured observability for debugging | No log format | Structured `[INFER]` logs + `rosbag_trigger_node` | — |
| I-006 | S0 | Priority race between VLM and wander safety commands | Both wrote directly to `/diff_drive_base_controller/cmd_vel`; last-writer wins at 50 Hz | `cmd_vel_mux` with 3-channel priority arbitration (safety > VLM > wander) | — |
| I-007 | S1 | No independent stuck detector | vlm_planner handled stuck internally; single point of failure | `stuck_watchdog_node` (warn 30s / abort 60s / displacement 0.20m) | — |
| I-011 | S0 | Stop command routed through VLM inference loop (8–12s delay) | `_command_cb` queued all commands to VLM | Fast-path stop in `_command_cb` before VLM branch; latency < 20ms via `/cmd_vel/safety` | — |
| I-016 | S0 | Robot drives into walls without LiDAR trigger (wall-collision regression) | Three independent root causes (see below) | Three separate fixes in three commits | ddaba81 |

### I-016 detail — Three root causes

| Bug | Root cause | Fix |
|-----|-----------|-----|
| BUG-1 | LiDAR URDF configured 180° FOV (min_angle=-π/2, max_angle=π/2) — rear completely blind | Extended to 360° (min_angle=-π, max_angle=π), samples 720→1080 |
| BUG-2 | `_front_distance()` in vlm_planner checked only ±0.30 rad (±17°) — walls at 20° off dead-ahead invisible | Widened to ±0.52 rad (±30°) + diagonal sectors ±0.52–1.05 rad |
| BUG-3 | `wander.py` returned early during `VLM_TASK` state without any LiDAR check | Added secondary LiDAR check at 55% of safe_dist threshold during VLM_TASK |

---

## Open Issues

| ID | Severity | Issue | Impact | Workaround | Target release |
|----|----------|-------|--------|------------|----------------|
| I-001 | S1 | Arm/head JointTrajectoryController not loading in Gazebo Harmonic | Expressive gestures do not execute; head/arm stay at zero | None — cosmetic only | R1 |
| I-002 | S2 | wander does not use camera obstacle detection in production (CAM_AVOID untriggered) | Low-obstacle avoidance inactive unless manually enabled | None | R1 |
| I-008 | S2 | No spatial memory for known obstacles | Robot re-discovers same wall each mission | N/A | R2 |
| I-009 | S2 | Language interface terminal (language_interface.py) has no command history or completion | Poor operator UX for rapid testing | Use rosbag replay or direct `ros2 topic pub` | R1 |
| I-010 | S1 | VLM confidence threshold not enforced — mission continues even if confidence < 0.4 | Robot may approach wrong target if VLM misidentifies | Operator monitors visually | R1 |
| I-012 | S2 | No geofence/no-go zone enforcement | Robot navigates into restricted zones if commanded | Operator must supervise | R2 |
| I-014 | S2 | rosbag_trigger records only 60s after HIGH/CRITICAL event — may miss preceding context | Incomplete evidence for post-incident analysis | Manual rosbag record if needed | R1 |
| I-017 | S3 | LiDAR /scan delivery rate is ~7.96–8.0 Hz in simulation (target ≥8 Hz; URDF configured 10 Hz) | Simulation CPU load limits actual delivery | Validation in sim is acceptable; validate on hardware | R2 |

---

## Governance notes

- **S0 classification:** An issue is S0 if RPN ≥ 40 (FMEA scale) **or** if it involves person-contact risk regardless of RPN. R-001 (person collision, RPN=20) is S0 by veto because injury severity = 5 and mitigation cannot be fully validated in simulation.
- **Linked FMEA:** See [Risk Register / FMEA](docs/product/10_risk_register_fmea.md) for full risk scoring.
- **Linked UAT:** See [UAT Test Plan](docs/product/11_uat_test_plan.md) for regression test coverage (T-24 covers I-016).
- **Issue templates:** `.github/ISSUE_TEMPLATE/` — bug, safety, feature, experiment, UAT failure.
