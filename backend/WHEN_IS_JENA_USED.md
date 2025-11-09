# When Is Apache Jena Used?

## Short Answer: **NO, Jena is NOT used in every query**

---

## Current Usage: Jena is used CONDITIONALLY

### Conditions for Jena to be Used:

```python
# From src/core/sql_generator.py:287

if self.kg_query_resolver and financial_context:
    # Use Jena knowledge graph
```

**Requirements**:
1. ✅ `kg_query_resolver` must be initialized (happens at startup)
2. ✅ `financial_context` must exist (query must contain financial terms)

---

## When Jena IS Used

### Query Contains Financial Terms:

```
✅ "Show me total revenue"
   → financial_parser detects: "revenue" (L1 metric)
   → financial_context created
   → Jena used to get metric formula

✅ "What is gross profit margin?"
   → financial_parser detects: "gross profit" (L1 metric)
   → financial_context created
   → Jena provides formula: (Revenue - COGS) / Revenue

✅ "Compare revenue vs COGS by GL account"
   → financial_parser detects: "revenue", "COGS", "GL account"
   → financial_context created
   → Jena provides GL mappings
```

### What Jena Provides in These Cases:

**File**: `src/core/sql_generator.py:289-333`

1. **Synonym Resolution**
   - "sales" → "revenue"
   - "turnover" → "revenue"

2. **Metric Formulas**
   - Revenue = SUM(Gross_Revenue)
   - Gross Profit = Revenue - COGS

3. **GL Account Mappings**
   - Revenue GL codes: 40000-49999
   - COGS GL codes: 50000-59999

4. **Formula Components**
   - Which columns to use in calculations

---

## When Jena is NOT Used

### Generic/Non-Financial Queries:

```
❌ "Show me all customers"
   → No financial terms detected
   → financial_context = None
   → Jena SKIPPED

❌ "List products by region"
   → No financial terms
   → financial_context = None
   → Jena SKIPPED

❌ "What are the top 10 materials by quantity?"
   → No financial terms
   → financial_context = None
   → Jena SKIPPED
```

### Query Flow Without Jena:

```
User Query: "Show me all customers"
   ↓
1. Financial Parser runs
   └─> No financial terms detected
   └─> financial_context = None
   ↓
2. Jena check (line 287)
   └─> self.kg_query_resolver ✅ (initialized)
   └─> financial_context ❌ (None)
   └─> SKIP Jena
   ↓
3. Vector Search for tables
   ↓
4. LLM generates SQL
   ↓
5. Execute query
```

---

## What About Table Metadata in Jena?

### The 7,805 RDF Triples We Loaded:

**Status**: ✅ **Loaded but NOT USED in query generation**

```
Knowledge Graph Contains:
  • 14 table nodes
  • 1,003 column nodes
  • 284 table relationships

BUT: JoinPathFinder is NOT integrated into sql_generator.py
```

### Current Table Selection Method:

**File**: `src/core/sql_generator.py:381-398`

```python
# Currently uses table_registry (simple hardcoded relationships)
relationships = table_registry.find_relationships(selected_table_names)

# NOT using:
# from src.core.knowledge_graph.join_path_finder import JoinPathFinder
# finder = JoinPathFinder(self.knowledge_graph)
# join_order = finder.recommend_join_order(selected_table_names)
```

---

## Usage Statistics (Estimated)

Based on typical query patterns:

| Query Type | % of Queries | Jena Used? |
|-----------|-------------|-----------|
| Financial metrics (revenue, COGS, profit) | 30% | ✅ YES |
| Customer/product analysis | 40% | ❌ NO |
| Time-series/trends | 20% | 🟡 PARTIAL* |
| General data queries | 10% | ❌ NO |

*Time-series queries may or may not trigger financial parsing depending on content

**Overall Jena Usage**: ~30-40% of queries

---

## Two Separate Jena Features

### Feature 1: Financial Intelligence (ACTIVE ✅)

**What it does**:
- Resolves metric formulas
- Provides GL account mappings
- Synonym resolution

**When used**: Only for financial queries

**File**: `src/core/knowledge_graph/jena_query_resolver.py`

```python
# Example usage
metric_formula = kg_query_resolver.get_metric_formula("REV")
# Returns: MetricFormula(formula="SUM(Gross_Revenue)", ...)
```

---

### Feature 2: Table Relationship Intelligence (INACTIVE ❌)

**What it could do**:
- Find optimal JOIN paths
- Recommend join order
- Detect multi-hop relationships

**When it would be used**: Every multi-table query

**Status**: Built but not integrated

**File**: `src/core/knowledge_graph/join_path_finder.py`

```python
# Built but NOT CALLED from sql_generator.py
finder = JoinPathFinder(knowledge_graph)
join_order = finder.recommend_join_order(["table1", "table2", "table3"])
```

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   User Query Submitted                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │ Financial      │
            │ Parser         │
            └────────┬───────┘
                     │
         ┌───────────┴────────────┐
         │                        │
    Financial Terms          No Financial Terms
    Detected ✓               Detected ✗
         │                        │
         ▼                        │
    ┌─────────────┐              │
    │ Create      │              │
    │ financial_  │              │
    │ context     │              │
    └──────┬──────┘              │
           │                     │
           ▼                     ▼
    ┌──────────────────────────────────────┐
    │  Check: kg_query_resolver AND        │
    │         financial_context            │
    └──────┬───────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
  TRUE          FALSE
    │             │
    ▼             ▼
┌─────────┐  ┌──────────┐
│ USE     │  │ SKIP     │
│ JENA    │  │ JENA     │
│         │  │          │
│ • Get   │  │ Continue │
│   metrics│  │ without  │
│ • Get   │  │ KG       │
│   GL    │  │          │
│   codes │  │          │
│ • Resolve│ │          │
│   synonyms│ │         │
└─────────┘  └──────────┘
     │             │
     └──────┬──────┘
            │
            ▼
    Vector Search for Tables
            │
            ▼
    Generate SQL with LLM
            │
            ▼
    Execute Query
```

---

## Key Insights

### 1. Jena is Conditionally Used
- ✅ Only for financial queries
- ❌ Not for all queries
- 📊 ~30-40% query coverage

### 2. Table Metadata Not Used Yet
- ✅ Loaded (7,805 triples)
- ❌ Not integrated into query flow
- 🔧 JoinPathFinder exists but inactive

### 3. Two Independent Systems
```
Financial Intelligence (Jena Resolver)
  └─> Used in 30-40% of queries
  └─> Provides formulas, GL codes, synonyms

Table Relationship Intelligence (JoinPathFinder)
  └─> Built but NOT integrated
  └─> Would be used in ALL multi-table queries
  └─> Sitting idle
```

---

## How to Enable Jena for Every Query

### Option 1: Integrate JoinPathFinder

**Change**: `src/core/sql_generator.py:381`

```python
# Current (doesn't use Jena table metadata)
relationships = table_registry.find_relationships(selected_table_names)

# New (uses Jena table metadata)
from src.core.knowledge_graph.join_path_finder import JoinPathFinder

if self.knowledge_graph:
    finder = JoinPathFinder(self.knowledge_graph)
    join_order = finder.recommend_join_order(selected_table_names)
    # Use join_order instead of relationships
else:
    # Fallback to table_registry
    relationships = table_registry.find_relationships(selected_table_names)
```

**Impact**: Jena would be used in **100% of multi-table queries**

---

### Option 2: Make Financial Parsing More Aggressive

**Change**: `src/core/financial_semantic_parser.py`

```python
# Current: Only parses if specific financial terms found
# New: Parse ALL queries and create lightweight context

def parse_query(self, query: str):
    # Always create some context, even for non-financial queries
    if not self._has_financial_terms(query):
        # Still create minimal context for table selection help
        return {
            "hierarchy_level": None,
            "query_type": QueryType.GENERAL,
            "intent": QueryIntent.GENERAL,
            "metrics": []
        }
```

**Impact**: Jena would be attempted on more queries (but may not help much)

---

## Recommendation

**Priority 1**: Integrate JoinPathFinder (Option 1)
- More impactful
- Uses the 7,805 triples we loaded
- Helps ALL multi-table queries (not just financial)

**Priority 2**: Keep financial parsing selective (don't change)
- Current approach is correct
- Avoids unnecessary Jena calls for simple queries

---

## Summary Table

| Component | Status | Usage | Impact |
|-----------|--------|-------|--------|
| Jena Financial Resolver | ✅ Active | 30-40% of queries | Metric formulas, GL codes |
| Jena Table Metadata | ✅ Loaded | 0% of queries | None (not integrated) |
| JoinPathFinder | ✅ Built | 0% of queries | None (not integrated) |
| Vector Search | ✅ Active | 100% of queries | Table selection |
| LLM (Claude) | ✅ Active | 100% of queries | SQL generation |

**Bottom Line**: Jena is partially active but not being used to its full potential. The table relationship intelligence we built is sitting idle.
