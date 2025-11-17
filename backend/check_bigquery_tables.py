"""
Quick script to check available BigQuery tables for cross-database testing.
"""
import os
import sys
from google.cloud import bigquery

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

def check_bigquery_tables():
    """List available tables in BigQuery dataset."""
    try:
        # Initialize BigQuery client
        project = os.getenv('GOOGLE_CLOUD_PROJECT', 'arizona-poc')
        dataset = os.getenv('BIGQUERY_DATASET', 'copa_export_copa_data_000000000000')

        print(f"\n{'='*80}")
        print(f"Checking BigQuery Tables")
        print(f"{'='*80}")
        print(f"Project: {project}")
        print(f"Dataset: {dataset}\n")

        client = bigquery.Client(project=project)

        # List tables in dataset
        dataset_ref = client.dataset(dataset)
        tables = list(client.list_tables(dataset_ref))

        print(f"Found {len(tables)} tables:\n")

        for table in tables[:10]:  # Show first 10 tables
            table_ref = dataset_ref.table(table.table_id)
            table_obj = client.get_table(table_ref)

            print(f"  {table.table_id}")
            print(f"    Rows: {table_obj.num_rows:,}")
            print(f"    Columns: {len(table_obj.schema)}")

            # Show first few columns
            print(f"    Sample columns: {', '.join([field.name for field in table_obj.schema[:5]])}")
            print()

        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more tables\n")

        # Suggest a table for testing
        if tables:
            print(f"{'='*80}")
            print(f"Suggested table for cross-database JOIN: {tables[0].table_id}")
            print(f"{'='*80}\n")

        return tables

    except Exception as e:
        print(f"❌ Error checking BigQuery tables: {str(e)}")
        print(f"   Make sure credentials are configured correctly.")
        return []

if __name__ == '__main__':
    check_bigquery_tables()
