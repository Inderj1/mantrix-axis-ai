#!/usr/bin/env python3
"""Test column synonym resolution with original failing queries."""

import requests
import json
from datetime import datetime

# Test queries (modified to use correct date context)
QUERIES = [
    {
        "id": 1,
        "question": "Show me delivered quantity by material for last 6 months through June 2025",
        "expected_column": "ZCS_Shipped_Quantity"
    },
    {
        "id": 2,
        "question": "What's the aging inventory report for products through June 2025",
        "expected_column": "Inv_Quantity"
    },
    {
        "id": 3,
        "question": "Show inventory movement by product for first half of 2025",
        "expected_column": "Material_Description"
    },
    {
        "id": 4,
        "question": "Which products are showing declining sales trends in first 6 months of 2025",
        "expected_column": "Material_Description"
    },
    {
        "id": 5,
        "question": "Show me sales by product and region for Q1 2025",
        "expected_column": "Material_Description"
    },
    {
        "id": 6,
        "question": "Who are the top 10 customers by revenue through June 2025",
        "expected_column": "Customer_Name"
    },
    {
        "id": 7,
        "question": "What's the total quantity delivered by region in 2025 so far through June",
        "expected_column": "ZCS_Shipped_Quantity"
    },
    {
        "id": 8,
        "question": "Show me inventory levels by material category as of June 2025",
        "expected_column": "Material_Number"
    }
]

def test_query(query_info):
    """Test a single query and return results."""
    url = "http://localhost:8000/api/v1/query"
    payload = {"question": query_info["question"]}

    try:
        response = requests.post(url, json=payload, timeout=60)
        result = response.json()

        # Extract key info
        sql = result.get("sql", "")
        has_execution = "execution" in result
        row_count = 0
        if has_execution and result["execution"].get("results"):
            row_count = len(result["execution"]["results"])

        # Check if expected column is used
        column_used = query_info["expected_column"] in sql

        return {
            "id": query_info["id"],
            "question": query_info["question"],
            "success": row_count > 0,
            "row_count": row_count,
            "column_used_correctly": column_used,
            "expected_column": query_info["expected_column"],
            "sql_preview": sql[:200] + "..." if len(sql) > 200 else sql
        }
    except Exception as e:
        return {
            "id": query_info["id"],
            "question": query_info["question"],
            "success": False,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("COLUMN SYNONYM RESOLUTION TEST")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing {len(QUERIES)} queries\n")

    results = []
    for query in QUERIES:
        print(f"\n[Query {query['id']}/{len(QUERIES)}] {query['question'][:60]}...")
        result = test_query(query)
        results.append(result)

        if result.get("success"):
            print(f"  ✅ SUCCESS - {result['row_count']} rows")
            if result.get("column_used_correctly"):
                print(f"  ✅ Correct column: {query['expected_column']}")
            else:
                print(f"  ⚠️  Expected column not found: {query['expected_column']}")
        else:
            print(f"  ❌ FAILED - {result.get('error', 'No results')}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = sum(1 for r in results if r.get("success"))
    correct_columns = sum(1 for r in results if r.get("column_used_correctly"))

    print(f"Queries with results: {successful}/{len(QUERIES)} ({successful/len(QUERIES)*100:.0f}%)")
    print(f"Correct column usage: {correct_columns}/{len(QUERIES)} ({correct_columns/len(QUERIES)*100:.0f}%)")

    print("\nDetailed Results:")
    for r in results:
        status = "✅" if r.get("success") else "❌"
        column_status = "✅" if r.get("column_used_correctly") else "⚠️"
        rows = r.get("row_count", 0)
        print(f"{status} Query {r['id']}: {rows} rows | Column: {column_status}")

    # Save detailed results
    with open("/Users/inder/projects/mantrix-axis-ai/backend/column_synonym_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_queries": len(QUERIES),
                "successful": successful,
                "correct_columns": correct_columns,
                "success_rate": successful / len(QUERIES) * 100
            },
            "results": results
        }, f, indent=2)

    print("\nDetailed results saved to: column_synonym_test_results.json")

if __name__ == "__main__":
    main()
