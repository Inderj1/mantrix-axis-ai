#!/usr/bin/env python3
"""
Index all BigQuery tables into Weaviate with vector embeddings.
"""
import sys
from src.db.bigquery import BigQueryClient
from src.db.weaviate_client import WeaviateClient
from src.core.embeddings import EmbeddingService
from src.config import settings
import structlog

logger = structlog.get_logger()


def main():
    print("=" * 80)
    print("INDEXING ALL BIGQUERY TABLES INTO WEAVIATE")
    print("=" * 80)
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print(f"Weaviate: {settings.weaviate_url}")
    print()

    try:
        # Initialize clients
        print("Initializing clients...")
        bq = BigQueryClient()
        weaviate = WeaviateClient()
        embeddings = EmbeddingService()

        print(f"Using embedding provider: {embeddings.provider_type}")
        print(f"Embedding dimension: {embeddings.dimension}")
        print()

        # Get all tables
        print("Fetching table list from BigQuery...")
        tables = bq.list_tables()
        print(f"Found {len(tables)} tables to index")
        print()

        # Option to clear existing data
        print("Would you like to clear existing indexed data first? (y/n): ", end="")
        response = input().strip().lower()
        if response == 'y':
            print("Clearing existing data from Weaviate...")
            weaviate.delete_all_schemas()
            print("✓ Cleared\n")

        # Index each table
        indexed_count = 0
        failed_count = 0

        for i, table_name in enumerate(sorted(tables), 1):
            try:
                print(f"[{i}/{len(tables)}] Indexing {table_name}...")

                # Get table schema
                schema = bq.get_table_schema(table_name)

                # Create text representation for embedding
                columns_text = []
                for col in schema["columns"]:
                    col_text = f"{col['name']} ({col['type']})"
                    if col.get("description"):
                        col_text += f": {col['description']}"
                    columns_text.append(col_text)

                text_for_embedding = f"""
                Table: {schema['table_name']}
                Dataset: {schema['dataset']}
                Description: {schema.get('description', 'No description available')}
                Row Count: {schema.get('row_count', 0):,}
                Columns ({len(schema['columns'])}):
                {chr(10).join(columns_text)}
                """.strip()

                # Generate embedding
                embedding = embeddings.generate_embedding(text_for_embedding)

                # Index into Weaviate
                weaviate.index_table_schema(schema, embedding)

                print(f"  ✓ Indexed {table_name} ({schema.get('row_count', 0):,} rows, {len(schema['columns'])} columns)")
                indexed_count += 1

            except Exception as e:
                print(f"  ✗ Failed to index {table_name}: {e}")
                logger.error(f"Failed to index {table_name}", error=str(e))
                failed_count += 1
                continue

        print()
        print("=" * 80)
        print("INDEXING COMPLETE")
        print("=" * 80)
        print(f"Successfully indexed: {indexed_count}/{len(tables)} tables")
        if failed_count > 0:
            print(f"Failed: {failed_count} tables")
        print()

        # Test search
        print("Testing semantic search...")
        print("Enter a search query (or press Enter to skip): ", end="")
        test_query = input().strip()

        if test_query:
            print(f"\nSearching for: '{test_query}'")
            query_embedding = embeddings.generate_embedding(test_query)
            results = weaviate.search_similar_tables(query_embedding, limit=5)

            print(f"\nTop {len(results)} matching tables:")
            for i, result in enumerate(results, 1):
                distance = result.get('distance', 0)
                similarity = 1 - distance  # Convert distance to similarity
                print(f"\n{i}. {result['table_name']} (similarity: {similarity:.2%})")
                print(f"   Rows: {result.get('row_count', 0):,}")
                print(f"   Columns: {len(result.get('columns', []))}")
                if result.get('description'):
                    print(f"   Description: {result['description']}")

        print("\n✓ All done!")
        weaviate.close()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
