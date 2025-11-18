# Optimization Intelligence Enhancement Plan

## Overview

Enhance query optimization components to use **existing** Weaviate (vector DB) and Jena (RDF knowledge graph) infrastructure for intelligent, data-driven optimization decisions.

**Leverage Existing Build-Time Pipeline:**
```
Schema → RDF Builder → Vector Builder → Weaviate
   ↓          ↓              ↓
  DB      Jena KG      Enriched Vectors
```

The system ALREADY:
- Stores table metadata in RDF (relationships, domains, row counts)
- Generates enriched vectors from RDF (includes JOIN relationships)
- Queries RDF at build-time to create semantic embeddings

**What We Need to Add:**
- Column-level statistics (cardinality, indexes, selectivity) in RDF
- Query performance history in Weaviate
- Join path costs and recommendations in RDF
- Integration with optimization components

## Current State

### Query Pushdown Optimizer
- **Current**: Rule-based SQL parsing with sqlglot
- **Limitation**: No knowledge of data distribution, indexes, or column selectivity
- **Example**: Pushes all filters equally, regardless of selectivity

### Staging Table Manager
- **Current**: Size-based thresholds (100MB-10GB)
- **Limitation**: No consideration of data characteristics or join complexity
- **Example**: May use staging for simple joins that don't need it

### Cross-Database Executor
- **Current**: Basic strategy selection
- **Limitation**: No learning from past query performance
- **Example**: Repeats same mistakes for similar queries

## Existing Infrastructure to Leverage

### Current Pipeline Components (src/pipeline/)

**1. Schema Extractor** (`schema_extractor.py`):
- Already extracts table/column schemas
- Already tracks schema versions and changes
- **Enhancement**: Add column statistics extraction

**2. RDF Builder** (`rdf_builder.py`):
- Already creates RDF triples for tables
- Already discovers relationships between tables
- Already stores row counts
- **Enhancement**: Add column-level statistics and index information

**3. Vector Builder** (`vector_builder.py`):
- Already queries RDF to enrich descriptions
- Already generates embeddings with:
  - Table relationships
  - Business domains
  - Size categories
  - Common use cases
- **Enhancement**: Add query performance patterns

**4. Orchestrator** (`orchestrator.py`):
- Coordinates: Schema → RDF → Vector pipeline
- Runs incrementally (only changed tables)
- **Enhancement**: Add optimization metadata refresh

## Proposed Enhancements

### Phase 1: Extend RDF Builder with Optimization Metadata

#### 1.1 Add Column Statistics to RDF Builder

**Extend**: `src/pipeline/rdf_builder.py`

Add method to extract and store column statistics in `rdf_builder.py`:

```python
# NEW METHOD in RDFBuilder class
def add_column_statistics(self, table_name: str, bq_client: BigQueryClient):
    """
    Extract and store column-level statistics in RDF.

    Uses BigQuery INFORMATION_SCHEMA to get:
    - Cardinality (APPROX_COUNT_DISTINCT)
    - Index information
    - Selectivity estimates
    """
    # Query BigQuery for column stats
    stats_query = f"""
    SELECT
        column_name,
        data_type,
        APPROX_COUNT_DISTINCT({column_name}) as cardinality,
        COUNT(*) as total_rows
    FROM `{table_name}`
    GROUP BY column_name, data_type
    """

    results = bq_client.execute_query(stats_query)

    for row in results:
        selectivity = row['cardinality'] / row['total_rows'] if row['total_rows'] > 0 else 0

        # Add RDF triples
        col_uri = URIRef(f"{self.namespace}{table_name}.{row['column_name']}")
        self.graph.add((col_uri, RDF.type, self.namespace.Column))
        self.graph.add((col_uri, self.namespace.cardinality, Literal(row['cardinality'])))
        self.graph.add((col_uri, self.namespace.selectivity, Literal(selectivity)))

    logger.info(f"Added column statistics for {table_name}")
```

**RDF Schema**:

```turtle
# Table metadata
:sales.customers a :Table ;
    :row_count 1000000 ;
    :size_mb 500 ;
    :has_column :customers_city ,
                :customers_customer_id .

# Column metadata
:customers_city a :Column ;
    :cardinality 50 ;          # Only 50 unique cities
    :has_index true ;          # Indexed column
    :selectivity 0.02 ;        # Avg filter selectivity
    :data_type "VARCHAR" .

:customers_customer_id a :Column ;
    :cardinality 1000000 ;     # High cardinality (unique)
    :has_index true ;
    :selectivity 0.000001 ;    # Very selective
    :data_type "INTEGER" .
```

**SPARQL Query for Optimization**:
```sparql
SELECT ?column ?cardinality ?has_index ?selectivity
WHERE {
    :sales.customers :has_column ?column .
    ?column :cardinality ?cardinality .
    ?column :has_index ?has_index .
    ?column :selectivity ?selectivity .
    FILTER(?column = :customers_city)
}
```

#### 1.2 Join Path Intelligence

```turtle
# Join relationships with cost estimates
:join_customers_orders a :JoinPath ;
    :left_table :sales.customers ;
    :right_table :sales.orders ;
    :join_column "customer_id" ;
    :avg_execution_time_ms 150 ;
    :estimated_rows 5000 ;
    :recommended_strategy "move_to_primary" .
```

**Usage in Executor**:
```python
def _select_join_strategy(self, left_table, right_table):
    # Query RDF for recommended strategy
    join_info = self.jena_kg.get_join_metadata(left_table, right_table)

    if join_info.estimated_rows > 1000000:
        return ExecutionStrategy.STAGING_TABLE
    elif join_info.recommended_strategy:
        return join_info.recommended_strategy
    else:
        return self._fallback_strategy()
```

#### 1.3 Enhanced Pushdown Decisions

**Current**: Push all filters

**Enhanced**:
```python
def _prioritize_filters(self, filters, table_name):
    prioritized = []

    for filter in filters:
        # Get column metadata from RDF
        col_info = self.jena_kg.get_column_info(table_name, filter.column)

        # Calculate priority score
        score = 0
        if col_info.has_index:
            score += 100  # Indexed columns are fast
        if col_info.cardinality < 100:
            score += 50   # Low cardinality = good selectivity
        if col_info.selectivity < 0.01:
            score += 75   # Highly selective filter

        prioritized.append((filter, score))

    # Push highest priority filters first
    return sorted(prioritized, key=lambda x: x[1], reverse=True)
```

#### 1.2 Integrate with Existing Vector Builder

**Extend**: `src/pipeline/vector_builder.py`

The vector builder ALREADY queries RDF to enrich descriptions. Simply update `_generate_enriched_description()` to include column statistics:

```python
# EXISTING METHOD - just add this section
def _generate_enriched_description(self, snapshot: TableSchemaSnapshot) -> str:
    parts = []
    # ... existing code ...

    # === COLUMN OPTIMIZATION METADATA === (NEW)
    high_selectivity_cols = self._get_high_selectivity_columns(snapshot.table_name)
    if high_selectivity_cols:
        parts.append("\nHighly Selective Columns (good for WHERE filters):")
        for col in high_selectivity_cols:
            parts.append(
                f"  - {col['name']} (selectivity: {col['selectivity']:.3f}, "
                f"cardinality: {col['cardinality']:,})"
            )

    indexed_cols = self._get_indexed_columns(snapshot.table_name)
    if indexed_cols:
        parts.append("\nIndexed Columns (fast lookups):")
        for col in indexed_cols:
            parts.append(f"  - {col}")

    return "\n".join(parts)

# NEW METHOD
def _get_high_selectivity_columns(self, table_name: str) -> List[Dict]:
    """Query RDF for highly selective columns (good for filtering)"""
    query = f"""
    SELECT ?col_name ?selectivity ?cardinality
    WHERE {{
        ?table schema:tableName "{table_name}" ;
               schema:hasColumn ?column .
        ?column schema:columnName ?col_name ;
                schema:selectivity ?selectivity ;
                schema:cardinality ?cardinality .
        FILTER(?selectivity < 0.01)  # Less than 1% selectivity = very selective
    }}
    ORDER BY ?selectivity
    LIMIT 5
    """
    results = self.rdf_builder.graph.query(query)
    return [{'name': r.col_name, 'selectivity': r.selectivity, 'cardinality': r.cardinality}
            for r in results]
```

Now when vectors are generated, they'll automatically include optimization hints!

### Phase 2: Add Query Performance Tracking to Vector DB

#### 2.1 Create OptimizedQuery Collection in Weaviate

**Extend**: `src/db/weaviate_client.py`

Add new collection for query performance history (ALONGSIDE existing TableSchemas collection):

```python
# Schema in Weaviate
query_history_schema = {
    "class": "OptimizedQuery",
    "properties": [
        {"name": "sql_text", "dataType": ["text"]},
        {"name": "execution_time_ms", "dataType": ["number"]},
        {"name": "strategy_used", "dataType": ["string"]},
        {"name": "rows_returned", "dataType": ["number"]},
        {"name": "data_transferred_mb", "dataType": ["number"]},
        {"name": "pushdown_applied", "dataType": ["boolean"]},
        {"name": "success", "dataType": ["boolean"]},
        {"name": "timestamp", "dataType": ["date"]}
    ],
    "vectorizer": "text2vec-openai"  # Generate embeddings from SQL
}
```

**After each query**:
```python
async def _record_query_performance(self, query, result, metrics):
    await self.weaviate_client.create_object(
        class_name="OptimizedQuery",
        properties={
            "sql_text": query,
            "execution_time_ms": metrics.execution_time_ms,
            "strategy_used": metrics.strategy,
            "rows_returned": len(result),
            "data_transferred_mb": metrics.data_transferred_mb,
            "pushdown_applied": metrics.pushdown_used,
            "success": metrics.success,
            "timestamp": datetime.now().isoformat()
        }
    )
```

#### 2.2 Learn from Similar Queries

**Before executing new query**:
```python
def _get_optimization_hints(self, sql_query):
    # Find semantically similar queries
    similar_queries = self.weaviate_client.query.get(
        "OptimizedQuery",
        ["sql_text", "strategy_used", "execution_time_ms", "pushdown_applied"]
    ).with_near_text({
        "concepts": [sql_query],
        "distance": 0.2  # Very similar queries
    }).with_where({
        "path": ["success"],
        "operator": "Equal",
        "valueBoolean": True
    }).with_limit(10).do()

    # Analyze what worked well
    if similar_queries:
        # Most common successful strategy
        strategies = [q['strategy_used'] for q in similar_queries]
        recommended_strategy = max(set(strategies), key=strategies.count)

        # Average performance
        avg_time = sum(q['execution_time_ms'] for q in similar_queries) / len(similar_queries)

        return {
            'recommended_strategy': recommended_strategy,
            'expected_time_ms': avg_time,
            'confidence': len(similar_queries) / 10  # 0-1 based on sample size
        }
```

#### 2.3 Intelligent Staging Decision

**Enhanced staging manager**:
```python
async def should_use_staging_intelligent(
    self,
    query: str,
    estimated_size_mb: float,
    left_table: str,
    right_table: str
) -> Tuple[bool, str]:
    """
    Intelligent staging decision using vector DB + RDF.

    Returns:
        (use_staging, reason)
    """
    # 1. Check size threshold (existing logic)
    if estimated_size_mb < self.IN_MEMORY_THRESHOLD_MB:
        return False, "Dataset too small, in-memory JOIN faster"

    if estimated_size_mb > self.STAGING_TABLE_MAX_MB:
        return False, "Dataset too large, use cloud storage"

    # 2. Check RDF for join metadata
    join_info = await self.jena_kg.get_join_info(left_table, right_table)
    if join_info and join_info.recommended_strategy == "staging":
        return True, f"RDF recommends staging (avg time: {join_info.avg_time_ms}ms)"

    # 3. Check vector DB for similar queries
    hints = await self._get_optimization_hints(query)
    if hints['confidence'] > 0.7:  # High confidence
        if hints['recommended_strategy'] == 'staging':
            return True, f"Similar queries used staging (confidence: {hints['confidence']:.0%})"
        else:
            return False, f"Similar queries used {hints['recommended_strategy']}"

    # 4. Fallback to size-based decision
    return True, "Size-based decision (100MB-10GB range)"
```

### Phase 3: Integration with Optimization Components

#### 3.1 Integrate RDF Data into Query Pushdown Optimizer

**Extend**: `src/core/query_pushdown_optimizer.py`

```python
class QueryPushdownOptimizer:
    def __init__(self, jena_kg=None):
        self.jena_kg = jena_kg or get_jena_knowledge_graph()
        logger.info("QueryPushdownOptimizer initialized with RDF support")

    def _prioritize_filters_intelligent(self, filters, table_name):
        """Use RDF metadata to prioritize filters"""
        prioritized = []

        for filter in filters:
            # Query RDF for column metadata
            col_info = self._get_column_metadata_from_rdf(table_name, filter.column)

            # Calculate priority score using RDF data
            score = 0
            if col_info:
                if col_info.get('has_index'):
                    score += 100
                if col_info.get('cardinality', 1e9) < 100:
                    score += 50
                if col_info.get('selectivity', 1.0) < 0.01:
                    score += 75

            prioritized.append((filter, score))

        return sorted(prioritized, key=lambda x: x[1], reverse=True)

    def _get_column_metadata_from_rdf(self, table_name, column_name):
        """Query Jena RDF for column metadata"""
        query = f"""
        SELECT ?cardinality ?selectivity ?has_index
        WHERE {{
            ?table schema:tableName "{table_name}" ;
                   schema:hasColumn ?column .
            ?column schema:columnName "{column_name}" ;
                    schema:cardinality ?cardinality ;
                    schema:selectivity ?selectivity ;
                    schema:hasIndex ?has_index .
        }}
        """
        results = list(self.jena_kg.query(query))
        if results:
            row = results[0]
            return {
                'cardinality': int(row.cardinality),
                'selectivity': float(row.selectivity),
                'has_index': bool(row.has_index)
            }
        return None
```

#### 3.2 Integrate Vector DB into Cross-Database Executor

**Extend**: `src/core/cross_database_executor.py`

```python
class CrossDatabaseExecutor:
    def __init__(self, ..., weaviate_client=None):
        # ... existing code ...
        self.weaviate_client = weaviate_client or WeaviateClient()

    async def execute_cross_db_join(self, ...):
        # Before executing, check for similar queries
        hints = await self._get_query_hints_from_vector_db(left_query, right_query)

        if hints and hints['confidence'] > 0.7:
            logger.info(
                f"Using optimization hints from similar queries: {hints['recommended_strategy']}"
            )
            # Use recommended strategy from past successful queries

        # ... existing execution code ...

        # After execution, record performance
        await self._record_query_performance(query, result, metrics)

    async def _get_query_hints_from_vector_db(self, left_query, right_query):
        """Find similar queries in Weaviate"""
        combined_query = f"{left_query} JOIN {right_query}"

        results = self.weaviate_client.client.collections.get("OptimizedQuery").query.near_text(
            query=combined_query,
            limit=10,
            return_properties=["strategy_used", "execution_time_ms", "success"]
        )

        if results.objects:
            successful = [obj for obj in results.objects if obj.properties['success']]
            if successful:
                strategies = [obj.properties['strategy_used'] for obj in successful]
                recommended = max(set(strategies), key=strategies.count)
                return {
                    'recommended_strategy': recommended,
                    'confidence': len(successful) / 10
                }
        return None
```

## Implementation Plan

### Phase 1: Extend RDF Builder (Week 1-2)

**Task 1.1**: Extend RDF schema for optimization metadata
- Add table statistics (row count, size, freshness)
- Add column metadata (cardinality, indexes, selectivity)
- Add join path recommendations

**Task 1.2**: Create RDF population script
- Query databases for statistics (ANALYZE tables)
- Extract index information
- Store in Jena knowledge graph

**Task 1.3**: Integrate RDF into Query Pushdown Optimizer
- Query column metadata before pushdown
- Prioritize filters based on selectivity + indexes
- Measure improvement vs baseline

**Task 1.4**: Integrate RDF into Staging Table Manager
- Use join path metadata for strategy selection
- Consider table sizes from RDF
- Track decision accuracy

### Phase 2: Vector DB Integration (Week 3-4)

**Task 2.1**: Define Weaviate schema for query history
- OptimizedQuery class with performance metrics
- Auto-vectorization of SQL text
- Retention policy (keep last 10,000 queries)

**Task 2.2**: Implement query recording
- Hook into Cross-Database Executor
- Record all queries + performance metrics
- Store in Weaviate after execution

**Task 2.3**: Build similarity search
- Find similar queries by SQL embedding
- Filter by success/performance
- Return optimization hints

**Task 2.4**: Integrate hints into optimizers
- Use hints in strategy selection
- Fallback to rule-based if low confidence
- A/B test: hints vs no hints

### Phase 3: Learning Loop (Week 5)

**Task 3.1**: Performance feedback loop
- Track optimization decisions vs actual performance
- Update RDF recommendations based on outcomes
- Retrain confidence thresholds

**Task 3.2**: Dashboard for optimization insights
- Show most common query patterns
- Display optimization success rate
- Visualize strategy effectiveness

**Task 3.3**: Automated tuning
- Adjust thresholds based on historical data
- Identify optimization anti-patterns
- Alert on degraded performance

## Expected Benefits

### Immediate (Phase 1)
- **Better pushdown decisions**: Use indexed, selective columns first
- **Smarter join strategies**: Leverage historical join metadata
- **Reduced planning time**: Pre-computed recommendations in RDF

### Medium-term (Phase 2)
- **Learn from mistakes**: Don't repeat slow query patterns
- **Predict performance**: Estimate execution time before running
- **Semantic optimization**: Handle similar queries consistently

### Long-term (Phase 3)
- **Self-tuning system**: Automatically adjust thresholds
- **Proactive optimization**: Suggest query improvements
- **Cross-database intelligence**: Learn patterns across all databases

## Metrics for Success

1. **Query Performance**:
   - 20% reduction in average query execution time
   - 30% reduction in data transfer (better pushdown)
   - 90% accuracy in strategy selection

2. **Planning Efficiency**:
   - 50% faster query planning (cached in RDF)
   - 80% confidence in optimization decisions
   - <5% strategy changes after learning

3. **User Experience**:
   - Consistent performance for similar queries
   - Predictable execution times
   - Fewer query timeout errors

## Risks and Mitigations

**Risk 1**: RDF/Vector DB unavailable
- **Mitigation**: Graceful fallback to rule-based optimization
- **Code**: Always check if KG/Vector clients are available

**Risk 2**: Stale metadata in RDF
- **Mitigation**: TTL-based refresh (update stats daily)
- **Code**: Track metadata freshness, warn if >24h old

**Risk 3**: Vector similarity may not match SQL semantics
- **Mitigation**: Use confidence thresholds, require >70% confidence
- **Code**: A/B test: hint-based vs rule-based

**Risk 4**: Overhead of querying RDF/Vector on every query
- **Mitigation**: Cache optimization hints (Redis, 1-hour TTL)
- **Code**: Only query KG/Vector if cache miss

## Next Steps

1. Review this plan with team
2. Prioritize Phase 1 vs Phase 2 (can run in parallel)
3. Set up dev environment with Jena + Weaviate populated
4. Implement and test Phase 1.1 (RDF schema extension)
5. Measure baseline performance before enhancements

---

**Status**: Proposed (Not Started)
**Owner**: TBD
**Timeline**: 5 weeks estimated
**Dependencies**: Existing Jena RDF setup, Weaviate vector DB
