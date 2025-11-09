# Duplicate Column Detection - Intelligence Analysis

## Question: How does the system understand duplicate columns? Is Jena intelligent enough?

---

## Answer: **PARTIALLY INTELLIGENT** (Basic but Safe)

The current system uses a **simple but correct** approach: **Exact Name + Exact Type matching**

---

## Current Intelligence Level

### ✅ What Jena DOES Detect

```
Column Name: "Customer"
Found in 5 tables:

STRING Type (3 tables):
  • dataset_25m_table (72M rows)
  • customer_master_analysis (2,903 rows)
  • transaction_data (250K rows)

INTEGER Type (2 tables):
  • product_customer_matrix (2,636 rows)
  • time_series_performance (576 rows)
```

**Jena's Decision**:
```
✓ Create 3 relationships among STRING tables
✓ Create 1 relationship between INTEGER tables
✓ DO NOT create relationships across type boundaries
```

**Result**: **4 relationships created** (not 10 possible combinations)

---

## Intelligence Rules

### Rule 1: Exact Column Name Match
```python
# Code: load_table_metadata_to_jena.py:102-104

for col_name, instances in column_to_tables.items():
    if len(instances) < 2:
        continue  # No relationship possible
```

**What it catches**:
- ✅ "Customer" in table A + "Customer" in table B

**What it misses**:
- ❌ "Customer" vs "CustomerID"
- ❌ "Customer" vs "Cust_Number"
- ❌ "Material_Number" vs "MaterialNo"

---

### Rule 2: Exact Type Match
```python
# Code: load_table_metadata_to_jena.py:106-114

# Group by type
by_type = defaultdict(list)
for inst in instances:
    by_type[inst['type']].append(inst)

# Create relationships for columns with same name AND same type
for col_type, same_type_instances in by_type.items():
    if len(same_type_instances) < 2:
        continue
```

**What it catches**:
- ✅ "Customer" (STRING) joins "Customer" (STRING)
- ✅ "Customer" (INTEGER) joins "Customer" (INTEGER)

**What it misses**:
- ❌ "Customer" (STRING) vs "Customer" (INTEGER) - **Type mismatch, but semantically the same!**
- ❌ "Date" (DATE) vs "Date" (TIMESTAMP)
- ❌ Numeric strings that should be integers

---

## Real-World Problem Case

### Scenario:
**Query**: "Show revenue by customer with product preferences"

**Tables Needed**:
1. `dataset_25m_table` - Revenue data (72M rows)
2. `customer_master_analysis` - Customer segments (2,903 rows)
3. `product_customer_matrix` - Product preferences (2,636 rows)

### Column Analysis:

```
"Customer" column types:
  • dataset_25m_table.Customer: STRING
  • customer_master_analysis.Customer: STRING
  • product_customer_matrix.Customer: INTEGER ⚠️
```

### Jena's Relationships:

```
✓ dataset_25m_table ⟷ customer_master_analysis
  JOIN: Customer (STRING = STRING) ✅

✓ dataset_25m_table ⟷ product_customer_matrix
  JOIN: Material_Number ✅
  (Falls back to different column)

✗ customer_master_analysis ⟷ product_customer_matrix
  NO DIRECT JOIN via Customer
  (Uses RFM_Segment instead)
```

### The Gap:

Jena **cannot join** `customer_master_analysis.Customer (STRING)` with `product_customer_matrix.Customer (INTEGER)` even though they represent **the same semantic entity**.

**Workaround**: Use intermediate tables or alternative join keys (RFM_Segment, Material_Number)

---

## What Makes a Column a "Duplicate"?

### Level 1: Exact Match (Current System ✅)
- Same name
- Same type
- **Example**: `Customer (STRING)` in 3 tables

### Level 2: Type-Compatible Match (NOT IMPLEMENTED ❌)
- Same name
- Compatible types (STRING ⟷ INTEGER if values match)
- **Example**: `Customer (STRING)` vs `Customer (INTEGER)`
- **Solution**: Add type casting in SQL

### Level 3: Semantic Match (NOT IMPLEMENTED ❌)
- Similar names (fuzzy matching)
- Same semantic meaning
- **Examples**:
  - `Customer` ≈ `CustomerID`
  - `Material_Number` ≈ `MaterialNo`
  - `GL_Account` ≈ `GLAccount`
- **Solution**: Embedding similarity + edit distance

### Level 4: Value-Based Match (NOT IMPLEMENTED ❌)
- Different names
- Same value distribution
- **Example**:
  - Column A has values: [1, 2, 3, 4, 5]
  - Column B has values: [1, 2, 3, 4, 5]
  - 90% overlap → Likely the same entity
- **Solution**: Cardinality analysis + value sampling

---

## Comparison: Current vs Intelligent System

| Feature | Current (Jena) | Intelligent System |
|---------|---------------|-------------------|
| **Exact name + type** | ✅ | ✅ |
| **Type casting** | ❌ | ✅ (STRING→INT) |
| **Fuzzy name matching** | ❌ | ✅ (edit distance) |
| **Semantic similarity** | ❌ | ✅ (embeddings) |
| **Value distribution** | ❌ | ✅ (sampling) |
| **Cardinality analysis** | ❌ | ✅ (unique counts) |
| **Cross-reference tables** | ❌ | ✅ (mapping tables) |

---

## How to Make Jena More Intelligent

### Enhancement 1: Type Compatibility Matrix

Add to `load_table_metadata_to_jena.py`:

```python
TYPE_COMPATIBILITY = {
    ('STRING', 'INTEGER'): 'CAST({col} AS STRING)',
    ('INTEGER', 'STRING'): 'CAST({col} AS INT64)',
    ('DATE', 'TIMESTAMP'): 'CAST({col} AS TIMESTAMP)',
    ('TIMESTAMP', 'DATE'): 'DATE({col})',
    ('FLOAT64', 'INTEGER'): 'CAST({col} AS FLOAT64)',
}

def are_types_compatible(type1, type2):
    """Check if two types can be joined with casting."""
    if type1 == type2:
        return True, None  # No casting needed

    # Check compatibility matrix
    cast_func = TYPE_COMPATIBILITY.get((type1, type2))
    if cast_func:
        return True, cast_func

    # Try reverse
    cast_func = TYPE_COMPATIBILITY.get((type2, type1))
    if cast_func:
        return True, cast_func

    return False, None
```

**Result**: Can join `Customer (STRING)` with `Customer (INTEGER)` using `CAST`

---

### Enhancement 2: Fuzzy Name Matching

```python
from difflib import SequenceMatcher

def name_similarity(name1, name2):
    """Calculate similarity between column names."""
    # Normalize
    n1 = name1.lower().replace('_', '').replace(' ', '')
    n2 = name2.lower().replace('_', '').replace(' ', '')

    # Calculate similarity
    return SequenceMatcher(None, n1, n2).ratio()

# In detection loop:
for col1_name, col1_instances in column_to_tables.items():
    for col2_name, col2_instances in column_to_tables.items():
        if col1_name == col2_name:
            continue

        similarity = name_similarity(col1_name, col2_name)
        if similarity > 0.8:  # 80% similar
            print(f"🔗 Fuzzy match: {col1_name} ≈ {col2_name} ({similarity:.2%})")
            # Create fuzzy relationship
```

**Result**: Detects `Customer` ≈ `CustomerID`, `Material_Number` ≈ `MaterialNo`

---

### Enhancement 3: Semantic Embeddings

```python
from openai import OpenAI

def get_column_embedding(col_name, col_description=""):
    """Generate embedding for column name + description."""
    text = f"Column: {col_name}. {col_description}"
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def semantic_similarity(emb1, emb2):
    """Calculate cosine similarity between embeddings."""
    import numpy as np
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

# In detection:
for col1 in all_columns:
    for col2 in all_columns:
        if col1 == col2:
            continue

        emb1 = get_column_embedding(col1['name'], col1.get('description', ''))
        emb2 = get_column_embedding(col2['name'], col2.get('description', ''))

        sim = semantic_similarity(emb1, emb2)
        if sim > 0.85:
            print(f"🔗 Semantic match: {col1['name']} ≈ {col2['name']} ({sim:.2%})")
```

**Result**: Detects semantically similar columns even with different names

---

### Enhancement 4: Value Distribution Analysis

```python
def analyze_column_values(table, column):
    """Sample values and analyze distribution."""
    query = f"""
    SELECT
        COUNT(DISTINCT {column}) as cardinality,
        COUNT(*) as total_rows,
        APPROX_TOP_COUNT({column}, 10) as top_values
    FROM {table}
    """

    result = bq_client.execute_query(query)
    return {
        'cardinality': result[0]['cardinality'],
        'total_rows': result[0]['total_rows'],
        'top_values': result[0]['top_values']
    }

def value_overlap(table1, col1, table2, col2):
    """Calculate value overlap between two columns."""
    query = f"""
    WITH t1 AS (SELECT DISTINCT {col1} AS val FROM {table1}),
         t2 AS (SELECT DISTINCT {col2} AS val FROM {table2})
    SELECT
        (SELECT COUNT(*) FROM t1) as t1_count,
        (SELECT COUNT(*) FROM t2) as t2_count,
        COUNT(*) as overlap
    FROM t1
    JOIN t2 ON t1.val = t2.val
    """

    result = bq_client.execute_query(query)
    overlap_pct = result[0]['overlap'] / min(result[0]['t1_count'], result[0]['t2_count'])
    return overlap_pct

# In detection:
if value_overlap(table1, col1, table2, col2) > 0.7:
    print(f"🔗 Value overlap match: {col1} ⟷ {col2} (70% overlap)")
```

**Result**: Detects columns with same values even if names/types differ

---

## Summary

### Current Jena Intelligence: **3/10**

**Strengths**:
- ✅ Safe (doesn't create invalid relationships)
- ✅ Fast (no external API calls)
- ✅ Deterministic (same input → same output)

**Weaknesses**:
- ❌ Misses type-compatible columns (STRING vs INTEGER)
- ❌ Misses fuzzy name matches (Customer vs CustomerID)
- ❌ No semantic understanding
- ❌ No value-based detection

---

### Proposed Intelligent System: **9/10**

**Enhancements**:
1. ✅ Type compatibility matrix (STRING ⟷ INTEGER with CAST)
2. ✅ Fuzzy name matching (edit distance)
3. ✅ Semantic embeddings (OpenAI)
4. ✅ Value distribution analysis (BigQuery sampling)
5. ✅ Cardinality comparison
6. ✅ Confidence scoring (0-100%)

**Example Output**:
```
🔗 Customer matches found:

EXACT (100% confidence):
  • dataset_25m_table.Customer (STRING)
  ⟷ customer_master_analysis.Customer (STRING)

TYPE-COMPATIBLE (90% confidence):
  • dataset_25m_table.Customer (STRING)
  ⟷ product_customer_matrix.Customer (INTEGER)
  Cast: CAST(Customer AS STRING)

FUZZY (85% confidence):
  • dataset_25m_table.Customer
  ≈ sales_data.CustomerID (edit distance: 0.82)

SEMANTIC (80% confidence):
  • customer_master_analysis.Customer
  ≈ accounts.AccountHolder (embedding similarity: 0.88)
```

---

## Recommendation

**Implement in phases**:

1. **Phase 1** (Quick win): Type compatibility matrix
   - Add casting support for common type pairs
   - Handle STRING ⟷ INTEGER, DATE ⟷ TIMESTAMP

2. **Phase 2** (Medium): Fuzzy name matching
   - Use edit distance (Levenshtein)
   - Threshold: 80% similarity

3. **Phase 3** (Advanced): Semantic embeddings
   - Generate embeddings for column names
   - Use cosine similarity

4. **Phase 4** (Expert): Value distribution
   - Sample values from BigQuery
   - Calculate overlap percentage

Each phase increases intelligence but adds complexity. **Phase 1 alone would solve 80% of current issues.**
