# Data Dictionary — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Source:** ROS 2 telemetry via `mission_logger_node.py`; schema defined in [Event Contract v1.0](../product/09_event_contract_v1.md)

---

## Table: fact_missions

Written by `mission_logger_node.py` from `/mission/started` + `/mission/completed` topics.
One row per completed or aborted mission.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `mission_id` | string | No | Unique mission identifier (UUID or timestamp-based) | `msn_001` |
| `site_id` | string | No | Deployment site identifier | `warehouse_hn_01` |
| `robot_id` | string | No | Robot identifier | `walle3_01` |
| `user_command` | string | No | Raw operator command text | `go to the orange box` |
| `mission_type` | enum | No | `locate_and_fetch`, `navigation`, `search_only` | `locate_and_fetch` |
| `start_ts` | datetime | No | Mission start timestamp (ISO 8601) | `2026-04-20 09:01:12` |
| `end_ts` | datetime | Yes | Mission end timestamp; null if aborted before completion | `2026-04-20 09:02:38` |
| `duration_s` | float | Yes | Total mission duration in seconds | `86.0` |
| `outcome` | enum | No | `SUCCESS`, `FAILED` | `SUCCESS` |
| `reason` | enum | No | `target_reached`, `stuck_timeout_60s`, `operator_stop`, `vlm_error` | `target_reached` |
| `intervention_count` | int | No | Number of safety events during this mission | `1` |
| `inference_count` | int | No | Number of VLM inference calls during this mission | `5` |
| `schema_version` | string | No | Event contract schema version at time of mission | `1.0` |

**Key constraints:**
- `mission_id` is unique across all sites and robots.
- `outcome = 'SUCCESS'` implies `reason = 'target_reached'`.
- `outcome = 'FAILED'` + `reason = 'stuck_timeout_60s'` → review `fact_safety_events` for this `mission_id`.

---

## Table: fact_safety_events

Written by `mission_logger_node.py` from `/safety/event` topic.
One row per safety trigger event (collision risk, stuck, abort).

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `event_id` | string | No | Unique event identifier | `sev_001` |
| `mission_id` | string | No | Mission during which this event occurred | `msn_002` |
| `site_id` | string | No | Site identifier | `warehouse_hn_01` |
| `robot_id` | string | No | Robot identifier | `walle3_01` |
| `event_type` | enum | No | `collision_risk`, `stuck`, `stuck_abort`, `emergency_stop` | `collision_risk` |
| `severity` | enum | No | `INFO`, `MEDIUM`, `HIGH`, `CRITICAL` | `HIGH` |
| `timestamp` | datetime | No | Event timestamp | `2026-04-20 09:06:12` |
| `distance_m` | float | Yes | Minimum obstacle distance at trigger; null for non-LiDAR events | `0.34` |
| `channel` | enum | Yes | `SAFETY`, `VLM`, `WANDER` — which cmd_vel channel responded | `SAFETY` |
| `notes` | string | Yes | Free-text description from node logger | `LiDAR front sector triggered escape` |

**Severity definitions:**
- `CRITICAL`: RPN ≥ 40 or person-contact risk; robot stopped and escape initiated.
- `HIGH`: Obstacle within OBSTACLE_STOP_DIST (0.35m); escape triggered.
- `MEDIUM`: Obstacle within OBSTACLE_SLOW_DIST (0.60m); speed reduced.
- `INFO`: Watchdog warning (30s stuck threshold reached, not yet aborted).

**Key relationships:**
- `event_id` is unique.
- Multiple events per `mission_id` are expected; HIGH/CRITICAL count per mission is the Intervention Rate KPI.
- `event_type = 'stuck_abort'` means watchdog aborted the mission; `fact_missions.reason` will be `stuck_timeout_60s`.

---

## Table: fact_inference_events

Written by `mission_logger_node.py` from `/inference/event` topic.
One row per VLM inference call.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `inference_id` | string | No | Unique inference call identifier | `inf_001` |
| `mission_id` | string | No | Mission during which inference occurred | `msn_001` |
| `site_id` | string | No | Site identifier | `warehouse_hn_01` |
| `robot_id` | string | No | Robot identifier | `walle3_01` |
| `timestamp` | datetime | No | Inference start timestamp | `2026-04-20 09:01:22` |
| `model` | string | No | Model identifier | `Qwen2.5-VL-3B-INT4` |
| `latency_ms` | int | No | Wall-clock inference time in milliseconds | `8420` |
| `input_tokens` | int | Yes | Approximate prompt token count | `512` |
| `output_valid` | bool | No | Whether inference produced a valid JSON action plan | `true` |
| `target_found` | bool | Yes | Whether VLM identified the target object in this frame; null if `output_valid=false` | `false` |
| `confidence` | float | Yes | VLM confidence score 0.0–1.0; null if `output_valid=false` or not provided | `0.85` |
| `action_type` | enum | Yes | `go_forward`, `turn_left`, `turn_right`, `stop`, `search`, `reverse`; null if `output_valid=false` | `go_forward` |

**Key constraints:**
- `output_valid = false` means model produced invalid JSON or timed out; `target_found` and `confidence` will be null.
- `confidence < 0.40` is considered low-confidence (planned gate: I-010).
- `latency_ms` measures wall-clock time on the inference host GPU; network round-trip is zero (local inference).

**Derived KPIs from this table:**
- VLM latency p50/p95: `PERCENTILE(latency_ms, 0.50/0.95)` where `output_valid = true`
- Target not found rate: `COUNT(*) WHERE target_found = false / COUNT(*) WHERE output_valid = true`
- Invalid output rate: `COUNT(*) WHERE output_valid = false / COUNT(*)`

---

## Fact table relationships

```
fact_missions
    mission_id (PK)
         │
         ├──── fact_safety_events.mission_id (FK, 0 to many)
         │
         └──── fact_inference_events.mission_id (FK, 0 to many)
```

---

## Reference enumerations

### mission.outcome
| Value | Meaning |
|-------|---------|
| `SUCCESS` | Robot reached target and confirmed arrival |
| `FAILED` | Mission did not complete (see `reason`) |

### mission.reason
| Value | Trigger |
|-------|---------|
| `target_reached` | Robot confirmed target; state = COMPLETED |
| `stuck_timeout_60s` | Stuck watchdog aborted at 60s |
| `operator_stop` | Operator issued stop command |
| `vlm_error` | VLM produced invalid output for > 15s (NFR-008) |

### safety_event.event_type
| Value | Source | Action |
|-------|--------|--------|
| `collision_risk` | vlm_planner or wander LiDAR check | Escape maneuver |
| `stuck` | stuck_watchdog 30s warn | Log + continue |
| `stuck_abort` | stuck_watchdog 60s abort | Publish mission abort |
| `emergency_stop` | vlm_planner or wander | Safety channel halt |
