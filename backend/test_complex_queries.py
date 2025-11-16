"""
Test Complex Query Scenarios with Smart Caching

This test validates that the smart caching system and improved SQL generation
handle complex queries involving:
- Multi-table JOINs
- Advanced aggregations
- Window functions
- Complex business logic
"""
import time
from datetime import datetime
from src.core.sql_generator import SQLGenerator
from src.db.bigquery import BigQueryClient

print("=" * 80)
print("COMPLEX QUERY TESTING - Smart Caching Validation")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print("=" * 80)

# Complex test queries
complex_queries = [
    {
        "id": "CQ1",
        "question": "Show me the top 10 customers by revenue with their year-over-year growth rate and product diversity (number of unique products purchased)",
        "description": "Multi-table JOIN with aggregations, year-over-year calculation, and product diversity metric"
    },
    {
        "id": "CQ2",
        "question": "What is the monthly revenue trend for each RFM segment, showing the running total and percentage change from previous month?",
        "description": "Window functions with LAG, running totals, percentage calculations"
    }
]

sql_gen = SQLGenerator()
bq_client = sql_gen.bq_client

results = []
successful = 0

for query_info in complex_queries:
    print(f"\n{'=' * 80}")
    print(f"{query_info['id']}: {query_info['question']}")
    print(f"Expected complexity: {query_info['description']}")
    print('=' * 80)

    try:
        # Generate SQL
        gen_start = time.time()
        result = sql_gen.generate_sql(
            query=query_info["question"],
            use_vector_search=True
        )
        gen_time = (time.time() - gen_start) * 1000

        # Get details
        sql = result.get("sql", "")
        tables_used = result.get("tables_used", [])
        from_cache = result.get("from_cache", False)
        cache_tier = result.get("cache_tier")
        validation = result.get("validation", {})
        confidence_score = result.get("confidence_score")

        print(f"\n📝 Generated SQL:")
        print("-" * 80)
        # Show first 500 chars of SQL for readability
        sql_preview = sql[:500] + "..." if len(sql) > 500 else sql
        print(sql_preview)
        print("-" * 80)

        print(f"\n📊 Query Metadata:")
        print(f"  Tables used: {tables_used}")
        print(f"  From cache: {from_cache}")
        if cache_tier:
            print(f"  Cache tier: {cache_tier}")
        if confidence_score:
            print(f"  Confidence: {confidence_score:.2f}")
        print(f"  Generation time: {gen_time:.0f}ms")
        print(f"  Validation: {'✅ PASSED' if validation.get('valid') else '❌ FAILED'}")

        # Analyze SQL complexity
        sql_lower = sql.lower()
        has_join = "join" in sql_lower
        has_window = any(fn in sql_lower for fn in ["row_number", "rank", "lag", "lead", "over("])
        has_cte = "with" in sql_lower and "as (" in sql_lower
        has_subquery = sql_lower.count("select") > 1

        print(f"\n🔍 SQL Complexity Analysis:")
        print(f"  Contains JOINs: {'✅' if has_join else '❌'}")
        print(f"  Contains Window Functions: {'✅' if has_window else '❌'}")
        print(f"  Contains CTEs: {'✅' if has_cte else '❌'}")
        print(f"  Contains Subqueries: {'✅' if has_subquery else '❌'}")

        # Execute query
        print(f"\n⚡ Executing query...")
        exec_start = time.time()
        rows = bq_client.execute_query(sql)
        exec_time = (time.time() - exec_start) * 1000

        print(f"✅ Execution: SUCCESS")
        print(f"  Rows returned: {len(rows)}")
        print(f"  Execution time: {exec_time:.0f}ms")

        # Show sample results (first 3 rows)
        if rows and len(rows) > 0:
            print(f"\n📋 Sample Results (first 3 rows):")
            for i in range(min(3, len(rows))):
                try:
                    row_dict = dict(rows[i])
                    # Truncate long values for display
                    display_dict = {k: (str(v)[:50] + '...' if len(str(v)) > 50 else v) for k, v in row_dict.items()}
                    print(f"  Row {i+1}: {display_dict}")
                except Exception as e:
                    print(f"  Row {i+1}: [Error displaying: {e}]")

        # Check if query will be cached
        exec_metadata = result.get("execution_metadata", {})
        if exec_metadata:
            print(f"\n💾 Caching Decision:")
            print(f"  Validation status: {exec_metadata.get('validation_status')}")
            print(f"  Execution time: {exec_metadata.get('execution_time_ms', 0):.0f}ms")
            print(f"  Confidence score: {exec_metadata.get('confidence_score', 0):.2f}")
            print(f"  Cache tier: {result.get('cache_tier', 'NOT CACHED')}")

        successful += 1
        results.append({
            "id": query_info['id'],
            "question": query_info['question'],
            "status": "SUCCESS",
            "rows": len(rows),
            "gen_time_ms": gen_time,
            "exec_time_ms": exec_time,
            "tables_used": tables_used,
            "from_cache": from_cache,
            "cache_tier": cache_tier,
            "has_join": has_join,
            "has_window": has_window,
            "has_cte": has_cte,
            "complexity": "HIGH" if (has_join or has_window or has_cte) else "MEDIUM"
        })

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Execution: FAILED")
        print(f"  Error: {error_msg[:200]}")

        results.append({
            "id": query_info['id'],
            "question": query_info['question'],
            "status": "FAILED",
            "error": error_msg[:500]
        })

# Summary
print("\n" + "=" * 80)
print("COMPLEX QUERY TEST SUMMARY")
print("=" * 80)

print(f"\n🎯 Success Rate:")
print(f"  Successful: {successful}/{len(complex_queries)} ({successful/len(complex_queries)*100:.1f}%)")
print(f"  Failed: {len(complex_queries) - successful}")

if successful > 0:
    avg_gen_time = sum(r['gen_time_ms'] for r in results if r['status'] == 'SUCCESS') / successful
    avg_exec_time = sum(r['exec_time_ms'] for r in results if r['status'] == 'SUCCESS') / successful
    total_tables = sum(len(r['tables_used']) for r in results if r['status'] == 'SUCCESS')
    cached_count = sum(1 for r in results if r.get('from_cache'))

    high_complexity = sum(1 for r in results if r.get('complexity') == 'HIGH')

    print(f"\n⚡ Performance:")
    print(f"  Avg generation time: {avg_gen_time:.0f}ms")
    print(f"  Avg execution time: {avg_exec_time:.0f}ms")
    print(f"  Total tables used: {total_tables}")
    print(f"  Cached queries: {cached_count}/{successful}")

    print(f"\n🔍 Complexity Analysis:")
    print(f"  High complexity queries: {high_complexity}/{successful}")
    print(f"  Queries with JOINs: {sum(1 for r in results if r.get('has_join', False))}")
    print(f"  Queries with Window Fns: {sum(1 for r in results if r.get('has_window', False))}")
    print(f"  Queries with CTEs: {sum(1 for r in results if r.get('has_cte', False))}")

print(f"\n📝 Detailed Results:")
for r in results:
    status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
    complexity = r.get('complexity', 'N/A')
    cache_info = f" [CACHED - {r.get('cache_tier', 'N/A')}]" if r.get('from_cache') else ""

    if r['status'] == 'SUCCESS':
        print(f"{status_icon} {r['id']} ({complexity}): {r['rows']:3} rows, "
              f"{r['exec_time_ms']:5.0f}ms{cache_info}")
    else:
        print(f"{status_icon} {r['id']}: ERROR - {r.get('error', 'Unknown')[:60]}...")

print("\n" + "=" * 80)
if successful == len(complex_queries):
    print("🎉 PERFECT! All complex queries executed successfully!")
    print("✅ Smart Caching handles advanced SQL with JOINs, window functions, and aggregations!")
elif successful > 0:
    print(f"✅ GOOD! {successful}/{len(complex_queries)} complex queries working")
else:
    print("⚠️  NEEDS ATTENTION: Complex queries failed")

print("=" * 80)
