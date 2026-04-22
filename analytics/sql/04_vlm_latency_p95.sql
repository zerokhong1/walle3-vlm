-- VLM inference latency percentiles
-- Business question: Is the AI inference fast enough? Where are the outliers?
-- KPI: VLM Inference Latency — p50 ≤10s, p95 ≤15s (NFR-002, RTX 3060 target)

-- Basic stats by site
SELECT
    site_id,
    COUNT(*)                                                               AS inference_count,
    ROUND(AVG(latency_ms), 0)                                             AS avg_latency_ms,
    ROUND(MIN(latency_ms), 0)                                             AS min_latency_ms,
    ROUND(MAX(latency_ms), 0)                                             AS max_latency_ms,
    SUM(CASE WHEN output_valid = 'false' THEN 1 ELSE 0 END)               AS invalid_outputs,
    ROUND(
        100.0 * SUM(CASE WHEN output_valid = 'false' THEN 1 ELSE 0 END)
        / COUNT(*), 1
    )                                                                      AS invalid_pct
FROM fact_inference_events
GROUP BY site_id;

-- Latency distribution buckets (≤9s / 9-11s / 11-15s / >15s)
SELECT
    CASE
        WHEN latency_ms <= 9000            THEN '≤9s (fast)'
        WHEN latency_ms <= 11000           THEN '9-11s (normal)'
        WHEN latency_ms <= 15000           THEN '11-15s (slow)'
        ELSE '>15s (outlier)'
    END                                                                    AS latency_bucket,
    COUNT(*)                                                               AS inference_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                    AS pct_of_total
FROM fact_inference_events
WHERE output_valid = 'true'
GROUP BY latency_bucket
ORDER BY MIN(latency_ms);

-- Confidence vs latency correlation
-- High latency + low confidence = model struggling (candidate for fallback)
SELECT
    CASE
        WHEN confidence < 0.40             THEN '<0.40 (low)'
        WHEN confidence < 0.70             THEN '0.40-0.70 (medium)'
        ELSE '≥0.70 (high)'
    END                                                                    AS confidence_band,
    ROUND(AVG(latency_ms), 0)                                             AS avg_latency_ms,
    COUNT(*)                                                               AS count,
    SUM(CASE WHEN target_found = 'true' THEN 1 ELSE 0 END)                AS target_found_count
FROM fact_inference_events
WHERE output_valid = 'true'
GROUP BY confidence_band
ORDER BY MIN(confidence);
