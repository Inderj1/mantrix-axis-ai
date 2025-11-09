#!/usr/bin/env python3
"""
Enhanced table metadata loader with intelligent column matching.

Improvements over basic version:
1. Type compatibility (STRING ⟷ INTEGER with CAST)
2. Fuzzy name matching (Customer ≈ CustomerID)
3. Confidence scoring for relationships
"""
import sys
from collections import defaultdict
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from src.db.bigquery import BigQueryClient
from src.config import settings
from src.core.knowledge_graph.column_matcher import EnhancedColumnMatcher
import structlog

logger = structlog.get_logger()

# Define namespace
FIN = Namespace("http://example.com/finance#")


def main():
    print("=" * 80)
    print("LOADING TABLE METADATA WITH ENHANCED COLUMN MATCHING")
    print("=" * 80)
    print(f"Project: {settings.google_cloud_project}")
    print(f"Dataset: {settings.bigquery_dataset}")
    print()

    # Initialize graph
    graph = Graph()
    graph.bind("fin", FIN)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    # Initialize column matcher
    matcher = EnhancedColumnMatcher()

    try:
        # Initialize BigQuery client
        bq = BigQueryClient()

        # Get all tables
        tables = bq.get_dataset_schema()
        tables = sorted(tables, key=lambda x: x['table_name'])
        print(f"Loading {len(tables)} tables into knowledge graph...")
        print()

        # Collect columns for relationship detection
        table_columns = {}  # table_name -> list of columns

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

            # Store columns for this table
            table_columns[table_name] = []

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

                # Store for relationship detection
                table_columns[table_name].append({
                    'name': col_name,
                    'type': col_type,
                    'uri': col_uri,
                    'table_uri': table_uri
                })

            print(f"  ✓ {table_name}: {schema.get('row_count', 0):,} rows, {len(schema['columns'])} columns")

        # Step 2: Enhanced relationship detection
        print("\n" + "=" * 80)
        print("STEP 2: Detecting Table Relationships (Enhanced)")
        print("=" * 80)

        relationship_count = 0
        exact_matches = 0
        type_compatible_matches = 0
        fuzzy_matches = 0

        # Compare all table pairs
        table_names = list(table_columns.keys())
        for i, table1 in enumerate(table_names):
            for table2 in table_names[i+1:]:
                # Find all matches between these two tables
                matches = matcher.find_all_matches(
                    table_columns[table1],
                    table_columns[table2]
                )

                if matches:
                    # Use best match for join
                    best_match = matches[0]

                    print(f"\n🔗 {table1} ⟷ {table2}")
                    print(f"   Column: {best_match.source_column} ({best_match.source_type}) → "
                          f"{best_match.target_column} ({best_match.target_type})")
                    print(f"   Match: {best_match.match_type} (confidence: {best_match.confidence:.0%})")
                    if best_match.cast_required:
                        print(f"   Cast: {best_match.cast_required}")

                    # Create relationship node
                    rel_id = f"{table1}__{table2}__{best_match.source_column}"
                    rel_uri = FIN[f"Relationship_{rel_id}"]

                    # Find table URIs
                    table1_uri = FIN[f"Table_{table1}"]
                    table2_uri = FIN[f"Table_{table2}"]

                    graph.add((rel_uri, RDF.type, FIN["TableRelationship"]))
                    graph.add((rel_uri, FIN["sourceTable"], table1_uri))
                    graph.add((rel_uri, FIN["targetTable"], table2_uri))
                    graph.add((rel_uri, FIN["joinColumn"], Literal(best_match.source_column)))
                    graph.add((rel_uri, FIN["columnType"], Literal(best_match.source_type)))
                    graph.add((rel_uri, FIN["matchType"], Literal(best_match.match_type)))
                    graph.add((rel_uri, FIN["confidence"], Literal(best_match.confidence, datatype=XSD.float)))

                    if best_match.cast_required:
                        graph.add((rel_uri, FIN["castRequired"], Literal(best_match.cast_required)))

                    # Determine relationship type (LEFT JOIN is safe default)
                    graph.add((rel_uri, FIN["joinType"], Literal("LEFT")))

                    relationship_count += 1

                    # Track match types
                    if best_match.match_type == 'exact':
                        exact_matches += 1
                    elif best_match.match_type == 'type_compatible':
                        type_compatible_matches += 1
                    elif best_match.match_type == 'fuzzy':
                        fuzzy_matches += 1

        print(f"\n✓ Created {relationship_count} relationships")
        print(f"   Exact matches: {exact_matches}")
        print(f"   Type-compatible matches: {type_compatible_matches}")
        print(f"   Fuzzy matches: {fuzzy_matches}")

        # Step 3: Link to financial hierarchy
        print("\n" + "=" * 80)
        print("STEP 3: Linking to Financial Hierarchy")
        print("=" * 80)

        # Link GL_Accounts table to GL_Account entity type
        if 'GL_Accounts' in table_names:
            gl_table_uri = FIN["Table_GL_Accounts"]
            graph.add((gl_table_uri, FIN["entityType"], FIN["GLAccount"]))
            graph.add((gl_table_uri, FIN["isDimensionTable"], Literal(True)))
            print("  ✓ Linked GL_Accounts to GLAccount entity type")

        # Mark fact vs dimension tables
        fact_tables = ['dataset_25m_table', 'transaction_data', 'sales_order_cockpit_export']
        dimension_tables = ['GL_Accounts', 'customer_master_analysis', 'product_customer_matrix']

        for table_name in fact_tables:
            if table_name in table_names:
                table_uri = FIN[f"Table_{table_name}"]
                graph.add((table_uri, FIN["tableType"], Literal("FACT")))
                graph.add((table_uri, FIN["isFactTable"], Literal(True)))
                print(f"  ✓ Marked {table_name} as FACT table")

        for table_name in dimension_tables:
            if table_name in table_names:
                table_uri = FIN[f"Table_{table_name}"]
                graph.add((table_uri, FIN["tableType"], Literal("DIMENSION")))
                graph.add((table_uri, FIN["isDimensionTable"], Literal(True)))
                print(f"  ✓ Marked {table_name} as DIMENSION table")

        # Save to file
        print("\n" + "=" * 80)
        print("SAVING ENHANCED KNOWLEDGE GRAPH")
        print("=" * 80)

        output_file = "table_metadata_kg_enhanced.ttl"
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

        print(f"Tables: {table_count}")
        print(f"Columns: {column_count}")
        print(f"Relationships: {rel_count}")
        print(f"  - Exact: {exact_matches}")
        print(f"  - Type-compatible: {type_compatible_matches}")
        print(f"  - Fuzzy: {fuzzy_matches}")

        # Test SPARQL query
        print("\n" + "=" * 80)
        print("TEST SPARQL QUERY")
        print("=" * 80)

        query = """
        PREFIX fin: <http://example.com/finance#>

        SELECT ?sourceTable ?targetTable ?joinCol ?matchType ?confidence
        WHERE {
            ?rel a fin:TableRelationship ;
                 fin:sourceTable ?source ;
                 fin:targetTable ?target ;
                 fin:joinColumn ?joinCol ;
                 fin:matchType ?matchType ;
                 fin:confidence ?confidence .

            ?source fin:tableName ?sourceTable .
            ?target fin:tableName ?targetTable .
        }
        ORDER BY DESC(?confidence)
        LIMIT 10
        """

        print("Query: Top 10 relationships by confidence")
        print("-" * 60)

        results = graph.query(query)
        for row in results:
            print(f"  • {row.sourceTable} ⟷ {row.targetTable}")
            print(f"    Join: {row.joinCol} ({row.matchType}, {float(row.confidence):.0%})")

        print("\n" + "=" * 80)
        print("✅ COMPLETE!")
        print("=" * 80)

        print("\nNext steps:")
        print("1. Copy table_metadata_kg_enhanced.ttl to table_metadata_kg.ttl")
        print("2. Restart server to reload knowledge graph")
        print("3. Test queries with enhanced JOIN discovery")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
