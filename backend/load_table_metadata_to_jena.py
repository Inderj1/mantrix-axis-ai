#!/usr/bin/env python3
"""
Load table metadata and relationships into Jena RDF knowledge graph.
"""
import sys
import json
from pathlib import Path
from collections import defaultdict
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from src.db.bigquery import BigQueryClient
from src.config import settings
import structlog
import signal
from contextlib import contextmanager

logger = structlog.get_logger()

# Define namespace
FIN = Namespace("http://example.com/finance#")


class TimeoutError(Exception):
    pass


@contextmanager
def timeout(seconds):
    """Context manager for timeout handling."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the signal handler and alarm
    old_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def main():
    print("=" * 80)
    print("LOADING TABLE METADATA INTO JENA KNOWLEDGE GRAPH")
    print("=" * 80)
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print()

    # Initialize graph
    graph = Graph()
    graph.bind("fin", FIN)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    try:
        # Initialize BigQuery client with timeout
        print("Initializing BigQuery client...")
        with timeout(30):
            bq = BigQueryClient()
        print("✓ BigQuery client initialized")

        # Get all tables with timeout
        print("\nFetching dataset schema...")
        with timeout(60):
            tables = bq.get_dataset_schema()
        tables = sorted(tables, key=lambda x: x['table_name'])
        print(f"Loading {len(tables)} tables into knowledge graph...")
        print()

        # Collect column overlap for relationship detection
        column_to_tables = defaultdict(list)

        # Step 1: Load table and column nodes
        print("=" * 80)
        print("STEP 1: Loading Tables & Columns")
        print("=" * 80)

        for i, schema in enumerate(tables, 1):
            table_name = schema['table_name']
            print(f"[{i}/{len(tables)}] Processing {table_name}...")

            # Create table node
            table_uri = FIN[f"Table_{table_name}"]
            graph.add((table_uri, RDF.type, FIN["Table"]))
            graph.add((table_uri, FIN["tableName"], Literal(table_name)))
            graph.add((table_uri, FIN["dataset"], Literal(schema['dataset'])))
            graph.add((table_uri, FIN["project"], Literal(schema['project'])))
            graph.add((table_uri, FIN["rowCount"], Literal(schema.get('row_count', 0), datatype=XSD.integer)))

            if schema.get('description'):
                graph.add((table_uri, FIN["description"], Literal(schema['description'])))

            # Create column nodes
            for col in schema['columns']:
                col_name = col['name']
                col_type = col['type']

                # Create column node
                col_uri = FIN[f"Column_{table_name}_{col_name}"]
                graph.add((col_uri, RDF.type, FIN["Column"]))
                graph.add((col_uri, FIN["columnName"], Literal(col_name)))
                graph.add((col_uri, FIN["dataType"], Literal(col_type)))
                graph.add((col_uri, FIN["isNullable"], Literal(col.get('is_nullable', True))))

                if col.get('description'):
                    graph.add((col_uri, FIN["description"], Literal(col['description'])))

                # Link column to table
                graph.add((table_uri, FIN["hasColumn"], col_uri))
                graph.add((col_uri, FIN["belongsToTable"], table_uri))

                # Track for relationship detection
                column_to_tables[col_name].append({
                    'table': table_name,
                    'type': col_type,
                    'uri': col_uri,
                    'table_uri': table_uri
                })

            print(f"  ✓ {table_name}: {schema.get('row_count', 0):,} rows, {len(schema['columns'])} columns")

        # Step 2: Detect and create relationships
        print("\n" + "=" * 80)
        print("STEP 2: Detecting Table Relationships")
        print("=" * 80)

        relationship_count = 0

        for col_name, instances in column_to_tables.items():
            if len(instances) < 2:
                continue  # No relationship possible

            # Group by type
            by_type = defaultdict(list)
            for inst in instances:
                by_type[inst['type']].append(inst)

            # Create relationships for columns with same name AND same type
            for col_type, same_type_instances in by_type.items():
                if len(same_type_instances) < 2:
                    continue

                print(f"\n🔗 Found join key: {col_name} ({col_type})")
                print(f"   Tables: {', '.join([i['table'] for i in same_type_instances])}")

                # Create pairwise relationships
                for i, source in enumerate(same_type_instances):
                    for target in same_type_instances[i+1:]:
                        # Create relationship node
                        rel_id = f"{source['table']}__{target['table']}__{col_name}"
                        rel_uri = FIN[f"Relationship_{rel_id}"]

                        graph.add((rel_uri, RDF.type, FIN["TableRelationship"]))
                        graph.add((rel_uri, FIN["sourceTable"], source['table_uri']))
                        graph.add((rel_uri, FIN["targetTable"], target['table_uri']))
                        graph.add((rel_uri, FIN["joinColumn"], Literal(col_name)))
                        graph.add((rel_uri, FIN["columnType"], Literal(col_type)))

                        # Determine relationship type based on row counts
                        # (This is a heuristic - could be improved with actual cardinality analysis)
                        graph.add((rel_uri, FIN["joinType"], Literal("LEFT")))

                        relationship_count += 1

        print(f"\n✓ Created {relationship_count} relationships")

        # Step 3: Link to financial hierarchy (if tables match)
        print("\n" + "=" * 80)
        print("STEP 3: Linking to Financial Hierarchy")
        print("=" * 80)

        # Link GL_Accounts table to GL_Account entity type
        if 'GL_Accounts' in [t['table_name'] for t in tables]:
            gl_table_uri = FIN["Table_GL_Accounts"]
            graph.add((gl_table_uri, FIN["entityType"], FIN["GLAccount"]))
            graph.add((gl_table_uri, FIN["isDimensionTable"], Literal(True)))
            print("  ✓ Linked GL_Accounts to GLAccount entity type")

        # Mark fact vs dimension tables
        fact_tables = ['dataset_25m_table', 'transaction_data', 'sales_order_cockpit_export']
        dimension_tables = ['GL_Accounts', 'customer_master_analysis', 'product_customer_matrix']

        for table_name in fact_tables:
            table_uri = FIN[f"Table_{table_name}"]
            graph.add((table_uri, FIN["tableType"], Literal("FACT")))
            graph.add((table_uri, FIN["isFactTable"], Literal(True)))
            print(f"  ✓ Marked {table_name} as FACT table")

        for table_name in dimension_tables:
            table_uri = FIN[f"Table_{table_name}"]
            graph.add((table_uri, FIN["tableType"], Literal("DIMENSION")))
            graph.add((table_uri, FIN["isDimensionTable"], Literal(True)))
            print(f"  ✓ Marked {table_name} as DIMENSION table")

        # Step 4: Load column synonyms
        print("\n" + "=" * 80)
        print("STEP 4: Loading Column Synonyms")
        print("=" * 80)

        synonym_file = Path(__file__).parent / "column_synonyms.json"
        if synonym_file.exists():
            print(f"Loading synonyms from: {synonym_file}")
            with open(synonym_file, 'r') as f:
                synonym_data = json.load(f)

            synonym_count = 0
            for mapping in synonym_data.get('column_synonyms', []):
                table_name = mapping['target_table']
                column_name = mapping['target_column']
                confidence = mapping['confidence']
                description = mapping.get('description', '')

                # Create column URI
                col_uri = FIN[f"Column_{table_name}_{column_name}"]

                # Check if column exists in graph
                if (col_uri, RDF.type, FIN["Column"]) not in graph:
                    print(f"  ⚠️  Column not found: {table_name}.{column_name} - skipping synonyms")
                    continue

                # Create synonym nodes for each user term
                for idx, user_term in enumerate(mapping['user_terms']):
                    synonym_id = f"{table_name}_{column_name}_{idx}"
                    synonym_uri = FIN[f"ColumnSynonym_{synonym_id}"]

                    graph.add((synonym_uri, RDF.type, FIN["ColumnSynonym"]))
                    graph.add((synonym_uri, FIN["term"], Literal(user_term.lower())))
                    graph.add((synonym_uri, FIN["isPrimary"], Literal(False)))
                    graph.add((synonym_uri, FIN["synonymOf"], col_uri))
                    graph.add((synonym_uri, FIN["confidence"], Literal(confidence, datatype=XSD.float)))

                    if description:
                        graph.add((synonym_uri, FIN["description"], Literal(description)))

                    # Also link from column to synonym
                    graph.add((col_uri, FIN["hasSynonym"], synonym_uri))

                    synonym_count += 1

                print(f"  ✓ {column_name}: {len(mapping['user_terms'])} synonyms")

            print(f"\n✓ Loaded {synonym_count} column synonyms")
        else:
            print(f"⚠️  Synonym file not found: {synonym_file}")
            print("  Skipping column synonym loading")

        # Save to file
        print("\n" + "=" * 80)
        print("SAVING KNOWLEDGE GRAPH")
        print("=" * 80)

        output_file = "table_metadata_kg.ttl"
        graph.serialize(destination=output_file, format="turtle")

        print(f"\n✓ Saved to: {output_file}")
        print(f"  Total triples: {len(graph):,}")

        # Statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)

        table_count = len(list(graph.subjects(RDF.type, FIN["Table"])))
        column_count = len(list(graph.subjects(RDF.type, FIN["Column"])))
        rel_count = len(list(graph.subjects(RDF.type, FIN["TableRelationship"])))
        synonym_count = len(list(graph.subjects(RDF.type, FIN["ColumnSynonym"])))

        print(f"Tables: {table_count}")
        print(f"Columns: {column_count}")
        print(f"Relationships: {rel_count}")
        print(f"Column Synonyms: {synonym_count}")

        # Test SPARQL query
        print("\n" + "=" * 80)
        print("TEST SPARQL QUERY")
        print("=" * 80)

        query = """
        PREFIX fin: <http://example.com/finance#>

        SELECT ?tableName ?rowCount
        WHERE {
            ?table a fin:Table ;
                   fin:tableName ?tableName ;
                   fin:rowCount ?rowCount .
        }
        ORDER BY DESC(?rowCount)
        LIMIT 5
        """

        print("Query: Top 5 largest tables")
        print("-" * 60)

        results = graph.query(query)
        for row in results:
            print(f"  • {row.tableName}: {int(row.rowCount):,} rows")

        print("\n" + "=" * 80)
        print("✅ COMPLETE!")
        print("=" * 80)

        print("\nNext steps:")
        print("1. Merge this graph with existing financial hierarchy")
        print("2. Update Jena client to load from table_metadata_kg.ttl")
        print("3. Test query resolution with join discovery")

    except TimeoutError as e:
        print(f"\n✗ Timeout Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your internet connection")
        print("2. Verify BigQuery permissions: gcloud auth application-default login")
        print("3. Check if BigQuery API is enabled for your project")
        print("4. Increase timeout values if dataset is very large")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check BigQuery credentials: gcloud auth application-default login")
        print("2. Verify project and dataset settings in .env file")
        print("3. Ensure BigQuery API is enabled")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
