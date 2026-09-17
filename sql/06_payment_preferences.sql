-- Business Question: How do payment preferences change based on the total order value?
WITH order_totals AS (
    SELECT 
        o.order_id,
        SUM(p.payment_value) as total_order_value,
        MAX(p.payment_type) as primary_payment_type
    FROM staging.stg_orders o
    JOIN staging.stg_payments p ON o.order_id = p.order_id
    GROUP BY 1
),
bucketed_orders AS (
    SELECT 
        order_id,
        primary_payment_type,
        CASE 
            WHEN total_order_value < 50 THEN 'Low (<$50)'
            WHEN total_order_value BETWEEN 50 AND 200 THEN 'Medium ($50-$200)'
            ELSE 'High (>$200)'
        END AS order_value_tier
    FROM order_totals
)
SELECT 
    order_value_tier,
    primary_payment_type,
    COUNT(order_id) as num_orders
FROM bucketed_orders
GROUP BY 1, 2
ORDER BY order_value_tier, num_orders DESC;
