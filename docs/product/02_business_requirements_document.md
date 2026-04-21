# Business Requirements Document — WallE3 VLM

**Version:** 1.0 | **Status:** Approved | **Date:** April 2026
**Author:** Cong Thai | **Reviewer:** —

---

## 1. Executive Summary

WallE3 VLM addresses the locate-and-fetch labor problem in warehouse and mall environments by providing a natural-language-controlled autonomous service robot. This BRD defines the business requirements that the product must satisfy for initial pilot deployment.

---

## 2. Business Context

### 2.1 Problem Statement

In warehouse and retail operations in Vietnam, human staff spend an estimated 15–30% of their shift on locate-and-fetch tasks:
- Walking to retrieve items from storage zones
- Guiding customers to product locations
- Moving items between pick zones and drop points

Current automation options require:
- AMR solutions: $50,000–$200,000 per unit, 2–6 weeks integration
- Fixed conveyors: not reusable across layout changes
- Manual waypoint programming: breaks on every layout change

**The business gap:** No affordable, re-programmable solution exists that understands natural language and adapts to dynamic environments without re-programming.

### 2.2 Opportunity

The combination of open-source ROS 2, GPU-accelerated VLMs (3B params, INT4 quantization), and commodity hardware ($400 GPU) now makes natural-language robot navigation viable at pilot cost < $2,000 total hardware.

### 2.3 Stakeholders

| Stakeholder | Role | Key Interest |
|-------------|------|-------------|
| Warehouse Manager | Primary sponsor | Reduce labor cost, increase throughput |
| Operators (floor staff) | Primary users | Easy command interface, safe robot |
| Safety Officer | Veto stakeholder | Zero unsafe incidents |
| IT/Engineering | Implementation | Low integration complexity, observability |
| Finance | Budget approval | ROI within 12 months |

---

## 3. Business Requirements

### BR-001 — Natural Language Control
The system shall accept operator commands in Vietnamese and English without requiring pre-programmed waypoints or menus.

**Rationale:** Eliminate the programming bottleneck that prevents non-technical staff from delegating tasks to robots.

**Acceptance:** A warehouse operator with zero robotics training can issue 5 distinct navigation commands within 10 minutes of first use.

---

### BR-002 — Task Delegation Without Layout Reprogramming
The system shall navigate to visually-described targets (by color, shape, or type) without requiring a map update or waypoint change when the physical layout changes.

**Rationale:** Warehouses rearrange zones weekly. Reprogramming costs more than the labor saved.

**Acceptance:** After moving 3 objects to new positions, an operator can still locate them using natural language commands with ≥ 70% success rate.

---

### BR-003 — Safety-First Operation
The robot shall never cause harm to personnel or property. Safety response shall be faster than operator reaction time.

**Rationale:** A single injury incident would terminate the pilot and expose the operator to liability.

**Acceptance:** All safety failures (collision risk, stuck, operator stop) are responded to within 50ms. Safety events are logged with timestamp and severity.

**Non-negotiable:** This is a veto requirement. Failure disqualifies the product from any deployment.

---

### BR-004 — Operator Stop Control
An operator shall be able to halt the robot immediately using a voice or text command, with no dependence on the VLM pipeline.

**Rationale:** Operators must have reliable emergency control regardless of AI model state.

**Acceptance:** Stop commands ("stop", "dừng", "halt") halt the robot within 20ms of command receipt, bypassing the VLM inference loop.

---

### BR-005 — Mission Observability
All robot missions shall be logged with structured data enabling post-hoc analysis of success, failure, duration, and safety events.

**Rationale:** Operations managers need data to justify continued deployment and identify improvement areas.

**Acceptance:** Every mission generates at least 4 telemetry events: started, completed, safety events (if any), inference events. Data is queryable in CSV format within 1 minute of mission end.

---

### BR-006 — Affordable Hardware
The robot platform shall run on hardware costing < $2,000 total (GPU + compute) without cloud dependency.

**Rationale:** Pilot cost must be recoverable within 6 months of deployment.

**Acceptance:** Full system runs on a single workstation with NVIDIA GPU ≥ 8 GB VRAM. No per-mission cloud API cost.

---

### BR-007 — Operator Onboarding < 30 Minutes
A new operator shall be able to use the system independently after ≤ 30 minutes of training.

**Rationale:** High staff turnover in warehouse/retail means onboarding must be minimal.

**Acceptance:** A new operator, after a 30-minute orientation covering command vocabulary and safety procedures, can complete 3 missions without supervisor assistance.

---

### BR-008 — Autonomous Stuck Recovery
The robot shall detect when it is unable to make progress and escalate appropriately without requiring operator intervention.

**Rationale:** An immobile robot that requires manual reset eliminates the labor-saving value.

**Acceptance:** Robot automatically escalates (warn at 30s, abort at 60s) when stuck. Operator receives alert. False positive rate < 5% in open environments.

---

## 4. Constraints

| Constraint | Description |
|------------|-------------|
| Hardware | NVIDIA GPU ≥ 8 GB VRAM for VLM inference |
| Software | ROS 2 Jazzy, Ubuntu 24.04 LTS |
| Network | Must operate offline (no cloud dependency for inference) |
| Safety regulation | Must comply with local workplace safety guidelines before physical deployment |
| Language | Must support Vietnamese (primary) and English |
| Budget | Total hardware cost ≤ $2,000 for pilot unit |

---

## 5. Assumptions

1. Pilot environment has adequate lighting for camera-based object detection.
2. Operators have basic smartphone/tablet literacy.
3. Floor layout changes occur ≤ 3 times per week.
4. Safety officer approval is required before any physical (non-simulation) deployment.
5. Pilot partner provides a dedicated test zone ≥ 20m × 15m for the initial deployment.

---

## 6. Out of Scope

- Multi-robot fleet coordination
- Autonomous charging and return-to-base
- SLAM-based mapping and localization
- Integration with WMS (Warehouse Management System)
- Physical manipulation (pick and place — navigation only)
- Outdoor operation

---

## 7. Success Criteria for R1 (Simulation)

| Criterion | Measurement |
|-----------|-------------|
| ≥ 70% mission success rate | Measured over 50 simulation runs |
| 0 unrecovered collisions | Robot stops before physical contact |
| ≤ 20ms stop latency | Measured from command publish to motor halt |
| 100% mission event logging | Every mission has started + completed events |

---

## 8. Change Log

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | Apr 2026 | Initial release | Cong Thai |
