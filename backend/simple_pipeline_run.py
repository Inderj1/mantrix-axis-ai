"""
Simple script to run the pipeline and index schemas into Weaviate.
"""
from src.pipeline.orchestrator import PipelineOrchestrator
from src.db.bigquery import BigQueryClient
from src.core.cache_manager import CacheManager
import time

print("Starting pipeline...")
print("=" * 80)

bq_client = BigQueryClient()
cache_manager = CacheManager()
# Use keyword arguments to avoid parameter mixup
orchestrator = PipelineOrchestrator(
    bq_client=bq_client,
    cache_manager=cache_manager
)

start = time.time()
result = orchestrator.execute_pipeline(incremental=False, force_refresh=True)
duration = time.time() - start

print("\n" + "=" * 80)
print("PIPELINE COMPLETED!")
print("=" * 80)
print(f"Run ID: {result.run_id}")
print(f"Status: {result.status.value}")
print(f"Duration: {duration:.2f}s")
print(f"Tables Processed: {result.tables_processed}")
print(f"Changes Detected: {result.changes_detected}")

if result.errors:
    print(f"\nErrors: {len(result.errors)}")
    for error in result.errors:
        print(f"  - {error}")

print("\n" + "=" * 80)
