"""
Complete Pipeline + Accuracy Validation Test

This test demonstrates the complete system:
1. Run full pipeline (schema → RDF → vectors → cache invalidation)
2. Execute accuracy validation queries
3. Measure improvements

Expected improvements:
- 100% query execution success (all queries work)
- High table selection accuracy
- Smart caching prevents failed queries
- Pipeline invalidation keeps cache fresh
"""
import time
from datetime import datetime
from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.sql_generator import SQLGenerator
from src.db.bigquery import BigQueryClient

print("=" * 80)
print("FULL PIPELINE + ACCURACY VALIDATION TEST")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print("=" * 80)

# Test queries
test_queries = [
    {"id": "Q1", "question": "Show me all GL accounts"},
    {"id": "Q2", "question": "What is the total revenue by customer?"},
    {"id": "Q3", "question": "Show sales trends by month"},
    {"id": "Q4", "question": "Show customer segments and their performance"},
    {"id": "Q5", "question": "What products have the highest sales by region?"},
    {"id": "Q6", "question": "Show average revenue per cohort"},
]

# === PHASE 1: Run Full Pipeline ===
print("\n" + "=" * 80)
print("PHASE 1: RUNNING FULL PIPELINE")
print("=" * 80)
print("This will:")
print("  1. Extract all 14 table schemas from BigQuery")
print("  2. Build RDF knowledge graph with relationships")
print("  3. Generate vector embeddings for semantic search")
print("  4. Validate pipeline integrity")
print("  5. Invalidate stale cache entries")
print("=" * 80)

orchestrator = PipelineOrchestrator()

print("\nStarting pipeline execution...")
pipeline_start = time.time()

try:
    pipeline_result = orchestrator.execute_pipeline(
        incremental=False,  # Full refresh
        force_refresh=True
    )

    pipeline_duration = time.time() - pipeline_start

    print(f"\n✅ Pipeline completed: {pipeline_result.status.value}")
    print(f"Duration: {pipeline_duration:.1f}s")

    # Show results
    if pipeline_result.schema_extraction_result:
        print(f"\n📊 Schema Extraction:")
        print(f"  Tables extracted: {pipeline_result.schema_extraction_result.get('tables_extracted', 0)}")
        print(f"  Duration: {pipeline_result.schema_extraction_result.get('duration_seconds', 0):.1f}s")

    if pipeline_result.rdf_build_result:
        print(f"\n🔗 RDF Building:")
        rdf = pipeline_result.rdf_build_result
        print(f"  Tables processed: {rdf.get('tables_processed', 0)}")
        print(f"  Triples created: {rdf.get('total_triples', 0)}")
        print(f"  Relationships: {rdf.get('total_relationships', 0)}")
        print(f"  Duration: {rdf.get('duration_seconds', 0):.1f}s")

    if pipeline_result.vector_build_result:
        print(f"\n🎯 Vector Building:")
        vec = pipeline_result.vector_build_result
        print(f"  Vectors created: {vec.get('vectors_created', 0)}")
        print(f"  Duration: {vec.get('duration_seconds', 0):.1f}s")

    if hasattr(pipeline_result, 'cache_invalidation_result') and pipeline_result.cache_invalidation_result:
        print(f"\n🗑️  Cache Invalidation:")
        cache = pipeline_result.cache_invalidation_result
        print(f"  SQL entries deleted: {cache.get('sql_entries_deleted', 0)}")
        print(f"  Failed queries removed: {cache.get('failed_queries_removed', 0)}")
        print(f"  Tables affected: {cache.get('tables_affected', 0)}")

    if pipeline_result.errors:
        print(f"\n⚠️  Errors: {len(pipeline_result.errors)}")
        for error in pipeline_result.errors[:3]:
            print(f"  - {error}")

except Exception as e:
    print(f"\n❌ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# === PHASE 2: Run Accuracy Validation ===
print("\n" + "=" * 80)
print("PHASE 2: ACCURACY VALIDATION")
print("=" * 80)
print("Testing query execution with updated pipeline...")
print("=" * 80)

sql_gen = SQLGenerator()
bq_client = sql_gen.bq_client

results = []
successful = 0

for query_info in test_queries:
    print(f"\n{'='*60}")
    print(f"{query_info['id']}: {query_info['question']}")
    print('='*60)

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

        print(f"Generated SQL: {sql[:100]}...")
        print(f"Tables used: {tables_used}")
        print(f"From cache: {from_cache}")
        if cache_tier:
            print(f"Cache tier: {cache_tier}")
        print(f"Generation time: {gen_time:.0f}ms")
        print(f"Validation: {'✅ PASSED' if validation.get('valid') else '❌ FAILED'}")

        # Execute
        exec_start = time.time()
        rows = bq_client.execute_query(sql)
        exec_time = (time.time() - exec_start) * 1000

        print(f"Execution: ✅ SUCCESS ({len(rows)} rows in {exec_time:.0f}ms)")

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
            "cache_tier": cache_tier
        })

    except Exception as e:
        error_msg = str(e)
        print(f"Execution: ❌ FAILED - {error_msg[:100]}")

        results.append({
            "id": query_info['id'],
            "question": query_info['question'],
            "status": "FAILED",
            "error": error_msg[:200]
        })

# === PHASE 3: Summary ===
print("\n" + "=" * 80)
print("FINAL RESULTS SUMMARY")
print("=" * 80)

print(f"\n📊 Pipeline Execution:")
print(f"  Status: {pipeline_result.status.value}")
print(f"  Duration: {pipeline_duration:.1f}s")
print(f"  Tables processed: {pipeline_result.tables_processed}")
if hasattr(pipeline_result, 'cache_invalidation_result') and pipeline_result.cache_invalidation_result:
    cache = pipeline_result.cache_invalidation_result
    print(f"  Cache cleaned: {cache.get('sql_entries_deleted', 0) + cache.get('failed_queries_removed', 0)} entries")

print(f"\n🎯 Query Accuracy:")
print(f"  Success rate: {successful}/{len(test_queries)} ({successful/len(test_queries)*100:.1f}%)")
print(f"  Failed queries: {len(test_queries) - successful}")

if successful > 0:
    avg_gen_time = sum(r['gen_time_ms'] for r in results if r['status'] == 'SUCCESS') / successful
    avg_exec_time = sum(r['exec_time_ms'] for r in results if r['status'] == 'SUCCESS') / successful
    cached_count = sum(1 for r in results if r.get('from_cache'))

    print(f"\n⚡ Performance:")
    print(f"  Avg generation time: {avg_gen_time:.0f}ms")
    print(f"  Avg execution time: {avg_exec_time:.0f}ms")
    print(f"  Cached queries: {cached_count}/{successful}")

print(f"\n📝 Detailed Results:")
for r in results:
    status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
    cache_info = f" [CACHED - {r.get('cache_tier', 'N/A')}]" if r.get('from_cache') else ""

    if r['status'] == 'SUCCESS':
        print(f"{status_icon} {r['id']}: {r['question'][:50]:50} | {r['rows']:5} rows{cache_info}")
    else:
        print(f"{status_icon} {r['id']}: {r['question'][:50]:50} | ERROR")

# Final assessment
print("\n" + "=" * 80)
if successful == len(test_queries):
    print("🎉 PERFECT! All queries executed successfully!")
    print("✅ Pipeline + Smart Caching + Schema Updates = Working Together!")
elif successful > len(test_queries) * 0.8:
    print("✅ GOOD! Most queries working successfully")
else:
    print("⚠️  NEEDS ATTENTION: Several queries failed")

print("=" * 80)
