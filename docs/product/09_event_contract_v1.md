# Event Contract v1.0 — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Schema stability:** Breaking changes require version increment in `/mission/started`

All topics use `std_msgs/String` with UTF-8 JSON payloads (except `/planner/state` and `/controller/mode` which are plain strings).

---

## Topic Index

| Topic | Publisher | Type | Rate | Purpose |
|-------|-----------|------|------|---------|
| `/planner/state` | vlm_planner | plain string | 50 Hz | Mission lifecycle state |
| `/controller/mode` | vlm_planner, wander | plain string | 50 Hz | Controller behavior mode |
| `/mux/active_channel` | cmd_vel_mux | plain string | 2 Hz (on change) | Active velocity channel |
| `/mission/started` | vlm_planner | JSON | per mission | Mission start event |
| `/mission/completed` | vlm_planner, stuck_watchdog | JSON | per mission | Mission end event |
| `/safety/event` | vlm_planner, wander, stuck_watchdog | JSON | on event | Safety incidents |
| `/inference/event` | vlm_planner | JSON | per inference (~0.2 Hz) | VLM inference stats |

---

## Topic Schemas

### `/planner/state` — Plain string

**Values:** `IDLE` | `PLANNING` | `SEARCHING` | `APPROACHING` | `CONFIRMING` | `COMPLETED`

**State transitions:**
```
IDLE → PLANNING   (on command receipt)
PLANNING → SEARCHING  (on first VLM plan)
SEARCHING → APPROACHING  (target_found=true)
APPROACHING → CONFIRMING  (status=reached)
CONFIRMING → COMPLETED  (confirmation complete)
COMPLETED → IDLE  (after celebration)
Any → IDLE  (on stop command or stuck abort)
```

---

### `/controller/mode` — Plain string

**Values:** `VLM_TASK` | `CAM_AVOID` | `LIDAR_AVOID` | `WANDER` | `EMERGENCY_STOP`

---

### `/mux/active_channel` — Plain string

**Values:** `SAFETY` | `VLM` | `WANDER` | `idle`

Published every 2 seconds and on channel transition.

---

### `/mission/started` — JSON

```json
{
  "mission_id": "string (UUID4)",
  "mission_type": "string (vlm_navigation)",
  "user_command": "string",
  "timestamp": "float (Unix seconds, nanosecond precision)",
  "robot_id": "string",
  "site_id": "string",
  "schema_version": "string (v1.0)"
}
```

**Example:**
```json
{
  "mission_id": "f3a1b2c4-...",
  "mission_type": "vlm_navigation",
  "user_command": "go to the orange box",
  "timestamp": 1745302841.123456789,
  "robot_id": "walle3",
  "site_id": "arena",
  "schema_version": "v1.0"
}
```

---

### `/mission/completed` — JSON

```json
{
  "mission_id": "string (UUID4, matches /mission/started)",
  "success": "boolean",
  "duration_s": "float (seconds)",
  "intervention_count": "integer",
  "reason": "string"
}
```

**Reason values:**
| Reason | Success | Publisher |
|--------|---------|-----------|
| `target_reached` | true | vlm_planner |
| `operator_stop` | false | vlm_planner |
| `stuck_timeout_60s` | false | stuck_watchdog |
| `vlm_timeout` | false | vlm_planner |
| `not_found` | false | vlm_planner |

**Example:**
```json
{
  "mission_id": "f3a1b2c4-...",
  "success": false,
  "duration_s": 62.4,
  "intervention_count": 3,
  "reason": "stuck_timeout_60s"
}
```

---

### `/safety/event` — JSON

```json
{
  "event_type": "string",
  "severity": "string",
  "timestamp": "float (Unix seconds)"
}
```

**event_type values:**
| event_type | Description | Publisher |
|-----------|-------------|-----------|
| `collision_risk` | LiDAR obstacle within 0.35m | vlm_planner, wander |
| `stuck` | Displacement < 0.20m for 30s | stuck_watchdog |
| `stuck_abort` | Displacement < 0.20m for 60s | stuck_watchdog |
| `cam_obstacle` | Camera-detected low obstacle | wander |
| `emergency_stop` | Operator stop command | vlm_planner |
| `contact` | Physical contact via bumper sensor | (future, US-014) |

**severity values:** `low` | `medium` | `high` | `critical`

**Severity matrix:**
| event_type | Default severity |
|-----------|-----------------|
| collision_risk | high |
| stuck | high |
| stuck_abort | critical |
| cam_obstacle | medium |
| emergency_stop | high |
| contact | critical |

---

### `/inference/event` — JSON

```json
{
  "model": "string",
  "latency_ms": "float",
  "input_tokens": "integer",
  "output_valid": "boolean",
  "target_found": "boolean",
  "confidence": "float (0.0–1.0)"
}
```

**Example:**
```json
{
  "model": "Qwen/Qwen2.5-VL-3B-Instruct",
  "latency_ms": 9234.5,
  "input_tokens": 0,
  "output_valid": true,
  "target_found": true,
  "confidence": 0.82
}
```

---

## Schema Change Policy

1. **Non-breaking changes** (new optional field): increment patch (v1.0 → v1.1). No consumer update required.
2. **Breaking changes** (rename, remove, type change): increment minor (v1.0 → v2.0). All consumers must be updated before deployment.
3. **Schema version** embedded in `/mission/started.schema_version`. Module B validates this field on ingestion.

---

## Module B Ingestion Contract

Module B (walle3-mission-analytics) subscribes to all 7 topics via ROS bridge or CSV files from mission_logger. Module B must:
- Validate `schema_version` on ingestion
- Reject events with unknown schema versions (not silently accept)
- Store raw JSON alongside computed KPIs for audit
