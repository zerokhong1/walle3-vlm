# README Insert — BA/PM Section

*Copy this section into the main README.md under a "Product Documentation" heading.*

---

## Product Documentation (BA/PM)

This project is documented as a complete BA/PM case study demonstrating product thinking applied to robotics.

### Why this matters

Building a robot that *runs* is an engineering problem. Building a robot that *should be built* — with clear requirements, measurable KPIs, safety governance, and a path to pilot — is a product problem. This section documents the latter.

### Documentation Package

| Document | Purpose |
|----------|---------|
| [Case Study](docs/product/00_portfolio_case_study.md) | Full project narrative from BA/PM perspective |
| [Product One-Pager](docs/product/01_product_one_pager.md) | Problem, users, solution, value in one page |
| [BRD](docs/product/02_business_requirements_document.md) | 8 business requirements with acceptance criteria |
| [PRD](docs/product/03_product_requirements_document.md) | 23 functional + 9 non-functional requirements |
| [Personas & Journey](docs/product/04_personas_user_journey.md) | 4 user personas, 3 journey maps |
| [Service Blueprint](docs/product/05_service_blueprint.md) | Operator ↔ robot ↔ telemetry alignment |
| [Backlog](docs/product/06_backlog_user_stories.md) | 14 user stories, 4 sprints, MoSCoW priority |
| [Traceability Matrix](docs/product/07_requirements_traceability_matrix.md) | BR → FR → Story → Test |
| [KPI Dashboard Spec](docs/product/08_kpi_dashboard_spec.md) | 8 KPIs with targets, thresholds, alerting |
| [Event Contract v1.0](docs/product/09_event_contract_v1.md) | Telemetry schema for all 7 topics |
| [Risk Register / FMEA](docs/product/10_risk_register_fmea.md) | 12 failure modes, mitigations, residual risk |
| [UAT Test Plan](docs/product/11_uat_test_plan.md) | 24 acceptance scenarios across 6 categories |
| [Release Roadmap](docs/product/12_release_roadmap.md) | R0–R4, 18 months, with exit criteria |
| [Stakeholder Plan](docs/product/13_stakeholder_communication_plan.md) | Cadence, key messages, escalation path |
| [Pilot Rollout Plan](docs/product/14_pilot_rollout_plan.md) | 90-day physical deployment plan |
| [Postmortem Template](docs/product/15_postmortem_template.md) | Structured incident review |
| [Interview Pitch](docs/product/16_interview_pitch.md) | 30s / 60s / 2-min pitches, CV bullets |
| [ROI / TCO](docs/product/17_roi_tco_one_pager.md) | Business case: payback in < 6 months |
| [Decision Log](docs/product/18_product_decision_log.md) | 7 key product decisions with rationale |

### Key Product Decisions

- **Safety before features:** Every sprint had a safety story as the gate. The robot must stop before it navigates.
- **Dual-loop architecture:** 50Hz safety loop runs independently of 8–12s VLM inference — satisfying both real-time safety and AI capability.
- **Event contract first:** Telemetry schema was defined before the first line of analytics code — forcing precise definition of "mission success."
- **No cloud dependency:** VLM runs locally on RTX 3060. No subscription cost, no privacy risk, no latency from API calls.

### Issue Governance

Issues are tracked in [ISSUES.md](ISSUES.md) with severity (S0–S3), root cause, and fix history.

GitHub issue templates in `.github/ISSUE_TEMPLATE/`:
- [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)
- [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)
- [Safety Issue](.github/ISSUE_TEMPLATE/safety_issue.md)
- [Experiment Report](.github/ISSUE_TEMPLATE/experiment_report.md)
- [UAT Failure](.github/ISSUE_TEMPLATE/uat_failure.md)
