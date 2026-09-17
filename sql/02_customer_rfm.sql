-- Business Question: Who are our best customers, and who is at risk of churning?
WITH rfm_base AS (
    SELECT 
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_purchase_date,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(i.price) AS monetary
    FROM staging.stg_customers c
    JOIN staging.stg_orders o ON c.customer_id = o.customer_id
    JOIN staging.stg_order_items i ON o.order_id = i.order_id
    GROUP BY c.customer_unique_id
),
rfm_calc AS (
    SELECT 
        customer_unique_id,
        DATE_DIFF('day', last_purchase_date, (SELECT MAX(order_purchase_timestamp) FROM staging.stg_orders)) AS recency,
        frequency,
        monetary
    FROM rfm_base
)
SELECT 
    customer_unique_id,
    recency,
    frequency,
    monetary,
    NTILE(4) OVER (ORDER BY recency ASC) AS r_score,
    NTILE(4) OVER (ORDER BY frequency DESC) AS f_score,
    NTILE(4) OVER (ORDER BY monetary DESC) AS m_score
FROM rfm_calc;
