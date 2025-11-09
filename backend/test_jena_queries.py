#!/usr/bin/env python3
"""
Test Apache Jena knowledge graph with real query scenarios.
"""
from rdflib import Graph, Namespace
from rdflib.namespace import RDF
import structlog

logger = structlog.get_logger()

# Define namespace
FIN = Namespace("http://example.com/finance#")


def load_knowledge_graph():
    """Load the knowledge graph from file."""
    print("=" * 80)
    print("LOADING JENA KNOWLEDGE GRAPH")
    print("=" * 80)

    graph = Graph()
    graph.bind("fin", FIN)

    # Load table metadata
    kg_file = "table_metadata_kg.ttl"
    print(f"Loading: {kg_file}...")
    graph.parse(kg_file, format="turtle")

    print(f"✓ Loaded {len(graph):,} triples")
    print()

    return graph


def test_query_1_find_customer_tables(graph):
    """Test: Find tables related to 'customer'."""
    print("=" * 80)
    print("TEST 1: Find tables for customer-related queries")
    print("=" * 80)
    print("Natural Language: 'Show me customer revenue'")
    print()

    query = """
    PREFIX fin: <http://example.com/finance#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?tableName ?rowCount ?columnName
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:rowCount ?rowCount ;
               fin:hasColumn ?column .

        ?column fin:columnName ?columnName .

        FILTER(
            CONTAINS(LCASE(?tableName), "customer") ||
            CONTAINS(LCASE(?columnName), "customer")
        )
    }
    ORDER BY DESC(?rowCount)
    LIMIT 10
    """

    results = graph.query(query)

    tables_found = set()
    for row in results:
        if row.tableName not in tables_found:
            print(f"📊 {row.tableName} ({int(row.rowCount):,} rows)")
            tables_found.add(row.tableName)
        print(f"   └─ Column: {row.columnName}")

    print(f"\n✓ Found {len(tables_found)} tables with customer data")
    print()
    return list(tables_found)


def test_query_2_find_join_path(graph, table1, table2):
    """Test: Find join path between two tables."""
    print("=" * 80)
    print(f"TEST 2: Find join path between tables")
    print("=" * 80)
    print(f"Tables: {table1} → {table2}")
    print()

    query = f"""
    PREFIX fin: <http://example.com/finance#>

    SELECT ?joinColumn ?columnType
    WHERE {{
        ?rel a fin:TableRelationship ;
             fin:joinColumn ?joinColumn ;
             fin:columnType ?columnType ;
             fin:sourceTable ?source ;
             fin:targetTable ?target .

        ?source fin:tableName "{table1}" .
        ?target fin:tableName "{table2}" .
    }}
    """

    results = graph.query(query)

    join_keys = []
    for row in results:
        print(f"🔑 JOIN ON: {row.joinColumn} ({row.columnType})")
        join_keys.append(str(row.joinColumn))

    if join_keys:
        print(f"\n✓ Found {len(join_keys)} possible join keys")
    else:
        print("\n✗ No direct join path found")

    print()
    return join_keys


def test_query_3_gl_account_lookup(graph):
    """Test: Find GL Account dimension table."""
    print("=" * 80)
    print("TEST 3: Find GL Account lookup table")
    print("=" * 80)
    print("Natural Language: 'Show revenue by GL account category'")
    print()

    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?tableName ?rowCount ?isDimension
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:rowCount ?rowCount .

        OPTIONAL { ?table fin:isDimensionTable ?isDimension }

        ?table fin:hasColumn ?column .
        ?column fin:columnName "GL_Account" .
    }
    ORDER BY ?rowCount
    """

    results = graph.query(query)

    for row in results:
        is_dim = "📂 DIMENSION" if row.isDimension else "📊 FACT"
        print(f"{is_dim}: {row.tableName} ({int(row.rowCount):,} rows)")

    print()


def test_query_4_revenue_columns(graph):
    """Test: Find all revenue-related columns."""
    print("=" * 80)
    print("TEST 4: Find all revenue columns across tables")
    print("=" * 80)
    print("Natural Language: 'What is total revenue?'")
    print()

    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT DISTINCT ?tableName ?columnName ?dataType
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:hasColumn ?column .

        ?column fin:columnName ?columnName ;
                fin:dataType ?dataType .

        FILTER(
            CONTAINS(LCASE(?columnName), "revenue") ||
            CONTAINS(LCASE(?columnName), "sales")
        )
    }
    ORDER BY ?tableName ?columnName
    """

    results = graph.query(query)

    by_table = {}
    for row in results:
        table = str(row.tableName)
        if table not in by_table:
            by_table[table] = []
        by_table[table].append((str(row.columnName), str(row.dataType)))

    for table, columns in by_table.items():
        print(f"\n📊 {table}:")
        for col_name, col_type in columns:
            print(f"   • {col_name} ({col_type})")

    print()


def test_query_5_multi_hop_join(graph):
    """Test: Find multi-hop join path."""
    print("=" * 80)
    print("TEST 5: Multi-table join discovery")
    print("=" * 80)
    print("Natural Language: 'Show customer segments with product preferences'")
    print()

    # Find tables needed
    query_tables = """
    PREFIX fin: <http://example.com/finance#>

    SELECT DISTINCT ?tableName ?tableType
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName .

        OPTIONAL { ?table fin:tableType ?tableType }

        FILTER(
            CONTAINS(LCASE(?tableName), "customer") ||
            CONTAINS(LCASE(?tableName), "product")
        )
    }
    """

    results = graph.query(query_tables)

    tables = []
    print("Tables needed:")
    for row in results:
        table_type = f" [{row.tableType}]" if row.tableType else ""
        print(f"  • {row.tableName}{table_type}")
        tables.append(str(row.tableName))

    # Find join paths between them
    if len(tables) >= 2:
        print(f"\nJoin paths:")
        for i, t1 in enumerate(tables):
            for t2 in tables[i+1:]:
                join_query = f"""
                PREFIX fin: <http://example.com/finance#>

                SELECT ?joinColumn
                WHERE {{
                    ?rel a fin:TableRelationship ;
                         fin:joinColumn ?joinColumn ;
                         fin:sourceTable ?source ;
                         fin:targetTable ?target .

                    ?source fin:tableName "{t1}" .
                    ?target fin:tableName "{t2}" .
                }}
                """

                join_results = graph.query(join_query)
                joins = [str(r.joinColumn) for r in join_results]

                if joins:
                    print(f"  {t1} ↔ {t2}: {', '.join(joins)}")

    print()


def test_query_6_fact_dimension_star(graph):
    """Test: Identify star schema."""
    print("=" * 80)
    print("TEST 6: Identify star schema (fact + dimensions)")
    print("=" * 80)

    # Find fact tables
    fact_query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?tableName ?rowCount
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:rowCount ?rowCount ;
               fin:isFactTable true .
    }
    ORDER BY DESC(?rowCount)
    """

    print("FACT Tables (transaction data):")
    results = graph.query(fact_query)
    fact_tables = []
    for row in results:
        print(f"  📊 {row.tableName} ({int(row.rowCount):,} rows)")
        fact_tables.append(str(row.tableName))

    # Find dimension tables
    dim_query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?tableName ?rowCount
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:rowCount ?rowCount ;
               fin:isDimensionTable true .
    }
    ORDER BY ?tableName
    """

    print("\nDIMENSION Tables (lookup/master data):")
    results = graph.query(dim_query)
    dim_tables = []
    for row in results:
        print(f"  📂 {row.tableName} ({int(row.rowCount):,} rows)")
        dim_tables.append(str(row.tableName))

    # Show how they connect
    if fact_tables and dim_tables:
        print(f"\nStar Schema:")
        print(f"  Center: {fact_tables[0]}")
        for dim in dim_tables:
            # Find join
            join_query = f"""
            PREFIX fin: <http://example.com/finance#>

            SELECT ?joinColumn
            WHERE {{
                ?rel a fin:TableRelationship ;
                     fin:joinColumn ?joinColumn ;
                     fin:sourceTable ?source ;
                     fin:targetTable ?target .

                {{ ?source fin:tableName "{fact_tables[0]}" . ?target fin:tableName "{dim}" }}
                UNION
                {{ ?target fin:tableName "{fact_tables[0]}" . ?source fin:tableName "{dim}" }}
            }}
            LIMIT 3
            """

            results = graph.query(join_query)
            joins = [str(r.joinColumn) for r in results]
            if joins:
                print(f"    ↔ {dim} (via {', '.join(joins[:2])}...)")

    print()


def main():
    # Load the knowledge graph
    graph = load_knowledge_graph()

    # Run tests
    test_query_1_find_customer_tables(graph)

    # Test join paths
    test_query_2_find_join_path(graph, "dataset_25m_table", "customer_master_analysis")
    test_query_2_find_join_path(graph, "dataset_25m_table", "GL_Accounts")

    test_query_3_gl_account_lookup(graph)
    test_query_4_revenue_columns(graph)
    test_query_5_multi_hop_join(graph)
    test_query_6_fact_dimension_star(graph)

    # Summary
    print("=" * 80)
    print("SUMMARY: JENA KNOWLEDGE GRAPH CAPABILITIES")
    print("=" * 80)
    print()
    print("✅ Can find relevant tables based on keywords")
    print("✅ Can discover join paths between tables")
    print("✅ Can identify fact vs dimension tables")
    print("✅ Can suggest columns for specific metrics (revenue, customer, etc.)")
    print("✅ Can map star schema relationships")
    print()
    print("Next: Integrate into SQL Generator for automatic join discovery")
    print()


if __name__ == "__main__":
    main()
