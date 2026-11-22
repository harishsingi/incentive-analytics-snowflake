-- Snowflake transformation sketch: tier dealers by quarterly units vs historic pattern
SELECT dealer_id, quarter, SUM(units) AS units, CASE WHEN SUM(units)>=500 THEN 'Platinum' WHEN SUM(units)>=250 THEN 'Gold' ELSE 'Standard' END AS bonus_tier FROM silver_dealer_sales GROUP BY dealer_id, quarter;
