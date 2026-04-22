# Risk Register & FMEA-lite — WallE3 VLM

**Version:** 1.1 | **Date:** April 2026
**Method:** FMEA-lite (Failure Mode and Effects Analysis, simplified)
**Scope:** Module A simulation + physical pilot

---

## FMEA Scoring

- **Severity (S):** 1 (minor) → 5 (catastrophic)
- **Occurrence (O):** 1 (rare) → 5 (frequent)
- **Detectability (D):** 1 (obvious) → 5 (invisible)
- **RPN = S × O × D** — Risk Priority Number

**Thresholds:** RPN ≥ 40 = S0/Critical | 20–39 = S1/High | 10–19 = S2/Medium | < 10 = S3/Low

**Severity veto rule:** Any failure mode with S=5 (catastrophic — person injury) is classified S0 regardless of RPN, because Occurrence and Detectability cannot be fully validated in simulation. This follows common FMEA practice for life-safety risks.

---

## S0 — Critical Risks (RPN ≥ 40 or S=5 veto)

### R-001 — Robot collides with person

| Field | Value |
|-------|-------|
| Failure Mode | Robot drives into human operator |
| Effect | Physical injury, pilot termination, liability |
| Cause | LiDAR blind spot, VLM overrides safety, network delay |
| S | 5 |
| O | 2 |
| D | 2 |
| **RPN** | **20** |
| **S0 classification** | **Severity veto (S=5, person-contact risk) — cannot be fully validated in simulation** |
| Current Controls | 360° LiDAR, 50Hz safety check, priority mux P0, contact sensor |
| Mitigation | Geofence exclusion zones around human work areas; reduce robot speed to 0.15m/s in human-present zones |
| Residual Risk | Low after mitigation |
| Owner | Safety Officer |
| Status | Mitigated (sim) — pending physical validation |

---

### R-002 — Robot hits wall without LiDAR trigger (I-016)

| Field | Value |
|-------|-------|
| Failure Mode | Robot navigates into wall; LiDAR safety not triggered |
| Effect | Hardware damage, safety regression, loss of pilot confidence |
| Cause | LiDAR FOV only 180° (BUG-1); vlm_planner sector ±17° (BUG-2); wander skips safety during VLM_TASK (BUG-3) |
| S | 4 |
| O | 4 |
| D | 3 |
| **RPN** | **48** |
| Current Controls | None (was undetected) |
| Mitigation | Extended LiDAR to 360°; widened vlm_planner sector to ±30° + diagonals; wander safety check during VLM_TASK |
| Residual Risk | Low after fix deployment |
| Owner | Engineering |
| Status | Fixed ✅ (commits ddaba81, c8ebdaa, dad3632) |

---

### R-003 — VLM inference blocks safety loop

| Field | Value |
|-------|-------|
| Failure Mode | VLM inference runs in main ROS thread; LiDAR scan rate drops to 0Hz during inference |
| Effect | Robot blind for 8–12s; cannot avoid obstacles |
| Cause | SingleThreadedExecutor + blocking VLM call |
| S | 5 |
| O | 3 |
| D | 3 |
| **RPN** | **45** |
| Current Controls | Background thread for VLM inference; 50Hz fast timer for safety |
| Mitigation | MultiThreadedExecutor in vlm_planner; VLM inference in daemon thread; fast timer isolated |
| Residual Risk | Low — verified via Phase 7.1 diagnostic |
| Owner | Engineering |
| Status | Mitigated ✅ (dual-loop architecture) |

---

## S1 — High Risks (RPN 20–39)

### R-004 — Robot stuck in corridor, blocking operations

| Field | Value |
|-------|-------|
| Failure Mode | Robot cannot navigate out of narrow space; blocks aisle |
| Effect | Operational disruption; negative operator perception |
| Cause | VLM search rotation in place; narrow corridor traps escape maneuver |
| S | 3 |
| O | 3 |
| D | 2 |
| **RPN** | **18** |
| Mitigation | Stuck watchdog (warn 30s, abort 60s); corner-trap escape (wider turn); supervisor alert |
| Status | Mitigated |

---

### R-005 — VLM hallucinates target position

| Field | Value |
|-------|-------|
| Failure Mode | VLM reports target_found=true at wrong location; robot drives to wrong object |
| Effect | Task failure; incorrect item retrieval |
| Cause | VLM model hallucination; low confidence plan executed |
| S | 3 |
| O | 3 |
| D | 3 |
| **RPN** | **27** |
| Mitigation | Confidence threshold enforcement (I-010, planned); temporal filtering (majority vote, window=3); operator confirmation for high-value tasks |
| Status | Partially mitigated (temporal filtering done; confidence threshold not yet enforced) |

---

### R-006 — Mission logger crash loses telemetry

| Field | Value |
|-------|-------|
| Failure Mode | mission_logger node crashes; CSV data lost for active missions |
| Effect | Incomplete telemetry; safety audit gap |
| Cause | Node exception, disk full, permission error |
| S | 3 |
| O | 2 |
| D | 2 |
| **RPN** | **12** |
| Mitigation | Logger runs as separate node (fault isolated); rosbag auto-record as backup; disk space check on startup |
| Status | Partially mitigated |

---

### R-007 — QoS mismatch causes LiDAR data drop

| Field | Value |
|-------|-------|
| Failure Mode | LiDAR publisher uses BEST_EFFORT but subscriber uses RELIABLE; messages silently dropped |
| Effect | Stale LiDAR data; false "clear" readings; collision |
| Cause | Default QoS mismatch between Gazebo bridge and ROS subscriber |
| S | 4 |
| O | 2 |
| D | 4 |
| **RPN** | **32** |
| Mitigation | All LiDAR subscribers explicitly set BEST_EFFORT QoS; bridge.yaml uses SENSOR_DATA profile |
| Status | Mitigated ✅ (verified in Phase 1 diagnostic) |

---

## S2 — Medium Risks (RPN 10–19)

### R-008 — Stop keyword not recognized due to encoding

| Field | Value |
|-------|-------|
| Failure Mode | Vietnamese stop keyword (dừng) not matched due to UTF-8 encoding mismatch |
| Effect | Stop command fails; operator cannot halt robot reliably |
| Cause | Terminal encoding vs. ROS message encoding |
| S | 5 |
| O | 1 |
| D | 2 |
| **RPN** | **10** |
| Mitigation | Stop keyword set includes ASCII variants (dung, dừng, thoat, thoát); test in CI |
| Status | Mitigated |

---

### R-009 — Camera frame age causes stale VLM inference

| Field | Value |
|-------|-------|
| Failure Mode | VLM processes 10-second-old camera frame; navigation plan for old scene |
| Effect | Robot navigates toward object that has moved |
| Cause | Camera rate < VLM inference rate; frame not timestamped |
| S | 2 |
| O | 3 |
| D | 3 |
| **RPN** | **18** |
| Mitigation | Camera age check before inference; frame discarded if > 2s old |
| Status | Partially mitigated |

---

### R-010 — Physical deployment: LiDAR height too low

| Field | Value |
|-------|-------|
| Failure Mode | On physical robot, LiDAR mounted at 0.18m absolute height; rays hit floor tiles |
| Effect | Floor reflections cause false obstacle detections; robot stops randomly |
| Cause | Glossy warehouse floor reflects LiDAR; range_min filter insufficient |
| S | 2 |
| O | 3 |
| D | 2 |
| **RPN** | **12** |
| Mitigation | Physical mounting: raise LiDAR to 0.25m minimum; add floor angle filter (exclude rays > 10° below horizontal) |
| Status | Simulation N/A; flag for physical pilot |

---

### R-011 — Rosbag disk space exhaustion

| Field | Value |
|-------|-------|
| Failure Mode | Auto-recorded rosbags fill disk; system crashes or stops recording |
| Effect | Safety audit data lost; node crashes |
| Cause | Frequent safety events in testing; no rotation policy |
| S | 2 |
| O | 3 |
| D | 3 |
| **RPN** | **18** |
| Mitigation | Disk check before recording; 7-day retention policy; alert if disk < 10 GB |
| Status | Planned (R2) |

---

### R-012 — Contact sensor plugin unavailable in Gazebo Harmonic

| Field | Value |
|-------|-------|
| Failure Mode | `gz-sim-contact-system` plugin not available; contact sensor silently fails |
| Effect | Last-resort safety net disabled without warning |
| Cause | Plugin naming/availability differences across Gazebo versions |
| S | 3 |
| O | 2 |
| D | 3 |
| **RPN** | **18** |
| Mitigation | Verify plugin at launch; log warning if /bumper topic has 0 publishers; document alternative plugin names |
| Status | Needs validation at next launch |

---

## Risk Summary

| ID | Risk | RPN | Status |
|----|------|-----|--------|
| R-001 | Person collision | 20 | Mitigated (sim) |
| R-002 | Wall collision (I-016) | 48 | Fixed ✅ |
| R-003 | VLM blocks safety | 45 | Fixed ✅ |
| R-004 | Corridor stuck | 18 | Mitigated |
| R-005 | VLM hallucination | 27 | Partial |
| R-006 | Logger crash | 12 | Partial |
| R-007 | QoS mismatch | 32 | Fixed ✅ |
| R-008 | Stop keyword encoding | 10 | Fixed ✅ |
| R-009 | Stale camera frame | 18 | Partial |
| R-010 | Physical LiDAR height | 12 | Simulation N/A |
| R-011 | Disk exhaustion | 18 | Planned |
| R-012 | Contact sensor plugin | 18 | Needs validation |

**3 risks remain partially mitigated (R-005, R-009, R-012) — must be resolved before physical pilot.**
