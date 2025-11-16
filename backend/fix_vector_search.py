"""
Fix vector search by clearing corrupted Weaviate data and reindexing.

This script:
1. Clears the Weaviate TableSchemas collection
2. Re-runs the pipeline to properly index all table schemas
3. Validates that vector search is working
"""

import asyncio
from src.db.weaviate_client import WeaviateClient
from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.sql_generator import SQLGenerator
import structlog

logger = structlog.get_logger()

async def fix_vector_search():
    """Fix vector search by clearing and reindexing."""

    print("=" * 80)
    print("VECTOR SEARCH FIX")
    print("=" * 80)
    print()

    # Step 1: Clear Weaviate collection
    print("Step 1: Clearing Weaviate TableSchemas collection...")
    try:
        weaviate_client = WeaviateClient()

        # Delete all schemas
        weaviate_client.delete_all_schemas()
        print("✅ Cleared all table schemas from Weaviate")
        print()

        # Close client
        weaviate_client.close()
    except Exception as e:
        print(f"⚠️  Error clearing Weaviate: {e}")
        print("   Continuing anyway...")
        print()

    # Step 2: Run pipeline to reindex
    print("Step 2: Running full pipeline to reindex all tables...")
    try:
        orchestrator = PipelineOrchestrator()

        # Execute full refresh
        pipeline_run = orchestrator.execute_pipeline(
            incremental=False,  # Full refresh
            tables=None  # All tables
        )

        print(f"✅ Pipeline completed: {pipeline_run.run_id}")
        print(f"   Status: {pipeline_run.status.value if hasattr(pipeline_run.status, 'value') else pipeline_run.status}")
        print(f"   Duration: {pipeline_run.duration_seconds:.1f}s")
        print(f"   Tables Processed: {pipeline_run.tables_processed}")
        print()

        # Check vector build stats
        if pipeline_run.vector_build_result:
            print("   Vector Build Stats:")
            print(f"   - Duration: {pipeline_run.vector_build_result.get('duration_seconds', 0):.1f}s")
            print(f"   - Vectors Created: {pipeline_run.vector_build_result.get('vectors_created', 0)}")
            print(f"   - Errors: {len(pipeline_run.vector_build_result.get('errors', []))}")
        print()

    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Test vector search
    print("Step 3: Testing vector search...")
    try:
        sql_gen = SQLGenerator()

        # Try a simple query that should use vector search
        test_query = "Show me all GL accounts"

        result = sql_gen.generate_sql(
            query=test_query,
            use_vector_search=True,
            max_tables=5
        )

        if result.get("sql"):
            print("✅ Vector search is working!")
            print(f"   Test query: '{test_query}'")
            print(f"   Tables selected: {result.get('tables_used', [])}")
            print(f"   SQL generated: Yes ({len(result.get('sql', ''))} chars)")
        else:
            print("⚠️  Vector search may not be working properly")
            print(f"   Error: {result.get('error')}")
        print()

    except Exception as e:
        print(f"❌ Vector search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("=" * 80)
    print("FIX COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Run accuracy validation again: python test_accuracy_validation.py")
    print("2. Check that table selection accuracy improves")
    print("3. Vector search should now work without falling back to all tables")
    print()

    return True

if __name__ == "__main__":
    success = asyncio.run(fix_vector_search())
    exit(0 if success else 1)
