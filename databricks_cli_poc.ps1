$ErrorActionPreference = "Stop"

$env:DATABRICKS_HOST = "https://dbc-c826d0ff-d953.cloud.databricks.com"
$env:DATABRICKS_TOKEN = "<YOUR_TOKEN>"
$warehouseId = "9dced3754115277d"

Write-Host "--- Databricks CLI Authentication ---"
.\databricks.exe auth auth-info

Write-Host "`n--- Creating Tables in Serverless SQL Warehouse ---"
# Databricks SQL API requires statements to be executed one at a time.
$queries = @(
    "CREATE OR REPLACE TABLE workspace.default.stg_customers AS SELECT * FROM read_files('/Volumes/workspace/default/retailpulse/stg_customers.csv', format => 'csv', header => true)",
    "CREATE OR REPLACE TABLE workspace.default.stg_orders AS SELECT * FROM read_files('/Volumes/workspace/default/retailpulse/stg_orders.csv', format => 'csv', header => true)",
    "CREATE OR REPLACE TABLE workspace.default.stg_order_items AS SELECT * FROM read_files('/Volumes/workspace/default/retailpulse/stg_order_items.csv', format => 'csv', header => true)"
)

$i = 1
foreach ($q in $queries) {
    Write-Host "Running Query $i..."
    $payload = @{
        warehouse_id = $warehouseId
        statement = $q
        wait_timeout = "50s"
    } | ConvertTo-Json
    [IO.File]::WriteAllText("$PWD\temp_query.json", $payload)
    
    $out = .\databricks.exe api post /api/2.0/sql/statements --json "@temp_query.json" | ConvertFrom-Json
    if ($out.status.state -eq "FAILED") {
        Write-Error "Query failed: $($out.status.error.message)"
    }
    $i++
}
Write-Host "Tables created successfully."

Write-Host "`n--- Executing RFM Segmentation Query via CLI ---"
$rfm_sql = @"
WITH rfm_base AS (
    SELECT 
        c.customer_unique_id,
        MAX(o.order_purchase_timestamp) AS last_purchase_date,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(i.price) AS monetary
    FROM workspace.default.stg_customers c
    JOIN workspace.default.stg_orders o ON c.customer_id = o.customer_id
    JOIN workspace.default.stg_order_items i ON o.order_id = i.order_id
    GROUP BY c.customer_unique_id
),
rfm_calc AS (
    SELECT 
        customer_unique_id,
        DATEDIFF(last_purchase_date, (SELECT MAX(order_purchase_timestamp) FROM workspace.default.stg_orders)) * -1 AS recency,
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
FROM rfm_calc
LIMIT 10;
"@

$rfmJson = @{
    warehouse_id = $warehouseId
    statement = $rfm_sql
    wait_timeout = "50s"
} | ConvertTo-Json

[IO.File]::WriteAllText("$PWD\rfm_query.json", $rfmJson)

$output = .\databricks.exe api post /api/2.0/sql/statements --json "@rfm_query.json"
[IO.File]::WriteAllText("$PWD\databricks_rfm_output.json", $output)

$parsed = $output | ConvertFrom-Json
if ($parsed.status.state -eq "SUCCEEDED") {
    Write-Host "Query completed! Raw JSON output saved to databricks_rfm_output.json"
    Write-Host "`n--- Proof-of-Concept Complete! ---"
} else {
    Write-Error "RFM Query Failed: $($parsed.status.error.message)"
}
