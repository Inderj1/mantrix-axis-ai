# Current Query Flow - Complete System Walkthrough

## Overview
This document explains how natural language queries are processed from entry to SQL execution and results.

---

## Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        USER SUBMITS QUERY                                │
│  Example: "Show me customer revenue by RFM segment"                     │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 1: API ENTRY POINT                                                 │
│  File: src/api/routes.py:253 - POST /query                               │
│                                                                           │
│  Options:                                                                │
│  • use_vector_search: true (default)                                     │
│  • max_tables: 5 (default)                                               │
│  • execute: true (generate + execute)                                    │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 2: SQL GENERATOR INITIALIZATION                                    │
│  File: src/core/sql_generator.py:218 - generate_sql()                    │
│                                                                           │
│  Components Initialized:                                                 │
│  ✓ LLM Client (Claude Sonnet 4.5)                                        │
│  ✓ BigQuery Client                                                       │
│  ✓ Weaviate Vector Client (14 tables indexed)                            │
│  ✓ Cache Manager (Redis)                                                 │
│  ✓ Jena Knowledge Graph (7,805 triples loaded)                           │
│  ✓ Financial Parser                                                      │
│  ✓ Business Config Manager                                               │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 3: FINANCIAL SEMANTIC PARSING                                      │
│  File: src/core/sql_generator.py:232                                     │
│                                                                           │
│  Analyzes query for:                                                     │
│  • Hierarchy Level: L1 Metric, L2 Bucket, GL Account                     │
│  • Query Type: TREND, COMPARISON, TOP_N, etc.                            │
│  • Intent: METRIC_CALCULATION, BREAKDOWN, etc.                           │
│  • Metrics: Extracts mentioned metrics (Revenue, COGS, etc.)             │
│                                                                           │
│  Example Output:                                                         │
│  {                                                                        │
│    "hierarchy_level": "L2_BUCKET",                                       │
│    "query_type": "BREAKDOWN",                                            │
│    "intent": "METRIC_CALCULATION",                                       │
│    "metrics": [{"metric_code": "REV", "metric_name": "Revenue"}]         │
│  }                                                                        │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 4: KNOWLEDGE GRAPH ENHANCEMENT                                     │
│  File: src/core/sql_generator.py:285                                     │
│                                                                           │
│  Jena/RDF KG provides:                                                   │
│  • Metric formulas (e.g., Revenue = GL_Amount WHERE GL > 0)              │
│  • Synonym resolution (Sales → Revenue)                                  │
│  • GL Account mappings                                                   │
│  • Table relationships                                                   │
│                                                                           │
│  Example Enhancement:                                                    │
│  {                                                                        │
│    "synonyms_resolved": {"sales": "revenue"},                            │
│    "suggested_metrics": [{                                               │
│      "code": "REV",                                                      │
│      "formula": "SUM(Gross_Revenue)",                                    │
│      "components": ["Gross_Revenue"]                                     │
│    }],                                                                   │
│    "gl_accounts": [...],                                                 │
│    "kg_confidence": 0.85                                                 │
│  }                                                                        │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 5: BUSINESS CONFIG ENHANCEMENT                                     │
│  File: src/core/sql_generator.py:336                                     │
│                                                                           │
│  Client-specific mappings:                                               │
│  • GL Account ranges for metrics                                         │
│  • Material hierarchy                                                    │
│  • Custom business rules                                                 │
│                                                                           │
│  Active Config: arizona_beverages                                        │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 6: PRE-CALCULATED VALUE CHECK                                      │
│  File: src/core/sql_generator.py:352                                     │
│                                                                           │
│  Checks if query matches pre-calculated results:                         │
│  • Monthly revenue aggregates                                            │
│  • Customer segment totals                                               │
│  • Product performance metrics                                           │
│                                                                           │
│  If match found → Return immediately (FAST PATH)                         │
│  If no match → Continue to table selection                               │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 7: VECTOR SEARCH FOR TABLE SELECTION                               │
│  File: src/core/sql_generator.py:659 - _get_relevant_schemas()           │
│                                                                           │
│  Process:                                                                │
│  1. Generate query embedding (OpenAI text-embedding-3-small)             │
│  2. Cache embedding in Redis                                             │
│  3. Search Weaviate for similar table schemas (max 5 tables)             │
│  4. Return ranked tables by semantic similarity                          │
│                                                                           │
│  Example for "customer revenue by RFM segment":                          │
│  Tables Selected:                                                        │
│  1. dataset_25m_table (72M rows) - similarity: 0.92                      │
│  2. customer_master_analysis (2,903 rows) - similarity: 0.88             │
│  3. GL_Accounts (267 rows) - similarity: 0.65                            │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 8: JOIN PATH DISCOVERY                                             │
│  File: src/core/sql_generator.py:381 (currently uses table_registry)    │
│                                                                           │
│  Current Implementation:                                                 │
│  • table_registry.find_relationships(selected_tables)                    │
│  • Returns join hints: {source, target, keys, type}                      │
│                                                                           │
│  NEW CAPABILITY (not yet integrated):                                    │
│  • JoinPathFinder.recommend_join_order()                                 │
│  • Uses Jena KG for optimal JOIN ordering                                │
│  • Fact tables first, then dimensions by size                            │
│                                                                           │
│  Example Output:                                                         │
│  join_hints = [                                                          │
│    {                                                                     │
│      "source": "dataset_25m_table",                                      │
│      "target": "customer_master_analysis",                               │
│      "keys": ["Customer"],                                               │
│      "type": "LEFT"                                                      │
│    }                                                                     │
│  ]                                                                        │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 9: CACHE CHECK                                                     │
│  File: src/core/sql_generator.py:455                                     │
│                                                                           │
│  Check Redis cache for:                                                  │
│  • Query + Schema hash → SQL                                             │
│                                                                           │
│  If cached → Return immediately                                          │
│  If not cached → Generate with LLM                                       │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 10: SQL GENERATION (LLM)                                           │
│  File: src/core/llm_client.py - generate_sql()                           │
│                                                                           │
│  Input to Claude:                                                        │
│  • Natural language query                                                │
│  • Selected table schemas (structure, columns, types)                    │
│  • Financial context (hierarchy, metrics, formulas)                      │
│  • Business context (GL mappings, client config)                         │
│  • Join hints (how tables relate)                                        │
│                                                                           │
│  LLM generates:                                                          │
│  • SQL query                                                             │
│  • Explanation                                                           │
│  • Confidence score                                                      │
│                                                                           │
│  Example SQL:                                                            │
│  SELECT                                                                  │
│    c.RFM_Segment,                                                        │
│    SUM(d.Gross_Revenue) AS total_revenue                                 │
│  FROM dataset_25m_table d                                                │
│  LEFT JOIN customer_master_analysis c                                    │
│    ON d.Customer = c.Customer                                            │
│  GROUP BY c.RFM_Segment                                                  │
│  ORDER BY total_revenue DESC                                             │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 11: POST-PROCESSING & VALIDATION                                   │
│  File: src/core/sql_generator.py:476                                     │
│                                                                           │
│  Fixes common issues:                                                    │
│  • Revenue column corrections (GL_Amount → Gross_Revenue)                │
│  • Date format standardization                                           │
│  • Column name validation                                                │
│                                                                           │
│  Validation:                                                             │
│  • Syntax check                                                          │
│  • Column existence verification                                         │
│  • Table availability check                                              │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 12: OPTIMIZATION                                                   │
│  File: src/core/query_optimizer.py                                       │
│                                                                           │
│  Applies optimizations:                                                  │
│  • Query plan analysis                                                   │
│  • Index usage verification                                              │
│  • JOIN order optimization                                               │
│  • Partitioning hints for BigQuery                                       │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 13: EXECUTION (if execute=true)                                    │
│  File: src/db/bigquery.py - execute_query()                              │
│                                                                           │
│  BigQuery Execution:                                                     │
│  1. Submit query to BigQuery                                             │
│  2. Wait for job completion                                              │
│  3. Fetch results (limit: 10,000 rows by default)                        │
│  4. Convert to JSON format                                               │
│                                                                           │
│  Error Handling:                                                         │
│  • Syntax errors → Return detailed error                                 │
│  • Timeout → Return partial results                                      │
│  • Permission errors → Return auth error                                 │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 14: RESULTS FORMATTING                                             │
│  File: src/core/sql_generator.py:520+                                    │
│                                                                           │
│  Format results:                                                         │
│  • Row count                                                             │
│  • Column names and types                                                │
│  • Sample data (first N rows)                                            │
│  • Execution metadata (time, bytes processed)                            │
│                                                                           │
│  Example Response:                                                       │
│  {                                                                        │
│    "sql": "SELECT...",                                                   │
│    "explanation": "This query calculates...",                            │
│    "execution": {                                                        │
│      "success": true,                                                    │
│      "results": [...],                                                   │
│      "row_count": 5,                                                     │
│      "execution_time_ms": 1234                                           │
│    }                                                                     │
│  }                                                                        │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 15: SUGGESTION GENERATION                                          │
│  File: src/api/routes.py:305 - generate_suggestions_async()              │
│                                                                           │
│  Generates follow-up queries:                                            │
│  • Related metrics                                                       │
│  • Drill-down options                                                    │
│  • Time-based variations                                                 │
│                                                                           │
│  Example Suggestions:                                                    │
│  1. "Show monthly revenue trend for Champions segment"                   │
│  2. "Compare revenue across all RFM segments"                            │
│  3. "Show top 10 customers in Champions segment"                         │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 16: RESPONSE TO USER                                               │
│  File: src/api/routes.py:370+                                            │
│                                                                           │
│  Returns to client:                                                      │
│  • SQL query                                                             │
│  • Explanation                                                           │
│  • Results (if executed)                                                 │
│  • Suggestions for follow-up                                             │
│  • Metadata (timing, confidence, etc.)                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Parallel Flows

### Agent Mode (Autonomous)
For complex queries requiring multi-step analysis:

```
POST /api/v1/agents/analyze-stream

┌─────────────────────────────────────────┐
│  CrewAI Financial Crew                  │
├─────────────────────────────────────────┤
│  1. Query Understanding Agent           │
│  2. SQL Generation Agent                │
│  3. Analysis Agent                      │
│  4. Results Formatting Agent            │
└─────────────────────────────────────────┘
      │
      ├─> Streams execution steps in real-time
      ├─> Iterative refinement
      ├─> Multi-table analysis
      └─> Final formatted analysis
```

### Chat Mode (Conversational)
For conversational interfaces with history:

```
POST /api/v1/margen/chat

┌─────────────────────────────────────────┐
│  Chat Service                           │
├─────────────────────────────────────────┤
│  • Conversation history tracking        │
│  • Context-aware responses              │
│  • Follow-up handling                   │
│  • Multi-turn dialogue                  │
└─────────────────────────────────────────┘
```

---

## Key Components Detail

### 1. Vector Search (Weaviate)
**Purpose**: Semantic table discovery

**How it works**:
- 14 tables indexed with embeddings
- Query embedding: OpenAI text-embedding-3-small (1536 dimensions)
- Similarity search: Cosine distance
- Returns top 5 most relevant tables

**Example**:
```
Query: "customer revenue"
Embedding: [0.123, -0.456, 0.789, ...]

Search Results:
1. dataset_25m_table (score: 0.92)
2. customer_master_analysis (score: 0.88)
3. GL_Accounts (score: 0.65)
```

### 2. Knowledge Graph (Jena/RDF)
**Purpose**: Semantic understanding + relationship discovery

**Capabilities**:
- 7,805 RDF triples
- 284 table relationships
- Metric formulas
- GL account mappings
- Synonym resolution

**Example Query**:
```sparql
PREFIX fin: <http://example.com/finance#>

SELECT ?joinColumn ?columnType
WHERE {
    ?rel a fin:TableRelationship ;
         fin:joinColumn ?joinColumn ;
         fin:columnType ?columnType ;
         fin:sourceTable ?source ;
         fin:targetTable ?target .

    ?source fin:tableName "dataset_25m_table" .
    ?target fin:tableName "customer_master_analysis" .
}

# Returns: Customer (STRING)
```

### 3. Financial Parser
**Purpose**: Understand financial terminology

**Detects**:
- Hierarchy levels (L1, L2, GL)
- Query types (TREND, COMPARISON, etc.)
- Metrics (Revenue, COGS, Gross Profit, etc.)
- Time periods (monthly, quarterly, YoY)

### 4. Cache Layers (Redis)
**What's cached**:
1. Query embeddings (TTL: 1 hour)
2. Generated SQL (TTL: 24 hours)
3. Table schemas (TTL: 1 hour)
4. Jena RDF graph (persistent)

**Hit Rate**: ~40-60% for common queries

---

## Performance Metrics

| Operation | Time (avg) | Notes |
|-----------|-----------|-------|
| Embedding generation | 100-200ms | OpenAI API call |
| Vector search | 50-100ms | Weaviate local |
| Jena SPARQL query | 10-50ms | In-memory RDF |
| SQL generation (LLM) | 2-5s | Claude API |
| BigQuery execution | 500ms-10s | Depends on query |
| **Total (cache miss)** | **3-15s** | |
| **Total (cache hit)** | **500ms-2s** | |

---

## Limitations & Gaps

### Current Limitations:

1. **JOIN Discovery Not Fully Integrated**
   - JoinPathFinder exists but not yet used in SQL generation
   - Still relies on table_registry (less intelligent)

2. **No Forecasting**
   - Time-series queries don't generate predictions
   - No trend extrapolation

3. **Limited Multi-Hop JOINs**
   - Can find multi-hop paths but doesn't use them automatically
   - Complex star schema queries may fail

4. **No Query Result Caching**
   - Only SQL is cached, not execution results
   - Same query executes BigQuery every time

5. **Limited Error Recovery**
   - Syntax errors → full failure
   - No automatic retry with corrections

---

## Next Enhancements

### Priority 1: Integrate JoinPathFinder
**File**: `src/core/sql_generator.py:381`

**Change**:
```python
# Current:
relationships = table_registry.find_relationships(selected_table_names)

# New:
from src.core.knowledge_graph.join_path_finder import JoinPathFinder
finder = JoinPathFinder(self.knowledge_graph)
join_order = finder.recommend_join_order(selected_table_names)
```

### Priority 2: Add Forecasting
Integrate time-series forecasting for trend queries

### Priority 3: Result Caching
Cache execution results for exact query matches

---

## Summary

The query flow is a **sophisticated 16-step pipeline** that:

1. ✅ **Understands** queries semantically (financial parser + KG)
2. ✅ **Discovers** relevant tables (vector search)
3. ✅ **Enhances** context (business config + GL mappings)
4. ✅ **Generates** optimal SQL (LLM with rich context)
5. ✅ **Executes** on BigQuery
6. ✅ **Suggests** follow-ups

**Strengths**:
- Multi-layered intelligence (vector + graph + LLM)
- Client-specific customization
- Comprehensive caching
- Rich context provision

**Gaps**:
- JOIN path finder not integrated
- No forecasting
- Limited multi-hop JOIN support
