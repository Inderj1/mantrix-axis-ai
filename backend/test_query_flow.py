#!/usr/bin/env python3
"""
Test the complete query flow with easy, medium, and complex queries.
"""
import sys
import json
from src.core.sql_generator import SQLGenerator
from src.db.bigquery import BigQueryClient


def test_query(generator, bq_client, query, difficulty):
    """Test a single query and display the flow."""
    print("\n" + "=" * 80)
    print(f"{difficulty.upper()} QUERY: {query}")
    print("=" * 80)

    try:
        # Generate SQL
        print("\n[1] SQL Generation...")
        result = generator.generate_sql(query)

        print(f"\n[2] Generated SQL:")
        print("-" * 60)
        print(result.get('sql', 'No SQL generated'))
        print("-" * 60)

        print(f"\n[3] Explanation:")
        print(result.get('explanation', 'No explanation'))

        # Show knowledge graph usage
        if 'kg_enhanced' in result or 'knowledge_graph' in str(result):
            print(f"\n[4] Knowledge Graph Used: ✓")
        else:
            print(f"\n[4] Knowledge Graph Used: ✗")

        # Show financial hierarchy context
        if 'hierarchy_level' in str(result) or 'financial_context' in str(result):
            print(f"[5] Financial Hierarchy Used: ✓")
        else:
            print(f"[5] Financial Hierarchy Used: ✗")

        # Show table selection
        if 'tables' in result:
            print(f"\n[6] Tables Selected:")
            for table in result.get('tables', []):
                print(f"    - {table}")

        # Execute if SQL was generated
        if result.get('sql'):
            print(f"\n[7] Executing query...")
            try:
                execution_result = bq_client.execute_query(result['sql'])
                print(f"    ✓ Query executed successfully")
                print(f"    Rows returned: {len(execution_result)}")

                if execution_result and len(execution_result) > 0:
                    print(f"\n[8] Sample Results (first 3 rows):")
                    for i, row in enumerate(execution_result[:3], 1):
                        print(f"    Row {i}: {json.dumps(row, default=str)[:200]}...")
            except Exception as e:
                print(f"    ✗ Execution failed: {e}")

        print(f"\n{'✓' * 40} SUCCESS")
        return True

    except Exception as e:
        print(f"\n{'✗' * 40} FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("TESTING COMPLETE QUERY FLOW")
    print("=" * 80)

    # Initialize components
    print("\nInitializing SQL Generator...")
    generator = SQLGenerator()
    bq_client = BigQueryClient()

    # Check which knowledge graph is active
    print("\n[SYSTEM CHECK]")
    print("-" * 60)
    print(f"Knowledge Graph Available: {generator.knowledge_graph is not None}")
    print(f"Jena KG Resolver: {generator.kg_query_resolver is not None}")
    print(f"Financial Features Enabled: {generator.enable_financial_features}")
    print(f"Cache Enabled: {generator.cache_manager is not None}")
    print(f"Vector Search Enabled: {generator.vector_client is not None}")

    # Define test queries
    test_cases = [
        # EASY - Simple aggregation
        {
            "query": "What is the total revenue?",
            "difficulty": "easy",
            "expected": "Should use dataset_25m_table, sum Net_Sales or similar"
        },

        # EASY - Simple filter
        {
            "query": "Show me sales for customer 1000123",
            "difficulty": "easy",
            "expected": "Should filter by Customer column"
        },

        # MEDIUM - Multiple aggregations
        {
            "query": "Show revenue and COGS by customer segment",
            "difficulty": "medium",
            "expected": "Should join customer_master_analysis for RFM_Segment"
        },

        # MEDIUM - Time series
        {
            "query": "What are monthly revenue trends?",
            "difficulty": "medium",
            "expected": "Should group by month from Posting_Date"
        },

        # COMPLEX - Multiple joins
        {
            "query": "Show top 10 customers by revenue with their RFM segments and product preferences",
            "difficulty": "complex",
            "expected": "Should join customer_master_analysis and product_customer_matrix"
        },

        # COMPLEX - Financial hierarchy (if KG is working)
        {
            "query": "What is the gross profit margin breakdown by GL account categories?",
            "difficulty": "complex",
            "expected": "Should use GL_Accounts mapping and calculate (Revenue - COGS) / Revenue"
        }
    ]

    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'#' * 80}")
        print(f"TEST {i}/{len(test_cases)}")
        print(f"{'#' * 80}")
        print(f"Expected: {test_case['expected']}")

        success = test_query(
            generator,
            bq_client,
            test_case['query'],
            test_case['difficulty']
        )

        results.append({
            'query': test_case['query'],
            'difficulty': test_case['difficulty'],
            'success': success
        })

        print(f"\n{'_' * 80}")

    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    easy_success = sum(1 for r in results if r['difficulty'] == 'easy' and r['success'])
    easy_total = sum(1 for r in results if r['difficulty'] == 'easy')

    medium_success = sum(1 for r in results if r['difficulty'] == 'medium' and r['success'])
    medium_total = sum(1 for r in results if r['difficulty'] == 'medium')

    complex_success = sum(1 for r in results if r['difficulty'] == 'complex' and r['success'])
    complex_total = sum(1 for r in results if r['difficulty'] == 'complex')

    print(f"\nEasy Queries:    {easy_success}/{easy_total} passed")
    print(f"Medium Queries:  {medium_success}/{medium_total} passed")
    print(f"Complex Queries: {complex_success}/{complex_total} passed")
    print(f"\nOverall:         {sum(r['success'] for r in results)}/{len(results)} passed")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
