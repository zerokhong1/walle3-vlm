# Compliance Mapping — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Status:** Preliminary portfolio mapping — not a certification claim
**Purpose:** Identify applicable safety standards, map current project evidence, and document gaps before physical pilot deployment

> **Disclaimer:** This document is a structured analysis of applicable standards for portfolio and planning purposes. It does not constitute a formal safety assessment, risk assessment under any specific standard, or certification claim. Physical deployment requires engagement with a certified safety assessor.

---

## 1. Applicable Standards

| Area | Standard | Applicability to WallE3 | Priority |
|------|----------|------------------------|----------|
| Autonomous Mobile Robot (AMR) indoor | **ISO 3691-4:2023** — Safety requirements for driverless industrial trucks and their systems | Primary — WallE3 is a driverless, indoor, autonomous mobile platform for industrial environments (warehouse/factory) | P0 |
| Service/social robot in shared human spaces | **ISO 13482:2014** — Safety requirements for personal care robots | Applicable if deployed in mall/hospital (public-facing) | P1 |
| Safety-related control systems | **ISO 13849-1:2023** — Safety-related parts of control systems | Relevant to safety loop (50Hz LiDAR check, cmd_vel_mux priority) | P0 |
| Functional safety (electronics/software) | **IEC 62061:2021** — Functional safety for machinery with electrical control systems | Applicable to safety-critical software components (vlm_planner safety loop, stuck watchdog) | P1 |
| Industrial robots (if future arm added) | **ISO 10218-1/2:2023** — Safety requirements for industrial robots | Currently not applicable (navigation only, no manipulator) | P2 |
| Workplace safety (Vietnam) | **QCVN 26:2016/BLĐTBXH** — National technical regulation on safety for industrial equipment | Applicable for any physical pilot in Vietnam | P0 |

---

## 2. ISO 3691-4 Mapping (Primary standard for indoor AMR)

### Key requirements vs current project evidence

| Requirement area | ISO 3691-4 clause | Current evidence | Gap before pilot |
|-----------------|-------------------|-----------------|-----------------|
| Speed limiting | 5.3.1 — max operating speed | OBSTACLE_SLOW_DIST triggers 40% speed reduction; max speed 0.25 m/s in config | Formal speed validation test on physical hardware |
| Emergency stop | 5.4.2 — emergency stop system | Fast-path stop < 20ms (T-01 PASS); safety channel P0 priority | Formal braking distance measurement (not done in simulation) |
| Obstacle detection | 5.6 — detection of persons and obstacles | LiDAR 360° FOV, 1080 samples, 50Hz check; OBSTACLE_STOP_DIST = 0.35m | Validation in physical environment with varying surfaces |
| Safe speed in detection zone | 5.6.3 — safe distance calculation | 0.35m stop threshold; 1.5s escape maneuver | Formal safe stopping distance calculation per ISO 3691-4:Annex B |
| Warning — people in path | 5.7 — warning devices | No audible/visual warning implemented | Add audio warning or light indicator before pilot |
| Operating zone delineation | 6.3 — intended use area | Not implemented (no geofence) | Define and enforce operating zones; add geofence logic |
| Operator training | 7.1 — information for use | 30-min onboarding target (NFR-011); README + TUI | Formal operator training documentation per standard |
| Validation and verification | 8 — verification | UAT T-01 to T-24 (see UAT plan); 10/24 PASS | Full V&V on physical hardware; independent safety assessment |

---

## 3. ISO 13849-1 Mapping (Safety-related control systems)

| Control function | Current design | Performance Level estimate | Gap |
|-----------------|---------------|--------------------------|-----|
| Emergency stop (stop keyword fast-path) | Single channel; vlm_planner publishes to /cmd_vel/safety | PLc (estimated) — single software channel | Hardware E-stop redundancy not implemented |
| Obstacle detection stop | LiDAR → vlm_planner fast loop → /cmd_vel/safety | PLb–PLc — single LiDAR sensor, single software path | Redundant sensor or hardware interlock for PLd |
| Speed monitoring | Software-only speed clamping | PLb | Hardware speed feedback loop not implemented |
| Safety channel priority (cmd_vel_mux) | Software timeout-based arbitration | PLb | Hardware-enforced priority would improve PL |

> Note: Performance Level (PL) estimates are informal. Formal PL assessment requires hazard analysis (FMEA), MTTF_d calculation, and CCF analysis per ISO 13849-1:2023 methodology.

---

## 4. Current Project Safety Evidence

| Evidence | Location | Covers |
|----------|----------|--------|
| FMEA-lite risk register | [docs/product/10_risk_register_fmea.md](../product/10_risk_register_fmea.md) | 12 failure modes, RPN scoring |
| UAT safety tests | [docs/product/11_uat_test_plan.md](../product/11_uat_test_plan.md) | T-01 to T-06 (6 safety scenarios) |
| Priority arbitration | `walle_ws/src/walle_demo/walle_demo/cmd_vel_mux.py` | Safety > VLM > wander |
| Fast-path stop | `walle_ws/src/walle_demo/walle_demo/vlm_planner.py` line 285 | < 20ms stop latency |
| Stuck watchdog | `walle_ws/src/walle_demo/walle_demo/stuck_watchdog_node.py` | Independent abort at 60s |
| Safety telemetry | `/safety/event` topic | Audit trail for all safety triggers |
| Issue governance | [ISSUES.md](../../ISSUES.md) | I-016 wall-collision root cause and fix |
| Product decision log | [docs/product/18_product_decision_log.md](../product/18_product_decision_log.md) | PDL-001 to PDL-007 |

---

## 5. Gaps Before Physical Pilot (Compliance Checklist)

### Safety engineering

- [ ] Formal braking distance test on physical hardware at max speed
- [ ] Formal safe stopping distance calculation (ISO 3691-4:Annex B)
- [ ] Redundant E-stop implementation (hardware button)
- [ ] Audible/visual warning system for pedestrian awareness
- [ ] Geofence / operating zone enforcement
- [ ] Formal hazard identification and risk assessment (FMEA → full RA)
- [ ] Performance Level assessment for safety functions

### Operational

- [ ] Operator training curriculum and records
- [ ] Site survey and risk assessment for specific deployment location
- [ ] No-go zone mapping and physical barriers if needed
- [ ] Emergency procedures documented and trained
- [ ] Incident/accident reporting procedure

### Documentation

- [ ] Declaration of Conformity (if required by local regulations)
- [ ] Safety manual for operators
- [ ] Maintenance schedule and inspection checklist

---

## 6. Pre-Pilot Approval Gate

Before physical deployment, the following must be signed off:

| Gate | Owner | Criterion |
|------|-------|-----------|
| Engineering validation | Robotics Engineer | All hardware safety tests passed |
| Safety assessment | Safety Officer | Site-specific risk assessment complete |
| Operator readiness | Operations Manager | Training completed; procedures documented |
| Product sign-off | Product Owner | UAT physical scenarios passed |
| Regulatory acknowledgment | Legal/Compliance | Applicable standards reviewed; gaps documented |

See [Pilot Rollout Plan](../product/14_pilot_rollout_plan.md) for full 90-day deployment plan.
