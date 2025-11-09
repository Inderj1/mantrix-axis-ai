#!/usr/bin/env python3
"""
List all tables in the configured BigQuery dataset.
"""
import sys
from src.db.bigquery import BigQueryClient
from src.config import settings


def main():
    print(f"Connecting to BigQuery...")
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print()

    try:
        # Initialize BigQuery client
        bq = BigQueryClient()

        # List all tables
        print("Fetching table list...")
        tables = bq.list_tables()

        if not tables:
            print("No tables found in this dataset.")
            return

        print(f"\nFound {len(tables)} tables in dataset '{settings.bigquery_dataset}':")
        print("=" * 80)

        for i, table_name in enumerate(sorted(tables), 1):
            print(f"{i:3d}. {table_name}")

        print("=" * 80)
        print(f"\nTotal: {len(tables)} tables")

        # Optionally get detailed info for each table
        print("\nWould you like to see detailed schema information? (y/n): ", end="")
        response = input().strip().lower()

        if response == 'y':
            print("\nFetching detailed schema information...")
            for table_name in sorted(tables):
                try:
                    schema = bq.get_table_schema(table_name)
                    print(f"\n{'=' * 80}")
                    print(f"Table: {schema['table_name']}")
                    print(f"Rows: {schema['row_count']:,}")
                    print(f"Created: {schema.get('created', 'N/A')}")
                    print(f"Columns ({len(schema['columns'])}):")
                    for col in schema['columns']:
                        nullable = "NULL" if col['is_nullable'] else "NOT NULL"
                        print(f"  - {col['name']:<30} {col['type']:<15} {nullable}")
                except Exception as e:
                    print(f"\nError getting schema for {table_name}: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
