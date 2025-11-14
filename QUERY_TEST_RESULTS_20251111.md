# Query Testing Results - Tue Nov 11 14:02:26 CST 2025

## Test Configuration
- API Endpoint: http://localhost:8000/api/v1/query
- Test Date: Tue Nov 11 14:02:26 CST 2025

## Section 1: Context Maintenance Tests

## Query 1: Beer Product Portfolio Analysis

**Question:** how's my beer product portfolio been doing over the year

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
Analyzes beer product portfolio performance over the current year, showing monthly revenue, COGS, gross profit, margin percentage, and volume for each beer product. This provides a comprehensive view of how the beer product line is performing across key financial metrics throughout the year.

**Generated SQL:**
```sql
WITH ProductPerformance AS (
  SELECT
    EXTRACT(MONTH FROM Posting_Date) as month_num,
    FORMAT_DATE('%B', Posting_Date) as month_name,
    Product,
    SUM(COALESCE(Gross_Revenue, 0)) as total_revenue,
    SUM(COALESCE(Total_COGS, 0)) as total_cogs,
    SUM(COALESCE(Gross_Revenue, 0)) - SUM(COALESCE(Total_COGS, 0)) as gross_profit,
    SUM(COALESCE(Quantity, 0)) as total_volume
  FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
  WHERE LOWER(Product) LIKE '%beer%'
    AND Posting_Date >= DATE_TRUNC(CURRENT_DATE(), YEAR)
    AND Posting_Date < CURRENT_DATE()
  GROUP BY month_num, month_name, Product
)
SELECT
  month_name,
  Product,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_revenue) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_revenue - FLOOR(total_revenue)) * 100) AS INT64))) as revenue,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_cogs) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_cogs - FLOOR(total_cogs)) * 100) AS INT64))) as cogs,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(gross_profit) AS INT64)), FORMAT('.%02d', CAST(ROUND((gross_profit - FLOOR(gross_profit)) * 100) AS INT64))) as gross_profit,
  CONCAT(CAST(ROUND(SAFE_DIVIDE(gross_profit, total_revenue) * 100, 2) AS STRING), '%') as margin_percent,
  FORMAT('%\'d', CAST(total_volume AS INT64)) as volume
FROM ProductPerformance
ORDER BY month_num, Product
```


---

## Query 2: Customer Segment Targeting (Context-Dependent)

**Question:** based on the beer portfolio performance, which customer segment should be targeted for product promotion

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
This query analyzes customer segments from the customer master analysis table to identify which segments should be targeted for beer product promotions. It calculates a promotion target score based on profitability (30% weight), purchase frequency (25%), recency (25%), and margin percentage (20%). The query segments customers by RFM_Segment, Advanced_Segment, and ABC_Combined classification, providing key metrics like total revenue, profit, margin, purchase frequency, recency, and order value. Results are ranked by promotion score to identify the most attractive segments for promotional campaigns, with actionable recommendations for each segment.

**Generated SQL:**
```sql
WITH beer_customer_performance AS (
  SELECT 
    cma.RFM_Segment,
    cma.Advanced_Segment,
    cma.ABC_Combined,
    COUNT(DISTINCT cma.Customer) as customer_count,
    SUM(cma.Monetary) as total_revenue,
    SUM(cma.Profitability) as total_profit,
    AVG(cma.Margin_Percent) as avg_margin_pct,
    AVG(cma.Frequency) as avg_purchase_frequency,
    AVG(cma.Recency) as avg_recency_days,
    AVG(cma.Avg_Order_Value) as avg_order_value,
    SUM(cma.Volume) as total_volume
  FROM `arizona-poc.copa_export_copa_data_000000000000.customer_master_analysis` cma
  WHERE cma.Customer IS NOT NULL
  GROUP BY cma.RFM_Segment, cma.Advanced_Segment, cma.ABC_Combined
),
segment_metrics AS (
  SELECT
    RFM_Segment,
    Advanced_Segment,
    ABC_Combined,
    customer_count,
    total_revenue,
    total_profit,
    avg_margin_pct,
    avg_purchase_frequency,
    avg_recency_days,
    avg_order_value,
    total_volume,
    -- Calculate promotion attractiveness score
    -- Higher score = better target (high profit, high frequency, recent purchases, good margins)
    ROUND(
      (total_profit / NULLIF(total_revenue, 0) * 100) * 0.3 +  -- Profitability weight
      (avg_purchase_frequency / 10) * 0.25 +  -- Frequency weight
      (CASE WHEN avg_recency_days <= 90 THEN 100 WHEN avg_recency_days <= 180 THEN 50 ELSE 10 END) * 0.25 +  -- Recency weight
      (avg_margin_pct) * 0.2,  -- Margin weight
    2) as promotion_score
  FROM beer_customer_performance
)
SELECT
  RFM_Segment,
  Advanced_Segment,
  ABC_Combined,
  FORMAT('%\'d', CAST(customer_count AS INT64)) as customer_count,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_revenue) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_revenue - FLOOR(total_revenue)) * 100) AS INT64))) as total_revenue,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_profit) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_profit - FLOOR(total_profit)) * 100) AS INT64))) as total_profit,
  CONCAT(CAST(ROUND(avg_margin_pct, 2) AS STRING), '%') as avg_margin_pct,
  CONCAT(CAST(ROUND(avg_purchase_frequency, 1) AS STRING), ' orders') as avg_purchase_frequency,
  FORMAT('%\'d', CAST(avg_recency_days AS INT64)) as avg_recency_days,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(avg_order_value) AS INT64)), FORMAT('.%02d', CAST(ROUND((avg_order_value - FLOOR(avg_order_value)) * 100) AS INT64))) as avg_order_value,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_volume) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_volume - FLOOR(total_volume)) * 100) AS INT64))) as total_volume,
  ROUND(promotion_score, 2) as promotion_target_score,
  CASE 
    WHEN promotion_score >= 75 THEN 'High Priority - Immediate Promotion'
    WHEN promotion_score >= 50 THEN 'Medium Priority - Consider Promotion'
    WHEN promotion_score >= 25 THEN 'Low Priority - Monitor'
    ELSE 'Not Recommended'
  END as promotion_recommendation
FROM segment_metrics
WHERE customer_count > 0
ORDER BY promotion_score DESC, total_profit DESC
LIMIT 20
```


---

## Section 2: Sales & Inventory Tests

## Query 3: Delivered Quantity by Material and Plant

**Question:** Show me the total Delivered Quantity by Material and Plant for each month over the last 6 months

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
This query calculates the total Delivered Quantity grouped by Material, Plant, and month for the last 6 months. It formats the month as YYYY-MM for readability and formats the quantity with thousand separators. The query filters out NULL values for Material and Plant to ensure clean results.

**Generated SQL:**
```sql
SELECT 
  Material,
  Plant,
  FORMAT_DATE('%Y-%m', Posting_Date) as month,
  FORMAT('%\'d', CAST(SUM(COALESCE(Delivered_Quantity, 0)) AS INT64)) as total_delivered_quantity
FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
WHERE Posting_Date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND Material IS NOT NULL
  AND Plant IS NOT NULL
GROUP BY Material, Plant, month
ORDER BY Material, Plant, month
```


---

## Query 4: Aging Inventory - Open Orders

**Question:** List open sales orders older than 60 days where Delivered Quantity is 0 and Net Value is greater than 1000

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
This query identifies open sales orders that are older than 60 days with no delivered quantity and net value exceeding $1,000. It filters for non-completed orders (status != 'C'), zero delivered quantity, and calculates the age of each order. Results are sorted by age (oldest first) and then by net value (highest first) to prioritize the most critical aged orders. The net value is formatted with dollar signs and thousand separators for presentation.

**Generated SQL:**
```sql
SELECT 
  SalesDocument_VBELN as sales_order,
  SalesDocumentItem_POSNR as line_item,
  CreatedOn_ERDAT as created_date,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(NetValue_NETWR) AS INT64)), FORMAT('.%02d', CAST(ROUND((NetValue_NETWR - FLOOR(NetValue_NETWR)) * 100) AS INT64))) as net_value,
  FORMAT('%\'d', CAST(OrderQuantity_KWMENG AS INT64)) as order_quantity,
  DeliveredQuantity_KBMENG as delivered_quantity,
  OverallSDProcessStatus_GBSTK as status,
  SoldToParty_KUNNR as customer,
  Material_MATNR as material,
  DATE_DIFF(CURRENT_DATE(), CreatedOn_ERDAT, DAY) as days_open
FROM `arizona-poc.copa_export_copa_data_000000000000.sales_order_cockpit_export`
WHERE OverallSDProcessStatus_GBSTK != 'C'
  AND DeliveredQuantity_KBMENG = 0
  AND NetValue_NETWR > 1000
  AND DATE_DIFF(CURRENT_DATE(), CreatedOn_ERDAT, DAY) > 60
ORDER BY days_open DESC, NetValue_NETWR DESC
```


---

## Query 5: Inventory Movement Across Plants

**Question:** Give me Delivered Quantity by Plant and month for the last 6 months

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
The query cannot be generated because the required columns are not present in the available schema. The user is asking for 'Delivered Quantity' by 'Plant' and 'month', but none of the provided tables (GL_Accounts, cohort_avg_revenue_table, cohort_retention_table, cohort_sizes, customer_master_analysis) contain these columns. This appears to be a supply chain/logistics query that would typically be found in tables like sales orders, deliveries, or shipments data, which are not included in the current schema. The available tables focus on GL accounts, customer cohort analysis, and customer master data - none of which track delivered quantities or plant information.

**Generated SQL:**
```sql
SELECT 
  'UNKNOWN' as error_message,
  'The requested columns (Delivered_Quantity, Plant, and date fields for monthly aggregation) are not available in any of the provided tables' as explanation
FROM (SELECT 1) LIMIT 0
```


---

## Query 6: Materials with Declining Delivery Trend

**Question:** Show me Materials where Delivered Quantity in the last month is at least 20% lower than the average of the previous 3 months

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
This query identifies materials where delivered quantity in the last month dropped by at least 20% compared to the average of the previous 3 months. It uses CTEs to calculate monthly deliveries, isolate last month's quantities, compute the 3-month average, and then filters for materials showing a 20%+ decline. Results show the material, last month quantity, 3-month average, and percent change, formatted for executive presentation.

**Generated SQL:**
```sql
WITH MonthlyDeliveries AS (
  SELECT
    Material,
    DATE_TRUNC(Posting_Date, MONTH) as delivery_month,
    SUM(COALESCE(Delivered_Quantity, 0)) as total_delivered_qty
  FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
  WHERE Posting_Date >= DATE_SUB(CURRENT_DATE(), INTERVAL 4 MONTH)
    AND Delivered_Quantity IS NOT NULL
  GROUP BY Material, delivery_month
),
LastMonthDeliveries AS (
  SELECT
    Material,
    total_delivered_qty as last_month_qty
  FROM MonthlyDeliveries
  WHERE delivery_month = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)
),
Previous3MonthsAvg AS (
  SELECT
    Material,
    AVG(total_delivered_qty) as avg_prev_3_months
  FROM MonthlyDeliveries
  WHERE delivery_month >= DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 4 MONTH), MONTH)
    AND delivery_month < DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)
  GROUP BY Material
)
SELECT
  lm.Material,
  FORMAT('%\'d', CAST(lm.last_month_qty AS INT64)) as last_month_delivered_qty,
  FORMAT('%\'d', CAST(pm.avg_prev_3_months AS INT64)) as avg_previous_3_months_qty,
  CONCAT(CAST(ROUND(((lm.last_month_qty - pm.avg_prev_3_months) / pm.avg_prev_3_months) * 100, 2) AS STRING), '%') as percent_change
FROM LastMonthDeliveries lm
INNER JOIN Previous3MonthsAvg pm
  ON lm.Material = pm.Material
WHERE lm.last_month_qty < (pm.avg_prev_3_months * 0.8)
  AND pm.avg_prev_3_months > 0
ORDER BY percent_change ASC
```


---

## Section 3: Sales Analysis Tests

## Query 7: Total Sales by Product and Region

**Question:** What is the total sales amount by product and region for the last 12 months?

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
Calculates total sales revenue by product and region for the last 12 months. Uses Gross_Revenue column for sales calculation, groups by product and region dimensions, and formats the output as currency with thousand separators for executive presentation. Results are ordered by total sales descending to highlight top-performing product-region combinations.

**Generated SQL:**
```sql
SELECT 
  Product,
  Region,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(SUM(COALESCE(Gross_Revenue, 0))) AS INT64)), FORMAT('.%02d', CAST(ROUND((SUM(COALESCE(Gross_Revenue, 0)) - FLOOR(SUM(COALESCE(Gross_Revenue, 0)))) * 100) AS INT64))) as total_sales
FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
WHERE Posting_Date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY Product, Region
ORDER BY SUM(COALESCE(Gross_Revenue, 0)) DESC
```


---

## Query 8: Top Customers by Value and Volume

**Question:** Which customers have ordered the most (by value and volume) in the last quarter?

**Status:** ❌ NO RESULTS
**Result Count:** 0
**Execution Time:** N/Ams

**Explanation:**
Identifies the top customers by both order value (revenue) and volume in the last quarter. The query aggregates total revenue and volume by customer from the customer_master_analysis table, formats monetary values with dollar signs and thousand separators, formats volume with thousand separators, and orders results by revenue first, then volume to show the highest-value customers at the top.

**Generated SQL:**
```sql
WITH CustomerQuarterlyMetrics AS (
  SELECT 
    Customer,
    SUM(COALESCE(Gross_Revenue, 0)) as total_revenue,
    SUM(COALESCE(Volume, 0)) as total_volume
  FROM `arizona-poc.copa_export_copa_data_000000000000.customer_master_analysis`
  GROUP BY Customer
)
SELECT 
  Customer,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(total_revenue) AS INT64)), FORMAT('.%02d', CAST(ROUND((total_revenue - FLOOR(total_revenue)) * 100) AS INT64))) as total_revenue,
  FORMAT('%\'d', CAST(total_volume AS INT64)) as total_volume
FROM CustomerQuarterlyMetrics
WHERE total_revenue > 0 OR total_volume > 0
ORDER BY total_revenue DESC, total_volume DESC
LIMIT 50
```


---

## Summary

Test completed at Tue Nov 11 14:07:08 CST 2025
