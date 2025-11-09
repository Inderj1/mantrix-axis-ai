#!/usr/bin/env python3
"""
Test how well Jena identifies duplicate columns and their intelligence.
"""
import os
os.environ['SKIP_REDIS'] = 'true'

from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph


def test_duplicate_column_detection():
    """Test how Jena detects duplicate columns."""
    print("=" * 80)
    print("TESTING DUPLICATE COLUMN INTELLIGENCE")
    print("=" * 80)

    kg = get_jena_knowledge_graph()

    # Test 1: Find all tables with "Customer" column
    print("\n📊 TEST 1: Find all tables with 'Customer' column")
    print("-" * 60)

    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?tableName ?columnType ?rowCount
    WHERE {
        ?table a fin:Table ;
               fin:tableName ?tableName ;
               fin:rowCount ?rowCount ;
               fin:hasColumn ?column .

        ?column fin:columnName "Customer" ;
                fin:dataType ?columnType .
    }
    ORDER BY DESC(?rowCount)
    """

    results = kg.query(query)

    customer_tables = {}
    for row in results:
        table = str(row['tableName'])
        col_type = str(row['columnType'])
        row_count = int(row['rowCount'])

        customer_tables[table] = {
            'type': col_type,
            'rows': row_count
        }

        print(f"  • {table}")
        print(f"    Type: {col_type}")
        print(f"    Rows: {row_count:,}")

    # Test 2: Check what relationships Jena created
    print("\n📊 TEST 2: What relationships did Jena create for 'Customer'?")
    print("-" * 60)

    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?sourceTable ?targetTable ?joinColumn ?columnType
    WHERE {
        ?rel a fin:TableRelationship ;
             fin:joinColumn ?joinColumn ;
             fin:columnType ?columnType ;
             fin:sourceTable ?source ;
             fin:targetTable ?target .

        ?source fin:tableName ?sourceTable .
        ?target fin:tableName ?targetTable .

        FILTER(?joinColumn = "Customer")
    }
    ORDER BY ?sourceTable ?targetTable
    """

    results = kg.query(query)

    relationships = []
    for row in results:
        source = str(row['sourceTable'])
        target = str(row['targetTable'])
        col_type = str(row['columnType'])

        relationships.append({
            'source': source,
            'target': target,
            'type': col_type
        })

        print(f"  ✓ {source} ⟷ {target} (type: {col_type})")

    # Test 3: Intelligence Analysis
    print("\n📊 TEST 3: Intelligence Analysis")
    print("-" * 60)

    # Check if Jena caught the type mismatch
    customer_types = set(info['type'] for info in customer_tables.values())

    print(f"\nColumn Types Found: {customer_types}")

    if len(customer_types) > 1:
        print(f"⚠️  TYPE MISMATCH DETECTED!")
        print(f"   'Customer' column has {len(customer_types)} different types:")
        for ctype in customer_types:
            tables_with_type = [t for t, info in customer_tables.items() if info['type'] == ctype]
            print(f"   • {ctype}: {', '.join(tables_with_type)}")

        # Check if Jena created relationships across type boundaries
        cross_type_rels = []
        for rel in relationships:
            # Get types for source and target
            source_type = customer_tables.get(rel['source'], {}).get('type')
            target_type = customer_tables.get(rel['target'], {}).get('type')

            if source_type and target_type and source_type != target_type:
                cross_type_rels.append(rel)

        if cross_type_rels:
            print(f"\n❌ PROBLEM: Jena created {len(cross_type_rels)} relationships across type boundaries!")
            for rel in cross_type_rels[:3]:
                print(f"   {rel['source']} ({customer_tables[rel['source']]['type']}) "
                      f"⟷ {rel['target']} ({customer_tables[rel['target']]['type']})")
        else:
            print(f"\n✓ GOOD: Jena correctly avoided creating relationships across type boundaries")
            print(f"   Created {len(relationships)} relationships only within same type")
    else:
        print(f"✓ All 'Customer' columns have the same type: {list(customer_types)[0]}")

    # Test 4: Semantic duplicate detection
    print("\n📊 TEST 4: Can Jena detect semantic duplicates?")
    print("-" * 60)

    # Check if we have synonyms or semantic mappings
    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?term ?synonym
    WHERE {
        ?s a fin:Synonym ;
           fin:term ?term ;
           fin:synonym ?synonym .
    }
    LIMIT 10
    """

    results = kg.query(query)

    if results:
        print("✓ Jena has synonym mappings:")
        for row in results[:5]:
            print(f"   {row['term']} → {row['synonym']}")
    else:
        print("❌ Jena does NOT have semantic duplicate detection")
        print("   It only matches on exact column name + type")

    # Test 5: Proposed enhancement
    print("\n📊 TEST 5: What would intelligent duplicate detection look like?")
    print("-" * 60)

    print("\nCurrent approach (simple):")
    print("  ✓ Match: Column name EXACT + Type EXACT")
    print("  ✗ Miss: 'Customer' (STRING) vs 'Customer' (INTEGER)")
    print("  ✗ Miss: 'Customer' vs 'CustomerID'")
    print("  ✗ Miss: 'Customer' vs 'Cust_Number'")

    print("\nProposed intelligent approach:")
    print("  1. Name similarity (fuzzy matching)")
    print("     • 'Customer' ≈ 'CustomerID' (edit distance)")
    print("     • 'Material_Number' ≈ 'MaterialNo'")
    print("  2. Type compatibility (not exact match)")
    print("     • STRING ⟷ INTEGER (if values are numeric strings)")
    print("     • DATE ⟷ TIMESTAMP")
    print("  3. Value distribution analysis")
    print("     • Check cardinality (unique values)")
    print("     • Sample value overlap")
    print("  4. Semantic embedding similarity")
    print("     • Embed column name + description")
    print("     • Find semantically similar columns")

    print("\n" + "=" * 80)


def test_problem_case():
    """Test a specific problematic case."""
    print("\n" + "=" * 80)
    print("PROBLEM CASE: Customer column type mismatch")
    print("=" * 80)

    kg = get_jena_knowledge_graph()

    print("\nScenario: User asks 'Show revenue by customer for product preferences'")
    print("Tables needed: dataset_25m_table, customer_master_analysis, product_customer_matrix")
    print()

    # Check if we can join all three
    query = """
    PREFIX fin: <http://example.com/finance#>

    SELECT ?source ?target ?joinCol ?colType
    WHERE {
        ?rel a fin:TableRelationship ;
             fin:joinColumn ?joinCol ;
             fin:columnType ?colType ;
             fin:sourceTable ?s ;
             fin:targetTable ?t .

        ?s fin:tableName ?source .
        ?t fin:tableName ?target .

        VALUES ?source { "dataset_25m_table" "customer_master_analysis" "product_customer_matrix" }
        VALUES ?target { "dataset_25m_table" "customer_master_analysis" "product_customer_matrix" }

        FILTER(?source != ?target)
    }
    """

    results = kg.query(query)

    join_map = {}
    for row in results:
        source = str(row['source'])
        target = str(row['target'])
        join_col = str(row['joinCol'])

        key = f"{source}→{target}"
        if key not in join_map:
            join_map[key] = []
        join_map[key].append(join_col)

    print("Possible JOINs found:")
    for key, cols in sorted(join_map.items()):
        print(f"  {key}: {', '.join(cols)}")

    # Check if we can connect all three tables
    needed_joins = [
        "dataset_25m_table→customer_master_analysis",
        "dataset_25m_table→product_customer_matrix",
        "customer_master_analysis→product_customer_matrix"
    ]

    missing = []
    for needed in needed_joins:
        if needed not in join_map:
            # Try reverse
            parts = needed.split("→")
            reverse = f"{parts[1]}→{parts[0]}"
            if reverse not in join_map:
                missing.append(needed)

    if missing:
        print(f"\n⚠️  PROBLEM: Cannot create full join path!")
        print(f"   Missing: {', '.join(missing)}")
        print(f"\n   This happens because 'Customer' column has different types:")
        print(f"   • dataset_25m_table.Customer: STRING")
        print(f"   • customer_master_analysis.Customer: STRING")
        print(f"   • product_customer_matrix.Customer: INTEGER")
        print(f"\n   Solution: Need type-aware join path finding with CAST operations")
    else:
        print("\n✓ All tables can be joined!")


if __name__ == "__main__":
    test_duplicate_column_detection()
    test_problem_case()
