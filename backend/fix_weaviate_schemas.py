"""
Fix Weaviate schemas by clearing and re-indexing with correct column information.
"""
import asyncio
from src.db.weaviate_client import WeaviateClient
from src.pipeline.orchestrator import PipelineOrchestrator
from src.db.bigquery import BigQueryClient
from src.core.cache_manager import CacheManager

def fix_schemas():
    """Clear Weaviate and re-run pipeline."""

    print("=" * 80)
    print("FIXING WEAVIATE SCHEMAS")
    print("=" * 80)

    # Step 1: Clear Weaviate
    print("\nStep 1: Clearing Weaviate...")
    weaviate_client = WeaviateClient()
    weaviate_client.delete_all_schemas()
    print("✓ Weaviate cleared")

    # Step 2: Run pipeline to re-index
    print("\nStep 2: Running pipeline to re-index schemas...")
    bq_client = BigQueryClient()
    cache_manager = CacheManager()
    orchestrator = PipelineOrchestrator(bq_client, cache_manager)

    result = orchestrator.execute_pipeline(incremental=False, force_refresh=True)

    print(f"\n✓ Pipeline completed!")
    print(f"  Run ID: {result.run_id}")
    print(f"  Status: {result.status.value}")
    print(f"  Duration: {result.duration_seconds:.2f}s")
    print(f"  Tables Processed: {result.tables_processed}")

    # Step 3: Verify one table
    print("\nStep 3: Verifying GL_Accounts has columns...")
    from src.core.embeddings import EmbeddingService
    embedding_service = EmbeddingService()

    query_embedding = embedding_service.generate_embedding("GL Accounts")
    results = weaviate_client.search_similar_tables(query_embedding, limit=1)

    if results and results[0]['table_name'] == 'GL_Accounts':
        gl_schema = results[0]
        print(f"✓ GL_Accounts found in Weaviate")
        print(f"  Columns: {len(gl_schema.get('columns', []))}")

        if len(gl_schema.get('columns', [])) > 0:
            print("\n✓✓✓ SUCCESS! Columns are now stored correctly!")
            print("\nFirst 3 columns:")
            for col in gl_schema['columns'][:3]:
                print(f"  - {col.get('name')}: {col.get('type')}")
        else:
            print("\n❌ FAILED! Still no columns in Weaviate!")
    else:
        print("❌ GL_Accounts not found in results")

    weaviate_client.close()

if __name__ == "__main__":
    fix_schemas()
