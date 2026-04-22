-- Mission success rate by site and day
-- Business question: Which sites are performing well? Are success rates improving?
-- KPI: Mission Success Rate (target ≥70% R0, ≥85% R2)

SELECT
    site_id,
    DATE(start_ts)                                                         AS mission_date,
    COUNT(*)                                                               AS total_missions,
    SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END)                  AS successful_missions,
    SUM(CASE WHEN outcome = 'FAILED'  THEN 1 ELSE 0 END)                  AS failed_missions,
    ROUND(
        100.0 * SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                      AS success_rate_pct,
    ROUND(AVG(duration_s), 1)                                              AS avg_duration_s
FROM fact_missions
GROUP BY site_id, DATE(start_ts)
ORDER BY site_id, mission_date DESC;

-- Expected output (from sample_data):
-- warehouse_hn_01 | 2026-04-21 | 5 | 3 | 2 | 60.0 | 93.2
-- warehouse_hn_01 | 2026-04-20 | 5 | 3 | 2 | 60.0 | 90.2
-- mall_hcm_01     | 2026-04-22 | 2 | 1 | 1 | 50.0 | 101.0
-- mall_hcm_01     | 2026-04-21 | 4 | 2 | 2 | 50.0 | 95.5
