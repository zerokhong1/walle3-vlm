-- ROI estimation by site from operational telemetry
-- Business question: Is the robot creating measurable value? What is the payback signal?
-- Note: Labor cost assumptions are portfolio estimates — validate with real site data.
--
-- Assumptions (align with docs/product/17_roi_tco_one_pager.md):
--   Manual task time:  avg 8 min per locate-and-fetch task
--   Robot mission time: from fact_missions.duration_s (avg ~90s)
--   Labor rate: $6 USD/hr (Vietnam warehouse operator)
--   Tasks per operator per day: 40
--   Operator FTEs supported per robot: 2

WITH mission_stats AS (
    SELECT
        site_id,
        DATE(start_ts)                                                     AS mission_date,
        COUNT(*)                                                           AS total_missions,
        SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END)              AS successful_missions,
        ROUND(AVG(duration_s), 1)                                         AS avg_robot_duration_s
    FROM fact_missions
    GROUP BY site_id, DATE(start_ts)
),
labor_savings AS (
    SELECT
        site_id,
        mission_date,
        total_missions,
        successful_missions,
        avg_robot_duration_s,
        -- Time saved per successful mission (manual 480s vs robot avg)
        ROUND((480 - avg_robot_duration_s) * successful_missions / 3600.0, 2)
                                                                          AS hours_saved,
        -- Dollar savings at $6/hr
        ROUND((480 - avg_robot_duration_s) * successful_missions / 3600.0 * 6, 2)
                                                                          AS daily_labor_savings_usd
    FROM mission_stats
)
SELECT
    site_id,
    mission_date,
    total_missions,
    successful_missions,
    avg_robot_duration_s,
    hours_saved,
    daily_labor_savings_usd,
    -- Annualized projection (250 working days)
    ROUND(daily_labor_savings_usd * 250, 0)                               AS projected_annual_savings_usd
FROM labor_savings
ORDER BY site_id, mission_date;

-- Payback summary (assuming robot cost = $12,000 USD)
SELECT
    site_id,
    ROUND(AVG(daily_labor_savings_usd) * 250, 0)                          AS projected_annual_savings_usd,
    ROUND(12000.0 / (AVG(daily_labor_savings_usd) * 250) * 12, 1)         AS estimated_payback_months
FROM labor_savings
GROUP BY site_id;
