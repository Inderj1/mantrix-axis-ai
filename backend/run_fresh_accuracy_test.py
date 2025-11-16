"""
Run fresh accuracy validation test after fixing cache and Weaviate schemas.
This will compare before/after pipeline performance with clean cache.
"""
import os
import json
from datetime import datetime
from src.core.sql_generator import SQLGenerator
from src.db.bigquery import BigQueryClient
from src.pipeline.orchestrator import PipelineOrchestrator

print("=" * 80)
print("FRESH ACCURACY VALIDATION TEST (POST-FIX)")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print("This test runs after:")
print("1. ✅ Fixed Weaviate schema storage (added columns field)")
print("2. ✅ Cleared stale Redis cache")
print("3. ✅ Verified SQL generation with correct column names")
print("=" * 80)

# Test queries - comprehensive suite
test_queries = [
    {"id": "Q1", "question": "Show me all GL accounts", "expected_tables": ["GL_Accounts"]},
    {"id": "Q2", "question": "What is the total revenue by customer?", "expected_tables": ["dataset_25m_table"]},
    {"id": "Q3", "question": "Show sales trends by month", "expected_tables": ["dataset_25m_table"]},
    {"id": "Q4", "question": "Show me customer segments and their performance", "expected_tables": ["customer_master_analysis", "segment_performance_summary"]},
    {"id": "Q5", "question": "What products have the highest sales by region?", "expected_tables": ["sales_order_cockpit_export"]},
    {"id": "Q6", "question": "Show average revenue per cohort", "expected_tables": ["cohort_avg_revenue_table"]},
]

# Initialize components
sql_gen = SQLGenerator()
bq_client = sql_gen.bq_client

def run_test_queries(queries, phase_name):
    """Test queries and return results."""
    results = []

    for query_info in queries:
        print(f"\nTesting {query_info['id']}: {query_info['question']}")

        try:
            # Generate SQL
            result = sql_gen.generate_sql(
                query=query_info["question"],
                use_vector_search=True
            )

            # Try to execute
            try:
                rows = bq_client.execute_query(result['sql'])
                execution_status = "SUCCESS"
                row_count = len(rows)
                error = None
                print(f"  ✅ SQL executed successfully - {row_count} rows")
            except Exception as e:
                execution_status = "FAILED"
                row_count = 0
                error = str(e)[:100]
                print(f"  ❌ Execution failed: {error}")

            # Check table accuracy
            tables_used = result.get('tables_used', [])
            expected_tables = set(query_info['expected_tables'])
            actual_tables = set(tables_used)

            table_accuracy = len(expected_tables & actual_tables) / len(expected_tables) if expected_tables else 0

            results.append({
                "query_id": query_info['id'],
                "question": query_info['question'],
                "sql_generated": True,
                "execution_status": execution_status,
                "row_count": row_count,
                "table_accuracy": table_accuracy,
                "expected_tables": list(expected_tables),
                "actual_tables": list(actual_tables),
                "error": error
            })

        except Exception as e:
            print(f"  ❌ SQL generation failed: {str(e)[:100]}")
            results.append({
                "query_id": query_info['id'],
                "question": query_info['question'],
                "sql_generated": False,
                "execution_status": "FAILED",
                "row_count": 0,
                "table_accuracy": 0,
                "error": str(e)[:100]
            })

    return results

print("\n" + "=" * 80)
print("PHASE 1: TESTING CURRENT STATE")
print("=" * 80)
current_results = run_test_queries(test_queries, "CURRENT")

# Calculate metrics
successful = sum(1 for r in current_results if r['execution_status'] == 'SUCCESS')
total = len(current_results)
avg_table_accuracy = sum(r['table_accuracy'] for r in current_results) / total * 100

print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print(f"✅ Execution Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
print(f"📊 Average Table Accuracy: {avg_table_accuracy:.1f}%")
print("\nDetailed Results:")
for r in current_results:
    status = "✅" if r['execution_status'] == 'SUCCESS' else "❌"
    print(f"{status} {r['query_id']}: {r['question'][:50]:50} | Rows: {r['row_count']:5} | Tables: {r['table_accuracy']*100:.0f}%")

# Save results
os.makedirs("test_results", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
results_file = f"test_results/fresh_accuracy_{timestamp}.json"

with open(results_file, 'w') as f:
    json.dump({
        "timestamp": timestamp,
        "results": current_results,
        "metrics": {
            "success_rate": successful/total,
            "table_accuracy": avg_table_accuracy,
            "successful_queries": successful,
            "total_queries": total
        }
    }, f, indent=2)

print(f"\n💾 Results saved to: {results_file}")
print("\n✅ TEST COMPLETE")