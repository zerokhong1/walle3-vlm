# Market & Use Case Analysis — WallE3 VLM

**Version:** 1.0 | **Date:** April 2026
**Author:** Cong Thai | **Purpose:** Identify target industries, use cases, buyer personas, and business value drivers

> Note: Market sizing figures are portfolio assumptions based on publicly available industry data. They would be validated through customer interviews, site surveys, and pilot data in a real engagement.

---

## 1. Problem Statement

Warehouse operators, mall staff, and factory floor workers spend **15–30% of working time** on locate-and-fetch and guidance tasks — walking to a zone, finding an object, returning to the requester. These tasks:

- Are **repetitive** — same locations, same objects.
- Are **layout-sensitive** — any rearrangement invalidates waypoint-programmed robots.
- Produce **no structured data** — no telemetry on task duration, failure rate, or bottlenecks.
- Are **resistant to traditional automation** — barcode scanning and conveyor systems require fixed infrastructure.

**WallE3's value proposition:** a natural-language-driven robot that requires **zero waypoint reprogramming**, produces structured telemetry, and handles real-world object variation via a Vision-Language Model.

---

## 2. Target Industry Matrix

| Industry | Pain Point | Specific Use Case | Primary Buyer | Success Metric |
|----------|-----------|-------------------|---------------|----------------|
| **Warehouse / 3PL** | Staff spend time locating SKUs, cartons, pallets | Locate-and-fetch navigation assistant for zone-to-zone tasks | Operations Manager, Warehouse Director | Mission success rate, time saved per task, layout-change cost |
| **Retail / Mall** | Staff repeatedly guide customers, answer location queries | Customer/object guidance assistant | Store Manager, Mall Operations | Staff time redirected, customer wait time |
| **Factory floor** | Operators walk between stations to pick materials or tools | Material movement helper for non-safety-critical paths | Production Manager, IE Engineer | Throughput, walking distance reduction |
| **University / Research lab** | Equipment, sample, or document movement between labs | Indoor delivery robot for controlled environments | Lab Manager, Admin | Task completion rate, researcher time saved |
| **Hospital / Healthcare** | Non-clinical supply movement (linens, non-hazardous supplies) | Supply logistics assistant | Facilities Manager | Delivery cycle time, staff hours redirected |

---

## 3. Prioritized Use Case Roadmap

| Use Case | Business Value | Technical Feasibility | Safety Risk | Regulatory Complexity | Priority |
|----------|---------------|----------------------|-------------|----------------------|----------|
| Warehouse locate-and-fetch | High (high task volume, clear ROI) | Medium (complex layouts, varying objects) | Medium (human co-presence) | Low (indoor industrial) | **P0 — R0/R1** |
| Lab delivery (controlled env) | Medium (moderate volume, clear scope) | High (structured environment, predictable objects) | Low–Medium (limited human traffic) | Low | **P0 — R1** |
| Retail / mall guidance | Medium (brand value, staff time) | Medium (crowded, dynamic) | High (public + children) | Medium (public space liability) | **P1 — R2** |
| Factory material movement | High (manufacturing efficiency) | Low–Medium (machinery, strict safety zones) | High (machine proximity) | High (ISO 10218, functional safety) | **P1 — R2** |
| Hospital supply logistics | High (healthcare efficiency) | Medium (structured corridors) | High (patient safety) | High (IEC 62304, MDR if applicable) | **P2 — R3+** |

---

## 4. Buyer Persona Mapping

| Persona | Title | Key Concern | Decision Trigger | Success Criteria |
|---------|-------|-------------|-----------------|-----------------|
| Operations Manager | Warehouse/Logistics Ops Manager | Cost reduction, throughput | Layout change that broke existing AMR | Time-per-task reduction ≥ 30% |
| Safety Officer | EHS / Safety Lead | Incident prevention, liability | Previous forklift near-miss incident | Zero robot-human contact incidents in pilot |
| IT / Systems Lead | IT Manager or Systems Integrator | Integration complexity, maintenance | Vendor lock-in concern with legacy WMS | ROS 2 open standard + CSV/API telemetry |
| Floor Operator | Warehouse Associate / Lab Tech | Ease of use, trust | Frustration with scripted commands | Issues command in plain language, sees correct result |
| Finance / Procurement | CFO / Procurement Manager | Payback period, TCO | Annual budget cycle | Break-even < 18 months (see ROI/TCO) |

See [Personas & User Journey](../product/04_personas_user_journey.md) for full persona profiles.

---

## 5. Competitive Positioning

| Dimension | Fixed-path AMR (Geek+, HAI Robotics) | Cloud-API robot (requires connectivity) | WallE3 VLM |
|-----------|--------------------------------------|-----------------------------------------|------------|
| Reprogramming on layout change | Manual waypoint update (hours–days) | Manual update or retraining | Zero — natural language adapts automatically |
| Language interface | Scripted commands or WMS integration | API integration required | Plain language (EN + VI) |
| Cloud dependency | No | Yes — latency, privacy, cost | No — local GPU inference |
| Hardware cost | $15,000–$80,000 | $10,000–$50,000 | ~$8,000–$12,000 (current prototype basis) |
| VLM / vision capability | No | Yes (cloud GPT-4V or Gemini) | Yes (local Qwen2.5-VL-3B) |
| Data sovereignty | N/A | Data sent to cloud | All data stays on-premise |
| Suitable environment | Structured warehouse with fixed layout | Any with internet | Indoor, semi-structured, with camera visibility |

---

## 6. Addressable Market Sizing (Vietnam pilot — portfolio estimate)

| Segment | Estimated facilities in Vietnam | Robot candidates per facility | Market units |
|---------|--------------------------------|------------------------------|--------------|
| Modern warehouses / 3PL | ~1,200 | 1–5 | ~3,000–6,000 robots |
| Retail / mall (medium-large) | ~800 | 1–3 | ~1,000–2,400 robots |
| Factory floor (electronics, textiles) | ~2,500 | 1–2 | ~2,500–5,000 robots |
| University / research | ~200 | 1–2 | ~200–400 robots |
| **Total serviceable market (Vietnam)** | — | — | **~7,000–14,000 robots** |

At an average robot price of $10,000 USD, the Vietnam addressable market is approximately **$70M–$140M USD** — before considering SaaS/analytics revenue from telemetry (Module B).

---

## 7. Key Business Questions Answered by Telemetry

| Business Question | Data Source | KPI |
|-------------------|-------------|-----|
| Is the robot worth the investment? | `fact_missions.duration_s` vs manual baseline | ROI / payback |
| Where are robots struggling? | `fact_missions.reason`, `fact_safety_events.event_type` | Stuck abort rate, intervention rate |
| Is the AI accurate enough? | `fact_inference_events.confidence`, `target_found` | Target not found rate |
| Is the robot safe? | `fact_safety_events.severity`, `distance_m` | CRITICAL events/day |
| Is the robot fast enough? | `fact_inference_events.latency_ms` | VLM latency p50/p95 |

See [KPI Dashboard Spec](../product/08_kpi_dashboard_spec.md) and [analytics/](../../analytics/) for SQL queries and Python analysis.
