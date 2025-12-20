#!/usr/bin/env python3
"""
Sample BigQuery Data Script

Discovers all tables in a BigQuery dataset and samples data from each.
Used to understand schema structure for generating synthetic test data.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/sample_bigquery_data.py
"""

import json
import sys
import os
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

# Add backend to path so 'src' module is importable
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.db.connectors.bigquery_connector import BigQueryConnector
import structlog

logger = structlog.get_logger()


def json_serializer(obj):
    """Custom JSON serializer for non-serializable types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    raise TypeError(f"Type {type(obj)} not serializable")


def sample_bigquery_dataset(
    project_id: str = "arizona-poc",
    dataset_id: str = "copa_export_copa_data_000000000000",
    sample_size: int = 1000,
    output_file: str = "bigquery_samples.json"
):
    """
    Sample all tables in a BigQuery dataset.

    Args:
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
        sample_size: Number of rows to sample per table
        output_file: Output JSON file path
    """
    print(f"\n{'='*60}")
    print(f"BigQuery Data Sampling")
    print(f"{'='*60}")
    print(f"Project: {project_id}")
    print(f"Dataset: {dataset_id}")
    print(f"Sample size: {sample_size} rows per table")
    print(f"{'='*60}\n")

    # Connect to BigQuery
    print("Connecting to BigQuery...")
    connector = BigQueryConnector(
        project_id=project_id,
        dataset_id=dataset_id,
        auto_connect=True
    )

    # List all tables
    print("Discovering tables...")
    tables = connector.list_tables()
    print(f"Found {len(tables)} tables\n")

    # Sample each table
    samples = {
        "metadata": {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "sample_size": sample_size,
            "sampled_at": datetime.utcnow().isoformat(),
            "table_count": len(tables)
        },
        "tables": {}
    }

    for i, table_name in enumerate(tables, 1):
        print(f"[{i}/{len(tables)}] Processing: {table_name}")

        try:
            # Get schema
            schema = connector.get_table_schema(table_name)
            row_count = schema.get('row_count', 'Unknown')

            print(f"  Schema: {len(schema.get('columns', []))} columns, ~{row_count:,} rows" if isinstance(row_count, int) else f"  Schema: {len(schema.get('columns', []))} columns")

            # Sample data
            query = f"SELECT * FROM `{project_id}.{dataset_id}.{table_name}` LIMIT {sample_size}"
            result = connector.execute_query(query)

            sample_rows = result.get('rows', [])
            print(f"  Sampled: {len(sample_rows)} rows")

            # Store sample
            samples["tables"][table_name] = {
                "schema": {
                    "columns": schema.get('columns', []),
                    "row_count": row_count,
                    "size_bytes": schema.get('size_bytes'),
                    "description": schema.get('description')
                },
                "sample_rows": sample_rows[:100],  # Keep first 100 for file size
                "sample_count": len(sample_rows)
            }

            # Print column summary
            print("  Columns:")
            for col in schema.get('columns', [])[:8]:
                print(f"    - {col['name']}: {col['type']}")
            if len(schema.get('columns', [])) > 8:
                print(f"    ... and {len(schema.get('columns', [])) - 8} more")

        except Exception as e:
            print(f"  ERROR: {e}")
            samples["tables"][table_name] = {
                "error": str(e)
            }

        print()

    # Save to file
    output_path = Path(__file__).parent.parent / output_file
    print(f"Saving samples to: {output_path}")

    with open(output_path, 'w') as f:
        json.dump(samples, f, indent=2, default=json_serializer)

    print(f"\nDone! Sampled {len(tables)} tables.")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_rows = 0
    for table_name, data in samples["tables"].items():
        if "schema" in data:
            row_count = data["schema"].get("row_count")
            if isinstance(row_count, int):
                total_rows += row_count
            columns = len(data["schema"].get("columns", []))
            print(f"  {table_name}: {columns} cols, {row_count:,} rows" if isinstance(row_count, int) else f"  {table_name}: {columns} cols")

    print(f"\nTotal estimated rows: {total_rows:,}")
    print(f"Output file: {output_path}")

    return samples


def print_schema_for_synthetic_generation(samples: dict):
    """
    Print schema information formatted for synthetic data generation.
    """
    print(f"\n{'='*60}")
    print("SCHEMA FOR SYNTHETIC DATA GENERATION")
    print(f"{'='*60}\n")

    for table_name, data in samples.get("tables", {}).items():
        if "schema" not in data:
            continue

        schema = data["schema"]
        print(f"-- Table: {table_name}")
        print(f"-- Rows: {schema.get('row_count', 'Unknown')}")
        print("CREATE TABLE synthetic_data.{} (".format(table_name.lower()))

        columns = schema.get("columns", [])
        for i, col in enumerate(columns):
            col_name = col["name"]
            col_type = col["type"]

            # Map BigQuery types to generic SQL types
            type_mapping = {
                "STRING": "VARCHAR(255)",
                "INT64": "BIGINT",
                "INTEGER": "BIGINT",
                "FLOAT64": "DECIMAL(15,2)",
                "FLOAT": "DECIMAL(15,2)",
                "NUMERIC": "DECIMAL(15,2)",
                "BOOL": "BOOLEAN",
                "BOOLEAN": "BOOLEAN",
                "DATE": "DATE",
                "DATETIME": "TIMESTAMP",
                "TIMESTAMP": "TIMESTAMP",
                "TIME": "TIME",
                "BYTES": "BINARY",
            }

            sql_type = type_mapping.get(col_type.upper(), "VARCHAR(255)")
            comma = "," if i < len(columns) - 1 else ""
            print(f"    {col_name} {sql_type}{comma}")

        print(");\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sample BigQuery dataset")
    parser.add_argument("--project", default="arizona-poc", help="GCP project ID")
    parser.add_argument("--dataset", default="copa_export_copa_data_000000000000", help="BigQuery dataset ID")
    parser.add_argument("--sample-size", type=int, default=1000, help="Rows to sample per table")
    parser.add_argument("--output", default="bigquery_samples.json", help="Output JSON file")
    parser.add_argument("--print-schema", action="store_true", help="Print schema for synthetic generation")

    args = parser.parse_args()

    samples = sample_bigquery_dataset(
        project_id=args.project,
        dataset_id=args.dataset,
        sample_size=args.sample_size,
        output_file=args.output
    )

    if args.print_schema:
        print_schema_for_synthetic_generation(samples)
