"""
Minimal test to debug a single query execution failure.
"""
import asyncio
import structlog
from src.db.bigquery import BigQueryClient
from src.config import settings

logger = structlog.get_logger()

async def test_query():
    """Test Q1 - Show me all GL accounts"""

    # Initialize BigQuery client (no parameters needed, reads from settings)
    bq_client = BigQueryClient()

    # Q1 SQL from the test results
    sql = """SELECT
  GL_Account,
  GL_Account_Name,
  GL_Account_Type,
  Financial_Statement_Category,
  Account_Group,
  Account_Class
FROM `arizona-poc.copa_export_copa_data_000000000000.GL_Accounts`
ORDER BY GL_Account"""

    print("Testing Q1: Show me all GL accounts")
    print("=" * 80)
    print(f"\nSQL:\n{sql}\n")
    print("=" * 80)

    try:
        print("\nExecuting query...")
        results = bq_client.execute_query(sql)

        print(f"✅ SUCCESS! Got {len(results)} rows")
        if results:
            print(f"\nFirst row: {results[0]}")

    except Exception as e:
        print(f"❌ FAILED with error:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

        # Print full traceback
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query())
