-- Business Question: What does revenue growth look like over time, and is it accelerating or slowing?
WITH monthly_revenue AS (
    SELECT 
        date_trunc('month', o.order_purchase_timestamp) AS order_month,
        SUM(i.price + i.freight_value) AS total_revenue
    FROM staging.stg_orders o
    JOIN staging.stg_order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp >= '2017-01-01'
    GROUP BY 1
)
SELECT 
    order_month,
    total_revenue,
    LAG(total_revenue) OVER (ORDER BY order_month) AS prev_month_revenue,
    (total_revenue - LAG(total_revenue) OVER (ORDER BY order_month)) / 
        LAG(total_revenue) OVER (ORDER BY order_month) * 100 AS mom_growth_pct
FROM monthly_revenue
ORDER BY order_month;
