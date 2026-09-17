import duckdb
import os

print("Exporting staging tables from DuckDB to CSV for Databricks upload...")
os.makedirs('data/export', exist_ok=True)
con = duckdb.connect('retailpulse.duckdb')

tables = ['stg_customers', 'stg_orders', 'stg_order_items']
for t in tables:
    con.execute(f"COPY staging.{t} TO 'data/export/{t}.csv' (HEADER, DELIMITER ',')")
    print(f"Exported {t}.csv successfully.")
