#!/usr/bin/env python3
"""
Validate the knowledge graph TTL file and check for financial metrics.
This script doesn't require BigQuery - it just reads and validates the existing KG.
"""
from rdflib import Graph, Namespace
from rdflib.namespace import RDF
import sys

# Define namespace
FIN = Namespace("http://example.com/finance#")


def main():
    print("=" * 80)
    print("KNOWLEDGE GRAPH VALIDATION")
    print("=" * 80)

    try:
        # Load existing graph
        print("\nLoading knowledge graph from table_metadata_kg.ttl...")
        graph = Graph()
        graph.parse("table_metadata_kg.ttl", format="turtle")
        print(f"✓ Loaded {len(graph):,} triples")

        # Statistics
        print("\n" + "=" * 80)
        print("STATISTICS")
        print("=" * 80)

        # Count different entity types
        table_count = len(list(graph.subjects(RDF.type, FIN["Table"])))
        column_count = len(list(graph.subjects(RDF.type, FIN["Column"])))
        rel_count = len(list(graph.subjects(RDF.type, FIN["TableRelationship"])))
        metric_count = len(list(graph.subjects(RDF.type, FIN["L1Metric"])))
        template_count = len(list(graph.subjects(RDF.type, FIN["QueryTemplate"])))

        print(f"Tables: {table_count}")
        print(f"Columns: {column_count}")
        print(f"Relationships: {rel_count}")
        print(f"Financial Metrics: {metric_count}")
        print(f"Query Templates: {template_count}")

        # List financial metrics
        if metric_count > 0:
            print("\n" + "=" * 80)
            print("FINANCIAL METRICS DEFINED")
            print("=" * 80)

            query = """
            PREFIX fin: <http://example.com/finance#>

            SELECT ?metric ?name ?code ?category ?formula
            WHERE {
                ?metric a fin:L1Metric ;
                       fin:name ?name ;
                       fin:code ?code ;
                       fin:category ?category ;
                       fin:formula ?formula .
            }
            ORDER BY ?code
            """

            results = graph.query(query)
            for i, row in enumerate(results, 1):
                print(f"\n{i}. {row.code}: {row.name}")
                print(f"   Category: {row.category}")
                print(f"   Formula: {row.formula}")

        # List tables
        print("\n" + "=" * 80)
        print("TABLES IN KNOWLEDGE GRAPH")
        print("=" * 80)

        table_query = """
        PREFIX fin: <http://example.com/finance#>

        SELECT ?tableName ?rowCount ?tableType
        WHERE {
            ?table a fin:Table ;
                   fin:tableName ?tableName ;
                   fin:rowCount ?rowCount .
            OPTIONAL { ?table fin:tableType ?tableType }
        }
        ORDER BY DESC(?rowCount)
        LIMIT 10
        """

        results = graph.query(table_query)
        for i, row in enumerate(results, 1):
            table_type = row.tableType if row.tableType else "N/A"
            print(f"{i}. {row.tableName}: {int(row.rowCount):,} rows [{table_type}]")

        # Validate query templates
        if template_count > 0:
            print("\n" + "=" * 80)
            print("QUERY TEMPLATES DEFINED")
            print("=" * 80)

            template_query = """
            PREFIX fin: <http://example.com/finance#>

            SELECT ?template ?name ?metric
            WHERE {
                ?template a fin:QueryTemplate ;
                         fin:templateName ?name .
                OPTIONAL { ?template fin:forMetric ?metric }
            }
            """

            results = graph.query(template_query)
            for i, row in enumerate(results, 1):
                print(f"{i}. {row.name}")
                if row.metric:
                    print(f"   For metric: {row.metric}")

        print("\n" + "=" * 80)
        print("✅ VALIDATION COMPLETE!")
        print("=" * 80)
        print(f"\nKnowledge graph is valid and contains {metric_count} financial metrics")

    except FileNotFoundError:
        print("\n✗ Error: table_metadata_kg.ttl not found")
        print("\nPlease run load_table_metadata_to_jena.py first to generate the knowledge graph")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
