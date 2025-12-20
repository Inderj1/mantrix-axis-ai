# SQL Generator Refactoring Plan

## Problem Statement
`sql_generator.py` is ~2971 lines with mixed responsibilities:
- LLM-based SQL generation
- Query execution
- Query analysis and optimization
- Connector management
- Schema/table lookup
- Cross-database execution

This makes it hard to:
1. Debug issues (like the `requires_async` bug)
2. Test individual components
3. Understand the flow
4. Make changes without side effects

## Current Architecture (Monolithic)

```
routes.py
    └── SQLGenerator.generate_sql()  [1020-1737: 717 lines]
            ├── Schema lookup
            ├── Financial parsing
            ├── Knowledge graph enhancement
            ├── LLM call
            ├── Validation
            └── Format normalization

    └── SQLGenerator.execute_query()  [2202-2654: 452 lines]
            ├── Connector selection
            ├── Query analysis/optimization
            ├── Strategy selection (DIRECT/OPTIMIZED/FEDERATED)
            ├── requires_async check (BURIED HERE!)
            ├── Materialized view lookup
            └── Actual execution
```

## Proposed Architecture (Separated Concerns)

```
routes.py
    └── QueryOrchestrator.process_query()
            │
            ├── 1. QueryAnalyzer.analyze()
            │       └── Returns: tables, row counts, strategy, requires_async
            │
            ├── 2. [If requires_async] → Return early with long_running status
            │
            ├── 3. SQLGenerator.generate()
            │       └── Returns: SQL, explanation, tables_used
            │
            └── 4. QueryExecutor.execute()
                    └── Returns: results, row_count, execution_time
```

## New Module Breakdown

### 1. `query_analyzer.py` (~300 lines)
**Responsibility**: Analyze SQL/tables to determine execution strategy

```python
class QueryAnalyzer:
    def analyze(self, sql: str, database_type: str) -> QueryAnalysis:
        """
        Analyzes a SQL query and returns execution metadata.

        Returns:
            QueryAnalysis with:
            - tables: List[str]
            - table_row_counts: Dict[str, int]
            - largest_table: str
            - largest_table_rows: int
            - strategy: ExecutionStrategy (DIRECT/OPTIMIZED/FEDERATED)
            - requires_async: bool (True if any table > 1B rows)
            - estimated_result_rows: int
            - has_aggregation: bool
            - has_joins: bool
            - supports_pagination: bool
            - warnings: List[str]
        """

    def estimate_row_count(self, table: str) -> int:
        """Get row count from Jena/Weaviate metadata."""

    def determine_strategy(self, analysis: QueryAnalysis) -> ExecutionStrategy:
        """Select DIRECT/OPTIMIZED/FEDERATED based on analysis."""
```

**Methods to extract from sql_generator.py**:
- Row count lookup logic (currently in SingleDatabaseQueryOptimizer)
- Strategy selection logic
- `requires_async` determination

### 2. `query_executor.py` (~400 lines)
**Responsibility**: Execute SQL queries on various databases

```python
class QueryExecutor:
    def execute(
        self,
        sql: str,
        database_type: str,
        analysis: Optional[QueryAnalysis] = None
    ) -> ExecutionResult:
        """
        Execute SQL and return results.

        Returns:
            ExecutionResult with:
            - rows: List[Dict]
            - row_count: int
            - execution_time_seconds: float
            - truncated: bool
            - pagination: Optional[PaginationInfo]
        """

    def execute_federated(
        self,
        sql: str,
        database_type: str,
        analysis: QueryAnalysis
    ) -> ExecutionResult:
        """Execute large queries through federation path."""

    def get_connector(self, database_type: str) -> BaseDatabaseConnector:
        """Get appropriate connector for database type."""
```

**Methods to extract from sql_generator.py**:
- `execute_query()` (lines 2202-2654)
- `_execute_federated_single_db()` (lines 2656-2800)
- Connector selection logic

### 3. `sql_generator.py` (Simplified, ~500 lines)
**Responsibility**: ONLY generate SQL from natural language using LLM

```python
class SQLGenerator:
    def generate(
        self,
        query: str,
        schemas: List[Dict],
        conversation_context: Optional[Dict] = None,
        persona_context: Optional[Dict] = None
    ) -> GenerationResult:
        """
        Generate SQL from natural language.

        Returns:
            GenerationResult with:
            - sql: str
            - explanation: str
            - tables_used: List[str]
            - confidence_score: float
            - warnings: List[str]
        """

    def _build_prompt(self, query: str, schemas: List[Dict]) -> str:
        """Build LLM prompt with schema context."""

    def _call_llm(self, prompt: str) -> str:
        """Call Anthropic API."""

    def _parse_response(self, response: str) -> GenerationResult:
        """Parse LLM response into structured result."""
```

**What stays in sql_generator.py**:
- `generate_sql()` core LLM logic
- Prompt building
- Response parsing
- Financial context integration

**What gets removed**:
- All execution logic
- Connector management
- Query analysis
- Strategy selection

### 4. `query_orchestrator.py` (~200 lines)
**Responsibility**: Coordinate the query processing pipeline

```python
class QueryOrchestrator:
    def __init__(
        self,
        analyzer: QueryAnalyzer,
        generator: SQLGenerator,
        executor: QueryExecutor,
        schema_service: SchemaService
    ):
        pass

    def process_query(
        self,
        question: str,
        database_type: str,
        execute: bool = True,
        conversation_context: Optional[Dict] = None
    ) -> QueryResult:
        """
        Main entry point for query processing.

        Flow:
        1. Get relevant schemas
        2. Generate SQL
        3. Analyze SQL for execution strategy
        4. If requires_async, return early
        5. Execute and return results
        """

    def preview_query(self, question: str) -> PreviewResult:
        """Quick preview without execution - for UI warnings."""
```

### 5. `schema_service.py` (~200 lines)
**Responsibility**: Schema lookup and table metadata

```python
class SchemaService:
    def get_relevant_schemas(
        self,
        query: str,
        limit: int = 5,
        connector_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Vector search for relevant tables."""

    def get_table_metadata(self, table: str) -> TableMetadata:
        """Get row count, columns, etc. from Weaviate/Jena."""
```

**Methods to extract from sql_generator.py**:
- `_get_relevant_schemas()` (lines 1754-1860)
- `_per_connector_vector_search()` (lines 1862-1952)
- Schema indexing logic

## Migration Steps

### Phase 1: Create New Modules (Non-Breaking)
1. Create `query_analyzer.py` with `QueryAnalysis` dataclass
2. Create `query_executor.py` with execution logic
3. Create `schema_service.py` with schema lookup
4. Create `query_orchestrator.py` to coordinate

### Phase 2: Wire Up New Architecture
1. Update `routes.py` to use `QueryOrchestrator`
2. Add `requires_async` check at orchestrator level
3. Keep old `SQLGenerator` methods as fallback

### Phase 3: Simplify sql_generator.py
1. Remove execution logic (now in QueryExecutor)
2. Remove analysis logic (now in QueryAnalyzer)
3. Remove schema lookup (now in SchemaService)
4. Keep only LLM generation

### Phase 4: Cleanup
1. Remove deprecated methods
2. Update tests
3. Update documentation

## Key Benefits

1. **Clear requires_async Flow**:
   ```python
   # In QueryOrchestrator.process_query():
   analysis = self.analyzer.analyze(sql, database_type)

   if analysis.requires_async:
       return QueryResult(
           status="long_running",
           requires_async=True,
           largest_table_rows=analysis.largest_table_rows,
           estimated_minutes=analysis.estimated_minutes
       )
   ```

2. **Easier Testing**: Each module can be unit tested independently

3. **Better Debugging**: Clear boundaries make issues easier to locate

4. **Flexibility**: Can swap implementations (e.g., different LLM providers)

## File Size Targets

| File | Current | Target |
|------|---------|--------|
| sql_generator.py | 2971 lines | ~500 lines |
| query_analyzer.py | N/A | ~300 lines |
| query_executor.py | N/A | ~400 lines |
| query_orchestrator.py | N/A | ~200 lines |
| schema_service.py | N/A | ~200 lines |
| **Total** | 2971 lines | ~1600 lines |

## Timeline Estimate

- Phase 1: Create new modules - 1-2 hours
- Phase 2: Wire up routes.py - 1 hour
- Phase 3: Simplify sql_generator.py - 2-3 hours
- Phase 4: Testing and cleanup - 1-2 hours

**Total: 5-8 hours of focused work**

## Immediate Win: requires_async Fix

Once `QueryOrchestrator` is in place, the fix is simple:

```python
class QueryOrchestrator:
    def process_query(self, question: str, ...) -> QueryResult:
        # 1. Get schemas
        schemas = self.schema_service.get_relevant_schemas(question)

        # 2. Generate SQL
        generation = self.generator.generate(question, schemas)

        # 3. Analyze for execution strategy
        analysis = self.analyzer.analyze(generation.sql, database_type)

        # 4. CHECK REQUIRES_ASYNC HERE - SINGLE CLEAR LOCATION!
        if analysis.requires_async:
            return QueryResult(
                status="long_running",
                requires_async=True,
                sql=generation.sql,
                largest_table_rows=analysis.largest_table_rows,
                estimated_minutes=self._estimate_minutes(analysis)
            )

        # 5. Execute
        result = self.executor.execute(generation.sql, database_type, analysis)

        return QueryResult(status="complete", ...)
```
