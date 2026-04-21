# Release Roadmap — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026 | **Horizon:** R0–R4 (18 months)

---

## Release Overview

| Release | Name | Timeline | Focus |
|---------|------|----------|-------|
| R0 | Technical MVP | Completed | Core robot runs in simulation |
| R1 | Productized MVP | Apr 2026 | BA/PM documentation, portfolio ready |
| R2 | Operator Experience | Q3 2026 | UX improvements, Vietnamese voice, reliability |
| R3 | Pilot Readiness | Q4 2026 | Physical hardware, site survey, spatial memory |
| R4 | Production Readiness | Q2 2027 | Monitoring, incident process, fleet support |

---

## R0 — Technical MVP (Complete)

**Goal:** Prove the core technology works in simulation.

**Exit criteria (all met):**
- [x] Robot accepts natural language commands
- [x] VLM identifies visual targets (Qwen2.5-VL 3B INT4)
- [x] 6-state mission planner (IDLE → COMPLETED)
- [x] LiDAR obstacle avoidance (360° after I-016 fix)
- [x] Priority cmd_vel mux (safety > VLM > wander)
- [x] Independent stuck watchdog (30s/60s)
- [x] Stop command latency < 20ms
- [x] Structured telemetry (7 topics, event contract v1.0)
- [x] Auto rosbag on safety events
- [x] Warehouse world simulation

**Blockers resolved:** I-003, I-004, I-005, I-006, I-007, I-011, I-016

---

## R1 — Productized MVP (Current)

**Goal:** Transform the technical prototype into a portfolio-ready product case study demonstrating BA/PM capabilities.

**Timeline:** April 2026 (4 weeks)

**Deliverables:**
- [ ] Complete `docs/product/` package (19 documents)
- [ ] GitHub issue templates + PR template
- [ ] ISSUES.md updated with I-016 and fix history
- [ ] README updated with BA/PM section
- [ ] Interview pitch documented

**Exit criteria:**
- [ ] All P0 documents complete and reviewed
- [ ] UAT test plan written (T-01 to T-24)
- [ ] Risk register covers all S0/S1 risks with mitigations
- [ ] KPI dashboard spec complete with alerting rules
- [ ] Release roadmap extends to R4

**Audience:** Recruiters, hiring managers, portfolio reviewers.

---

## R2 — Operator Experience (Q3 2026)

**Goal:** Make the robot feel like a real product, not a demo.

**Timeline:** 8 weeks (July–August 2026)

**Key features:**

| Feature | User Story | Priority |
|---------|-----------|----------|
| Voice input (speech → /user_command) | US-015 | Must |
| Confidence threshold enforcement | US-017 | Must |
| Disk usage monitor + rotation policy | R-011 mitigation | Must |
| TUI mission history view (past 10 missions) | — | Should |
| RViz2 mission overlay (target circle) | — | Should |
| Vietnamese language model fine-tuning | — | Could |
| Watchdog dashboard integration (Module B) | — | Could |

**Exit criteria:**
- [ ] Voice input works for 5 Vietnamese command templates
- [ ] Confidence < 0.4 triggers "target not found" (not random navigation)
- [ ] Mission success rate ≥ 85% over 50 simulation runs
- [ ] Stuck abort rate ≤ 10%
- [ ] All UAT T-01 to T-24 pass

---

## R3 — Pilot Readiness (Q4 2026)

**Goal:** Deploy physical robot in a real warehouse or mall for controlled pilot.

**Timeline:** 10 weeks (October–December 2026)

**Prerequisites:**
- Pilot partner identified and signed MOU
- Safety officer approval
- Physical hardware procured (robot body + GPU workstation)
- Site survey completed

**Key features:**

| Feature | Description | Risk |
|---------|-------------|------|
| Sim-to-real transfer | Tune LiDAR height, camera exposure, wheel odometry | Medium |
| Spatial memory | Remember obstacle positions across sessions (I-008) | Medium |
| Geofencing | Restrict robot to approved zones | Low |
| Hardware safety checklist | Estop button, physical bumper, cable management | Low |
| Pilot monitoring dashboard | Module B deployed for ops team | Low |

**Exit criteria:**
- [ ] Robot completes 20 pilot missions with ≥ 70% success
- [ ] 0 safety incidents (person contact, property damage)
- [ ] Operator NPS ≥ +30 after pilot week
- [ ] Safety officer sign-off document
- [ ] All CRITICAL and HIGH risks mitigated in physical environment

---

## R4 — Production Readiness (Q2 2027)

**Goal:** Prepare for multi-site deployment with operational excellence.

**Timeline:** Q1–Q2 2027

**Key features:**
- Incident response playbook
- Multi-robot fleet management (Module C)
- WMS API integration (receive tasks from warehouse system)
- Automated performance regression testing (CI/CD)
- Support SLA: < 4h response for CRITICAL, < 24h for HIGH

**Exit criteria:**
- [ ] ≥ 95% mission success rate in pilot site after 30 days
- [ ] MTTD (mean time to detect) safety events < 1 minute
- [ ] MTTR (mean time to recover) < 30 minutes
- [ ] Operations runbook complete
- [ ] Incident process tested (tabletop exercise)

---

## Dependencies & Risks

| Release | Key Dependency | Risk |
|---------|---------------|------|
| R2 | STT model quality (Vietnamese) | Medium — may need fine-tuning |
| R3 | Pilot partner timeline | High — external dependency |
| R3 | Physical hardware reliability | Medium — sim-to-real gap |
| R4 | Multi-robot coordination complexity | High — scope risk |

---

## Product Principles (enforced across all releases)

1. **Safety gates every release.** No feature ships if it degrades safety metrics.
2. **Telemetry first.** Every new feature must emit structured events before shipping.
3. **Operator veto.** Any operator can halt the robot; this capability cannot be degraded.
4. **Measurable exit criteria.** No release ships without quantified success metrics.
