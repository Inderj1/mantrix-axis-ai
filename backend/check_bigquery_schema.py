"""
Check schema of BigQuery table for cross-database JOIN planning.
"""
import os
import sys
from google.cloud import bigquery

sys.path.insert(0, os.path.dirname(__file__))

def check_table_schema(table_name='customer_master_analysis'):
    """Check schema and sample data from a BigQuery table."""
    try:
        project = os.getenv('GOOGLE_CLOUD_PROJECT', 'arizona-poc')
        dataset = os.getenv('BIGQUERY_DATASET', 'copa_export_copa_data_000000000000')

        print(f"\n{'='*80}")
        print(f"BigQuery Table Schema: {table_name}")
        print(f"{'='*80}\n")

        client = bigquery.Client(project=project)
        table_ref = client.dataset(dataset).table(table_name)
        table = client.get_table(table_ref)

        # Print schema
        print("Columns:")
        for field in table.schema:
            print(f"  {field.name:30} {field.field_type:10} {field.mode}")

        # Get sample data
        print(f"\n{'='*80}")
        print("Sample Data (first 3 rows):")
        print(f"{'='*80}\n")

        query = f"""
        SELECT *
        FROM `{project}.{dataset}.{table_name}`
        LIMIT 3
        """

        results = client.query(query).result()

        for i, row in enumerate(results, 1):
            print(f"Row {i}:")
            for key, value in dict(row).items():
                print(f"  {key}: {value}")
            print()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    # Check customer_master_analysis
    check_table_schema('customer_master_analysis')

    print(f"\n{'='*80}")
    print("Also checking: cohort_sizes (simpler table)")
    print(f"{'='*80}")
    check_table_schema('cohort_sizes')
