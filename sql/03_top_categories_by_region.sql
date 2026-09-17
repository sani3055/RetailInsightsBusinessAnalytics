-- Business Question: Which product categories drive the most revenue in each state?
WITH regional_sales AS (
    SELECT 
        c.customer_state,
        p.product_category_name,
        SUM(i.price) as total_revenue,
        COUNT(i.order_item_id) as total_items_sold
    FROM staging.stg_orders o
    JOIN staging.stg_customers c ON o.customer_id = c.customer_id
    JOIN staging.stg_order_items i ON o.order_id = i.order_id
    JOIN staging.stg_products p ON i.product_id = p.product_id
    WHERE p.product_category_name IS NOT NULL
    GROUP BY 1, 2
),
ranked_sales AS (
    SELECT 
        customer_state,
        product_category_name,
        total_revenue,
        RANK() OVER (PARTITION BY customer_state ORDER BY total_revenue DESC) as category_rank
    FROM regional_sales
)
SELECT * FROM ranked_sales WHERE category_rank <= 3;
