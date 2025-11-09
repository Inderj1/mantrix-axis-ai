#!/usr/bin/env python3
"""
Analyze column overlap across all BigQuery tables to identify potential join keys.
"""
from collections import defaultdict
from src.db.bigquery import BigQueryClient
from src.config import settings


def main():
    print("=" * 80)
    print("ANALYZING COLUMN OVERLAP ACROSS BIGQUERY TABLES")
    print("=" * 80)
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print()

    # Initialize BigQuery client
    bq = BigQueryClient()

    # Get all tables
    tables = sorted(bq.list_tables())
    print(f"Analyzing {len(tables)} tables...\n")

    # Collect all columns
    column_to_tables = defaultdict(list)
    table_schemas = {}

    for table_name in tables:
        schema = bq.get_table_schema(table_name)
        table_schemas[table_name] = schema

        for col in schema['columns']:
            col_name = col['name']
            col_type = col['type']
            column_to_tables[col_name].append({
                'table': table_name,
                'type': col_type,
                'nullable': col['is_nullable']
            })

    # Find overlapping columns (appears in 2+ tables)
    overlapping_columns = {
        col: tables_list
        for col, tables_list in column_to_tables.items()
        if len(tables_list) > 1
    }

    print(f"Total unique columns: {len(column_to_tables)}")
    print(f"Columns appearing in 2+ tables: {len(overlapping_columns)}")
    print()

    # Sort by number of tables (descending)
    sorted_overlaps = sorted(
        overlapping_columns.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    print("=" * 80)
    print("OVERLAPPING COLUMNS (sorted by frequency)")
    print("=" * 80)

    for col_name, tables_list in sorted_overlaps:
        print(f"\n📊 {col_name} ({len(tables_list)} tables)")
        print("-" * 60)

        # Group by type
        types = defaultdict(list)
        for t in tables_list:
            types[t['type']].append(t['table'])

        for col_type, table_names in types.items():
            print(f"  Type: {col_type}")
            for tname in table_names:
                row_count = table_schemas[tname].get('row_count', 0)
                print(f"    • {tname} ({row_count:,} rows)")

    # Identify likely join keys
    print("\n" + "=" * 80)
    print("POTENTIAL JOIN KEYS (same name + same type in 2+ tables)")
    print("=" * 80)

    join_keys = []
    for col_name, tables_list in sorted_overlaps:
        # Check if all instances have the same type
        types = set(t['type'] for t in tables_list)
        if len(types) == 1:  # All same type
            join_keys.append({
                'column': col_name,
                'type': list(types)[0],
                'tables': [t['table'] for t in tables_list],
                'count': len(tables_list)
            })

    for key in sorted(join_keys, key=lambda x: x['count'], reverse=True):
        print(f"\n🔑 {key['column']} ({key['type']})")
        print(f"   Used in {key['count']} tables: {', '.join(key['tables'][:5])}")
        if len(key['tables']) > 5:
            print(f"   ... and {len(key['tables']) - 5} more")

    # Analyze specific high-value tables
    print("\n" + "=" * 80)
    print("KEY TABLE RELATIONSHIPS")
    print("=" * 80)

    main_tables = ['dataset_25m_table', 'transaction_data', 'customer_master_analysis',
                   'product_customer_matrix', 'GL_Accounts']

    for main_table in main_tables:
        if main_table not in table_schemas:
            continue

        print(f"\n📁 {main_table} ({table_schemas[main_table].get('row_count', 0):,} rows)")

        main_cols = {col['name']: col['type'] for col in table_schemas[main_table]['columns']}

        # Find which other tables it can join with
        joins = defaultdict(list)
        for col_name, col_type in main_cols.items():
            if col_name in overlapping_columns:
                for other_info in overlapping_columns[col_name]:
                    if other_info['table'] != main_table and other_info['type'] == col_type:
                        joins[other_info['table']].append(col_name)

        if joins:
            print("  Can join with:")
            for other_table, join_cols in sorted(joins.items(), key=lambda x: len(x[1]), reverse=True):
                other_rows = table_schemas[other_table].get('row_count', 0)
                print(f"    • {other_table} ({other_rows:,} rows)")
                print(f"      Join keys: {', '.join(join_cols[:5])}")
                if len(join_cols) > 5:
                    print(f"      ... and {len(join_cols) - 5} more")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
