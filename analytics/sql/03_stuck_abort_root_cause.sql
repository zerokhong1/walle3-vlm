-- Stuck abort analysis — root cause drill-down
-- Business question: Why are missions aborting? What pattern predicts abort?
-- KPI: Stuck Abort Rate (target ≤20% R0, ≤10% R2)

-- Overall abort rate
SELECT
    site_id,
    COUNT(*)                                                               AS total_missions,
    SUM(CASE WHEN reason = 'stuck_timeout_60s' THEN 1 ELSE 0 END)         AS stuck_aborts,
    SUM(CASE WHEN reason = 'operator_stop'     THEN 1 ELSE 0 END)         AS operator_stops,
    ROUND(
        100.0 * SUM(CASE WHEN reason = 'stuck_timeout_60s' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                      AS stuck_abort_rate_pct
FROM fact_missions
GROUP BY site_id;

-- Aborted missions: how many safety events preceded the abort?
-- High safety event count before abort = tight/complex environment
SELECT
    m.mission_id,
    m.site_id,
    m.user_command,
    m.duration_s,
    m.intervention_count,
    m.inference_count,
    COUNT(s.event_id)                                                      AS safety_events_before_abort,
    COUNT(CASE WHEN s.severity = 'CRITICAL' THEN 1 END)                   AS critical_before_abort
FROM fact_missions m
JOIN fact_safety_events s ON m.mission_id = s.mission_id
WHERE m.reason = 'stuck_timeout_60s'
GROUP BY m.mission_id, m.site_id, m.user_command, m.duration_s,
         m.intervention_count, m.inference_count
ORDER BY critical_before_abort DESC;

-- Pattern: VLM confidence in aborted missions vs successful missions
SELECT
    m.outcome,
    ROUND(AVG(i.confidence), 3)                                            AS avg_vlm_confidence,
    ROUND(AVG(i.latency_ms), 0)                                            AS avg_latency_ms,
    SUM(CASE WHEN i.target_found = 'true'  THEN 1 ELSE 0 END)             AS frames_target_found,
    SUM(CASE WHEN i.output_valid = 'false' THEN 1 ELSE 0 END)             AS invalid_outputs
FROM fact_missions m
JOIN fact_inference_events i ON m.mission_id = i.mission_id
GROUP BY m.outcome;
