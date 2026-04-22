-- Safety interventions per mission by site
-- Business question: Is the robot creating safety incidents? Where are they concentrated?
-- KPI: Intervention Rate (target ≤1 per mission R0, ≤0.3 R2)

SELECT
    m.site_id,
    COUNT(DISTINCT m.mission_id)                                           AS total_missions,
    COUNT(s.event_id)                                                      AS total_safety_events,
    SUM(CASE WHEN s.severity = 'CRITICAL' THEN 1 ELSE 0 END)              AS critical_events,
    SUM(CASE WHEN s.severity = 'HIGH'     THEN 1 ELSE 0 END)              AS high_events,
    ROUND(
        1.0 * COUNT(s.event_id) / COUNT(DISTINCT m.mission_id), 2
    )                                                                      AS interventions_per_mission,
    ROUND(AVG(s.distance_m), 3)                                            AS avg_trigger_distance_m
FROM fact_missions m
LEFT JOIN fact_safety_events s
    ON m.mission_id = s.mission_id
    AND s.event_type = 'collision_risk'
GROUP BY m.site_id
ORDER BY interventions_per_mission DESC;

-- Severity distribution for drill-down
SELECT
    m.site_id,
    s.event_type,
    s.severity,
    COUNT(*)                                                               AS event_count,
    ROUND(AVG(s.distance_m), 3)                                            AS avg_distance_m,
    ROUND(MIN(s.distance_m), 3)                                            AS min_distance_m
FROM fact_missions m
JOIN fact_safety_events s ON m.mission_id = s.mission_id
GROUP BY m.site_id, s.event_type, s.severity
ORDER BY m.site_id, event_count DESC;
