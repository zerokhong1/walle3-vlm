# Requirements Traceability Matrix — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026

Each row traces: Business Requirement → Functional/Non-Functional Requirement → User Story → UAT Test Case

---

| BR | FR / NFR | User Story | Test Case | Status |
|----|----------|-----------|-----------|--------|
| BR-001 Natural language | FR-001 Command reception | US-005 | T-07, T-09 | Done ✅ |
| BR-001 Natural language | FR-003 Language support | US-005 | T-09 | Done ✅ |
| BR-001 Natural language | FR-004 Command ack | US-005 | T-07 | Done ✅ |
| BR-001 Natural language | NFR-011 30-min onboarding | US-011 | T-15 | Done ✅ |
| BR-002 No reprogramming | FR-005 VLM target ID | US-005 | T-07 | Done ✅ |
| BR-002 No reprogramming | FR-006 Autonomous nav | US-005 | T-07, T-12 | Done ✅ |
| BR-002 No reprogramming | FR-007 Search behavior | US-006 | T-08 | Done ✅ |
| BR-002 No reprogramming | FR-008 Target reached | US-007 | T-07 | Done ✅ |
| BR-003 Safety-first | FR-010 LiDAR detection | US-002 | T-02, T-03 | Done ✅ |
| BR-003 Safety-first | FR-011 Stable escape | US-002 | T-02 | Done ✅ |
| BR-003 Safety-first | FR-012 Rear obstacle | US-002 | T-04 | Done ✅ |
| BR-003 Safety-first | FR-013 Camera obstacle | US-012 | — | Done ✅ |
| BR-003 Safety-first | FR-015 Priority mux | US-003 | T-06 | Done ✅ |
| BR-003 Safety-first | FR-016 Contact sensor | US-014 | — | In Progress 🔄 |
| BR-003 Safety-first | NFR-006 Safety channel ≤40ms | US-003 | T-06 | Done ✅ |
| BR-004 Operator stop | FR-002 Stop fast-path | US-001 | T-01, T-16 | Done ✅ |
| BR-004 Operator stop | NFR-003 Stop ≤20ms | US-001 | T-01 | Done ✅ |
| BR-005 Observability | FR-017 Event contract | US-008 | — | Done ✅ |
| BR-005 Observability | FR-018 Mission logging | US-008 | — | Done ✅ |
| BR-005 Observability | FR-019 Auto rosbag | US-009 | — | Done ✅ |
| BR-005 Observability | FR-020 Inference logging | US-008 | T-19 | Done ✅ |
| BR-006 Affordable | FR-005 Local GPU inference | US-005 | T-19 | Done ✅ |
| BR-006 Affordable | NFR-002 VLM ≤10s | US-005 | T-19 | Done ✅ |
| BR-007 30-min onboarding | FR-021 Terminal TUI | US-010 | T-13, T-14 | Done ✅ |
| BR-007 30-min onboarding | FR-022 RViz2 | US-011 | T-15 | Done ✅ |
| BR-007 30-min onboarding | FR-023 One-command startup | US-011 | T-15 | Done ✅ |
| BR-008 Stuck recovery | FR-014 Stuck watchdog | US-004 | T-05 | Done ✅ |
| BR-008 Stuck recovery | NFR-007 Watchdog independence | US-004 | T-05 | Done ✅ |
| BR-008 Stuck recovery | NFR-010 Stuck rate ≤20% | US-004 | T-20 | Pending |

---

## Coverage Summary

| Business Requirement | FR Count | NFR Count | Story Count | Test Count | Coverage |
|--------------------|----------|-----------|------------|------------|----------|
| BR-001 | 3 | 1 | 2 | 3 | 100% |
| BR-002 | 4 | 0 | 3 | 4 | 100% |
| BR-003 | 6 | 2 | 5 | 5 | 90% (contact sensor pending) |
| BR-004 | 1 | 1 | 1 | 2 | 100% |
| BR-005 | 4 | 0 | 2 | 1 | 100% |
| BR-006 | 1 | 1 | 1 | 1 | 100% |
| BR-007 | 3 | 0 | 2 | 3 | 100% |
| BR-008 | 1 | 2 | 1 | 2 | 100% |
| **Total** | **23** | **7** | **14** | **21** | **97%** |

**Gap:** FR-016 (contact sensor) and T-11 (confidence threshold) not fully tested — both are in-progress / future backlog.
