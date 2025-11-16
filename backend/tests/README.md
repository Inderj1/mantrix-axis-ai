# Mantrix Axis AI - Test Suite

This directory contains all tests for the Mantrix Axis AI backend system, organized by test type and scope.

## Directory Structure

```
tests/
├── unit/                        # Unit tests (fast, isolated)
│   ├── core/                    # Core functionality tests
│   │   ├── test_cache_manager.py
│   │   ├── test_sql_generator.py
│   │   ├── test_query_optimizer.py
│   │   └── test_financial_formulas.py
│   ├── knowledge_graph/         # Knowledge graph component tests
│   │   ├── test_column_synonyms.py
│   │   ├── test_join_path_finder.py
│   │   ├── test_jena_queries.py
│   │   └── test_kg_init.py
│   └── db/                      # Database client tests
│       └── test_database_clients.py
│
├── integration/                 # Integration tests (multi-component)
│   ├── test_apis.py             # API endpoint tests
│   ├── test_pipeline_api.py     # Pipeline API tests
│   ├── test_duplicate_column_intelligence.py
│   ├── test_enhanced_system.py
│   ├── test_phase1_implementation.py
│   └── test_phase2_pipeline.py
│
├── e2e/                         # End-to-end tests (full workflows)
│   ├── test_full_pipeline_accuracy.py
│   ├── test_complex_queries.py
│   └── test_smart_caching.py
│
├── ui/                          # UI/Frontend tests
│   └── test_playwright.py
│
├── fixtures/                    # Shared test data and fixtures
│   ├── sample_queries.py
│   └── sample_schemas.py
│
├── conftest.py                  # Pytest configuration and shared fixtures
└── README.md                    # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1 second per test)
- **Dependencies**: Minimal, use mocks for external services
- **When to use**: Testing specific functions, classes, or utilities
- **Examples**: Cache key generation, SQL parsing, column matching

**Run unit tests:**
```bash
./run_tests.sh unit
# or
pytest tests/unit/ -v
```

### Integration Tests (`tests/integration/`)
- **Purpose**: Test multiple components working together
- **Speed**: Medium (1-10 seconds per test)
- **Dependencies**: May use real databases, Redis, etc.
- **When to use**: Testing API endpoints, pipeline phases, multi-step processes
- **Examples**: Query execution through API, pipeline orchestration

**Run integration tests:**
```bash
./run_tests.sh integration
# or
pytest tests/integration/ -v
```

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows
- **Speed**: Slow (10+ seconds per test)
- **Dependencies**: Full infrastructure (databases, caches, knowledge graph)
- **When to use**: Validating entire features, regression testing
- **Examples**: Full pipeline execution, complex query handling, smart caching validation

**Run E2E tests:**
```bash
./run_tests.sh e2e
# or
pytest tests/e2e/ -v
```

### UI Tests (`tests/ui/`)
- **Purpose**: Test frontend components and user interactions
- **Speed**: Slow (browser-based)
- **Dependencies**: Playwright, running frontend
- **When to use**: Testing UI flows, dashboard interactions

**Run UI tests:**
```bash
./run_tests.sh ui
# or
pytest tests/ui/ -v
```

## Running Tests

### Quick Start

```bash
# Run all tests
./run_tests.sh

# Run specific test category
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh e2e

# Run specific test files
./run_tests.sh smart-caching
./run_tests.sh complex-queries
./run_tests.sh pipeline
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run specific directory
pytest tests/unit/ -v

# Run specific file
pytest tests/e2e/test_smart_caching.py -v

# Run tests matching a pattern
pytest tests/ -k "test_cache" -v

# Run tests with markers
pytest tests/ -m "unit" -v
pytest tests/ -m "slow" -v
```

### Test Markers

Tests can be marked with the following pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (>10s)
- `@pytest.mark.requires_db` - Requires database access
- `@pytest.mark.requires_redis` - Requires Redis
- `@pytest.mark.requires_weaviate` - Requires Weaviate

**Example:**
```python
import pytest

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.requires_db
def test_full_pipeline():
    # Test code here
    pass
```

## Test Results

Test results are saved to `test_results/`:
- JSON reports from E2E tests
- Coverage reports (if enabled)
- Pytest logs

## Coverage

Run tests with coverage reporting:

```bash
./run_tests.sh coverage
# or
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

View coverage report:
```bash
open test_results/coverage/index.html
```

## Benchmarks

Performance benchmarks are in `../benchmarks/`:

```bash
./run_tests.sh benchmark
# or
python benchmarks/benchmark_technical_limits.py
```

## Writing New Tests

### Unit Test Example

```python
# tests/unit/core/test_my_component.py
import pytest
from src.core.my_component import MyComponent

@pytest.mark.unit
def test_my_function():
    component = MyComponent()
    result = component.my_function("input")
    assert result == "expected_output"
```

### Integration Test Example

```python
# tests/integration/test_my_integration.py
import pytest
from src.core.sql_generator import SQLGenerator
from src.db.bigquery import BigQueryClient

@pytest.mark.integration
@pytest.mark.requires_db
def test_query_execution(sql_generator, bigquery_client):
    # Uses fixtures from conftest.py
    result = sql_generator.generate_sql("Show me all customers")
    assert result["sql"] is not None
    
    # Execute on real database
    rows = bigquery_client.execute_query(result["sql"])
    assert len(rows) > 0
```

### E2E Test Example

```python
# tests/e2e/test_my_workflow.py
import pytest

@pytest.mark.e2e
@pytest.mark.slow
def test_complete_workflow():
    # Test entire user workflow
    # 1. Generate SQL
    # 2. Validate
    # 3. Execute
    # 4. Cache
    # 5. Verify cache hit
    pass
```

## Shared Fixtures

Common fixtures are defined in `conftest.py`:
- `sql_generator` - Shared SQLGenerator instance
- `cache_manager` - Shared CacheManager instance
- `bigquery_client` - Shared BigQueryClient instance
- `clear_cache` - Clears cache before test
- `sample_queries` - List of test queries
- `sample_invalid_queries` - List of invalid queries

**Usage:**
```python
def test_with_fixture(sql_generator, sample_queries):
    for query in sample_queries:
        result = sql_generator.generate_sql(query)
        assert result is not None
```

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Unit Tests
  run: ./run_tests.sh unit

- name: Run Integration Tests
  run: ./run_tests.sh integration

- name: Run E2E Tests (optional)
  run: ./run_tests.sh e2e
  continue-on-error: true  # E2E tests may be flaky
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Use descriptive test names (e.g., `test_cache_stores_valid_query`)
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Services**: In unit tests, mock databases, APIs, etc.
5. **Use Fixtures**: Leverage shared fixtures from `conftest.py`
6. **Mark Tests**: Use pytest markers appropriately
7. **Fast Tests**: Keep unit tests fast (<1s)
8. **Cleanup**: Clean up resources (cache, temp files) after tests

## Troubleshooting

### Tests Failing
1. Check if all required services are running (Redis, Weaviate, etc.)
2. Verify environment variables are set correctly
3. Clear cache: `python -c "from src.core.cache_manager import CacheManager; CacheManager().clear_all_caches()"`
4. Check test logs in `test_results/pytest.log`

### Import Errors
- Ensure `PYTHONPATH` includes the backend directory
- `conftest.py` should handle this automatically

### Database Connection Errors
- Verify `GOOGLE_APPLICATION_CREDENTIALS` is set
- Check BigQuery project and dataset configuration
- Ensure you have proper permissions

## Contributing

When adding new tests:
1. Place in the appropriate directory (unit/integration/e2e)
2. Follow existing naming conventions
3. Add appropriate pytest markers
4. Update this README if adding new test categories
5. Ensure tests pass locally before committing

## Questions?

See also:
- `../SMART_CACHING_GUIDE.md` - Smart caching documentation
- `../COMPLEX_QUERY_EXAMPLES.md` - Complex query examples
- `../MULTI_DATABASE_IMPLEMENTATION_PLAN.md` - Multi-DB implementation plan
