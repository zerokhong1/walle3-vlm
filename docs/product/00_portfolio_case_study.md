# Portfolio Case Study — WallE3 VLM

**Role:** Product Manager / Business Analyst (solo project)
**Duration:** 3 months | **Stack:** ROS 2 Jazzy · Gazebo Harmonic · Qwen2.5-VL · Python
**Status:** Simulation-complete, pilot-ready spec

---

## The Problem

Warehouse and mall operators in Vietnam spend 15–30% of staff time on repetitive fetch-and-locate tasks — "where is SKU #4872?", "bring the carton from Zone B to picking." Existing solutions require expensive AMRs with pre-programmed waypoints that break every time the layout changes.

**The core insight:** A service robot that understands natural language commands can eliminate waypoint programming entirely. An operator says "go to the orange box" once — the robot goes.

---

## What I Built

**WallE3 VLM** is a ROS 2 autonomous robot that:
1. Accepts natural language commands in Vietnamese and English
2. Uses Qwen2.5-VL (Vision-Language Model, 3B params, INT4 quantized) to interpret the scene
3. Navigates autonomously with a priority-arbitrated safety layer
4. Streams structured telemetry for mission analytics

The system runs on a commodity GPU (RTX 3060 12 GB, ~$400) with no cloud dependency.

---

## My Contribution (BA/PM Lens)

### 1. Problem Framing
Conducted stakeholder interviews (simulated: warehouse manager, mall ops lead, safety officer) to identify the core jobs-to-be-done:
- Operators need to delegate locate-and-fetch without programming
- Safety officers need audit trails when the robot intervenes
- IT needs observability without deploying a separate monitoring stack

### 2. Requirements Definition
Translated engineering capability into structured requirements across two documents:
- **BRD:** 8 business requirements grounded in operator workflow (BR-001 to BR-008)
- **PRD:** 23 functional requirements + 9 non-functional requirements with measurable acceptance criteria

Key trade-off documented: Qwen2.5-VL 3B INT4 has 8–12s inference latency. I specified a dual-loop architecture (50 Hz safety + background VLM) to keep the robot reactive during inference — balancing VLM capability against real-time safety requirements.

### 3. Backlog & Prioritization
Built a 4-sprint backlog (28 user stories) using MoSCoW prioritization. Prioritized safety stories above feature stories in every sprint — establishing a product principle: *the robot must stop before it can navigate.*

### 4. KPI Framework
Defined 8 operational KPIs linking robot telemetry to business outcomes:

| KPI | Target | Source |
|-----|--------|--------|
| Mission success rate | ≥ 85% | `/mission/completed` |
| Operator intervention rate | ≤ 0.5/mission | `/safety/event` |
| Stop command latency | < 20ms | fast-path bypass |
| Stuck abort rate | < 10% | `/mission/completed` reason=stuck |

### 5. Safety Risk Management
Performed FMEA-lite on 12 failure modes. Identified 3 S0 risks (robot hits wall/person, silent failure during VLM inference) and specified mitigations:
- Priority-arbitrated cmd_vel mux (safety > VLM > wander)
- Independent stuck watchdog (warn 30s / abort 60s)
- Mandatory contact sensor as last-resort safety net

This directly led to fixing a critical regression (I-016) where the robot hit walls without triggering LiDAR safety — root-caused to a 17° frontal sector and 180° FOV limitation.

### 6. Event Contract
Designed a 7-topic telemetry schema consumed by Module B (mission analytics). Every topic has a fixed JSON schema with version pinning — enabling analytics without coordination overhead.

### 7. UAT Test Plan
Wrote 24 acceptance scenarios across 6 categories (navigation, safety, operator UX, performance, edge cases, regression). Each scenario has: preconditions, steps, expected result, pass/fail criteria.

### 8. Release Roadmap
Structured a 4-release roadmap from R0 (technical MVP) to R4 (production readiness), with measurable exit criteria for each release — enabling go/no-go decisions.

---

## Key Outcomes

- **0 untracked safety bugs** in simulation after implementing the FMEA-derived mitigations
- **< 20ms stop latency** vs. industry standard 100–500ms for similar systems
- **Full telemetry coverage** on 7 topics enabling mission-level analytics without code changes
- **Pilot-ready spec** with hardware checklist, site survey template, and 90-day rollout plan

---

## What I Learned

1. **Safety is a product requirement, not an engineering concern.** Every sprint had a safety story as the blocker for feature stories.
2. **Telemetry schema is a product decision.** The event contract I designed in week 2 forced me to clarify what "mission success" means before writing a single acceptance test.
3. **Latency budgets drive architecture.** The 8–12s VLM inference time forced the dual-loop design — understanding this tradeoff was critical to writing a coherent PRD.
4. **"Done" means validated, not deployed.** The UAT plan with 24 scenarios made me define acceptance criteria precisely enough that any engineer could run them without my involvement.

---

## Artifacts

All documentation is in [`docs/product/`](.) — 19 files covering the full BA/PM lifecycle from problem framing to pilot rollout.
