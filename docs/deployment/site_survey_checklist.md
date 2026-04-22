# Site Survey Checklist — WallE3 VLM Pilot

**Version:** 1.0 | **Date:** April 2026
**Use for:** Pre-pilot physical site assessment before any WallE3 deployment
**Approver:** Safety Officer + Operations Manager

> Complete this checklist before committing to a pilot site. Items marked ⛔ are blockers — deployment cannot proceed until resolved.

---

## Section 1: Environment Suitability

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1.1 | Indoor environment only (no outdoor, no ramps) | ☐ | |
| 1.2 | Floor is flat and level (±2cm over 5m) | ☐ | |
| 1.3 | Floor is dry (no water, oil, or slippery surfaces on robot path) | ☐ | |
| 1.4 | ⛔ No highly reflective floor surfaces (LiDAR accuracy risk) | ☐ | Polished marble, mirrored tiles |
| 1.5 | Minimum operational zone: 10m × 8m clear | ☐ | Arena baseline: 8×8m |
| 1.6 | Ceiling height ≥ 2.5m on full robot path | ☐ | |
| 1.7 | ⛔ No transparent obstacles on robot path (glass walls without markings) | ☐ | LiDAR passes through glass |
| 1.8 | Lighting is stable ≥ 100 lux on robot path | ☐ | VLM camera requires adequate light |
| 1.9 | No direct sunlight causing camera glare during operating hours | ☐ | |
| 1.10 | Ambient temperature: 10°C–40°C (GPU cooling requirement) | ☐ | |

---

## Section 2: Safety Zones

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 2.1 | Human traffic zones identified and mapped | ☐ | Draw floor plan with zones |
| 2.2 | ⛔ High-traffic crossing points assessed (e.g., main aisle intersections) | ☐ | |
| 2.3 | No-go zones defined (e.g., near forklift paths, loading docks) | ☐ | |
| 2.4 | Robot operating zone physically delineated (tape, barriers, or signage) | ☐ | |
| 2.5 | Emergency stop procedure posted at zone entry | ☐ | |
| 2.6 | ⛔ Hardware emergency stop button installed and tested | ☐ | Not in current prototype — required |
| 2.7 | All operators and bystanders briefed on robot behavior | ☐ | |
| 2.8 | Children / vulnerable persons not present in robot zone during operation | ☐ | |

---

## Section 3: Infrastructure

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 3.1 | 220V power outlet accessible in robot staging area | ☐ | Robot charging |
| 3.2 | ⛔ Compute unit (laptop/desktop with GPU) located safely near staging area | ☐ | |
| 3.3 | Wi-Fi available for remote monitoring (not required for inference) | ☐ | |
| 3.4 | Network port/IP for ROS 2 communication (if multi-machine) | ☐ | |
| 3.5 | Storage for CSV logs: ≥ 50 GB available | ☐ | `~/walle_logs/` |
| 3.6 | Storage for rosbags: ≥ 200 GB available | ☐ | `~/walle_bags/` |

---

## Section 4: Target Objects

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 4.1 | List of target objects defined (name, color, approximate size) | ☐ | |
| 4.2 | Target objects are visually distinct (color/shape difference ≥ 20%) | ☐ | |
| 4.3 | ⛔ Objects are not reflective, transparent, or uniformly white/black | ☐ | VLM struggles with low-contrast targets |
| 4.4 | Objects are placed at camera height range (0.3m–1.5m from floor) | ☐ | Robot camera height ~1.0m |
| 4.5 | Objects remain in fixed locations during pilot (no random repositioning) | ☐ | Controlled pilot only |
| 4.6 | Object names match natural language command vocabulary (tested in sim) | ☐ | |

---

## Section 5: Operations

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 5.1 | Pilot duration agreed: __ days | ☐ | Recommended: 14–30 days |
| 5.2 | Pilot KPIs agreed with site manager | ☐ | See [KPI Dashboard Spec](../product/08_kpi_dashboard_spec.md) |
| 5.3 | Baseline manual process time measured (min/task) | ☐ | Required for ROI calculation |
| 5.4 | Mission types and commands documented | ☐ | |
| 5.5 | Operator assigned as primary robot handler (min 1 person) | ☐ | |
| 5.6 | Supervisor/observer available during first 5 days | ☐ | |
| 5.7 | Incident reporting process established | ☐ | Use [Postmortem Template](../product/15_postmortem_template.md) |
| 5.8 | Data ownership and retention agreed | ☐ | Who owns CSV logs? |
| 5.9 | Pilot exit criteria agreed (what defines success/abort) | ☐ | |

---

## Section 6: Operator Readiness

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 6.1 | Operators completed 30-min onboarding session | ☐ | Minimum per NFR-011 |
| 6.2 | Operators can issue 5 distinct commands within 10 min | ☐ | BR-001 acceptance criterion |
| 6.3 | Operators know all stop keywords | ☐ | stop, dừng, halt, cancel |
| 6.4 | Operators know emergency procedure (hardware E-stop location) | ☐ | |
| 6.5 | Operators briefed on CRITICAL safety event response | ☐ | |

---

## Section 7: Data Collection Plan

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 7.1 | `mission_logger_node.py` enabled and writing to CSV | ☐ | |
| 7.2 | `rosbag_trigger_node.py` enabled for CRITICAL events | ☐ | |
| 7.3 | KPI dashboard owner assigned (who reviews data daily) | ☐ | |
| 7.4 | Review cadence set: daily during first week, weekly after | ☐ | |
| 7.5 | ⛔ Personal data in commands reviewed (no names, addresses in logs) | ☐ | |

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Safety Officer | | | |
| Operations Manager | | | |
| Robotics Engineer | | | |
| Site Manager | | | |

---

## Related documents

- [Pilot Rollout Plan](../product/14_pilot_rollout_plan.md) — 90-day deployment phases
- [Risk Register / FMEA](../product/10_risk_register_fmea.md) — failure modes and mitigations
- [Compliance Mapping](../safety/compliance_mapping.md) — applicable safety standards
- [UAT Test Plan](../product/11_uat_test_plan.md) — acceptance scenarios
