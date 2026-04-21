# KPI Dashboard Specification — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Consumer:** Module B (walle3-mission-analytics) | **Data source:** Event contract v1.0

---

## 1. Overview

This spec defines 8 operational KPIs for the WallE3 VLM dashboard. KPIs are computed from structured telemetry events published by Module A and ingested by Module B. The dashboard serves three audiences: operations managers (daily), robot supervisors (real-time), and safety officers (weekly audit).

---

## 2. KPI Definitions

### KPI-01 — Mission Success Rate

**Definition:** Percentage of missions that completed with `success=true`.

**Formula:**
```
mission_success_rate = COUNT(mission/completed WHERE success=true)
                     / COUNT(mission/completed) * 100
```

**Target:** ≥ 85% (pilot), ≥ 95% (production)
**Threshold:** Alert if < 70% over a 24-hour window
**Source topic:** `/mission/completed` → field `success`
**Refresh:** Per-mission (event-driven) + daily rollup
**Visualization:** Line chart (24h, 7d, 30d) + large number (today's rate)

---

### KPI-02 — Mean Mission Duration

**Definition:** Average time in seconds from mission start to completion (success or abort).

**Formula:**
```
mean_mission_duration = AVG(mission/completed.duration_s)
```

**Target:** ≤ 120s (pilot); < 60s as layout familiarity improves
**Threshold:** Alert if p95 > 300s (mission taking too long → likely stuck)
**Source topic:** `/mission/completed` → field `duration_s`
**Refresh:** Per-mission + hourly p50/p95 computation
**Visualization:** Histogram (duration distribution) + p50/p95 table

---

### KPI-03 — Operator Intervention Rate

**Definition:** Average number of safety interventions (HIGH or CRITICAL safety events) per mission.

**Formula:**
```
intervention_rate = SUM(mission/completed.intervention_count)
                  / COUNT(mission/completed)
```

**Target:** ≤ 0.5 interventions/mission (pilot)
**Threshold:** Alert if > 2.0/mission in any hour
**Source topic:** `/mission/completed` → field `intervention_count`
**Refresh:** Per-mission + hourly rolling average
**Visualization:** Bar chart (per hour) + daily trend

---

### KPI-04 — Safety Event Rate

**Definition:** Number of safety events per 10 missions, by severity.

**Formula:**
```
safety_event_rate = COUNT(safety/event) per 10 missions, grouped by severity
```

**Target:** CRITICAL = 0; HIGH ≤ 1 per 10 missions; MEDIUM ≤ 3 per 10 missions
**Threshold:** Any CRITICAL event triggers immediate page to safety officer
**Source topics:** `/safety/event` → fields `event_type`, `severity`, `timestamp`
**Refresh:** Real-time stream + 10-mission rolling window
**Visualization:** Stacked bar (severity breakdown) + CRITICAL counter badge

---

### KPI-05 — Stop Command Latency

**Definition:** Time in milliseconds from `/user_command` receive to diff-drive controller motor halt.

**Formula:**
```
stop_latency_ms = t(cmd_vel.linear.x=0) - t(user_command received)
```

**Target:** ≤ 20ms (SLA from BR-004)
**Threshold:** Alert if p95 > 50ms (degradation risk)
**Source:** Requires timestamp correlation between /user_command and /diff_drive_base_controller/cmd_vel
**Refresh:** Per stop command
**Visualization:** Gauge (current p50/p95) + time series

**Note:** Requires rosbag post-processing or instrumented timestamp injection. Tag: future enhancement.

---

### KPI-06 — VLM Inference Latency (p50/p95)

**Definition:** Time in milliseconds for VLM to process one camera frame and return an action plan.

**Formula:**
```
inference_latency_p50 = PERCENTILE(inference/event.latency_ms, 50)
inference_latency_p95 = PERCENTILE(inference/event.latency_ms, 95)
```

**Target:** p50 ≤ 10,000ms; p95 ≤ 15,000ms (RTX 3060 12 GB, 3B INT4)
**Threshold:** Alert if p50 > 15,000ms (model may be degraded)
**Source topic:** `/inference/event` → field `latency_ms`
**Refresh:** Per inference (every ~5s when active)
**Visualization:** Line chart (latency over time) + p50/p95 summary

---

### KPI-07 — Stuck Abort Rate

**Definition:** Percentage of missions aborted by the stuck watchdog (not completed by VLM or operator stop).

**Formula:**
```
stuck_abort_rate = COUNT(mission/completed WHERE reason LIKE 'stuck%')
                 / COUNT(mission/completed) * 100
```

**Target:** ≤ 10% (pilot), ≤ 5% (production)
**Threshold:** Alert if > 20% in a 2-hour window
**Source topic:** `/mission/completed` → field `reason`
**Refresh:** Per-mission
**Visualization:** Donut chart (abort reasons breakdown) + trend line

---

### KPI-08 — Target Not Found Rate

**Definition:** Percentage of missions where VLM never reported `target_found=true`.

**Formula:**
```
target_not_found_rate = COUNT(missions WHERE no inference/event had target_found=true)
                      / COUNT(missions) * 100
```

**Target:** ≤ 15% (pilot), ≤ 5% (production)
**Threshold:** Alert if > 30% in 4h (may indicate lighting issue or VLM degradation)
**Source topic:** `/inference/event` → field `target_found`, correlated with `mission_id`
**Refresh:** Per mission (computed at mission/completed)
**Visualization:** Bar chart by target type + overall gauge

---

## 3. Dashboard Layout

### View 1 — Operations Overview (Ops Manager, daily)

```
┌─────────────────────────────────────────────────────────────────┐
│  Today's Missions  │  Success Rate  │  Avg Duration  │  Safety  │
│  [total count]     │  [KPI-01 %]    │  [KPI-02 s]    │  [KPI-04]│
├─────────────────────────────────────────────────────────────────┤
│  Mission Success Rate — 30 days (line chart)                    │
├───────────────────────────────┬─────────────────────────────────┤
│  Abort Reasons Breakdown      │  Intervention Rate — 7 days     │
│  (donut KPI-07)               │  (bar chart KPI-03)             │
└───────────────────────────────┴─────────────────────────────────┘
```

### View 2 — Real-Time Monitor (Supervisor, always-on)

```
┌──────────────────────────────────────────────────────────────┐
│  LIVE: Planner State  │  Controller Mode  │  Active Channel  │
│  [from /planner/state]│  [/controller/mode]│ [/mux/active]  │
├──────────────────────────────────────────────────────────────┤
│  Safety Events (last 10, real-time)                          │
│  VLM Inference Latency (live gauge KPI-06)                   │
├──────────────────────────────────────────────────────────────┤
│  Current Mission: ID | Command | Duration | Interventions    │
└──────────────────────────────────────────────────────────────┘
```

### View 3 — Safety Audit (Safety Officer, weekly)

```
┌──────────────────────────────────────────────────────────────┐
│  Safety Events This Week                                     │
│  CRITICAL: [count]  HIGH: [count]  MEDIUM: [count]          │
├──────────────────────────────────────────────────────────────┤
│  Safety Event Timeline (bar chart by day, severity stacked)  │
├──────────────────────────────────────────────────────────────┤
│  Safety Event Log (searchable table)                         │
│  Columns: timestamp | event_type | severity | mission_id     │
│  [Export CSV button]                                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Data Pipeline

```
Module A (robot)
  ↓ ROS topics (7 event topics)
Mission Logger Node (~/walle_logs/*.csv)
  ↓ file watch or API push
Module B (walle3-mission-analytics)
  ↓ KPI computation engine
Dashboard (Grafana / custom React)
```

**CSV schema per topic:** `timestamp, mission_id, [topic-specific fields]`

**Retention:** 90 days rolling for operational data; 1 year for safety events.

---

## 5. Alerting Rules

| Alert | Condition | Severity | Recipient |
|-------|-----------|----------|-----------|
| Safety CRITICAL | Any /safety/event severity=CRITICAL | P0 | Safety officer (immediate) |
| Success rate drop | KPI-01 < 70% over 24h | P1 | Ops manager |
| High intervention | KPI-03 > 2.0/mission for 1h | P1 | Supervisor |
| Stuck rate spike | KPI-07 > 20% for 2h | P2 | Supervisor |
| Inference latency | KPI-06 p50 > 15s | P2 | IT engineer |
| Target not found | KPI-08 > 30% for 4h | P2 | Ops manager |
