#!/usr/bin/env python3
"""
Test script to diagnose multi-connector vector search behavior.

This script helps understand why vector search results are dominated by one database
when multiple connectors are enabled.

Run: cd backend && source venv/bin/activate && python test_multi_connector_search.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.weaviate_client import WeaviateClient
from src.core.embeddings import EmbeddingService


def test_search():
    """Test vector search with different connector configurations."""
    print("Initializing services...")

    # Initialize
    weaviate = WeaviateClient()
    embedding_service = EmbeddingService()

    print(f"Embedding provider: {embedding_service.provider_type}")
    print(f"Embedding dimension: {embedding_service.dimension}")

    # Test queries
    test_queries = ["clients", "customers", "how many clients do we have"]

    # Connector IDs from the logs (Demo organization)
    bigquery_connector = "692c4ba94a78978f0264a987"
    snowflake_connector = "692dc5ada4a096b958ae19a9"
    both_connectors = [bigquery_connector, snowflake_connector]

    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print('='*70)

        # Get embedding
        embedding = embedding_service.generate_embedding(query)
        print(f"Embedding generated (dim={len(embedding)})")

        # Test 1: Both connectors (current behavior)
        print(f"\n--- Test 1: Both Connectors (current behavior) ---")
        results = weaviate.search_similar_tables(
            query_embedding=embedding,
            limit=10,
            connector_ids=both_connectors,
            organization_id="Demo"
        )
        print(f"Found {len(results)} tables:")
        for i, r in enumerate(results, 1):
            db_type = r.get('database_type', 'unknown')
            table_name = r.get('table_name', 'unknown')
            distance = r.get('distance', 'N/A')
            if isinstance(distance, (int, float)):
                distance = f"{distance:.4f}"
            print(f"  {i}. [{db_type:12}] {table_name:40} (dist: {distance})")

        # Test 2: BigQuery only
        print(f"\n--- Test 2: BigQuery Only ---")
        results = weaviate.search_similar_tables(
            query_embedding=embedding,
            limit=5,
            connector_id=bigquery_connector,
            organization_id="Demo"
        )
        print(f"Found {len(results)} tables:")
        for i, r in enumerate(results, 1):
            table_name = r.get('table_name', 'unknown')
            distance = r.get('distance', 'N/A')
            if isinstance(distance, (int, float)):
                distance = f"{distance:.4f}"
            print(f"  {i}. {table_name:40} (dist: {distance})")

        # Test 3: Snowflake only
        print(f"\n--- Test 3: Snowflake Only ---")
        results = weaviate.search_similar_tables(
            query_embedding=embedding,
            limit=5,
            connector_id=snowflake_connector,
            organization_id="Demo"
        )
        print(f"Found {len(results)} tables:")
        for i, r in enumerate(results, 1):
            table_name = r.get('table_name', 'unknown')
            distance = r.get('distance', 'N/A')
            if isinstance(distance, (int, float)):
                distance = f"{distance:.4f}"
            print(f"  {i}. {table_name:40} (dist: {distance})")

        # Analysis
        print(f"\n--- Analysis ---")
        bq_results = weaviate.search_similar_tables(
            query_embedding=embedding,
            limit=10,
            connector_id=bigquery_connector,
            organization_id="Demo"
        )
        sf_results = weaviate.search_similar_tables(
            query_embedding=embedding,
            limit=10,
            connector_id=snowflake_connector,
            organization_id="Demo"
        )

        if bq_results and sf_results:
            bq_best = bq_results[0].get('distance', float('inf'))
            sf_best = sf_results[0].get('distance', float('inf'))

            if isinstance(bq_best, (int, float)) and isinstance(sf_best, (int, float)):
                print(f"Best BigQuery distance: {bq_best:.4f} ({bq_results[0].get('table_name')})")
                print(f"Best Snowflake distance: {sf_best:.4f} ({sf_results[0].get('table_name')})")

                if bq_best < sf_best:
                    print(f"BigQuery tables rank higher (lower distance = more similar)")
                else:
                    print(f"Snowflake tables rank higher (lower distance = more similar)")


def list_all_tables():
    """List all tables in Weaviate for Demo organization."""
    print("\n" + "="*70)
    print("Listing all indexed tables for Demo organization")
    print("="*70)

    weaviate = WeaviateClient()

    # Get a generic embedding to search all
    embedding_service = EmbeddingService()
    embedding = embedding_service.generate_embedding("table data schema")

    bigquery_connector = "692c4ba94a78978f0264a987"
    snowflake_connector = "692dc5ada4a096b958ae19a9"

    print("\n--- BigQuery Tables ---")
    results = weaviate.search_similar_tables(
        query_embedding=embedding,
        limit=50,
        connector_id=bigquery_connector,
        organization_id="Demo"
    )
    for r in results:
        print(f"  - {r.get('table_name')}")
    print(f"Total: {len(results)} tables")

    print("\n--- Snowflake Tables ---")
    results = weaviate.search_similar_tables(
        query_embedding=embedding,
        limit=50,
        connector_id=snowflake_connector,
        organization_id="Demo"
    )
    for r in results:
        print(f"  - {r.get('table_name')}")
    print(f"Total: {len(results)} tables")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test multi-connector vector search")
    parser.add_argument("--list", action="store_true", help="List all indexed tables")
    args = parser.parse_args()

    if args.list:
        list_all_tables()
    else:
        test_search()
