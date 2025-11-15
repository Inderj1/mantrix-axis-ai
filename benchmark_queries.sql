-- ============================================================================
-- MANTRIX AXIS AI - BENCHMARK QUERIES
-- ============================================================================
-- Run these queries against your BigQuery dataset to measure actual limits
-- Project: arizona-poc
-- Dataset: copa_export_copa_data_000000000000
-- ============================================================================

-- ============================================================================
-- SECTION 1: TABLE INVENTORY & SIZES
-- ============================================================================

-- Query 1.1: Get all tables with sizes and row counts
SELECT
    table_name,
    row_count,
    ROUND(size_bytes / 1024 / 1024 / 1024, 2) AS size_gb,
    ROUND(size_bytes / 1024 / 1024, 2) AS size_mb,
    ROUND(size_bytes / row_count, 2) AS avg_row_size_bytes
FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
WHERE row_count > 0
ORDER BY row_count DESC;

-- Query 1.2: Find widest tables (most columns)
SELECT
    table_name,
    row_count,
    (SELECT COUNT(*)
     FROM UNNEST(REGEXP_EXTRACT_ALL(
         TO_JSON_STRING(JSON_EXTRACT(options, '$.schema.fields')),
         r'"name"'
     ))) AS column_count
FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
ORDER BY row_count DESC
LIMIT 20;

-- Query 1.3: Calculate total dataset size
SELECT
    COUNT(*) AS total_tables,
    SUM(row_count) AS total_rows,
    ROUND(SUM(size_bytes) / 1024 / 1024 / 1024, 2) AS total_size_gb,
    ROUND(AVG(size_bytes / 1024 / 1024), 2) AS avg_table_size_mb
FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
WHERE row_count > 0;


-- ============================================================================
-- SECTION 2: RESULT SIZE LIMIT TESTS
-- ============================================================================
-- NOTE: Replace {TABLE_NAME} with your actual table name from Query 1.1

-- Query 2.1: Test 10K row limit (current system limit)
SELECT COUNT(*) OVER () AS total_rows_available, *
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
LIMIT 10000;
-- Check: Does total_rows_available > 10,000? If yes, data is being truncated!

-- Query 2.2: Test 50K row fetch
SELECT *
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
LIMIT 50000;
-- Record: execution time, bytes processed

-- Query 2.3: Test 100K row fetch
SELECT *
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
LIMIT 100000;
-- Record: execution time, bytes processed


-- ============================================================================
-- SECTION 3: QUERY TIMEOUT & PERFORMANCE TESTS
-- ============================================================================

-- Query 3.1: Simple COUNT (should be fast, uses metadata)
SELECT COUNT(*) as total_count
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`;
-- Expected: < 1 second

-- Query 3.2: Full table scan (will be slower)
SELECT *
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`;
-- Record: execution time, bytes scanned, cost
-- WARNING: This could be expensive on large tables!

-- Query 3.3: Complex aggregation (CPU intensive)
SELECT
    -- Replace with actual column names from your table
    column1,
    column2,
    COUNT(*) as record_count,
    COUNT(DISTINCT column3) as unique_count,
    AVG(CAST(numeric_column AS FLOAT64)) as avg_value,
    STDDEV(CAST(numeric_column AS FLOAT64)) as stddev_value
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
GROUP BY column1, column2
HAVING COUNT(*) > 10
ORDER BY record_count DESC
LIMIT 1000;
-- Record: execution time

-- Query 3.4: Window function performance
SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY column1 ORDER BY column2) as row_num,
    COUNT(*) OVER (PARTITION BY column1) as partition_count
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
LIMIT 10000;
-- Record: execution time


-- ============================================================================
-- SECTION 4: JOIN COMPLEXITY TESTS
-- ============================================================================

-- Query 4.1: Find potential join keys between tables
SELECT DISTINCT
    t1.table_name AS table1,
    c1.column_name AS column1_name,
    t2.table_name AS table2,
    c2.column_name AS column2_name,
    c1.data_type
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS` c1
JOIN `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS` c2
    ON c1.column_name = c2.column_name
    AND c1.data_type = c2.data_type
    AND c1.table_name < c2.table_name
JOIN `arizona-poc.copa_export_copa_data_000000000000.__TABLES__` t1
    ON c1.table_name = t1.table_name
JOIN `arizona-poc.copa_export_copa_data_000000000000.__TABLES__` t2
    ON c2.table_name = t2.table_name
WHERE t1.row_count > 1000
    AND t2.row_count > 1000
ORDER BY t1.table_name, t2.table_name
LIMIT 50;

-- Query 4.2: Test 2-table join performance
-- Replace table names and join columns from Query 4.1 results
SELECT COUNT(*) as join_match_count
FROM `arizona-poc.copa_export_copa_data_000000000000.table1` t1
INNER JOIN `arizona-poc.copa_export_copa_data_000000000000.table2` t2
    ON t1.join_column = t2.join_column;
-- Record: execution time, match count, bytes processed

-- Query 4.3: Test 3-table join performance
SELECT COUNT(*)
FROM `arizona-poc.copa_export_copa_data_000000000000.table1` t1
JOIN `arizona-poc.copa_export_copa_data_000000000000.table2` t2
    ON t1.key1 = t2.key1
JOIN `arizona-poc.copa_export_copa_data_000000000000.table3` t3
    ON t2.key2 = t3.key2;
-- Record: execution time, bytes processed

-- Query 4.4: Test JOIN with LTRIM (for COPA/Cockpit join issue)
-- This tests the leading zero mismatch problem
SELECT
    t1.table_name,
    t1.column_name,
    COUNT(*) as rows_with_leading_zeros
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS` t1
CROSS JOIN UNNEST(
    ARRAY(
        SELECT AS STRUCT column_value
        FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
    )
) AS sample
WHERE t1.data_type = 'STRING'
    AND REGEXP_CONTAINS(CAST(sample AS STRING), r'^0+[0-9]')
GROUP BY t1.table_name, t1.column_name
HAVING COUNT(*) > 0;


-- ============================================================================
-- SECTION 5: COST ESTIMATION TESTS
-- ============================================================================

-- Query 5.1: Calculate cost per table (full scan estimate)
SELECT
    table_name,
    ROUND(size_bytes / 1024 / 1024 / 1024, 2) AS size_gb,
    ROUND((size_bytes / 1e12) * 5.0, 4) AS estimated_full_scan_cost_usd
FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
WHERE row_count > 0
ORDER BY size_bytes DESC;

-- Query 5.2: Check recent query costs (last 24 hours)
-- NOTE: This requires JOBS_BY_PROJECT access in INFORMATION_SCHEMA
SELECT
    user_email,
    REGEXP_EXTRACT(query, r'FROM\s+`[^`]+\.([^`]+)`') AS table_accessed,
    ROUND(total_bytes_processed / 1e9, 2) AS gb_processed,
    ROUND((total_bytes_processed / 1e12) * 5.0, 4) AS cost_usd,
    ROUND(TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) / 1000, 2) AS execution_time_sec,
    creation_time,
    state,
    error_result.reason AS error_reason
FROM `arizona-poc.region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND job_type = 'QUERY'
    AND statement_type = 'SELECT'
ORDER BY total_bytes_processed DESC
LIMIT 50;
-- If this fails, try: `arizona-poc.region-US` or check your region

-- Query 5.3: Find most expensive queries (last 7 days)
SELECT
    REGEXP_EXTRACT(query, r'FROM\s+`[^`]+\.([^`]+)`') AS table_name,
    COUNT(*) AS query_count,
    ROUND(SUM(total_bytes_processed) / 1e9, 2) AS total_gb_scanned,
    ROUND(SUM((total_bytes_processed / 1e12) * 5.0), 4) AS total_cost_usd,
    ROUND(AVG(total_bytes_processed) / 1e9, 2) AS avg_gb_per_query
FROM `arizona-poc.region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND job_type = 'QUERY'
    AND state = 'DONE'
GROUP BY table_name
HAVING table_name IS NOT NULL
ORDER BY total_cost_usd DESC
LIMIT 20;


-- ============================================================================
-- SECTION 6: PARTITION & CLUSTERING ANALYSIS
-- ============================================================================

-- Query 6.1: Check for partitioned tables
SELECT
    table_name,
    ddl
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.TABLES`
WHERE table_type = 'BASE TABLE'
    AND (ddl LIKE '%PARTITION BY%' OR ddl LIKE '%CLUSTER BY%')
ORDER BY table_name;

-- Query 6.2: Analyze partition pruning effectiveness
-- Run this on a partitioned table to check if queries use partition pruning
-- Replace {PARTITIONED_TABLE} and {PARTITION_COLUMN}
SELECT
    COUNT(*) as total_records,
    MIN({PARTITION_COLUMN}) as min_date,
    MAX({PARTITION_COLUMN}) as max_date
FROM `arizona-poc.copa_export_copa_data_000000000000.{PARTITIONED_TABLE}`
WHERE {PARTITION_COLUMN} >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);
-- Check bytes scanned - should be much less than full table size


-- ============================================================================
-- SECTION 7: SCHEMA ANALYSIS
-- ============================================================================

-- Query 7.1: Get detailed schema for largest table
SELECT
    column_name,
    data_type,
    is_nullable,
    is_partitioning_column
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = '{LARGEST_TABLE_NAME}'
ORDER BY ordinal_position;

-- Query 7.2: Find STRING columns (potential join keys)
SELECT
    table_name,
    column_name,
    is_nullable
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS`
WHERE data_type = 'STRING'
    AND table_name IN (
        SELECT table_name
        FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
        WHERE row_count > 10000
        ORDER BY row_count DESC
        LIMIT 10
    )
ORDER BY table_name, column_name;

-- Query 7.3: Find numeric columns (potential aggregation targets)
SELECT
    table_name,
    column_name,
    data_type
FROM `arizona-poc.copa_export_copa_data_000000000000.INFORMATION_SCHEMA.COLUMNS`
WHERE data_type IN ('INT64', 'FLOAT64', 'NUMERIC', 'BIGNUMERIC')
    AND table_name IN (
        SELECT table_name
        FROM `arizona-poc.copa_export_copa_data_000000000000.__TABLES__`
        ORDER BY row_count DESC
        LIMIT 5
    )
ORDER BY table_name, column_name;


-- ============================================================================
-- SECTION 8: SAMPLING STRATEGIES
-- ============================================================================

-- Query 8.1: Random sample (1% of data)
SELECT *
FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
TABLESAMPLE SYSTEM (1 PERCENT)
LIMIT 1000;
-- Use this for testing queries on large tables cheaply

-- Query 8.2: Stratified sampling (top N per group)
SELECT *
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY column1 ORDER BY RAND()) as rn
    FROM `arizona-poc.copa_export_copa_data_000000000000.{TABLE_NAME}`
)
WHERE rn <= 100;  -- Top 100 rows per group


-- ============================================================================
-- USAGE INSTRUCTIONS
-- ============================================================================
/*

1. Copy these queries to BigQuery console or bq command line tool

2. Replace placeholders:
   - {TABLE_NAME} → Your table name from Query 1.1
   - {LARGEST_TABLE_NAME} → Largest table from Query 1.1
   - {PARTITIONED_TABLE} → Partitioned table from Query 6.1
   - {PARTITION_COLUMN} → Partition column name

3. Run queries in order to build understanding:
   - Section 1: Understand your data landscape
   - Section 2: Test result size limits
   - Section 3: Measure query performance
   - Section 4: Test join scenarios
   - Section 5: Estimate costs
   - Section 6-8: Advanced analysis

4. Record results in a spreadsheet:
   - Query name
   - Execution time (seconds)
   - Bytes processed (GB)
   - Cost (USD)
   - Row count returned
   - Any errors/warnings

5. Compare results with limits in TECHNICAL_LIMITS.md

6. Focus on:
   - Queries taking > 60 seconds (need timeout)
   - Queries costing > $0.10 (need optimization)
   - Join match rates < 50% (data quality issues)
   - Tables with > 1M rows (pagination needed)

*/
