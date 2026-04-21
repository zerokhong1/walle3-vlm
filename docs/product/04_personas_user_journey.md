# Personas & User Journey — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026

---

## Personas

### Persona 1 — Anh Minh, Warehouse Operator

| Attribute | Detail |
|-----------|--------|
| Age | 28 |
| Role | Floor operator, VinMart Distribution Center |
| Education | High school + 2 years vocational |
| Tech comfort | Uses smartphone daily, no coding experience |
| Language | Vietnamese (primary), basic English |
| Work pattern | 8-hour shifts, handles 50–80 pick requests/day |

**Goals:**
- Complete pick tasks faster without walking the entire warehouse
- Avoid memorizing where every SKU is located after rearrangements
- Have a robot that he can trust not to block the aisle or hit him

**Frustrations:**
- Re-walking the same routes multiple times per shift
- Current robot (AGV) breaks if he moves a pallet 1 meter
- Can't give the robot ad-hoc instructions — everything needs IT involvement

**Quote:** *"Tôi chỉ muốn nói với nó 'đi lấy thùng màu đỏ' và nó tự đi. Không cần cài lại gì hết."*

---

### Persona 2 — Chị Lan, Robot Supervisor

| Attribute | Detail |
|-----------|--------|
| Age | 35 |
| Role | Operations Lead / Robot Supervisor |
| Education | University, logistics management |
| Tech comfort | Excel power user, basic Python scripting |
| Language | Vietnamese + English (reads English docs) |

**Goals:**
- Monitor robot status without sitting in front of a terminal all day
- Know when a robot needs intervention before it becomes a problem
- Have data to report weekly mission success rates to management

**Frustrations:**
- Current system has no structured logs — she screenshots terminal output
- No alert when robot gets stuck — she has to walk the floor to check
- Mission data is in unstructured logs; creating reports takes 2 hours

**Quote:** *"Tôi cần biết robot đang làm gì và tại sao nó dừng lại — không chỉ thấy nó đứng im."*

---

### Persona 3 — Anh Khoa, Safety Officer

| Attribute | Detail |
|-----------|--------|
| Age | 42 |
| Role | EHS Officer (Environment, Health, Safety) |
| Education | Engineering degree |
| Tech comfort | Reads technical reports, not a programmer |
| Language | Vietnamese |

**Goals:**
- Ensure no personnel injury from robot operation
- Have audit trail for every safety event
- Approve new deployment areas only when risk is quantified

**Frustrations:**
- No documentation of how the robot decides to stop
- No way to replay what happened before an incident
- Safety certification process is unclear for AI-based systems

**Quote:** *"Tôi không cần robot hoàn hảo. Tôi cần robot có thể chứng minh nó an toàn."*

---

### Persona 4 — Anh Hùng, IT Engineer

| Attribute | Detail |
|-----------|--------|
| Age | 30 |
| Role | DevOps / Systems Engineer |
| Education | CS degree |
| Tech comfort | Linux, Docker, Python, ROS |
| Language | Vietnamese + English (technical) |

**Goals:**
- Deploy and maintain the robot with minimal custom code
- Have observability without building a monitoring stack from scratch
- Know about failures before users report them

**Frustrations:**
- Robots with proprietary stacks that can't be debugged
- No structured logs — can't feed data to existing Grafana setup
- VLM inference errors silently fail

---

## User Journey — Anh Minh (Primary Journey)

### Scenario: "Find the orange box in Zone B"

```
Pre-condition: Robot is idle in Zone A. Minh is at his workstation terminal.
```

| Step | Minh's Action | Robot Action | Emotion |
|------|--------------|--------------|---------|
| 1 | Opens terminal TUI on workstation | TUI shows: Planner=IDLE, Channel=idle | Neutral |
| 2 | Types: "đi tới thùng màu cam ở zone B" | Publishes to /user_command | Hopeful |
| 3 | Sees TUI update: Planner=PLANNING | Mission started event logged | Engaged |
| 4 | Watches robot move toward Zone B | VLM searches for orange box | Attentive |
| 5 | Robot pauses (VLM inference, 8-10s) | Continues previous plan at 50Hz | Slightly anxious |
| 6 | TUI shows: Planner=APPROACHING | VLM found target, navigating | Relieved |
| 7 | Robot reaches orange box, waves arms | Publishes COMPLETED + mission_completed | Satisfied |
| 8 | Minh collects item, types next command | State resets to IDLE | Efficient |

**Pain point resolved:** No waypoint re-programming. No IT ticket. 10-second onboarding.

---

## User Journey — Chị Lan (Monitoring Journey)

### Scenario: "Robot stuck during peak hours"

| Step | Lan's Action | System Action | Emotion |
|------|-------------|---------------|---------|
| 1 | Working at desk, TUI open on secondary screen | All metrics normal | Focused on other work |
| 2 | TUI log shows: [SAFETY:HIGH] stuck | Watchdog emitted safety event at 30s | Alert |
| 3 | Sees mission ID + elapsed time in log | Rosbag recording auto-started | In control |
| 4 | Radios floor: "Robot cần kiểm tra zone B" | Stuck watchdog counting to 60s | Proactive |
| 5 | Floor staff clears obstacle | Robot resumes | Relieved |
| 6 | Reviews CSV log after shift | Mission logged as intervention_count=1 | Data-driven |
| 7 | Reports weekly: stuck rate = 8% (target <10%) | — | Confident |

**Pain point resolved:** Proactive alert instead of discovering stuck robot hours later. Structured data for reports.

---

## User Journey — Anh Khoa (Safety Audit Journey)

### Scenario: "Post-incident audit after minor collision"

| Step | Khoa's Action | System Action | Emotion |
|------|--------------|---------------|---------|
| 1 | Receives report: robot bumped into cart | Contact sensor published CRITICAL event | Concerned |
| 2 | Opens ~/walle_bags/ | 60-second rosbag auto-recorded at event time | Relieved (evidence exists) |
| 3 | Replays rosbag in RViz | Full sensor data: LiDAR, camera, cmd_vel | Investigative |
| 4 | Reviews /safety/event CSV log | Full audit trail with timestamp, severity | Satisfied |
| 5 | Root causes: cart was in LiDAR blind spot (fixed) | Filed as I-016, fix deployed | Confident |
| 6 | Signs off on continued operation | — | Authorized |

**Pain point resolved:** Rosbag + structured event log = complete audit trail for every safety event.

---

## Jobs-to-be-Done Summary

| Persona | Primary JTBD | Secondary JTBD |
|---------|-------------|---------------|
| Minh (Operator) | Navigate to target without reprogramming | Issue stop command reliably |
| Lan (Supervisor) | Monitor all missions from desk | Generate weekly reports from logs |
| Khoa (Safety) | Audit every safety event | Approve deployment with documented risk |
| Hùng (IT) | Deploy without custom integration | Debug with standard tools (RViz, rosbag) |
