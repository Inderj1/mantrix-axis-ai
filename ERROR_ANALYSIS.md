# Error Analysis - Query Failures

## What the "NoneType" Error Meant

**Original Error:** `"object of type 'NoneType' has no len()"`

**Cause:** The test script tried to check `len(results)` when `results` was `None` instead of an empty list `[]`.

**Fixed:** Now the script properly handles `None` values and shows the actual BigQuery errors.

---

## Real Errors Found (After Fix)

### **Pattern: Column Name Mismatches**

All 5 failing queries have the same root cause: **LLM is guessing column names that don't exist in the table**.

---

## Query-by-Query Error Analysis

### ❌ Query 1: Beer Portfolio Performance

**Error:**
```
Unrecognized name: Product; Did you mean Product_BU?
```

**What LLM Generated:**
```sql
SELECT
  Product,  -- ❌ This column doesn't exist
  Product_Name,  -- ❌ This might not exist either
  ...
```

**Available Columns (likely):**
- `Product_BU` (Business Unit)
- Maybe `Material`, `Material_Description`

**Why it Failed:** LLM guessed "Product" but table has "Product_BU"

---

### ❌ Query 3: Delivered Quantity by Material/Plant

**Error:**
```
Unrecognized name: Material_MATNR
```

**What LLM Generated:**
```sql
SELECT
  Material,  -- Used this in SELECT
  Plant,
  ...
WHERE ... AND Material IS NOT NULL  -- Then tried to use Material
```

**But Then SQL Corrector Added:**
```sql
-- Correction tried to use: Material_MATNR
```

**Problem:** LLM used "Material", correction tried "Material_MATNR", but actual column might be something else entirely or doesn't exist.

---

### ❌ Query 4: Aging Inventory - Open Orders

**Error:**
```
Unrecognized name: DeliveredQuantity_KBMENG
```

**What LLM Generated:**
Referenced a table: `sales_order_cockpit_export` (this table might not be in the schema provided to LLM)

**Problem:** LLM is hallucinating table names and columns that don't exist in the available schema.

---

### ❌ Query 6: Declining Delivery Trend

**Error:**
```
Unrecognized name: Billing_Quantity_FKIMG
```

**What LLM Generated:**
```sql
SUM(COALESCE(Delivered_Quantity, 0))  -- LLM used this
-- But correction tried: Billing_Quantity_FKIMG
```

**Problem:** SQL query corrector is trying to fix column names but guessing wrong SAP field names.

---

### ❌ Query 7: Sales by Product/Region

**Error:**
```
Unrecognized name: Region
```

**What LLM Generated:**
```sql
SELECT
  Product,  -- ❌ Doesn't exist
  Region,   -- ❌ Doesn't exist
  ...
```

**Available Columns (likely):**
- Maybe: `Country`, `State`, `City`, `Sales_District`
- Or: `Region_Code`, `Sales_Region`

**Problem:** LLM guessed "Region" but table has different column name.

---

## Root Cause Analysis

### 1. **Schema Information Gap**

The LLM is not receiving accurate column names. It's guessing based on:
- Common SAP naming conventions (e.g., `Material_MATNR`, `DeliveredQuantity_KBMENG`)
- Generic business terms (e.g., `Product`, `Region`, `Plant`)

### 2. **SQL Query Corrector Issues**

When the initial query fails, a correction is attempted. The corrector:
- Tries to map generic names → SAP technical names
- But is also guessing incorrectly
- Uses SAP field names like `_KBMENG`, `_FKIMG`, `_MATNR` (these are SAP suffixes)

### 3. **Missing Tables**

Query 4 referenced `sales_order_cockpit_export` - this table might not be:
- In the database at all
- Included in the schema information sent to the LLM

---

## How to Fix This

### **Solution 1: Verify Schema Information (CRITICAL)**

Check what column names are actually being sent to the LLM:

```bash
# Check what's in Weaviate vector store
# Or check the schema sent to LLM in llm_client.py
```

**Steps:**
1. Query BigQuery to get actual column names:
   ```sql
   SELECT column_name
   FROM `arizona-poc.copa_export_copa_data_000000000000`.INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = 'dataset_25m_table'
   ORDER BY ordinal_position;
   ```

2. Compare with what Weaviate has stored
3. Update Weaviate if column names are wrong

---

### **Solution 2: Add Column Name Mapping**

Create a mapping file for common mismatches:

```python
COLUMN_ALIASES = {
    "Product": "Product_BU",  # or whatever the actual column is
    "Region": "Sales_District",
    "Material": "Material_Number",
    "Plant": "Plant_Code",
    "Delivered_Quantity": "Billing_Quantity"
}
```

---

### **Solution 3: Enhance LLM Instructions**

In `llm_client.py`, add stronger instructions:

```python
"""
CRITICAL: Use ONLY the exact column names from the schema provided below.
DO NOT infer or guess column names like "Product", "Region", "Material".
USE EXACT NAMES from the schema (e.g., "Product_BU", "Sales_District").
"""
```

---

### **Solution 4: Improve SQL Corrector**

The SQL query corrector (`backend/src/core/query_optimizer.py` or similar) needs to:

1. **Not guess column names** - only use columns from actual schema
2. **Provide helpful errors** instead of trying random SAP field suffixes
3. **Suggest alternatives** from actual available columns

---

## Verification Needed

### Check These Tables in BigQuery:

1. **`dataset_25m_table`** - Get all column names:
   ```sql
   SELECT column_name, data_type
   FROM `arizona-poc.copa_export_copa_data_000000000000`.INFORMATION_SCHEMA.COLUMNS
   WHERE table_name = 'dataset_25m_table';
   ```

2. **`sales_order_cockpit_export`** - Does this table even exist?
   ```sql
   SELECT COUNT(*)
   FROM `arizona-poc.copa_export_copa_data_000000000000.sales_order_cockpit_export`
   LIMIT 1;
   ```

3. **All tables** - List all available tables:
   ```sql
   SELECT table_name, row_count
   FROM `arizona-poc.copa_export_copa_data_000000000000`.__TABLES__;
   ```

---

## Immediate Action Items

1. ✅ **Fixed test script** - Now shows real errors
2. ⏳ **Verify schema in Weaviate** - Are column names accurate?
3. ⏳ **Check BigQuery actual columns** - What's really in the tables?
4. ⏳ **Update schema** if mismatched
5. ⏳ **Add column name mapping** for common aliases
6. ⏳ **Improve SQL corrector** to not guess invalid names

---

## Summary

**What "NoneType" Error Really Was:**
- Test script bug trying to check length of `None`

**Actual Problem:**
- LLM is generating SQL with **wrong column names**
- Columns like `Product`, `Region`, `Material`, `Plant`, `Delivered_Quantity` don't exist
- Actual columns are probably things like `Product_BU`, `Sales_District`, etc.

**Fix Priority:**
1. **HIGH**: Get actual column list from BigQuery
2. **HIGH**: Verify schema information in Weaviate
3. **MEDIUM**: Add column name mapping
4. **MEDIUM**: Improve SQL error correction logic

