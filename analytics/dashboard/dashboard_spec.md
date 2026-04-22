# KPI Dashboard Spec — WallE3 VLM

**Tool:** Python/Matplotlib (portable); production target: Power BI or Tableau
**Data source:** `analytics/sample_data/` (CSV fact tables from `mission_logger_node.py`)
**Script:** `analytics/python/mission_kpi_analysis.py`
**Output:** `analytics/dashboard/kpi_dashboard.png`

---

## Dashboard layout (3 rows × 4 columns)

| Row | Panel | KPI | Target |
|-----|-------|-----|--------|
| 0 | Scorecard: Mission Success Rate | ≥70% R0, ≥85% R2 | Green/Yellow/Red |
| 0 | Scorecard: Mean Mission Duration | ≤120s R0 | |
| 0 | Scorecard: Stuck Abort Rate | ≤20% R0 | |
| 0 | Scorecard: Safety Events/Mission | ≤1.0 R0 | |
| 1 | Bar: Daily Success Rate trend | ≥70% line | |
| 1 | Pie: Safety events by severity | CRITICAL/HIGH/MEDIUM | |
| 1 | KPI: VLM Latency p50/p95 | p50≤10s, p95≤15s | |
| 2 | Bar: Success Rate by site | ≥70% line | |
| 2 | Table: ROI snapshot | Break-even ≤18 months | |

## Color coding

| Color | Meaning |
|-------|---------|
| Green | KPI at or above target |
| Yellow | KPI within warning band |
| Red | KPI below threshold — action required |
| Gray | Informational |

## Data pipeline

```
ROS 2 topics
    /mission/started
    /mission/completed      → mission_logger_node.py → fact_missions.csv
    /safety/event           →                        → fact_safety_events.csv
    /inference/event        →                        → fact_inference_events.csv
                                        ↓
                           analytics/python/mission_kpi_analysis.py
                                        ↓
                           analytics/dashboard/kpi_dashboard.png
```

## Production migration path (Power BI)

1. Connect Power BI to CSV files (or replace with SQL database connection).
2. Replicate measures using DAX:
   - `Mission Success Rate = DIVIDE(COUNTROWS(FILTER(fact_missions, fact_missions[outcome]="SUCCESS")), COUNTROWS(fact_missions))`
   - `Interventions per Mission = DIVIDE(COUNTROWS(fact_safety_events), COUNTROWS(fact_missions))`
3. Add slicers: site_id, date range, mission_type.
4. Add drill-through from daily summary → mission list → safety event detail.
5. Publish to Power BI Service for operator/manager access.

## Alert thresholds

| KPI | Warning | Alert |
|-----|---------|-------|
| Mission success rate | < 70% | < 50% |
| Stuck abort rate | > 20% | > 35% |
| CRITICAL safety events/day | > 3 | > 8 |
| VLM latency p95 | > 12s | > 18s |

See [KPI Dashboard Spec](../docs/product/08_kpi_dashboard_spec.md) for full definition of all 8 KPIs.
