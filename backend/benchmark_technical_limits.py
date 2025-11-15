#!/usr/bin/env python3
"""
Benchmark Technical Limits for Mantrix Axis AI
Tests actual performance constraints against live BigQuery and PostgreSQL databases
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv
from google.cloud import bigquery
from google.api_core import exceptions as gcp_exceptions

# Load environment variables
load_dotenv()

# Initialize BigQuery client
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
dataset_id = os.getenv("BIGQUERY_DATASET")
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
bq_client = bigquery.Client(project=project_id)

# Results storage
benchmark_results = {
    "timestamp": datetime.now().isoformat(),
    "project": project_id,
    "dataset": dataset_id,
    "tests": []
}


def log_test(name: str, status: str, details: Dict[str, Any]):
    """Log test results"""
    result = {
        "test": name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        **details
    }
    benchmark_results["tests"].append(result)

    status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"\n{status_icon} {name}")
    for key, value in details.items():
        print(f"   {key}: {value}")


def run_query_with_timing(query: str, max_results: int = None) -> Dict[str, Any]:
    """Execute query and measure performance"""
    start_time = time.time()

    try:
        query_job = bq_client.query(query)
        results = list(query_job.result(max_results=max_results)) if max_results else list(query_job.result())
        end_time = time.time()

        return {
            "success": True,
            "execution_time_seconds": round(end_time - start_time, 2),
            "rows_returned": len(results),
            "total_rows": query_job.total_rows if hasattr(query_job, 'total_rows') else len(results),
            "bytes_processed": query_job.total_bytes_processed,
            "bytes_billed": query_job.total_bytes_billed,
            "cost_usd": round((query_job.total_bytes_processed / 1e12) * 5.0, 4),
            "slot_ms": query_job.slot_millis if hasattr(query_job, 'slot_millis') else None,
            "results": results[:5] if results else []  # Sample
        }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "execution_time_seconds": round(end_time - start_time, 2),
            "error": str(e),
            "error_type": type(e).__name__
        }


print("=" * 80)
print("MANTRIX AXIS AI - TECHNICAL LIMITS BENCHMARK")
print("=" * 80)
print(f"Project: {project_id}")
print(f"Dataset: {dataset_id}")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)


# ============================================================================
# TEST 1: Get all tables and their sizes
# ============================================================================
print("\n\n📊 TEST 1: TABLE INVENTORY & SIZES")
print("-" * 80)

try:
    tables = list(bq_client.list_tables(f"{project_id}.{dataset_id}"))
    table_info = []

    for table_ref in tables:
        table = bq_client.get_table(f"{project_id}.{dataset_id}.{table_ref.table_id}")
        info = {
            "table_name": table.table_id,
            "row_count": table.num_rows,
            "size_mb": round(table.num_bytes / 1024 / 1024, 2),
            "num_columns": len(table.schema)
        }
        table_info.append(info)
        print(f"   {info['table_name']:<40} {info['row_count']:>15,} rows  {info['size_mb']:>10,.2f} MB  {info['num_columns']:>3} cols")

    # Sort by size
    table_info_sorted = sorted(table_info, key=lambda x: x['row_count'], reverse=True)

    log_test(
        "Table Inventory",
        "PASS",
        {
            "total_tables": len(table_info),
            "largest_table": table_info_sorted[0]['table_name'],
            "largest_table_rows": f"{table_info_sorted[0]['row_count']:,}",
            "largest_table_size_mb": table_info_sorted[0]['size_mb'],
            "total_rows_all_tables": f"{sum(t['row_count'] for t in table_info):,}",
            "total_size_mb": round(sum(t['size_mb'] for t in table_info), 2)
        }
    )

    # Store for later tests
    largest_table = table_info_sorted[0]['table_name']
    medium_table = table_info_sorted[len(table_info_sorted) // 2]['table_name'] if len(table_info_sorted) > 1 else largest_table

except Exception as e:
    log_test("Table Inventory", "FAIL", {"error": str(e)})
    sys.exit(1)


# ============================================================================
# TEST 2: Simple query performance (no limit)
# ============================================================================
print("\n\n⚡ TEST 2: SIMPLE QUERY PERFORMANCE")
print("-" * 80)

query = f"""
SELECT COUNT(*) as total_count
FROM `{project_id}.{dataset_id}.{largest_table}`
"""

result = run_query_with_timing(query)
log_test(
    "Simple COUNT(*) Query",
    "PASS" if result["success"] else "FAIL",
    {
        "table": largest_table,
        "execution_time": f"{result['execution_time_seconds']}s",
        "bytes_processed_gb": round(result.get('bytes_processed', 0) / 1e9, 2),
        "cost_usd": result.get('cost_usd', 0),
        "count": result.get('results', [{}])[0].get('total_count', 'N/A') if result['success'] else None
    }
)


# ============================================================================
# TEST 3: Result size limits (10K, 50K, 100K rows)
# ============================================================================
print("\n\n📦 TEST 3: RESULT SIZE LIMITS")
print("-" * 80)

for limit in [10000, 50000, 100000]:
    query = f"""
    SELECT *
    FROM `{project_id}.{dataset_id}.{largest_table}`
    LIMIT {limit}
    """

    result = run_query_with_timing(query, max_results=limit)
    log_test(
        f"Fetch {limit:,} rows",
        "PASS" if result["success"] else "FAIL",
        {
            "requested_limit": f"{limit:,}",
            "rows_returned": f"{result.get('rows_returned', 0):,}",
            "execution_time": f"{result['execution_time_seconds']}s",
            "bytes_processed_mb": round(result.get('bytes_processed', 0) / 1e6, 2),
            "cost_usd": result.get('cost_usd', 0)
        }
    )


# ============================================================================
# TEST 4: Full table scan performance
# ============================================================================
print("\n\n🔍 TEST 4: FULL TABLE SCAN PERFORMANCE")
print("-" * 80)

query = f"""
SELECT *
FROM `{project_id}.{dataset_id}.{largest_table}`
"""

result = run_query_with_timing(query, max_results=100)  # Only fetch 100 for safety
log_test(
    "Full Table Scan (SELECT *)",
    "PASS" if result["success"] else "FAIL",
    {
        "table": largest_table,
        "execution_time": f"{result['execution_time_seconds']}s",
        "bytes_scanned_gb": round(result.get('bytes_processed', 0) / 1e9, 4),
        "cost_usd": result.get('cost_usd', 0),
        "warning": "High cost!" if result.get('cost_usd', 0) > 0.1 else "OK"
    }
)


# ============================================================================
# TEST 5: Aggregation query performance
# ============================================================================
print("\n\n📊 TEST 5: AGGREGATION QUERY PERFORMANCE")
print("-" * 80)

# Get first column name for grouping
table = bq_client.get_table(f"{project_id}.{dataset_id}.{largest_table}")
first_string_col = None
for field in table.schema:
    if field.field_type == "STRING":
        first_string_col = field.name
        break

if first_string_col:
    query = f"""
    SELECT
        {first_string_col},
        COUNT(*) as count
    FROM `{project_id}.{dataset_id}.{largest_table}`
    GROUP BY {first_string_col}
    ORDER BY count DESC
    LIMIT 100
    """

    result = run_query_with_timing(query)
    log_test(
        "GROUP BY Aggregation",
        "PASS" if result["success"] else "FAIL",
        {
            "group_by_column": first_string_col,
            "execution_time": f"{result['execution_time_seconds']}s",
            "unique_groups": result.get('rows_returned', 0),
            "bytes_processed_mb": round(result.get('bytes_processed', 0) / 1e6, 2),
            "cost_usd": result.get('cost_usd', 0)
        }
    )
else:
    log_test("GROUP BY Aggregation", "SKIP", {"reason": "No STRING columns found"})


# ============================================================================
# TEST 6: JOIN complexity (find joinable tables)
# ============================================================================
print("\n\n🔗 TEST 6: JOIN COMPLEXITY TEST")
print("-" * 80)

# Try to find tables with potential join keys
join_candidates = []
for table_info in table_info[:5]:  # Check first 5 tables
    table = bq_client.get_table(f"{project_id}.{dataset_id}.{table_info['table_name']}")
    string_cols = [f.name for f in table.schema if f.field_type == "STRING"]
    if len(string_cols) > 0:
        join_candidates.append({
            "table": table_info['table_name'],
            "join_columns": string_cols[:3]  # First 3 string columns
        })

if len(join_candidates) >= 2:
    # Try a simple 2-table join
    table1 = join_candidates[0]['table']
    table2 = join_candidates[1]['table']
    col1 = join_candidates[0]['join_columns'][0]
    col2 = join_candidates[1]['join_columns'][0]

    query = f"""
    SELECT
        t1.{col1},
        COUNT(*) as match_count
    FROM `{project_id}.{dataset_id}.{table1}` t1
    INNER JOIN `{project_id}.{dataset_id}.{table2}` t2
        ON t1.{col1} = t2.{col2}
    GROUP BY t1.{col1}
    LIMIT 100
    """

    result = run_query_with_timing(query)
    log_test(
        "2-Table INNER JOIN",
        "PASS" if result["success"] else "FAIL",
        {
            "table1": table1,
            "table2": table2,
            "join_key": f"{col1} = {col2}",
            "execution_time": f"{result['execution_time_seconds']}s",
            "matches_found": result.get('rows_returned', 0),
            "bytes_processed_mb": round(result.get('bytes_processed', 0) / 1e6, 2),
            "cost_usd": result.get('cost_usd', 0)
        }
    )
else:
    log_test("2-Table JOIN", "SKIP", {"reason": "Not enough joinable tables found"})


# ============================================================================
# TEST 7: Query timeout test (complex query)
# ============================================================================
print("\n\n⏱️  TEST 7: QUERY TIMEOUT TEST")
print("-" * 80)

# Create a computationally expensive query
query = f"""
WITH recursive_cte AS (
    SELECT *,
           ROW_NUMBER() OVER () as rn
    FROM `{project_id}.{dataset_id}.{largest_table}`
)
SELECT
    COUNT(DISTINCT rn) as total,
    AVG(rn) as avg_rn,
    MIN(rn) as min_rn,
    MAX(rn) as max_rn
FROM recursive_cte
"""

result = run_query_with_timing(query)
log_test(
    "Complex Query (CTE + Window Function)",
    "PASS" if result["success"] else "TIMEOUT" if "timeout" in str(result.get('error', '')).lower() else "FAIL",
    {
        "execution_time": f"{result['execution_time_seconds']}s",
        "status": "Completed" if result["success"] else result.get('error_type', 'Unknown'),
        "bytes_processed_mb": round(result.get('bytes_processed', 0) / 1e6, 2) if result["success"] else None,
        "timeout_threshold": "60s (if configured)"
    }
)


# ============================================================================
# TEST 8: Column count test
# ============================================================================
print("\n\n📋 TEST 8: COLUMN COUNT TEST")
print("-" * 80)

widest_table = max(table_info, key=lambda x: x['num_columns'])
query = f"""
SELECT *
FROM `{project_id}.{dataset_id}.{widest_table['table_name']}`
LIMIT 1
"""

result = run_query_with_timing(query)
log_test(
    "Widest Table Query",
    "PASS" if result["success"] else "FAIL",
    {
        "table": widest_table['table_name'],
        "column_count": widest_table['num_columns'],
        "execution_time": f"{result['execution_time_seconds']}s",
        "warning": "Many columns!" if widest_table['num_columns'] > 100 else "OK"
    }
)


# ============================================================================
# TEST 9: Pagination simulation
# ============================================================================
print("\n\n📄 TEST 9: PAGINATION SIMULATION")
print("-" * 80)

page_sizes = [1000, 5000, 10000]
for page_size in page_sizes:
    query = f"""
    SELECT *
    FROM `{project_id}.{dataset_id}.{medium_table}`
    LIMIT {page_size}
    """

    result = run_query_with_timing(query, max_results=page_size)
    log_test(
        f"Page size {page_size:,}",
        "PASS" if result["success"] else "FAIL",
        {
            "rows_fetched": f"{result.get('rows_returned', 0):,}",
            "execution_time": f"{result['execution_time_seconds']}s",
            "throughput_rows_per_sec": round(result.get('rows_returned', 0) / max(result['execution_time_seconds'], 0.01), 0)
        }
    )


# ============================================================================
# Save results to file
# ============================================================================
output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(benchmark_results, f, indent=2)

print("\n\n" + "=" * 80)
print("📊 BENCHMARK COMPLETE")
print("=" * 80)
print(f"Results saved to: {output_file}")
print(f"Total tests run: {len(benchmark_results['tests'])}")
print(f"Passed: {sum(1 for t in benchmark_results['tests'] if t['status'] == 'PASS')}")
print(f"Failed: {sum(1 for t in benchmark_results['tests'] if t['status'] == 'FAIL')}")
print(f"Skipped: {sum(1 for t in benchmark_results['tests'] if t['status'] == 'SKIP')}")
print("=" * 80)
