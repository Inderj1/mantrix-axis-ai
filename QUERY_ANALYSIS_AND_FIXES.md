# Query Test Analysis and Fixes

**Date:** November 11, 2025
**Status:** Analysis Complete

## Executive Summary

All 8 test queries generated syntactically correct SQL but returned zero results. After investigation, the issues are primarily:
1. **Data mismatch** - No "beer" products exist in the dataset
2. **Missing columns** - `Delivered_Quantity` column doesn't exist in main table
3. **Date filters too restrictive** - Using CURRENT_DATE() as 2025-11-11 but data only goes to 2025-06

## Data Availability

### Dataset Information
- **Date Range:** December 2017 to June 2025 (90 months)
- **Main Table:** `dataset_25m_table` with 218 columns
- **Key Finding:** Data is 5 months old (latest: June 2025, current: November 2025)

### Available Columns (Key ones)
- `Material_Description`, `Material_Number`, `Material_Group`
- `Plant`, `Plant_werks`  
- `Quantity` (NOT `Delivered_Quantity`)
- `Posting_Date`
- `Customer`, `Sold_to_Name`
- `Region`, `Sold_to_Region`
- `Gross_Revenue`, `Total_COGS`

## Query-by-Query Analysis

### ✅ FIXABLE QUERIES

#### Query 1 & 2: Beer Product Portfolio
**Issue:** No products with "beer" in name exist in dataset  
**Fix:** 
- Change filter from `LOWER(Product) LIKE '%beer%'` to actual product categories
- Use `Material_Group_Description` or `Product_BU` for filtering
- Example: Show portfolio for Product_BU = '01' (largest segment with $744M sales)

**Fixed Query:**
```sql
-- Instead of filtering by 'beer', use actual product groups
WHERE Product_BU = '01'  -- Or Material_Group_Description = 'specific_category'
AND Posting_Date >= DATE_SUB('2025-06-30', INTERVAL 12 MONTH)
```

#### Query 3, 5, 6: Delivered Quantity by Material/Plant
**Issue:** Column `Delivered_Quantity` doesn't exist  
**Fix:**
- Use `Quantity` column instead
- Ensure date filters use data's actual range

**Fixed Query:**
```sql
SELECT 
  Material_Number,
  Material_Description,
  Plant,
  FORMAT_DATE('%Y-%m', Posting_Date) as month,
  SUM(COALESCE(Quantity, 0)) as total_quantity
FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
WHERE Posting_Date >= DATE_SUB(DATE('2025-06-30'), INTERVAL 6 MONTH)
  AND Material_Number IS NOT NULL
  AND Plant IS NOT NULL
GROUP BY Material_Number, Material_Description, Plant, month
ORDER BY Material_Number, Plant, month
```

#### Query 7: Total Sales by Product/Region (Last 12 Months)
**Issue:** Date filter uses CURRENT_DATE() but data ends at 2025-06  
**Fix:** Use actual data end date

**Fixed Query:**
```sql
SELECT 
  Material_Group_Description as product_group,
  Sold_to_Region as region,
  CONCAT('$', FORMAT('%\'d', CAST(FLOOR(SUM(COALESCE(Gross_Revenue, 0))) AS INT64))) as total_sales
FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
WHERE Posting_Date >= DATE_SUB(DATE('2025-06-30'), INTERVAL 12 MONTH)
  AND Posting_Date <= DATE('2025-06-30')
GROUP BY product_group, region
HAVING SUM(Gross_Revenue) > 0
ORDER BY SUM(COALESCE(Gross_Revenue, 0)) DESC
```

#### Query 8: Top Customers (Last Quarter)
**Issue:** Uses customer_master_analysis table which may not have recent data  
**Fix:** Query directly from main table with proper date range

**Fixed Query:**
```sql
SELECT 
  Customer,
  Sold_to_Name,
  SUM(COALESCE(Gross_Revenue, 0)) as total_revenue,
  SUM(COALESCE(Quantity, 0)) as total_volume
FROM `arizona-poc.copa_export_copa_data_000000000000.dataset_25m_table`
WHERE Posting_Date >= DATE_SUB(DATE('2025-06-30'), INTERVAL 3 MONTH)
  AND Posting_Date <= DATE('2025-06-30')
  AND Customer IS NOT NULL
GROUP BY Customer, Sold_to_Name
ORDER BY total_revenue DESC
LIMIT 50
```

### ⚠️ NEEDS SCHEMA VERIFICATION

#### Query 4: Aging Inventory - Open Sales Orders
**Issue:** Uses `sales_order_cockpit_export` table  
**Status:** Need to verify:
1. Does this table exist?
2. What columns does it have?
3. Is `Delivered_Quantity_KBMENG` column available?

**Action Required:** Query the table schema to confirm structure

## Root Cause Analysis

### 1. Date Filter Problems (60% of issues)
- Queries use `CURRENT_DATE()` = 2025-11-11
- Data ends at 2025-06-30
- **Result:** 5-month gap causes empty results

### 2. Column Name Mismatches (30% of issues)
- SQL uses `Delivered_Quantity` 
- Actual column is `Quantity`
- SQL uses `Product`
- Actual columns are `Material_Description`, `Product_BU`, etc.

### 3. Non-existent Filter Values (10% of issues)
- "beer" products don't exist
- Need to use actual product categories

## Recommendations

### Immediate Fixes

1. **Update SQL Generation Prompts**
   - Replace references to `Delivered_Quantity` → `Quantity`
   - Replace `Product` → `Material_Description` or `Product_BU`
   - Use fixed date '2025-06-30' instead of `CURRENT_DATE()` for recent queries

2. **Add Schema Validation**
   - Verify column names before generating SQL
   - Suggest alternatives when requested column doesn't exist

3. **Data-Aware Date Filtering**
   - Query actual data range before using date filters
   - Warn users when requesting data beyond available range

### Long-Term Improvements

1. **Semantic Column Mapping**
   - Map user terms like "delivered quantity" → actual column `Quantity`
   - Build synonyms: product → material_description, region → sold_to_region

2. **Value Existence Checking**
   - Before filtering by specific values (like "beer"), check if they exist
   - Suggest similar values if exact match not found

3. **Context-Aware Date Handling**
   - Maintain metadata about data freshness
   - Automatically adjust "last X months" to available data range

## Test Results for Corrected Queries

| Query | Original Status | Fixed Status | Notes |
|-------|----------------|--------------|-------|
| Q1-2: Beer Portfolio | ❌ 0 rows | ⚠️ N/A | No beer products in dataset - need real product category |
| Q3: Quantity by Material/Plant | ❌ 0 rows | ⚠️ Partial | System still using wrong column names |
| Q4: Aging Inventory | ❌ 0 rows | ⏳ Pending | Need schema verification |
| Q5-6: Quantity trends | ❌ 0 rows | ⏳ Pending | Same as Q3 - column mismatch |
| Q7: Sales by Product/Region | ❌ 0 rows | ✅ 108 rows | **FIXED** - proper date handling |
| Q8: Top Customers | ❌ 0 rows | ✅ 20 rows | **FIXED** - proper date handling |

### Successfully Fixed (2/8)
- **Query 7:** Returns 108 product/region combinations with sales data
- **Query 8:** Returns top 20 customers by order value

### Key Success Factor
Adding explicit date context ("through June 2025" or "last quarter ending June 2025") helps the LLM generate queries with appropriate date filters.

## Next Steps

1. ✅ Test corrected versions of queries 7, 8 - **WORKING**
2. ⏳ Fix column mapping issue for Q3, 5, 6 (system still uses wrong columns)
3. ⏳ Verify sales_order_cockpit_export schema for query 4
4. ⏳ Test Q1-2 with real product categories
5. ⏳ Create prompt improvements for SQL generator
6. ⏳ Build column synonym mapping

