-- Business Question: Where are the biggest operational inefficiencies (delivery delays by state)?
WITH delay_calc AS (
    SELECT 
        o.order_id,
        c.customer_state,
        o.order_estimated_delivery_date,
        o.order_delivered_customer_date,
        DATE_DIFF('day', o.order_estimated_delivery_date, o.order_delivered_customer_date) AS delay_days
    FROM staging.stg_orders o
    JOIN staging.stg_customers c ON o.customer_id = c.customer_id
    WHERE o.order_delivered_customer_date IS NOT NULL
)
SELECT 
    customer_state,
    COUNT(order_id) AS total_orders,
    SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) AS delayed_orders,
    AVG(delay_days) AS avg_delay_days,
    (SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(order_id)) AS pct_delayed
FROM delay_calc
GROUP BY customer_state
ORDER BY pct_delayed DESC;
