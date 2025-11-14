#!/usr/bin/env python3
"""
API Testing Script for Query Responses
"""
import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/query"
USER_ID = f"test_user_{int(time.time())}"

# Test queries
QUERIES = [
    {
        "name": "Beer Portfolio Performance",
        "query": "how's my beer product portfolio been doing over the year (show details)",
        "category": "Context Maintenance"
    },
    {
        "name": "Customer Segment Targeting",
        "query": "based on the above which customer segment should be targeted for product promotion (show details)",
        "category": "Context Maintenance"
    },
    {
        "name": "Delivered Quantity by Material/Plant",
        "query": "Show me the total Delivered Quantity by Material and Plant for each month over the last 6 months",
        "category": "Sales Inventory"
    },
    {
        "name": "Aging Inventory - Open Orders",
        "query": "List open sales orders older than 60 days where Delivered Quantity is 0 and Net Value is greater than 1000",
        "category": "Sales Inventory"
    },
    {
        "name": "Inventory Movement by Plant",
        "query": "Give me Delivered Quantity by Plant and month for the last 6 months",
        "category": "Sales Inventory"
    },
    {
        "name": "Declining Delivery Trend",
        "query": "Show me Materials where Delivered Quantity in the last month is at least 20% lower than the average of the previous 3 months",
        "category": "Sales Inventory"
    },
    {
        "name": "Sales by Product/Region",
        "query": "What is the total sales amount by product and region for the last 12 months?",
        "category": "Sales Performance"
    },
    {
        "name": "Top Customers by Value/Volume",
        "query": "Which customers have ordered the most (by value and volume) in the last quarter?",
        "category": "Sales Performance"
    }
]

def test_query(query_info, query_num):
    """Test a single query and return results"""
    print(f"\n{'='*80}")
    print(f"Query {query_num}: {query_info['name']}")
    print(f"Category: {query_info['category']}")
    print(f"{'='*80}")
    print(f"Query Text: {query_info['query']}")
    print()

    payload = {
        "question": query_info['query'],
        "user_id": USER_ID,
        "execute": True
    }

    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=60)
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {
                "status": "FAILED",
                "error": f"HTTP {response.status_code}",
                "elapsed": elapsed
            }

        data = response.json()

        # Extract information
        has_sql = bool(data.get('sql'))
        has_execution = 'execution' in data

        # Handle execution results safely
        execution_data = data.get('execution', {})
        results = execution_data.get('results')
        row_count = len(results) if results is not None else 0
        execution_error = execution_data.get('error')

        error = data.get('error') or execution_error
        explanation = data.get('explanation', 'N/A')
        sql = data.get('sql', 'N/A')

        # Print results
        if error:
            print(f"❌ FAILED with error:")
            print(f"   {error}")
        else:
            print(f"✅ SUCCESS")

        print(f"⏱️  Execution time: {elapsed:.2f}s")
        print(f"📊 Rows returned: {row_count}")
        print(f"📝 SQL generated: {'YES' if has_sql else 'NO'}")

        if has_sql and sql != 'N/A':
            print(f"\n📄 Generated SQL (first 300 chars):")
            print(f"   {sql[:300]}...")

        if explanation and explanation != 'N/A':
            print(f"\n💡 Explanation:")
            print(f"   {explanation[:200]}...")

        if row_count > 0 and results:
            print(f"\n🔍 Sample Results (first row):")
            first_row = results[0]
            for key, value in list(first_row.items())[:5]:  # First 5 columns
                print(f"   {key}: {value}")

        return {
            "status": "SUCCESS" if not error else "FAILED",
            "error": error,
            "has_sql": has_sql,
            "row_count": row_count,
            "elapsed": elapsed,
            "sql": sql,
            "explanation": explanation
        }

    except requests.exceptions.Timeout:
        print(f"❌ FAILED: Request timeout (>60s)")
        return {"status": "TIMEOUT", "error": "Timeout", "elapsed": 60}

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return {"status": "ERROR", "error": str(e), "elapsed": 0}

def main():
    print(f"""
{'='*80}
QUERY API TESTING
{'='*80}
Test Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
API URL: {API_URL}
User ID: {USER_ID}
Total Queries: {len(QUERIES)}
{'='*80}
    """)

    results = []

    for i, query_info in enumerate(QUERIES, 1):
        result = test_query(query_info, i)
        results.append({
            **query_info,
            **result
        })
        time.sleep(1)  # Brief pause between queries

    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}\n")

    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed_count = sum(1 for r in results if r['status'] in ['FAILED', 'ERROR', 'TIMEOUT'])

    print(f"✅ Successful: {success_count}/{len(results)}")
    print(f"❌ Failed: {failed_count}/{len(results)}")
    print(f"⏱️  Average execution time: {sum(r['elapsed'] for r in results)/len(results):.2f}s")

    print(f"\n📋 Results by Category:")
    for category in set(q['category'] for q in QUERIES):
        cat_results = [r for r in results if r['category'] == category]
        cat_success = sum(1 for r in cat_results if r['status'] == 'SUCCESS')
        print(f"   {category}: {cat_success}/{len(cat_results)} successful")

    # Failed queries detail
    failed = [r for r in results if r['status'] != 'SUCCESS']
    if failed:
        print(f"\n❌ Failed Queries Detail:")
        for r in failed:
            print(f"   - {r['name']}: {r.get('error', 'Unknown error')}")

    # Save to JSON
    output_file = "test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "session": {
                "timestamp": datetime.now().isoformat(),
                "user_id": USER_ID,
                "total_queries": len(results)
            },
            "results": results
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
