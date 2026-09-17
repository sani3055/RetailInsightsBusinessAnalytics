import duckdb
import os

print("Connecting to DuckDB...")
db_path = 'retailpulse.duckdb'
if os.path.exists(db_path):
    os.remove(db_path) # Fresh start

con = duckdb.connect(db_path)

# Create Schemas
con.execute("CREATE SCHEMA IF NOT EXISTS raw")
con.execute("CREATE SCHEMA IF NOT EXISTS staging")
con.execute("CREATE SCHEMA IF NOT EXISTS curated")

# 1. Load Raw Data
print("Loading raw CSVs into 'raw' schema...")
tables = [
    "olist_customers_dataset",
    "olist_geolocation_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_orders_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "product_category_name_translation"
]

for table in tables:
    con.execute(f"CREATE TABLE raw.{table} AS SELECT * FROM read_csv_auto('data/{table}.csv', ignore_errors=true)")

# 2. Transform into Staging
print("Cleaning data and loading into 'staging' schema...")

# Orders: Handle timestamps correctly
con.execute("""
    CREATE TABLE staging.stg_orders AS 
    SELECT 
        order_id, customer_id, order_status, 
        TRY_CAST(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
        TRY_CAST(order_approved_at AS TIMESTAMP) AS order_approved_at,
        TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS order_delivered_carrier_date,
        TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
        TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date
    FROM raw.olist_orders_dataset
""")

# Reviews: Deduplicate on review_id
# DuckDB doesn't support DISTINCT ON, we use ROW_NUMBER() window function
con.execute("""
    CREATE TABLE staging.stg_reviews AS 
    SELECT * EXCLUDE(rn) FROM (
        SELECT *, ROW_NUMBER() OVER(PARTITION BY review_id ORDER BY review_creation_date DESC) as rn
        FROM raw.olist_order_reviews_dataset
    ) WHERE rn = 1
""")

# Items: Ensure types
con.execute("""
    CREATE TABLE staging.stg_order_items AS 
    SELECT 
        order_id, order_item_id, product_id, seller_id, 
        TRY_CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_date,
        CAST(price AS DOUBLE) AS price, 
        CAST(freight_value AS DOUBLE) AS freight_value
    FROM raw.olist_order_items_dataset
""")

# Customers, Products, Sellers (pass-through for now)
con.execute("CREATE TABLE staging.stg_customers AS SELECT * FROM raw.olist_customers_dataset")
con.execute("CREATE TABLE staging.stg_products AS SELECT * FROM raw.olist_products_dataset")
con.execute("CREATE TABLE staging.stg_sellers AS SELECT * FROM raw.olist_sellers_dataset")
con.execute("CREATE TABLE staging.stg_payments AS SELECT * FROM raw.olist_order_payments_dataset")

print("Phase 1 & 2 completed successfully! Local Data Warehouse is ready.")
