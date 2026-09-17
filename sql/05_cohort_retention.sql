-- Business Question: Where are we losing customers (retention drop-off month over month)?
WITH first_purchases AS (
    SELECT 
        c.customer_unique_id,
        date_trunc('month', MIN(o.order_purchase_timestamp)) AS cohort_month
    FROM staging.stg_customers c
    JOIN staging.stg_orders o ON c.customer_id = o.customer_id
    GROUP BY 1
),
subsequent_purchases AS (
    SELECT 
        c.customer_unique_id,
        date_trunc('month', o.order_purchase_timestamp) AS order_month
    FROM staging.stg_customers c
    JOIN staging.stg_orders o ON c.customer_id = o.customer_id
)
SELECT 
    f.cohort_month,
    DATE_DIFF('month', f.cohort_month, s.order_month) AS month_number,
    COUNT(DISTINCT s.customer_unique_id) AS active_customers
FROM first_purchases f
JOIN subsequent_purchases s ON f.customer_unique_id = s.customer_unique_id
GROUP BY 1, 2
ORDER BY 1, 2;
