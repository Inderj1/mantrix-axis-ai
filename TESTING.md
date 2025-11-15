# Testing Guide - Mantrix Axis AI Enhanced Architecture

This document provides comprehensive testing procedures for validating Phase 1 and Phase 2 implementations.

## Quick Start

```bash
# Run automated Phase 1 tests
cd backend
python test_phase1_implementation.py

# Run Phase 2 tests (after implementation)
python test_phase2_pipeline.py
```

---

## Phase 1: Foundation & Critical Fixes

### Test 1.1: Cache Configuration

**Automated Test:** ✅ Included in `test_phase1_implementation.py`

**Manual Verification:**

```bash
# Check Redis is running
redis-cli ping
# Expected: PONG

# Check cache settings
grep "CACHE_ENABLED" backend/.env
# Expected: CACHE_ENABLED=true

# Monitor cache activity
redis-cli MONITOR
# Then run a query and watch cache operations
```

**Expected Behavior:**
- Redis responds to ping
- All cache flags are `true` in `.env`
- Cache keys appear in Redis monitor during queries

**Success Criteria:**
- ✅ Redis connection successful
- ✅ Cache enabled in settings
- ✅ Can write/read from cache

---

### Test 1.2: Query Timeout

**Automated Test:** ✅ Included in `test_phase1_implementation.py`

**Manual Test Query:**

```python
from src.db.bigquery import BigQueryClient
from src.config import settings

bq_client = BigQueryClient()

# Test that timeout is configured
print(f"Timeout: {settings.bigquery_query_timeout_seconds}s")

# Run quick query with timeout
query = "SELECT COUNT(*) FROM `{project}.{dataset}.__TABLES__`".format(
    project=bq_client.project_id,
    dataset=bq_client.dataset_id
)

result = bq_client.execute_query(query, timeout=10)
print(f"Success: {len(result.get('rows', []))} rows")

# Test timeout enforcement (optional - will fail intentionally)
# Uncomment to test timeout behavior on long-running query
# long_query = "SELECT * FROM huge_table ORDER BY RAND() LIMIT 1000000"
# result = bq_client.execute_query(long_query, timeout=1)
```

**Expected Behavior:**
- Timeout setting is 60 seconds
- Quick queries complete normally
- Long queries respect timeout and fail gracefully

**Success Criteria:**
- ✅ Timeout configured in settings
- ✅ Query executes with timeout parameter
- ✅ Timeout is logged in query execution

---

### Test 1.3: Format Normalizer - LTRIM/LPAD Fix

**Automated Test:** ✅ Included in `test_phase1_implementation.py`

**Manual Test - Format Detection:**

```python
from src.db.bigquery import BigQueryClient
from src.core.cache_manager import CacheManager
from src.core.format_normalizer import FormatNormalizer
from src.config import settings

# Initialize
bq_client = BigQueryClient()
cache_manager = CacheManager(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db
)
normalizer = FormatNormalizer(bq_client, cache_manager)

# Test on a table (replace with your table name)
table_name = "CE11000"  # COPA table example
column_name = "KNDNR"   # Customer number (often has leading zeros)

# Detect format
format_info = normalizer.detect_column_format(table_name, column_name)

print(f"Table: {format_info.table_name}")
print(f"Column: {format_info.column_name}")
print(f"Format Type: {format_info.format_type.value}")
print(f"Leading Zero %: {format_info.leading_zero_percentage:.1%}")
print(f"Max Length: {format_info.max_length}")
print(f"Samples: {format_info.sample_values[:3]}")
```

**Manual Test - JOIN Normalization:**

```python
# Test JOIN normalization
test_query = """
SELECT
    copa.KNDNR,
    copa.VV001 as revenue,
    customer.NAME1 as customer_name
FROM `arizona-poc.copa_export_copa_data_000000000000.CE11000` copa
INNER JOIN `arizona-poc.copa_export_copa_data_000000000000.KNA1` customer
    ON copa.KNDNR = customer.KUNNR
LIMIT 10
"""

# Normalize
normalized = normalizer.normalize_join_query(test_query)

print("ORIGINAL:")
print(test_query)
print("\nNORMALIZED:")
print(normalized)

# Check if LTRIM or LPAD was applied
if "LTRIM" in normalized or "LPAD" in normalized:
    print("\n✅ Format normalization APPLIED - JOIN accuracy will be improved!")
else:
    print("\n✓ No normalization needed - formats already match")
```

**BigQuery Test - Before/After Accuracy:**

```sql
-- Test JOIN accuracy WITHOUT normalization
-- (Run this directly in BigQuery Console)

SELECT COUNT(*) as matches
FROM `arizona-poc.copa_export_copa_data_000000000000.CE11000` copa
INNER JOIN `arizona-poc.copa_export_copa_data_000000000000.KNA1` customer
    ON copa.KNDNR = customer.KUNNR;
-- Record this number

-- Test JOIN accuracy WITH normalization
SELECT COUNT(*) as matches
FROM `arizona-poc.copa_export_copa_data_000000000000.CE11000` copa
INNER JOIN `arizona-poc.copa_export_copa_data_000000000000.KNA1` customer
    ON LTRIM(copa.KNDNR, '0') = LTRIM(customer.KUNNR, '0');
-- This should be MUCH higher

-- Calculate improvement
-- Improvement = (normalized_matches - original_matches) / original_matches * 100
```

**Expected Behavior:**
- Format detection identifies leading zeros correctly
- JOIN normalization applies LTRIM/LPAD when needed
- JOIN match count increases dramatically with normalization

**Success Criteria:**
- ✅ Format type correctly detected (LEADING_ZEROS, LEFT_TRIMMED, or STANDARD)
- ✅ Sample values shown
- ✅ JOIN queries are normalized when format mismatch detected
- ✅ JOIN accuracy improves from <1% to 99%+ (in production data)

---

### Test 1.4: Pagination

**Automated Test:** ✅ Included in `test_phase1_implementation.py`

**Manual Test - Pagination Flow:**

```python
from src.db.bigquery import BigQueryClient

bq_client = BigQueryClient()

# Get a table with enough data
query = """
SELECT *
FROM `arizona-poc.copa_export_copa_data_000000000000.CE11000`
LIMIT 100
"""

# Page 1
print("=== PAGE 1 ===")
page1 = bq_client.execute_query(query, page_size=10)

print(f"Rows fetched: {page1['fetched_rows']}")
print(f"Total rows: {page1['total_rows']}")
print(f"Has more: {page1['has_more']}")
print(f"Next token: {page1['next_page_token'][:20]}..." if page1.get('next_page_token') else "None")

# Page 2
if page1['has_more']:
    print("\n=== PAGE 2 ===")
    page2 = bq_client.execute_query(
        query,
        page_size=10,
        page_token=page1['next_page_token']
    )

    print(f"Rows fetched: {page2['fetched_rows']}")
    print(f"Has more: {page2['has_more']}")

    # Verify different data
    if page1['rows'][0] != page2['rows'][0]:
        print("✅ Pages contain different data")
    else:
        print("❌ Pages contain same data (pagination not working)")

# Test large page size
print("\n=== LARGE PAGE (50 rows) ===")
large_page = bq_client.execute_query(query, page_size=50)
print(f"Rows fetched: {large_page['fetched_rows']}")

# Test max_rows limit
print("\n=== MAX ROWS LIMIT (25 total) ===")
limited = bq_client.execute_query(query, page_size=10, max_rows=25)
print(f"Rows fetched: {limited['fetched_rows']}")
print(f"Truncated: {limited['truncated']}")
```

**Expected Behavior:**
- First page returns 10 rows
- `has_more` is True if more data exists
- `next_page_token` is provided
- Second page returns different rows
- Large page sizes work up to 100K
- `max_rows` limit is enforced

**Success Criteria:**
- ✅ Pagination returns correct number of rows per page
- ✅ `next_page_token` enables fetching subsequent pages
- ✅ Pages contain different data
- ✅ `has_more` flag is accurate
- ✅ `max_rows` limit works correctly

---

### Test 1.5: End-to-End Integration

**Manual Test - Full SQL Generation with All Features:**

```python
from src.core.sql_generator import SQLGenerator

generator = SQLGenerator()

# Test 1: Simple query (tests caching)
print("=== TEST 1: Simple Query ===")
result1 = generator.generate_sql("Show me total revenue by customer")

print(f"SQL Generated: {result1.get('sql', 'ERROR')[:100]}...")
print(f"From Cache: {result1.get('from_cache', False)}")
print(f"Format Normalized: {result1.get('format_normalized', False)}")
print(f"Valid: {result1.get('validation', {}).get('valid', False)}")

# Run again - should hit cache
print("\n=== TEST 2: Same Query (Cache Hit) ===")
result2 = generator.generate_sql("Show me total revenue by customer")
print(f"From Cache: {result2.get('from_cache', False)}")
assert result2.get('from_cache') == True, "Should hit cache on second run"

# Test 3: Query with JOINs (tests format normalization)
print("\n=== TEST 3: JOIN Query (Format Normalization) ===")
result3 = generator.generate_sql(
    "Show me customer names with their total revenue"
)

print(f"SQL Generated: {result3.get('sql', 'ERROR')[:200]}...")
print(f"Format Normalized: {result3.get('format_normalized', 'N/A')}")

if result3.get('format_normalized'):
    print("✅ Format normalization was applied - JOIN accuracy improved!")

# Test 4: Execute and paginate
print("\n=== TEST 4: Execute with Pagination ===")
if result3.get('sql'):
    execution = generator.execute_query(result3['sql'] + " LIMIT 100")

    if execution.get('results'):
        print(f"Rows returned: {execution['row_count']}")
        print(f"Total available: {execution['total_rows']}")
        print(f"Has more pages: {execution.get('has_more', 'N/A')}")
```

**Expected Behavior:**
- First query generates SQL (cache miss)
- Second identical query hits cache (from_cache=True)
- JOIN queries apply format normalization when needed
- Execution returns paginated results

**Success Criteria:**
- ✅ SQL generation works
- ✅ Caching works (second query is cached)
- ✅ Format normalization integrates into generation
- ✅ Execution returns results with pagination info

---

## Performance Benchmarks

### Before Phase 1 (Baseline)

Run these queries to establish baseline:

```python
import time
from src.core.sql_generator import SQLGenerator

generator = SQLGenerator()

# Disable caching temporarily for baseline
generator.cache_manager = None

queries = [
    "Show me total revenue",
    "Show me top 10 customers by revenue",
    "Show me revenue by product category",
]

print("=== BASELINE (No Cache) ===")
for query in queries:
    start = time.time()
    result = generator.generate_sql(query)
    duration = (time.time() - start) * 1000
    print(f"{query[:40]:40} {duration:6.0f}ms")
```

### After Phase 1 (With Cache & Optimizations)

```python
# Enable caching
from src.core.sql_generator import SQLGenerator

generator = SQLGenerator()  # Cache enabled by default

queries = [
    "Show me total revenue",
    "Show me top 10 customers by revenue",
    "Show me revenue by product category",
]

print("\n=== WITH CACHE (First Run) ===")
for query in queries:
    start = time.time()
    result = generator.generate_sql(query)
    duration = (time.time() - start) * 1000
    print(f"{query[:40]:40} {duration:6.0f}ms")

print("\n=== WITH CACHE (Second Run - Cache Hits) ===")
for query in queries:
    start = time.time()
    result = generator.generate_sql(query)
    duration = (time.time() - start) * 1000
    cached = "✅ CACHED" if result.get('from_cache') else "❌ MISS"
    print(f"{query[:40]:40} {duration:6.0f}ms {cached}")
```

**Expected Improvements:**
- First run: Similar to baseline
- Second run: **~95% faster** (cached results)

---

## Common Issues & Troubleshooting

### Issue: Redis Connection Failed

```bash
# Check if Redis is running
redis-cli ping

# If not running, start Redis:
redis-server

# Or with Homebrew:
brew services start redis
```

### Issue: Timeout Errors

```python
# Check timeout setting
from src.config import settings
print(f"Timeout: {settings.bigquery_query_timeout_seconds}s")

# Increase if needed in .env:
# BIGQUERY_QUERY_TIMEOUT_SECONDS=120
```

### Issue: Format Normalizer Not Applied

```python
# Check if format normalizer is initialized
from src.core.sql_generator import SQLGenerator

generator = SQLGenerator()
print(f"Format Normalizer: {generator.format_normalizer}")

# If None, check logs for initialization errors
```

### Issue: Pagination Not Working

```python
# Verify BigQuery client has pagination params
from src.db.bigquery import BigQueryClient
import inspect

sig = inspect.signature(BigQueryClient.execute_query)
print(f"Parameters: {list(sig.parameters.keys())}")

# Should include: ['self', 'query', 'max_rows', 'timeout', 'page_token', 'page_size']
```

---

## Test Data Requirements

### Minimum Dataset Requirements:

1. **At least 1 table** with 10,000+ rows for pagination testing
2. **At least 2 tables** with a joinable column for format normalization testing
3. **String columns** with potential format variations (leading zeros, trimmed)

### Recommended Test Tables:

- **COPA Table (CE11000)**: Large transaction table, good for pagination
- **Customer Master (KNA1)**: Join testing with customer numbers
- **Material Master (MARA)**: Additional join scenarios

---

## Success Metrics

### Phase 1 Success Criteria:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cache Hit Rate | >80% | Second query should be cached |
| Query Timeout | 60s | Configured and applied |
| JOIN Accuracy | 99%+ | With format normalization |
| Pagination Support | 100K rows/page | No truncation errors |
| Performance (Cached) | 95% faster | Cache hits vs. misses |

---

## Next: Phase 2 Testing

After Phase 1 validation, proceed to Phase 2 pipeline testing:

```bash
python test_phase2_pipeline.py
```

Phase 2 tests will include:
- Schema extraction and versioning
- RDF graph building
- Vector embedding generation
- Build-time pipeline orchestration

---

## Reporting Issues

If tests fail, collect this information:

```bash
# 1. Environment info
python --version
pip list | grep -E "(google-cloud-bigquery|redis|anthropic)"

# 2. Settings
grep -E "(CACHE|TIMEOUT|REDIS)" backend/.env

# 3. Logs
tail -100 backend/logs/app.log

# 4. Test output
python test_phase1_implementation.py > test_results.txt 2>&1
```

Include in GitHub issue or bug report.
