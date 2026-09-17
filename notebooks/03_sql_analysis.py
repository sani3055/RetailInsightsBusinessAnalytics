import duckdb
import os
import re

print("Starting Phase 3: SQL Analysis...")
db_path = '../retailpulse.duckdb'
con = duckdb.connect(db_path)

# Ensure output directories exist
os.makedirs('../sql', exist_ok=True)
os.makedirs('../dashboard/data', exist_ok=True)

con.execute("CREATE SCHEMA IF NOT EXISTS curated")

queries = {
    "01_mom_revenue_growth": """
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
""",
    "02_customer_rfm": """
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
""",
    "03_top_categories_by_region": """
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
""",
    "04_delivery_delay_analysis": """
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
""",
    "05_cohort_retention": """
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
""",
    "06_payment_preferences": """
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
"""
}

for name, query in queries.items():
    # 1. Write the .sql file for the portfolio
    with open(f"../sql/{name}.sql", "w") as f:
        f.write(query.strip() + "\n")
    
    print(f"Executing {name}...")
    
    # 2. Execute query and create a table in the curated schema
    table_name = re.sub(r'^\d+_', '', name)
    con.execute(f"CREATE OR REPLACE TABLE curated.{table_name} AS {query}")
    
    # 3. Export the results to a CSV so Power BI can easily digest it
    con.execute(f"COPY (SELECT * FROM curated.{table_name}) TO '../dashboard/data/{name}.csv' WITH (HEADER 1, DELIMITER ',')")

print("Phase 3 complete! SQL queries written to /sql, tables created in curated schema, and exported to /dashboard/data for PowerBI.")
