# Service Blueprint — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Scenario:** Single-operator warehouse navigation mission

---

## Blueprint Overview

The service blueprint maps operator actions → frontstage robot behavior → backstage system processes → telemetry events — across a full mission lifecycle.

---

## Blueprint Table

| Phase | Operator Action | Robot (Frontstage) | System (Backstage) | Telemetry Event |
|-------|----------------|--------------------|--------------------|-----------------|
| **Pre-mission** | Opens terminal TUI | Displays state=IDLE, channel=idle | cmd_vel_mux running at 50Hz; wander in WANDER mode | — |
| | Verifies robot is visible in RViz2 | Idle in home position | LiDAR scanning 360°; camera streaming | /scan at 10Hz |
| **Command** | Types "go to the orange box" + Enter | Head tilts (attention) | command_cb receives text, checks stop keywords | — |
| | | State → PLANNING | _plan cleared; mission_id generated | /mission/started |
| | | VLM model queued | Background thread starts inference; fast loop continues at 50Hz | — |
| **Search** | Watches TUI: state=SEARCHING | Slow rotation scan | VLM reads camera frame; action_plan computed | /inference/event |
| | | Front obstacle check at 50Hz | LiDAR sectors checked: front ±30° + diagonals | — |
| **Approaching** | TUI: state=APPROACHING | Navigates toward target | VLM updates plan every 5s; fast loop executes at 50Hz | /inference/event |
| | | Speed adjusts near obstacles | front_min < 0.60m → speed × 0.4; < 0.35m → escape | /safety/event (if triggered) |
| | | Channel: VLM (visible in TUI) | cmd_vel_mux forwards /cmd_vel/vlm to controller | /mux/active_channel |
| **Obstacle event** | Observes robot pause | Escapes: reverse 1.5s + turn | Safety channel overrides VLM (P0 > P1) | /safety/event severity=high |
| | Sees [SAFETY:HIGH] in TUI log | resumes navigation | Watchdog monitors progress; escape completes | — |
| **Target reached** | Sees TUI: state=CONFIRMING | Stops at target; head nods, arms wave | VLM: status=reached; state → CONFIRMING → COMPLETED | /mission/completed success=true |
| | May retrieve item | Returns to idle pose | Mission logger writes CSV | — |
| **Post-mission** | Reviews TUI log | Returns to IDLE state | All events in ~/walle_logs/ | — |
| | Issues next command | Ready for next mission | — | — |

---

## Emergency Stop Scenario

| Phase | Operator Action | Robot (Frontstage) | System (Backstage) | Telemetry |
|-------|----------------|--------------------|--------------------|-----------|
| Any | Types "dừng" | Halts immediately | Stop keyword fast-path; no VLM lookup | — |
| | Sees state=IDLE in TUI | Motor velocity = 0 | safety_cmd_pub: (0,0); mission_completed published | /mission/completed reason=operator_stop |
| | Satisfied robot stopped | — | Latency < 20ms from command to halt | — |

---

## Stuck Scenario

| Phase | Operator Action | Robot (Frontstage) | System (Backstage) | Telemetry |
|-------|----------------|--------------------|--------------------|-----------|
| 0:00 | Normal operation | Robot cannot make progress | Stuck watchdog monitors odom | — |
| 0:30 | TUI shows [SAFETY:HIGH] stuck | Still attempting navigation | Watchdog: displacement < 0.20m for 30s | /safety/event severity=high |
| 0:30 | Radios floor staff | — | Rosbag auto-record starts | — |
| 1:00 | Staff clear obstacle | — | Watchdog: 60s → abort mission | /safety/event severity=critical |
| — | TUI shows mission failed | Returns to IDLE | /mission/completed success=false | /mission/completed reason=stuck_timeout_60s |

---

## Support Line (Out of Blueprint Scope for R0)

Future:
- IT escalation path for LiDAR/camera hardware failures
- Vendor support SLA for GPU workstation
- On-call runbook for CRITICAL safety events

---

## Physical Evidence (Touchpoints)

| Touchpoint | What Operator Sees | Format |
|------------|-------------------|--------|
| Terminal TUI | State, mode, channel, event log, command input | textual 8.x full-screen |
| RViz2 | Robot model, LiDAR scan, odometry trail | Graphical |
| ~/walle_logs/ | CSV telemetry, one file per mission | CSV, queryable |
| ~/walle_bags/ | Rosbag recordings on safety events | ROS2 bag format |
| run_walle.sh output | Startup progress, PID confirmation | Shell output |
