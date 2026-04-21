# Product One-Pager — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026 | **Author:** Cong Thai

---

## Problem

Warehouse and mall operators waste 15–30% of labor hours on repetitive locate-and-fetch tasks. Existing robot solutions require expensive waypoint programming that breaks every layout change. Operators have no way to delegate ad-hoc tasks to a robot using natural language.

---

## Users

| Persona | Key Job-to-be-Done | Pain Point |
|---------|-------------------|------------|
| Warehouse operator | "Find SKU and bring to picking area" | Must re-program waypoints after every layout change |
| Mall customer service | "Guide customer to product location" | No hands-free navigation delegation |
| Robot supervisor | "Monitor robot health in real-time" | Fragmented logs, no structured telemetry |
| Safety officer | "Ensure robot never harms people" | No audit trail for safety interventions |

---

## Solution

**WallE3 VLM** — an autonomous service robot that accepts natural language commands and navigates to visual targets without pre-programmed waypoints.

```
Operator: "go to the orange box"
Robot:    [camera → Qwen2.5-VL → action plan → navigate → stop at target]
```

**Key capabilities:**
- Natural language + Vietnamese commands (text and future voice)
- Vision-Language Model inference on local GPU (no cloud, no privacy risk)
- Priority-arbitrated safety: EMERGENCY_STOP always overrides navigation
- Structured telemetry for mission analytics (7 topics, JSON schema v1.0)
- < 20ms stop command latency (bypasses VLM pipeline)

---

## Value Proposition

| Stakeholder | Value |
|-------------|-------|
| Operations | Eliminate waypoint reprogramming — zero setup for new tasks |
| Safety | Independent watchdog + contact sensor — robot stops before it harms |
| IT/Analytics | Structured telemetry out-of-the-box — no instrumentation work |
| Finance | Runs on $400 GPU, no cloud subscription, no proprietary hardware |

---

## Technical Architecture (summary)

```
User command → VLM Planner (50 Hz safety + background VLM)
                    ↓
             cmd_vel_mux (safety P0 > vlm P1 > wander P2)
                    ↓
             diff_drive_controller → robot
```

Three-module platform:
- **Module A** (this repo): Robot runtime + safety + telemetry
- **Module B** (walle3-mission-analytics): KPI computation from telemetry
- **Module C** (walle3-ops-simulator): Synthetic training scenario generator

---

## Success Metrics

| KPI | MVP Target | Pilot Target |
|-----|-----------|-------------|
| Mission success rate | ≥ 70% | ≥ 85% |
| Operator intervention rate | ≤ 2/mission | ≤ 0.5/mission |
| Stop command latency | < 50ms | < 20ms |
| Safety event → stop time | < 100ms | < 50ms |
| Stuck abort rate | < 20% | < 10% |

---

## Current Status

- **R0 (Technical MVP):** Complete in simulation
- **R1 (Productized MVP):** In progress — BA/PM documentation package
- **R2–R4:** Roadmap defined, pending pilot partner

---

## Next Steps

1. Complete R1 documentation package (this folder)
2. Identify pilot partner (warehouse or mall operator in Hanoi/HCMC)
3. Hardware procurement + site survey for R3 pilot
4. Voice input integration (speech-to-text → `/user_command`)
