# Updated Databricks PySpark Data Cleaning Script - Phase 1

from pyspark.sql.functions import col, to_timestamp

# Instead of relying on the UI to create the tables, we will read the raw CSV files directly 
# from the default Databricks storage location where drag-and-drop files go.

def read_raw_csv(file_name):
    return spark.read.format("csv") \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .load(f"dbfs:/FileStore/tables/{file_name}")

# 1. Load Raw Data
orders_raw = read_raw_csv("olist_orders_dataset.csv")
reviews_raw = read_raw_csv("olist_order_reviews_dataset.csv")
items_raw = read_raw_csv("olist_order_items_dataset.csv")

# 2. Clean Orders Table
# Issue: Missing delivery dates for canceled/unavailable orders. 
# Strategy: Cast strings to timestamps so date math works later.
orders_clean = orders_raw \
    .withColumn("order_purchase_timestamp", to_timestamp("order_purchase_timestamp")) \
    .withColumn("order_delivered_customer_date", to_timestamp("order_delivered_customer_date")) \
    .withColumn("order_estimated_delivery_date", to_timestamp("order_estimated_delivery_date"))

# 3. Clean Reviews Table
# Issue: Duplicate review IDs exist. Strategy: Deduplicate.
reviews_clean = reviews_raw.dropDuplicates(["review_id"])

# 4. Clean Order Items Table
# Strategy: Ensure numeric types are correct
items_clean = items_raw \
    .withColumn("price", col("price").cast("double")) \
    .withColumn("freight_value", col("freight_value").cast("double"))

# 5. Create our schema (database) directly via code to guarantee it exists
spark.sql("CREATE DATABASE IF NOT EXISTS retailpulse")

# 6. Save Cleaned Data back as "staging" tables
orders_clean.write.mode("overwrite").saveAsTable("retailpulse.stg_orders")
reviews_clean.write.mode("overwrite").saveAsTable("retailpulse.stg_reviews")
items_clean.write.mode("overwrite").saveAsTable("retailpulse.stg_order_items")

display(spark.sql("SHOW TABLES IN retailpulse"))
