# Phase 2: Cross-Database Features - Task List

**Date**: November 17, 2025
**Status**: 🚧 IN PROGRESS
**Current Step**: Task 1.1 - SQL Dialect Translator Core

---

## Quick Start Checklist

### ✅ Prerequisites (COMPLETED)
- [x] Phase 1 multi-database support completed
- [x] All 5 database connectors implemented
- [x] sqlglot package installed (v28.0.0)
- [x] Phase 2 implementation plan created
- [x] requirements.txt updated

### ⏳ Next Session - Start Here

**First Task**: Create SQL Dialect Translator
**Estimated Time**: 2-3 hours
**Files to Create**: 3 new files
**Tests to Write**: 1 test file

---

## Task 1: SQL Dialect Translator Implementation

### Task 1.1: Create Core Translator ⏳ NEXT

**File**: `backend/src/core/sql_dialect_translator.py` (NEW)

**Steps**:
1. Create the file structure
2. Import dependencies (sqlglot, typing, structlog)
3. Define DIALECT_MAP constant
4. Implement `translate()` method
5. Implement `get_translation_cost()` method
6. Implement `_detect_changes()` helper
7. Implement `_validate_translation()` helper
8. Add comprehensive docstrings

**Implementation Template**:
```python
"""
SQL Dialect Translator

Translates SQL queries between different database dialects using sqlglot.
Supports: BigQuery, Snowflake, PostgreSQL, Redshift, Databricks.
"""
import sqlglot
from sqlglot import parse_one, transpile
from typing import Dict, List, Optional, Any
import structlog
from dataclasses import dataclass

logger = structlog.get_logger()


@dataclass
class TranslationResult:
    """Result of SQL dialect translation."""
    translated_sql: str
    source_dialect: str
    target_dialect: str
    changes: List[str]
    warnings: List[str]
    is_lossless: bool
    confidence_score: float  # 0-1, 1 = perfect translation


class SQLDialectTranslator:
    """
    Translate SQL between database dialects.

    Uses sqlglot for AST-based translation to ensure semantic correctness.
    """

    # Map our database types to sqlglot dialect names
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
    ) -> TranslationResult:
        """
        Translate SQL from source dialect to target dialect.

        Args:
            sql: SQL query to translate
            source_dialect: Source database type (bigquery, snowflake, etc.)
            target_dialect: Target database type
            validate: Validate syntax after translation

        Returns:
            TranslationResult with translated SQL and metadata

        Raises:
            ValueError: If dialects are invalid or SQL is malformed
            TranslationError: If translation fails
        """
        # TODO: Implement
        pass

    def get_translation_cost(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> float:
        """
        Estimate complexity/cost of translating query.

        Returns:
            Float 0-1 where:
            - 0 = trivial (identical syntax)
            - 0.5 = moderate (some function changes)
            - 1 = complex (may lose functionality)
        """
        # TODO: Implement
        pass

    def batch_translate(
        self,
        queries: List[str],
        source_dialect: str,
        target_dialect: str
    ) -> List[TranslationResult]:
        """
        Translate multiple queries in batch.
        """
        # TODO: Implement
        pass

    def _detect_changes(
        self,
        original_ast: Any,
        translated_ast: Any
    ) -> List[str]:
        """
        Detect what changed during translation.
        """
        # TODO: Implement
        pass

    def _validate_translation(
        self,
        sql: str,
        dialect: str
    ) -> bool:
        """
        Validate that translated SQL is syntactically correct.
        """
        # TODO: Implement
        pass
```

**Acceptance Criteria**:
- [ ] File created with all methods
- [ ] Can translate simple SELECT query
- [ ] Returns detailed TranslationResult
- [ ] Handles errors gracefully
- [ ] Logs translation attempts

**Test Command**:
```python
# Quick test
from src.core.sql_dialect_translator import SQLDialectTranslator

translator = SQLDialectTranslator()
result = translator.translate(
    "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
    source_dialect='bigquery',
    target_dialect='snowflake'
)
print(result.translated_sql)
# Expected: "SELECT DATEADD(DAY, -7, CURRENT_DATE())"
```

---

### Task 1.2: Create Dialect Handlers 📋 TODO

**Directory**: `backend/src/core/dialect_handlers/` (NEW)

**Files to Create**:
1. `__init__.py`
2. `base_handler.py` - Abstract base class
3. `bigquery_handler.py` - BigQuery-specific logic
4. `snowflake_handler.py` - Snowflake-specific logic
5. `postgresql_handler.py` - PostgreSQL-specific logic
6. `redshift_handler.py` - Redshift-specific logic (extends PostgreSQL)
7. `databricks_handler.py` - Databricks-specific logic

**Base Handler Template**:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BaseDialectHandler(ABC):
    """
    Base class for database-specific SQL translation logic.
    """

    @abstractmethod
    def get_function_mappings(self) -> Dict[str, str]:
        """
        Return function name mappings for this dialect.

        Example:
            {
                'DATE_SUB': 'DATEADD',
                'STRING_AGG': 'LISTAGG'
            }
        """
        pass

    @abstractmethod
    def get_data_type_mappings(self) -> Dict[str, str]:
        """
        Return data type mappings for this dialect.
        """
        pass

    @abstractmethod
    def handle_custom_syntax(self, sql: str) -> str:
        """
        Handle dialect-specific syntax that sqlglot might miss.
        """
        pass
```

**Acceptance Criteria**:
- [ ] Directory created
- [ ] Base handler defined
- [ ] All 5 handlers implemented
- [ ] Function mappings complete
- [ ] Custom syntax handlers working

---

### Task 1.3: Write Unit Tests 📋 TODO

**File**: `backend/tests/unit/core/test_sql_dialect_translator.py` (NEW)

**Test Cases to Implement**:

```python
import pytest
from src.core.sql_dialect_translator import SQLDialectTranslator, TranslationResult

class TestSQLDialectTranslator:
    """Test SQL dialect translation."""

    @pytest.fixture
    def translator(self):
        return SQLDialectTranslator()

    # BigQuery → Snowflake
    def test_bigquery_to_snowflake_date_functions(self, translator):
        """Test DATE_SUB → DATEADD translation."""
        sql = "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert 'DATEADD' in result.translated_sql
        assert 'DATE_SUB' not in result.translated_sql
        assert result.is_lossless is True

    def test_bigquery_to_snowflake_backticks(self, translator):
        """Test backtick removal for Snowflake."""
        sql = "SELECT * FROM `project.dataset.table`"
        result = translator.translate(sql, 'bigquery', 'snowflake')

        assert '`' not in result.translated_sql
        assert result.is_lossless is True

    # Snowflake → PostgreSQL
    def test_snowflake_to_postgresql_dateadd(self, translator):
        """Test DATEADD → INTERVAL translation."""
        sql = "SELECT DATEADD(DAY, -7, CURRENT_DATE())"
        result = translator.translate(sql, 'snowflake', 'postgresql')

        assert 'INTERVAL' in result.translated_sql
        assert result.is_lossless is True

    # PostgreSQL → BigQuery
    def test_postgresql_to_bigquery_interval(self, translator):
        """Test INTERVAL → DATE_SUB translation."""
        sql = "SELECT CURRENT_DATE - INTERVAL '7 days'"
        result = translator.translate(sql, 'postgresql', 'bigquery')

        assert 'DATE_SUB' in result.translated_sql or 'DATE_ADD' in result.translated_sql
        assert result.is_lossless is True

    # Error Handling
    def test_invalid_dialect(self, translator):
        """Test error handling for invalid dialect."""
        with pytest.raises(ValueError):
            translator.translate("SELECT 1", 'invalid', 'bigquery')

    def test_malformed_sql(self, translator):
        """Test error handling for malformed SQL."""
        with pytest.raises(Exception):
            translator.translate("SELECT FROM WHERE", 'bigquery', 'snowflake')

    # Translation Cost
    def test_translation_cost_identical(self, translator):
        """Test cost for identical SQL (Redshift → PostgreSQL)."""
        cost = translator.get_translation_cost(
            "SELECT * FROM users",
            'redshift',
            'postgresql'
        )
        assert cost < 0.2  # Should be very low

    def test_translation_cost_complex(self, translator):
        """Test cost for complex dialect-specific SQL."""
        sql = """
        SELECT DATE_TRUNC('month', date_column),
               ARRAY_AGG(DISTINCT value)
        FROM table
        """
        cost = translator.get_translation_cost(sql, 'snowflake', 'redshift')
        assert cost > 0.3  # Should be higher due to ARRAY_AGG

    # Batch Translation
    def test_batch_translate(self, translator):
        """Test batch translation of multiple queries."""
        queries = [
            "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
            "SELECT COUNT(*) FROM users",
            "SELECT STRING_AGG(name, ', ') FROM products"
        ]
        results = translator.batch_translate(queries, 'bigquery', 'snowflake')

        assert len(results) == 3
        assert all(isinstance(r, TranslationResult) for r in results)
```

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Test coverage > 80%
- [ ] Edge cases covered
- [ ] Performance tests included

---

## Task 2: Integration with Existing Systems

### Task 2.1: Add API Endpoint 📋 TODO

**File**: `backend/src/api/cross_database_routes.py` (NEW)

**Endpoint to Add**:
```python
@router.post("/api/v1/cross-db/translate")
async def translate_sql_dialect(
    request: TranslateSQLRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Translate SQL from one dialect to another.
    """
    translator = SQLDialectTranslator()
    result = translator.translate(
        sql=request.sql,
        source_dialect=request.source_dialect,
        target_dialect=request.target_dialect
    )

    return {
        "translated_sql": result.translated_sql,
        "changes": result.changes,
        "warnings": result.warnings,
        "is_lossless": result.is_lossless,
        "confidence_score": result.confidence_score
    }
```

**Acceptance Criteria**:
- [ ] Endpoint created
- [ ] Request/response models defined
- [ ] Permission checks added
- [ ] API documentation updated

### Task 2.2: Add CLI Tool 📋 TODO

**File**: `backend/scripts/translate_sql.py` (NEW)

**Purpose**: Command-line tool for testing SQL translation

```python
"""
CLI tool for testing SQL dialect translation.

Usage:
    python scripts/translate_sql.py \
        --sql "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)" \
        --from bigquery \
        --to snowflake
"""
```

---

## Task 3: Documentation & Examples

### Task 3.1: Create Examples 📋 TODO

**File**: `backend/examples/sql_translation_examples.md` (NEW)

**Content**:
- BigQuery → Snowflake examples
- Snowflake → PostgreSQL examples
- PostgreSQL → Databricks examples
- Common pitfalls and solutions
- Performance tips

### Task 3.2: Update API Docs 📋 TODO

**Files to Update**:
- `backend/README.md` - Add SQL translation section
- `backend/src/api/README.md` - Document new endpoints
- OpenAPI schema - Add translation endpoint

---

## Progress Tracking

### Week 1 Progress
- [x] Install sqlglot
- [x] Create Phase 2 plan
- [ ] **IN PROGRESS**: SQL Dialect Translator core
- [ ] Dialect handlers
- [ ] Unit tests
- [ ] API endpoint

### Week 2 Goals
- [ ] Complete SQL Dialect Translator
- [ ] Start Federated Query Planner
- [ ] Integration tests
- [ ] Documentation

---

## Commands Reference

### Development
```bash
# Activate virtual environment
cd backend
source venv/bin/activate

# Run translator in Python REPL
python
>>> from src.core.sql_dialect_translator import SQLDialectTranslator
>>> translator = SQLDialectTranslator()
>>> result = translator.translate("SELECT 1", 'bigquery', 'snowflake')
>>> print(result.translated_sql)

# Run unit tests
pytest tests/unit/core/test_sql_dialect_translator.py -v

# Run with coverage
pytest tests/unit/core/test_sql_dialect_translator.py --cov=src/core/sql_dialect_translator

# Test API endpoint (after implementation)
curl -X POST http://localhost:8000/api/v1/cross-db/translate \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
    "source_dialect": "bigquery",
    "target_dialect": "snowflake"
  }'
```

### Testing
```bash
# Test single dialect pair
python -c "
from src.core.sql_dialect_translator import SQLDialectTranslator
t = SQLDialectTranslator()
r = t.translate('SELECT 1', 'bigquery', 'snowflake')
print(r.translated_sql)
"

# Test all dialect pairs
python scripts/test_all_translations.py
```

---

## Quick Reference

### sqlglot Basics
```python
import sqlglot

# Parse SQL
parsed = sqlglot.parse_one("SELECT * FROM users", read='bigquery')

# Transpile to another dialect
transpiled = parsed.sql(dialect='snowflake')

# Available dialects
sqlglot.dialects.Dialects.BIGQUERY
sqlglot.dialects.Dialects.SNOWFLAKE
sqlglot.dialects.Dialects.POSTGRES
sqlglot.dialects.Dialects.REDSHIFT
sqlglot.dialects.Dialects.DATABRICKS
```

### Function Mappings (Quick Reference)
```python
# BigQuery → Snowflake
DATE_SUB() → DATEADD()
DATE_ADD() → DATEADD()
TIMESTAMP_SUB() → TIMESTAMPADD()
STRING_AGG() → LISTAGG()

# Snowflake → PostgreSQL
DATEADD() → date + INTERVAL
DATEDIFF() → date1 - date2
LISTAGG() → STRING_AGG()

# PostgreSQL → BigQuery
INTERVAL '7 days' → INTERVAL 7 DAY
NOW() → CURRENT_TIMESTAMP()
AGE() → DATE_DIFF()
```

---

## Success Criteria for Task 1 Completion

- [ ] SQLDialectTranslator class implemented with all methods
- [ ] Can translate between all 5 database dialects
- [ ] Dialect handlers created for each database
- [ ] Unit tests pass (>80% coverage)
- [ ] API endpoint working
- [ ] CLI tool functional
- [ ] Documentation complete
- [ ] Example queries translated successfully

---

## Estimated Time

**Task 1 (SQL Dialect Translator)**:
- Core implementation: 2-3 hours
- Dialect handlers: 2-3 hours
- Unit tests: 2-3 hours
- API endpoint: 1 hour
- Documentation: 1 hour

**Total**: 8-12 hours

---

## Next Steps After Task 1

Once SQL Dialect Translator is complete:

1. **Task 2**: Federated Query Planner
2. **Task 3**: Cross-Database Executor
3. **Task 4**: Performance Optimization
4. **Task 5**: Integration & Testing

---

**Status**: ⏳ READY TO START
**Next Action**: Create `src/core/sql_dialect_translator.py`
**Estimated Session Time**: 2-3 hours
