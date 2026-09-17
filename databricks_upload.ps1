$ErrorActionPreference = "Stop"

# 1. Download and extract Databricks CLI
if (-not (Test-Path "databricks.exe")) {
    Write-Host "Downloading Databricks CLI..."
    Invoke-WebRequest -Uri "https://github.com/databricks/cli/releases/download/v0.223.0/databricks_cli_windows_x86_64.zip" -OutFile "databricks.zip"
    Expand-Archive -Path "databricks.zip" -DestinationPath "." -Force
}

$env:DATABRICKS_HOST = "https://dbc-c826d0ff-d953.cloud.databricks.com"
$env:DATABRICKS_TOKEN = "<YOUR_TOKEN>"

Write-Host "Verifying Databricks CLI Auth..."
.\databricks.exe auth auth-info

# 2. Upload CSVs to DBFS
Write-Host "Uploading exported data to DBFS..."
.\databricks.exe fs mkdirs dbfs:/retailpulse_poc/
.\databricks.exe fs cp data/export/stg_customers.csv dbfs:/retailpulse_poc/stg_customers.csv --overwrite
.\databricks.exe fs cp data/export/stg_orders.csv dbfs:/retailpulse_poc/stg_orders.csv --overwrite
.\databricks.exe fs cp data/export/stg_order_items.csv dbfs:/retailpulse_poc/stg_order_items.csv --overwrite

Write-Host "Data upload complete! Ready for SQL execution."
