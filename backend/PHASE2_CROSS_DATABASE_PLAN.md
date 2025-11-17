# Phase 2: Cross-Database Features - Implementation Plan

**Date**: November 17, 2025
**Branch**: feature/phase2-cross-database
**Estimated Time**: 4-6 weeks
**Status**: 🚧 PLANNING

---

## Overview

Enable intelligent cross-database query execution with SQL dialect translation, federated query planning, and performance optimization.

### Goals

1. **SQL Dialect Translation** - Translate SQL between different database dialects
2. **Cross-Database Queries** - Execute queries that span multiple databases
3. **Federated Query Planning** - Optimize execution across databases
4. **Performance Optimization** - Cache, parallelize, and optimize queries

---

## Task Breakdown

### Week 1-2: SQL Dialect Translator

#### Task 1.1: Core Dialect Translator

**File**: `backend/src/core/sql_dialect_translator.py` (NEW)

**Features**:
- Translate SQL between BigQuery, Snowflake, PostgreSQL, Redshift, Databricks
- Use `sqlglot` library for AST-based translation
- Handle dialect-specific functions (DATE_SUB → DATE_TRUNC, etc.)
- Preserve query semantics during translation

**Implementation**:
```python
from typing import Dict, Optional
import sqlglot
from src.db.database_capabilities import DatabaseCapabilities

class SQLDialectTranslator:
    """
    Translate SQL between different database dialects using sqlglot.
    """

    DIALECT_MAP = {
        'bigquery': 'bigquery',
        'snowflake': 'snowflake',
        'postgresql': 'postgres',
        'redshift': 'redshift',
        'databricks': 'databricks'
    }

    def translate(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Translate SQL from source dialect to target dialect.

        Args:
            sql: SQL query to translate
            source_dialect: Source database type
            target_dialect: Target database type
            validate: Validate syntax after translation

        Returns:
            {
                'translated_sql': str,
                'source_dialect': str,
                'target_dialect': str,
                'changes': List[str],
                'warnings': List[str]
            }
        """
        pass

    def get_translation_cost(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> float:
        """
        Estimate complexity/cost of translating query.
        Returns 0-1 score (0=trivial, 1=complex/lossy).
        """
        pass
```

**Tests**: `tests/unit/core/test_sql_dialect_translator.py`

#### Task 1.2: Dialect-Specific Handlers

**Files**:
- `backend/src/core/dialect_handlers/bigquery_handler.py` (NEW)
- `backend/src/core/dialect_handlers/snowflake_handler.py` (NEW)
- `backend/src/core/dialect_handlers/postgresql_handler.py` (NEW)

**Features**:
- Handle database-specific syntax quirks
- Custom function mappings
- Data type conversions

**Example Translations**:
```python
# BigQuery → Snowflake
DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
→ DATEADD(DAY, -7, CURRENT_DATE())

# Snowflake → PostgreSQL
DATEADD(DAY, -7, CURRENT_DATE())
→ CURRENT_DATE - INTERVAL '7 days'

# BigQuery → PostgreSQL
STRING_AGG(column, ', ')
→ STRING_AGG(column, ', ')  # Same syntax!

# Databricks → BigQuery
DATE_FORMAT(date_column, 'yyyy-MM-dd')
→ FORMAT_DATE('%Y-%m-%d', date_column)
```

---

### Week 3-4: Cross-Database Query Executor

#### Task 2.1: Federated Query Planner

**File**: `backend/src/core/federated_query_planner.py` (NEW)

**Features**:
- Analyze queries spanning multiple databases
- Determine optimal execution strategy
- Split queries into sub-queries per database
- Plan data movement (which database to join in)

**Implementation**:
```python
class FederatedQueryPlanner:
    """
    Plan execution of queries spanning multiple databases.
    """

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to determine which databases are needed.

        Returns:
            {
                'databases': ['bigquery', 'snowflake'],
                'tables_by_db': {
                    'bigquery': ['dataset.table1'],
                    'snowflake': ['db.schema.table2']
                },
                'join_strategy': 'fetch_to_bigquery',
                'estimated_rows': {
                    'bigquery.table1': 1000000,
                    'snowflake.table2': 5000
                },
                'recommended_approach': 'move_snowflake_to_bigquery'
            }
        """
        pass

    def create_execution_plan(
        self,
        query: str,
        user_preference: Optional[str] = None
    ) -> ExecutionPlan:
        """
        Create optimal execution plan for federated query.

        Strategies:
        - move_to_primary: Fetch from secondary DB, execute in primary
        - distributed: Execute parts in each DB, merge results
        - materialize: Create temp table in one DB, join there
        """
        pass
```

#### Task 2.2: Cross-Database Executor

**File**: `backend/src/core/cross_database_executor.py` (NEW)

**Features**:
- Execute federated queries across multiple databases
- Handle data movement between databases
- Merge results from multiple sources
- Support for JOINs across databases

**Implementation**:
```python
class CrossDatabaseExecutor:
    """
    Execute queries across multiple databases.
    """

    def __init__(self, connector_factory: ConnectorFactory):
        self.factory = connector_factory
        self.planner = FederatedQueryPlanner()
        self.translator = SQLDialectTranslator()

    async def execute_federated_query(
        self,
        query: str,
        primary_database: str,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Execute query spanning multiple databases.

        Steps:
        1. Analyze query to identify databases needed
        2. Check user permissions for all databases
        3. Create execution plan
        4. Execute sub-queries in parallel
        5. Merge results
        6. Return unified result set
        """
        pass

    async def execute_cross_db_join(
        self,
        left_db: str,
        left_query: str,
        right_db: str,
        right_query: str,
        join_condition: str,
        join_type: str = 'INNER'
    ) -> pd.DataFrame:
        """
        Execute JOIN between tables in different databases.
        """
        pass
```

---

### Week 5: Performance Optimization

#### Task 3.1: Query Result Caching

**File**: `backend/src/core/cross_db_cache_manager.py` (NEW)

**Features**:
- Cache results per database
- Track data freshness across databases
- Invalidate cache when data changes
- Support for partial cache hits

**Implementation**:
```python
class CrossDatabaseCacheManager:
    """
    Manage caching for cross-database queries.
    """

    def get_cache_key(
        self,
        query: str,
        databases: List[str],
        user_context: Dict[str, Any]
    ) -> str:
        """
        Generate cache key for federated query.
        Includes: query hash, database versions, user permissions.
        """
        pass

    async def get_cached_result(
        self,
        cache_key: str,
        max_age_seconds: int = 3600
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and fresh.
        """
        pass

    async def cache_result(
        self,
        cache_key: str,
        result: Dict[str, Any],
        ttl: int = 3600,
        databases_accessed: List[str] = None
    ):
        """
        Cache federated query result.
        """
        pass
```

#### Task 3.2: Parallel Execution

**Features**:
- Execute sub-queries in parallel across databases
- Use asyncio for concurrent execution
- Handle errors gracefully (partial results)
- Timeout management per database

**Implementation**:
```python
class ParallelQueryExecutor:
    """
    Execute queries in parallel across multiple databases.
    """

    async def execute_parallel(
        self,
        queries_by_database: Dict[str, str],
        timeout_per_db: int = 300
    ) -> Dict[str, Any]:
        """
        Execute queries in parallel, return combined results.

        Returns:
            {
                'results': {
                    'bigquery': pd.DataFrame(...),
                    'snowflake': pd.DataFrame(...)
                },
                'execution_times': {
                    'bigquery': 2.5,
                    'snowflake': 1.8
                },
                'errors': {}
            }
        """
        pass
```

---

### Week 6: Integration & API

#### Task 4.1: API Endpoints

**File**: `backend/src/api/cross_database_routes.py` (NEW)

**Endpoints**:

```python
@router.post("/api/v1/cross-db/query")
async def execute_cross_database_query(
    request: CrossDatabaseQueryRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Execute query across multiple databases.

    Request:
        {
            "query": "SELECT * FROM bigquery.dataset.table1 JOIN snowflake.db.schema.table2",
            "primary_database": "bigquery",
            "strategy": "auto" | "move_to_primary" | "distributed"
        }

    Response:
        {
            "rows": [...],
            "total_rows": 1234,
            "databases_accessed": ["bigquery", "snowflake"],
            "execution_plan": {...},
            "execution_time_ms": 5432,
            "from_cache": false
        }
    """
    pass

@router.post("/api/v1/cross-db/translate")
async def translate_sql_dialect(
    request: TranslateSQLRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Translate SQL from one dialect to another.

    Request:
        {
            "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
            "source_dialect": "bigquery",
            "target_dialect": "snowflake"
        }

    Response:
        {
            "translated_sql": "SELECT DATEADD(DAY, -7, CURRENT_DATE())",
            "changes": ["DATE_SUB → DATEADD"],
            "warnings": [],
            "is_lossless": true
        }
    """
    pass

@router.post("/api/v1/cross-db/plan")
async def create_execution_plan(
    request: ExecutionPlanRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Create execution plan for federated query.

    Returns plan without executing query.
    """
    pass
```

#### Task 4.2: LLM Integration

**Update**: `backend/src/core/sql_generator.py`

**Features**:
- LLM can generate cross-database queries
- Auto-detect when multiple databases are needed
- Suggest optimal primary database
- Generate federated query syntax

**Example**:
```python
# User query: "Show me BigQuery sales data joined with Snowflake customer data"
# LLM generates:
SELECT
    bq.sale_date,
    bq.amount,
    sf.customer_name,
    sf.customer_tier
FROM bigquery.sales.transactions bq
JOIN snowflake.customers.dim_customer sf
    ON bq.customer_id = sf.customer_id
WHERE bq.sale_date >= CURRENT_DATE() - INTERVAL 30 DAY
```

---

## Implementation Order

### Phase 2A: Foundation (Week 1-2)
1. ✅ Install sqlglot: `pip install sqlglot`
2. ⏳ Implement `SQLDialectTranslator` core
3. ⏳ Add dialect-specific handlers
4. ⏳ Write unit tests for translation
5. ⏳ Validate with sample queries

### Phase 2B: Federated Queries (Week 3-4)
1. ⏳ Implement `FederatedQueryPlanner`
2. ⏳ Implement `CrossDatabaseExecutor`
3. ⏳ Add cross-database JOIN support
4. ⏳ Write integration tests
5. ⏳ Test with real databases

### Phase 2C: Optimization (Week 5)
1. ⏳ Implement `CrossDatabaseCacheManager`
2. ⏳ Add `ParallelQueryExecutor`
3. ⏳ Performance benchmarking
4. ⏳ Optimize data movement strategies

### Phase 2D: Integration (Week 6)
1. ⏳ Add API endpoints
2. ⏳ Update LLM prompts for cross-DB queries
3. ⏳ Add frontend support
4. ⏳ End-to-end testing
5. ⏳ Documentation

---

## Dependencies

### Python Packages
```bash
# Add to requirements.txt
sqlglot==20.0.0        # SQL dialect translation
pandas==2.0.0          # DataFrame operations for data merging
pyarrow==14.0.0        # Efficient data serialization
```

### External Services
- All 5 database connectors (already implemented in Phase 1)
- Redis (for cross-database caching)

---

## Testing Strategy

### Unit Tests
- SQL translation accuracy
- Execution plan generation
- Cache key generation
- Parallel execution

### Integration Tests
- Cross-database JOINs
- Data movement between databases
- Cache invalidation
- Error handling

### E2E Tests
- BigQuery ↔ Snowflake queries
- PostgreSQL ↔ Databricks queries
- Three-database queries
- Performance benchmarks

---

## Success Criteria

### Functional Requirements
- ✅ Translate SQL between all 5 database dialects
- ✅ Execute JOINs across 2+ databases
- ✅ Cache cross-database results
- ✅ Parallel query execution
- ✅ LLM generates federated queries

### Performance Requirements
- SQL translation: < 100ms
- Cross-DB JOIN (small tables): < 5 seconds
- Cross-DB JOIN (large tables): < 30 seconds
- Cache hit rate: > 60%
- Parallel speedup: 2-3x for 3 databases

### Quality Requirements
- Test coverage: > 80%
- Translation accuracy: > 95%
- No data loss during translation
- Proper error handling and rollback

---

## Risks & Mitigation

### Risk 1: SQL Translation Accuracy
**Mitigation**:
- Use sqlglot (battle-tested library)
- Extensive test suite for each dialect pair
- Fallback to manual translation for complex queries

### Risk 2: Data Movement Performance
**Mitigation**:
- Intelligent query planning (move small tables, not large)
- Use compression for data transfer
- Parallel execution where possible

### Risk 3: Permission Complexity
**Mitigation**:
- Check permissions for all databases before execution
- Clear error messages when access denied
- Audit log for cross-database access

### Risk 4: Cost Overruns
**Mitigation**:
- Estimate query cost before execution
- Warn user if query is expensive
- Set hard limits on data movement

---

## Future Enhancements (Phase 3)

1. **Materialized Views** - Cache cross-database JOINs
2. **Query Optimization** - Pushdown predicates, reduce data movement
3. **Data Lineage** - Track data sources across databases
4. **Incremental Updates** - Update cross-DB views incrementally
5. **Cost Tracking** - Track costs per database and federated query

---

## Next Steps

### Immediate (This Week)
1. Install sqlglot package
2. Create basic SQLDialectTranslator
3. Test BigQuery ↔ Snowflake translation
4. Validate with sample queries

### Short-term (Next 2 Weeks)
1. Implement full dialect translator
2. Add federated query planner
3. Basic cross-database executor

### Long-term (4-6 Weeks)
1. Complete Phase 2 implementation
2. Performance optimization
3. API endpoints and integration
4. Production deployment

---

**Status**: 🚧 READY TO START
**First Task**: Install sqlglot and create SQLDialectTranslator
**Estimated Completion**: 4-6 weeks from start date
