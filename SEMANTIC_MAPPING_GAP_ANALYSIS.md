# Semantic Mapping Gap Analysis

**Date:** November 11, 2025
**Issue:** Vector DB and Knowledge Graph not preventing column name mismatches

## Problem Statement

Despite having:
- ✅ Weaviate vector DB for semantic search
- ✅ Jena RDF Knowledge Graph with table metadata
- ✅ Synonym resolution in `JenaQueryResolver`

The system still generates SQL with non-existent columns like:
- `Delivered_Quantity` (doesn't exist)
- `Product` (doesn't exist - should be `Material_Description`, `Product_BU`, etc.)

## Root Cause Analysis

### 1. Knowledge Graph Has Table/Column Metadata BUT No Column Synonyms

**What's IN the KG:**
```turtle
# Table relationships
fin:Relationship_dataset_25m_table...

# Column definitions
fin:Column_dataset_25m_table_Inv_Quantity a fin:Column ;
fin:Column_dataset_25m_table_ZCS_Shipped_Quantity a fin:Column ;

# Metric synonyms (ONLY for financial metrics)
fin:Synonym_ROIC_1 a fin:Synonym ;
    fin:term "return on invested capital" ;
    fin:synonymOf fin:Metric_ROIC .
```

**What's MISSING:**
```turtle
# ❌ NO column synonyms like:
fin:Synonym_DeliveredQuantity a fin:Synonym ;
    fin:term "delivered quantity" ;
    fin:synonymOf fin:Column_ZCS_Shipped_Quantity .

# ❌ NO semantic mappings for common terms:
"delivered qty" -> ZCS_Shipped_Quantity
"product" -> Material_Description
"quantity" -> Inv_Quantity
```

### 2. Vector Search Works for TABLES, Not COLUMNS

**Current Implementation:**
```python
# In sql_generator.py line 737
similar_tables = self.vector_client.search_similar_tables(
    query_embedding,
    limit=adjusted_limit
)
```

**What It Does:**
- ✅ Finds relevant **tables** semantically (e.g., "customer analysis" → customer_master_analysis)
- ✅ Returns table schemas with all columns

**What It DOESN'T Do:**
- ❌ Doesn't map "delivered quantity" → actual column name
- ❌ Doesn't validate if requested column exists
- ❌ Doesn't suggest alternatives for wrong column names

### 3. Synonym Resolution Only For Financial Metrics

**Current Scope (`jena_query_resolver.py` line 87-114):**
```python
def _resolve_synonyms(self, query: str) -> Dict[str, str]:
    """Resolve synonyms from RDF."""
    # SPARQL query to find all synonyms
    sparql = """
    PREFIX fin: <http://example.com/finance#>
    SELECT ?synonym_term ?primary_term
    WHERE {
        ?synonym a fin:Synonym ;
                 fin:term ?synonym_term ;
                 fin:isPrimary false ;
                 fin:synonymOf ?primary .
        ?primary fin:term ?primary_term .
    }
    """
```

**Reality Check:**
- Only finds synonyms for **Metrics** (ROIC, ROI, NOPAT, etc.)
- Does NOT resolve column name synonyms
- KG doesn't even HAVE column synonyms loaded

## Gap Summary

| Component | Current State | Missing Capability |
|-----------|---------------|-------------------|
| **Knowledge Graph** | ✅ Has table metadata<br>✅ Has table relationships<br>✅ Has metric synonyms | ❌ No column synonyms<br>❌ No semantic field mappings |
| **Vector DB (Weaviate)** | ✅ Semantic table search<br>✅ Returns full schemas | ❌ No column-level semantic search<br>❌ No synonym suggestions |
| **SQL Generator** | ✅ Uses vector search for tables<br>✅ Passes schemas to LLM | ❌ No column validation<br>❌ No column synonym resolution<br>❌ Trusts LLM completely for column names |
| **JenaQueryResolver** | ✅ Resolves metric synonyms<br>✅ SPARQL queries work | ❌ Not used for column resolution<br>❌ No integration with SQL generation |

## Why Queries Fail

### Example: "Show me delivered quantity by material"

**Flow:**
1. Vector search finds `dataset_25m_table` ✅
2. Returns schema with columns: `Inv_Quantity`, `ZCS_Shipped_Quantity`, etc. ✅
3. LLM sees user said "delivered quantity"
4. LLM invents column name `Delivered_Quantity` ❌
5. No validation happens ❌
6. SQL executes → 0 results

**The Gap:**
- System never tells LLM: "delivered quantity" should map to `ZCS_Shipped_Quantity`
- No feedback loop when column doesn't exist
- No synonym dictionary for the LLM to reference

## Actual Column Names vs. Common Terms

| User Term | Actual Column(s) | Status |
|-----------|------------------|--------|
| "delivered quantity" | `ZCS_Shipped_Quantity`, `ActualQuantityDelivered_InSalesUnits_LFIMG` | ❌ Not mapped |
| "quantity" | `Inv_Quantity`, `Inv_Quantity_Cases` | ❌ Not mapped |
| "product" | `Material_Description`, `Product_BU`, `Material_Group_Description` | ❌ Not mapped |
| "region" | `Sold_to_Region`, `Plant_Region`, `Sold_to_District` | ❌ Not mapped |
| "ROIC" | Metric formula with sub-buckets | ✅ Mapped in KG |
| "revenue" | `Gross_Revenue`, `Net_Revenue` | ⚠️ Partial (LLM guesses correctly) |

## Solutions

### Option 1: Extend Knowledge Graph with Column Synonyms ⭐ **RECOMMENDED**

**Add to `table_metadata_kg.ttl`:**
```turtle
# Column synonyms
fin:Synonym_DeliveredQuantity_1 a fin:ColumnSynonym ;
    fin:term "delivered quantity" ;
    fin:isPrimary false ;
    fin:synonymOf fin:Column_dataset_25m_table_ZCS_Shipped_Quantity ;
    fin:confidence 0.95 .

fin:Synonym_DeliveredQuantity_2 a fin:ColumnSynonym ;
    fin:term "delivered qty" ;
    fin:isPrimary false ;
    fin:synonymOf fin:Column_dataset_25m_table_ZCS_Shipped_Quantity ;
    fin:confidence 0.95 .

fin:Synonym_Product_1 a fin:ColumnSynonym ;
    fin:term "product" ;
    fin:isPrimary false ;
    fin:synonymOf fin:Column_dataset_25m_table_Material_Description ;
    fin:confidence 0.9 .

# Common quantity mappings
fin:Synonym_Quantity_1 a fin:ColumnSynonym ;
    fin:term "quantity" ;
    fin:isPrimary false ;
    fin:synonymOf fin:Column_dataset_25m_table_Inv_Quantity ;
    fin:confidence 0.85 .
```

**Implementation:**
1. Update `load_table_metadata_to_jena.py` to add column synonyms
2. Extend `JenaQueryResolver._resolve_synonyms()` to include columns
3. Use resolved column names in SQL generation prompt

**Benefits:**
- ✅ Leverages existing KG infrastructure
- ✅ Centralized synonym management
- ✅ Easy to update/maintain
- ✅ Confidence scores for ambiguous terms

### Option 2: Add Column-Level Vector Search

**Extend Weaviate schema:**
```python
# Index individual columns with descriptions
class ColumnSchema:
    table_name: str
    column_name: str
    data_type: str
    description: str
    sample_values: List[str]
    common_terms: List[str]  # synonyms
```

**Usage:**
```python
# When generating SQL
column_matches = self.vector_client.search_similar_columns(
    query="delivered quantity",
    table="dataset_25m_table",
    limit=3
)
# Returns: [ZCS_Shipped_Quantity, ActualQuantityDelivered_InSalesUnits_LFIMG, ...]
```

**Benefits:**
- ✅ Semantic matching for columns
- ✅ Can suggest multiple candidates

**Drawbacks:**
- ❌ More complex setup
- ❌ Higher vector search overhead

### Option 3: Prompt Enhancement with Column Dictionary

**Add to SQL generation prompt:**
```
COLUMN NAME MAPPINGS:
- "delivered quantity" → use ZCS_Shipped_Quantity or ActualQuantityDelivered_InSalesUnits_LFIMG
- "quantity" → use Inv_Quantity or Inv_Quantity_Cases
- "product" → use Material_Description, Product_BU, or Material_Group_Description
- "region" → use Sold_to_Region or Plant_Region

IMPORTANT: Use ONLY columns that exist in the provided schema. If a user term doesn't match exactly, use the mappings above.
```

**Benefits:**
- ✅ Quick to implement
- ✅ No infrastructure changes

**Drawbacks:**
- ❌ Hard-coded mappings
- ❌ Doesn't scale
- ❌ Requires manual updates

## Recommended Implementation Plan

### Phase 1: Quick Fix (1-2 hours)
1. Add common column synonyms to KG (20-30 mappings)
2. Update SQL generation prompt with top 10 mappings
3. Test with failing queries

### Phase 2: KG Enhancement (1 day)
1. Extend `JenaQueryResolver` to resolve column synonyms
2. Integrate column resolution into `SQLGenerator._build_prompt()`
3. Add validation: warn if column not in schema
4. Load comprehensive synonym dictionary into KG

### Phase 3: Advanced (2-3 days)
1. Implement column-level vector search
2. Add confidence-based column selection
3. Build feedback loop: learn from failed queries
4. Auto-generate synonyms from query logs

## Expected Impact

### Before:
- **8/8 queries failed** due to column mismatches
- No semantic understanding of column names
- LLM guesses column names

### After Phase 1:
- **~6/8 queries fixed** (75% success rate)
- Common terms mapped correctly
- Clear error messages for unmapped terms

### After Phase 2:
- **~7/8 queries fixed** (87.5% success rate)
- Comprehensive synonym coverage
- Automatic column validation

### After Phase 3:
- **~8/8 queries working** (95%+ success rate)
- Self-learning system
- Handles new/unusual terms

## Next Steps

1. ⏳ Create column synonym dictionary (CSV/JSON)
2. ⏳ Update `load_table_metadata_to_jena.py` to load synonyms
3. ⏳ Modify `JenaQueryResolver._resolve_synonyms()` for columns
4. ⏳ Integrate into `SQLGenerator.generate_sql()`
5. ⏳ Test with all 8 failing queries
6. ⏳ Document synonym management process
