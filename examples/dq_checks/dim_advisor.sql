-- DQ golden checks for dim_advisor
--
-- Each check returns 1 (pass) or 0 (fail).
-- A fail blocks promotion to the reporting layer.
-- Check types: duplicate, null, reconciliation.
-- Anonymized — table and column names are illustrative placeholders.

-- CHECK: no duplicate business keys (advisor_id + data_region must be unique)
SELECT
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS check_result
FROM (
    SELECT advisor_id, data_region, COUNT(*) AS cnt
    FROM analytics_mart.dim_advisor
    WHERE run_date = CURRENT_DATE
    GROUP BY advisor_id, data_region
    HAVING cnt > 1
) dupes;

-- CHECK: required columns are non-null
SELECT
    CASE
        WHEN SUM(
            CASE WHEN advisor_id IS NULL
                   OR employee_id IS NULL
                   OR full_name IS NULL
                   OR status IS NULL
                THEN 1 ELSE 0
            END
        ) = 0 THEN 1
        ELSE 0
    END AS check_result
FROM analytics_mart.dim_advisor
WHERE run_date = CURRENT_DATE;

-- CHECK: row count reconciliation — target must be within 5% of source active advisors
SELECT
    CASE
        WHEN ABS(target_count - source_count) * 1.0 / NULLIF(source_count, 0) <= 0.05
        THEN 1 ELSE 0
    END AS check_result
FROM (
    SELECT
        (SELECT COUNT(*) FROM analytics_mart.dim_advisor
          WHERE run_date = CURRENT_DATE AND status = 'active')  AS target_count,
        (SELECT COUNT(*) FROM source_prod.advisors_raw
          WHERE status = 'active')                              AS source_count
) recon;
