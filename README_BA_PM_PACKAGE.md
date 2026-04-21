# WallE3 VLM — BA/PM Documentation Package

This document is a guide for reviewers, recruiters, and hiring managers to navigate the BA/PM documentation in this repository.

---

## What this is

WallE3 VLM is an autonomous service robot project. This documentation package transforms the technical prototype into a **complete BA/PM portfolio case study** demonstrating product thinking, requirements management, safety governance, and delivery planning.

---

## Quick Navigation

**Start here → [docs/product/00_portfolio_case_study.md](docs/product/00_portfolio_case_study.md)**

Then:
- [One-pager](docs/product/01_product_one_pager.md) — 2 minutes
- [BRD](docs/product/02_business_requirements_document.md) — 5 minutes
- [PRD](docs/product/03_product_requirements_document.md) — 10 minutes
- [Backlog](docs/product/06_backlog_user_stories.md) — 10 minutes
- [KPI Spec](docs/product/08_kpi_dashboard_spec.md) — 5 minutes
- [Risk Register](docs/product/10_risk_register_fmea.md) — 10 minutes
- [UAT Plan](docs/product/11_uat_test_plan.md) — 10 minutes
- [Roadmap](docs/product/12_release_roadmap.md) — 5 minutes

Full documentation index → [docs/product/README.md](docs/product/README.md)

---

## What demonstrates BA skills

| BA Skill | Where demonstrated |
|----------|--------------------|
| Problem framing | BRD §2.1 Problem Statement |
| Stakeholder analysis | BRD §2.3, Stakeholder Comms Plan |
| Requirements elicitation | BRD §3 (8 BRs), PRD §3 (23 FRs) |
| Acceptance criteria | Backlog (every story has ≥3 ACs) |
| Traceability | Traceability Matrix (BR→FR→Story→Test) |
| Gap analysis | FMEA risk register (current vs. target state) |
| Process mapping | Service Blueprint |
| UAT design | UAT Test Plan (24 scenarios, 6 categories) |

## What demonstrates PM skills

| PM Skill | Where demonstrated |
|----------|--------------------|
| User research | Personas & User Journey (4 personas, 3 journeys) |
| Product strategy | Release Roadmap (R0–R4, 18 months) |
| Prioritization | Backlog (MoSCoW, 4 sprints) |
| KPI framework | KPI Dashboard Spec (8 metrics, targets, alerting) |
| Risk management | FMEA-lite (12 failure modes, RPN scoring) |
| Product decisions | Decision Log (7 documented decisions + rationale) |
| Stakeholder management | Stakeholder Communication Plan |
| Delivery governance | PR Template, Issue Templates, Release criteria |
| Financial thinking | ROI/TCO One-Pager (< 6 month payback) |

---

## Key product decisions documented

1. Dual-loop architecture (safety vs. VLM throughput trade-off)
2. Priority mux design (3 channels, timeout-based)
3. Stop keyword fast-path (< 20ms SLA, bypasses VLM)
4. VLM model selection (3B INT4 vs. larger models — hardware constraint)
5. LiDAR 360° extension (I-016 root cause → configuration fix)
6. Event contract: JSON over custom .msg (loose coupling between modules)
7. Defense-in-depth safety (two independent LiDAR checks during VLM_TASK)

---

## Author

**Cong Thai** — VinUniversity · Robotics + BA/PM
GitHub: [zerokhong1](https://github.com/zerokhong1)
