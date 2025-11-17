# Database Factory Integration Plan
## SQL Generator Multi-Database Support

**Created**: November 17, 2025
**Status**: Planning Phase
**Estimated Effort**: 3-4 days (24-32 hours)
**Complexity**: High - Core Architecture Change

---

## Executive Summary

This document outlines the plan to integrate the database connector factory with the SQL generator and LLM client, enabling multi-database SQL generation for BigQuery, Snowflake, PostgreSQL, Redshift, and Databricks.

**Current State**: SQL generator is tightly coupled to BigQuery with 14+ hard-coded references
**Target State**: Database-agnostic SQL generator that uses connector factory to support all 5 databases
**Impact**: Core functionality - requires careful testing and backward compatibility

---

## Architecture Changes

### Current Architecture
```
User Query ’ SQL Generator (BigQuery-only) ’ LLM Client ’ BigQuery Client ’ Results
```

### Target Architecture
```
User Query ’ SQL Generator (database-agnostic)
           “
  Database Type Selection (from user context or config)
           “
  Connector Factory ’ Creates appropriate client (BigQuery/Snowflake/etc.)
           “
  LLM Client (with database dialect context)
           “
  Database-specific SQL generation
           “
  Execution via connector ’ Results
```

---

## Task Breakdown

### Task 1: Add Database Type Parameter to SQL Generator
**Estimated Effort**: 2 hours
**Priority**: High
**Dependencies**: None

**Scope**:
- Add `database_type` parameter to `SQLGenerator.__init__()`
  - Default to `'bigquery'` for backward compatibility
  - Validate against supported types from connector factory
- Add `database_config` parameter for database-specific configuration
- Store database type and capabilities as instance variables

**Files to Modify**:
- `backend/src/core/sql_generator.py` (lines 42-176)

**Implementation**:
```python
class SQLGenerator:
    def __init__(
        self,
        database_type: str = 'bigquery',
        database_config: Optional[Dict[str, Any]] = None
    ):
        self.database_type = database_type
        self.database_config = database_config or {}

        # Validate database type
        from src.db.connector_factory import ConnectorFactory
        if database_type not in ConnectorFactory.get_supported_types():
            raise ValueError(f"Unsupported database type: {database_type}")

        # Rest of initialization...
```

**Testing**:
- Verify SQLGenerator() still works (defaults to BigQuery)
- Verify SQLGenerator(database_type='snowflake') raises appropriate errors if not configured
- Verify invalid database types are rejected

---

### Task 2: Replace BigQueryClient with Connector Factory
**Estimated Effort**: 4 hours
**Priority**: High
**Dependencies**: Task 1

**Scope**:
- Replace `BigQueryClient()` instantiation with connector factory
- Rename `self.bq_client` to `self.db_client` for clarity
- Handle database-specific initialization (project/dataset for BigQuery, warehouse for Snowflake, etc.)
- Update all references from `self.bq_client` to `self.db_client`

**Files to Modify**:
- `backend/src/core/sql_generator.py` (all 14+ references)

**Implementation**:
```python
from src.db.connector_factory import ConnectorFactory

class SQLGenerator:
    def __init__(self, database_type='bigquery', database_config=None):
        # ...

        # Create database client using connector factory
        if database_type == 'bigquery':
            # Use existing BigQuery config for backward compatibility
            config = {
                'project_id': settings.google_cloud_project,
                'dataset_id': settings.bigquery_dataset
            }
        else:
            config = database_config or {}

        self.db_client = ConnectorFactory.create_connector(
            database_type,
            config
        )

        # Get database capabilities for dialect-specific handling
        self.db_capabilities = self.db_client.get_capabilities()
```

**Search/Replace Pattern**:
```bash
# Replace all instances (use with caution - verify each)
self.bq_client ’ self.db_client
```

**Testing**:
- Verify BigQuery functionality still works
- Test creating SQL generator with Snowflake connector
- Verify database capabilities are accessible

---

### Task 3: Abstract Database-Specific Attributes
**Estimated Effort**: 3 hours
**Priority**: High
**Dependencies**: Task 2

**Scope**:
- Replace BigQuery-specific attributes (`project_id`, `dataset_id`) with generic equivalents
- Create helper methods to get database-specific qualifiers
- Update schema indexing to use generic attributes

**Problem Areas**:
```python
# Current (BigQuery-specific):
self.db_client.project_id  # Only BigQuery has this
self.db_client.dataset_id   # Only BigQuery has this

# Target (database-agnostic):
self._get_database_qualifier()   # Returns project.dataset for BQ, database for Snowflake, etc.
self._get_schema_qualifier()     # Returns appropriate schema/dataset name
```

**Implementation**:
```python
def _get_database_qualifier(self) -> Optional[str]:
    """Get database-level qualifier (project, database, etc.)"""
    if self.database_type == 'bigquery':
        return getattr(self.db_client, 'project_id', None)
    elif self.database_type in ['snowflake', 'databricks']:
        return getattr(self.db_client, 'database', None)
    elif self.database_type in ['postgresql', 'redshift']:
        return getattr(self.db_client, 'database', None)
    return None

def _get_schema_qualifier(self) -> Optional[str]:
    """Get schema/dataset qualifier"""
    if self.database_type == 'bigquery':
        return getattr(self.db_client, 'dataset_id', None)
    else:
        return getattr(self.db_client, 'schema', None)
```

**Files to Modify**:
- `backend/src/core/sql_generator.py`:
  - Lines 188-189 (schema indexing)
  - Line 756 (cache keys)
  - Any other project_id/dataset_id references

**Testing**:
- Verify schema indexing works for BigQuery
- Test with Snowflake database/schema structure
- Verify cache keys are generated correctly

---

### Task 4: Update Dependent Components
**Estimated Effort**: 4 hours
**Priority**: Medium
**Dependencies**: Tasks 2, 3

**Scope**:
- Update `FormatNormalizer` to accept generic database client
- Update `FinancialMetricsPreCalculator` to work with any database
- Update other components that depend on BigQuery client

**Components to Update**:

1. **FormatNormalizer** (`backend/src/core/format_normalizer.py`):
   ```python
   class FormatNormalizer:
       def __init__(self, db_client, cache_manager=None):
           self.db_client = db_client  # Generic, not BigQuery-specific
           self.db_type = db_client.get_capabilities().database_type
   ```

2. **FinancialMetricsPreCalculator** (`backend/src/core/metrics_precalculation.py`):
   ```python
   class FinancialMetricsPreCalculator:
       def __init__(self, db_client, cache_manager=None):
           self.db_client = db_client  # Generic
           self.db_capabilities = db_client.get_capabilities()
   ```

**Files to Modify**:
- `backend/src/core/format_normalizer.py`
- `backend/src/core/metrics_precalculation.py`
- Any other components passed `bq_client`

**Testing**:
- Verify FormatNormalizer works with BigQuery
- Test metrics pre-calculation with different databases
- Ensure no BigQuery-specific assumptions remain

---

### Task 5: Add Database Dialect to LLM Prompts
**Estimated Effort**: 6 hours
**Priority**: High
**Dependencies**: Tasks 1-4

**Scope**:
- Modify LLM client or SQL generator to include database dialect in prompts
- Add database-specific SQL syntax guidelines
- Handle dialect differences (date functions, string concat, etc.)

**Implementation**:
```python
def _build_llm_prompt(self, user_query: str, schemas: List[Dict]) -> str:
    """Build LLM prompt with database dialect context"""

    # Get database-specific context
    db_name = self.db_capabilities.database_name
    dialect_guide = self._get_dialect_guide()

    prompt = f"""
You are a SQL expert generating queries for {db_name}.

DATABASE DIALECT: {self.database_type}
{dialect_guide}

User Question: {user_query}

Available Tables:
{self._format_schemas(schemas)}

Generate a valid {self.database_type} SQL query...
"""
    return prompt

def _get_dialect_guide(self) -> str:
    """Get database-specific SQL syntax guidelines"""
    guides = {
        'bigquery': """
- Use backticks for table names: `project.dataset.table`
- Date formatting: FORMAT_DATE('%Y-%m-%d', date_column)
- String concatenation: CONCAT(str1, str2) or ||
- Supports STRUCT and ARRAY types
        """,
        'snowflake': """
- Three-part names: database.schema.table
- Date formatting: TO_CHAR(date_column, 'YYYY-MM-DD')
- String concatenation: CONCAT(str1, str2) or ||
- Supports VARIANT for semi-structured data
        """,
        'postgresql': """
- Schema-qualified names: schema.table
- Date formatting: TO_CHAR(date_column, 'YYYY-MM-DD')
- String concatenation: CONCAT(str1, str2) or ||
- Case-insensitive search: ILIKE operator
        """,
        'redshift': """
- Similar to PostgreSQL but with limitations
- No recursive CTEs
- SUPER type for semi-structured data
- String concatenation: || or CONCAT
        """,
        'databricks': """
- Three-part names: catalog.schema.table
- Date formatting: DATE_FORMAT(date_column, 'yyyy-MM-dd')
- Spark SQL dialect
- Supports Delta Lake features
        """
    }
    return guides.get(self.database_type, "")
```

**Files to Modify**:
- `backend/src/core/sql_generator.py` (prompt building methods)
- Potentially `backend/src/core/llm_client.py` if prompts are built there

**Testing**:
- Generate queries for each database type
- Verify dialect-specific syntax is used
- Test with queries requiring database-specific functions

---

### Task 6: Update Query Validation and Execution
**Estimated Effort**: 3 hours
**Priority**: Medium
**Dependencies**: Tasks 2, 3

**Scope**:
- Update query validation to use generic connector `validate_query()` method
- Update query execution to use generic connector `execute_query()` method
- Handle database-specific pagination (page_token for BigQuery, limit/offset for others)

**Current Issues**:
```python
# Lines 592, 614, 629, 1020, 1034
validation = self.bq_client.validate_query(result["sql"])

# Line 679
test_results = self.bq_client.execute_query(test_sql)
```

**Solution**: Already using base connector interface methods - just need to update variable name from `bq_client` to `db_client`.

**Testing**:
- Verify query validation works for all databases
- Test query execution with pagination
- Ensure error handling works across databases

---

### Task 7: Add Database Type to API Routes
**Estimated Effort**: 4 hours
**Priority**: Medium
**Dependencies**: Tasks 1-6

**Scope**:
- Add `database_type` parameter to query execution endpoints
- Update API models to include database selection
- Add database type to user context/session
- Implement database type routing based on user permissions

**Files to Modify**:
- `backend/src/api/routes.py` (main query endpoint)
- `backend/src/api/models.py` (request/response models)

**Implementation**:
```python
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    database_type: str = 'bigquery'  # Default to BigQuery
    database_config: Optional[Dict[str, Any]] = None
    # ... other fields

@router.post("/api/v1/query")
async def execute_query_endpoint(
    request: QueryRequest,
    user: Dict = Depends(require_auth)
):
    # Check user has permission for database type
    from src.db.connector_factory import ConnectorFactory
    has_access = ConnectorFactory.check_user_access(
        user_id=user['id'],
        database_type=request.database_type,
        required_level='read',
        organization_id=user.get('organization_id')
    )

    if not has_access:
        raise HTTPException(403, "No access to this database type")

    # Create SQL generator with database type
    generator = SQLGenerator(
        database_type=request.database_type,
        database_config=request.database_config
    )

    result = generator.generate_sql(request.query)
    # ...
```

**Testing**:
- Test API with different database_type values
- Verify permission checks work
- Test backward compatibility (no database_type specified)

---

### Task 8: Comprehensive Testing and Documentation
**Estimated Effort**: 6 hours
**Priority**: High
**Dependencies**: All previous tasks

**Scope**:
- Create end-to-end tests for each database type
- Test SQL generation accuracy for each dialect
- Performance testing (ensure no regression)
- Update documentation

**Test Coverage**:

1. **Unit Tests**:
   - SQLGenerator initialization with each database type
   - Database-agnostic helper methods
   - Dialect guide generation
   - Connector factory integration

2. **Integration Tests**:
   ```python
   def test_bigquery_query_generation():
       generator = SQLGenerator(database_type='bigquery')
       result = generator.generate_sql("Show me top 10 customers by revenue")
       assert '`' in result['sql']  # BigQuery uses backticks
       assert 'LIMIT 10' in result['sql']

   def test_snowflake_query_generation():
       generator = SQLGenerator(
           database_type='snowflake',
           database_config={'account': 'test', 'user': 'test', ...}
       )
       result = generator.generate_sql("Show me top 10 customers by revenue")
       assert 'database.schema.table' in result['sql']  # Three-part names
       assert 'LIMIT 10' in result['sql']
   ```

3. **End-to-End Tests**:
   - Full query flow from API to results for each database
   - Permission-based database access
   - Multi-database session handling

**Documentation to Update**:
- `MULTI_DATABASE_IMPLEMENTATION_PLAN.md` - Mark task as complete
- `DATABASE_FACTORY_INTEGRATION_PLAN.md` - Add implementation notes
- API documentation - Add database_type parameter
- Configuration guide - Add database-specific setup for SQL generation

**Files to Create**:
- `backend/tests/test_multi_database_sql_generation.py`
- `backend/tests/integration/test_database_factory_integration.py`

---

## Risk Assessment

### High Risks

1. **Breaking Changes to Existing BigQuery Functionality**
   - **Mitigation**: Maintain backward compatibility, extensive testing
   - **Rollback Plan**: Git revert, feature flag to disable multi-database

2. **Performance Degradation**
   - **Risk**: Additional abstraction layer may slow down queries
   - **Mitigation**: Performance benchmarks before/after, optimize hot paths
   - **Threshold**: <5% performance degradation acceptable

3. **SQL Dialect Errors**
   - **Risk**: LLM generates incorrect SQL for non-BigQuery databases
   - **Mitigation**: Comprehensive dialect guides, validation, extensive testing
   - **Monitoring**: Track query validation failure rates per database

### Medium Risks

4. **Incomplete Database-Specific Feature Support**
   - **Risk**: Some features may not work on all databases
   - **Mitigation**: Document database-specific limitations, graceful degradation

5. **Configuration Complexity**
   - **Risk**: Users may struggle with database-specific configuration
   - **Mitigation**: Clear documentation, configuration validation, helpful error messages

---

## Rollback Plan

If critical issues arise during deployment:

1. **Immediate Rollback** (< 5 minutes):
   ```python
   # Add feature flag to sql_generator.py __init__
   USE_MULTI_DATABASE = os.getenv('ENABLE_MULTI_DATABASE', 'false').lower() == 'true'

   if not USE_MULTI_DATABASE:
       # Use legacy BigQueryClient
       self.db_client = BigQueryClient()
   ```

2. **Git Revert** (< 10 minutes):
   ```bash
   git revert <commit-hash>
   git push origin main
   # Redeploy
   ```

3. **Gradual Rollout**:
   - Deploy to staging environment first
   - Test with synthetic queries
   - Enable for beta users
   - Monitor error rates
   - Gradual rollout to all users

---

## Success Metrics

1. **Functionality**:
   -  All 5 database types supported
   -  100% backward compatibility with existing BigQuery functionality
   -  <95% SQL generation accuracy for each database

2. **Performance**:
   -  <5% performance degradation vs. current BigQuery-only implementation
   -  Query generation time <3 seconds (p95)

3. **Reliability**:
   -  Query validation failure rate <5% per database
   -  No increase in error rates

4. **Code Quality**:
   -  Test coverage >80% for new code
   -  All tests passing
   -  No regressions in existing tests

---

## Timeline and Sequencing

### Phase 1: Foundation (Day 1-2, 12 hours)
- Task 1: Add database type parameter (2h)
- Task 2: Replace BigQueryClient with connector factory (4h)
- Task 3: Abstract database-specific attributes (3h)
- Task 6: Update query validation/execution (3h)

### Phase 2: Integration (Day 2-3, 10 hours)
- Task 4: Update dependent components (4h)
- Task 5: Add database dialect to LLM prompts (6h)

### Phase 3: API and Testing (Day 3-4, 10 hours)
- Task 7: Add database type to API routes (4h)
- Task 8: Comprehensive testing and documentation (6h)

**Total: 32 hours (~4 days)**

---

## Dependencies and Prerequisites

**Before Starting**:
-  All 5 database connectors implemented and tested
-  Connector factory with permission system
-  Base connector interface standardized
- ó Database configuration guide (from MULTI_DATABASE_IMPLEMENTATION_PLAN.md)

**External Dependencies**:
- None - all database connectors are already available

---

## Implementation Notes

### Backward Compatibility Strategy

To ensure zero disruption to existing deployments:

1. **Default to BigQuery**: All parameters default to BigQuery behavior
2. **Gradual Migration**: Existing code continues to work without changes
3. **Opt-in Multi-Database**: New database types must be explicitly specified
4. **Feature Flags**: Can disable multi-database support if issues arise

### Configuration Management

Database configurations should be managed at multiple levels:

1. **Environment Variables** (for default/system-wide settings)
2. **User Preferences** (per-user database type selection)
3. **API Parameters** (per-request database override)
4. **Permission-based** (users only see databases they have access to)

Priority: API Parameters > User Preferences > Environment Variables

---

## Next Steps

1. **Review this plan** with the team
2. **Commit current work** (Snowflake + BigQuery connector enhancements)
3. **Create GitHub issue/epic** tracking all 8 tasks
4. **Schedule implementation** sprint (4 days dedicated work)
5. **Set up monitoring** for the new functionality

---

## Appendix: Code Locations Reference

**Key Files to Modify**:
- `backend/src/core/sql_generator.py` (1,281 lines) - PRIMARY
- `backend/src/core/format_normalizer.py` - Database client usage
- `backend/src/core/metrics_precalculation.py` - Database client usage
- `backend/src/api/routes.py` - Add database_type parameter
- `backend/src/api/models.py` - Request/response models

**BigQuery References** (14+ locations in sql_generator.py):
- Line 35: Import
- Line 45: Instantiation
- Line 80: FormatNormalizer dependency
- Line 159: FinancialMetricsPreCalculator dependency
- Lines 181-192: Schema indexing
- Lines 592, 614, 629, 1020, 1034: Query validation
- Line 679: Query execution
- Line 756: Cache key generation
- Lines 775, 851, 1027: Schema retrieval

**Testing Files to Create**:
- `backend/tests/test_multi_database_sql_generation.py`
- `backend/tests/integration/test_database_factory_integration.py`
- `backend/tests/e2e/test_snowflake_query_flow.py`
- `backend/tests/e2e/test_databricks_query_flow.py`

---

**Document Version**: 1.0
**Last Updated**: November 17, 2025
**Author**: Claude Code
**Status**: Ready for Review
