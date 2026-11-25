-- Snowflake transformation: dealer bonus gold table.
--
-- Stages: raw staging -> silver (validated, deduplicated) -> gold
-- (one row per dealer per quarter, with tier, variable-payment
-- estimate, and a trend flag against the same quarter last year).
--
-- IMPORTANT: the thresholds and rates below must match config.yaml
-- (tiers.platinum_min_units / gold_min_units, variable_payment_per_unit,
-- trend_threshold_pct). The Python package in src/incentive_analytics
-- is the runnable mirror of this SQL and is what the tests exercise;
-- this file is the Snowflake form of the same logic, for a warehouse
-- that has the silver table loaded. All values are synthetic; the
-- payment rates are illustrative demo parameters, not real bonus rates.

-- Silver: keep the first occurrence of each transaction, drop rows
-- that fail the schema checks (nulls, bad quarter format, negative
-- units). Rejected rows belong in a quarantine table, not in silver.
CREATE OR REPLACE TABLE silver_dealer_sales AS
SELECT transaction_id, dealer_id, quarter, units
FROM (
    SELECT
        transaction_id,
        dealer_id,
        quarter,
        units,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_id ORDER BY transaction_id
        ) AS rn
    FROM staging_dealer_sales
    WHERE transaction_id IS NOT NULL
      AND dealer_id REGEXP '^D[0-9]{2}$'
      AND quarter REGEXP '^[0-9]{4}Q[1-4]$'
      AND units IS NOT NULL
      AND units >= 0
)
WHERE rn = 1;

-- Gold: quarterly totals, tier, variable-payment estimate, trend flag.
CREATE OR REPLACE TABLE gold_dealer_bonus AS
WITH quarterly AS (
    SELECT
        dealer_id,
        quarter,
        SUM(units) AS units
    FROM silver_dealer_sales
    GROUP BY dealer_id, quarter
),
with_prior_year AS (
    SELECT
        q.dealer_id,
        q.quarter,
        q.units,
        p.units AS prior_year_units
    FROM quarterly q
    LEFT JOIN quarterly p
        ON p.dealer_id = q.dealer_id
        AND p.quarter = (
            (CAST(SUBSTRING(q.quarter, 1, 4) AS INTEGER) - 1)
            || 'Q' || SUBSTRING(q.quarter, 6, 1)
        )
)
SELECT
    dealer_id,
    quarter,
    units,
    CASE
        WHEN units >= 500 THEN 'Platinum'
        WHEN units >= 250 THEN 'Gold'
        ELSE 'Standard'
    END AS bonus_tier,
    units * CASE
        WHEN units >= 500 THEN 150
        WHEN units >= 250 THEN 100
        ELSE 50
    END AS variable_payment_estimate,
    CASE
        WHEN prior_year_units IS NULL THEN 'no_baseline'
        WHEN prior_year_units = 0 AND units > 0 THEN 'improving'
        WHEN prior_year_units = 0 THEN 'flat'
        WHEN (units - prior_year_units) / prior_year_units > 0.05 THEN 'improving'
        WHEN (units - prior_year_units) / prior_year_units < -0.05 THEN 'declining'
        ELSE 'flat'
    END AS trend_flag,
    prior_year_units
FROM with_prior_year
ORDER BY dealer_id, quarter;
