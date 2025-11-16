"""Quick test to verify vector search is working."""

from src.core.sql_generator import SQLGenerator
import structlog

logger = structlog.get_logger()

print("=" * 80)
print("QUICK VECTOR SEARCH TEST")
print("=" * 80)
print()

# Test 1: Simple query
print("Test 1: Testing vector search with 'Show me all GL accounts'...")
try:
    sql_gen = SQLGenerator()

    result = sql_gen.generate_sql(
        query="Show me all GL accounts",
        use_vector_search=True,
        max_tables=5
    )

    if result.get("sql"):
        print(f"✅ SQL Generated Successfully")
        print(f"   Tables selected: {result.get('tables_used', [])}")
        print(f"   Expected: ['GL_Accounts']")

        # Check if correct table was selected
        tables_used = result.get('tables_used', [])
        if 'GL_Accounts' in tables_used:
            print(f"   ✅ Correct table selected!")
        else:
            print(f"   ⚠️  Wrong tables: {tables_used}")
    else:
        print(f"❌ SQL Generation Failed: {result.get('error')}")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Transaction data query
print("Test 2: Testing vector search with 'What is in the transaction data?'...")
try:
    result = sql_gen.generate_sql(
        query="What is in the transaction data?",
        use_vector_search=True,
        max_tables=5
    )

    if result.get("sql"):
        print(f"✅ SQL Generated Successfully")
        print(f"   Tables selected: {result.get('tables_used', [])}")
        print(f"   Expected: ['transaction_data']")

        # Check if correct table was selected
        tables_used = result.get('tables_used', [])
        if 'transaction_data' in tables_used:
            print(f"   ✅ Correct table selected!")
        else:
            print(f"   ⚠️  Wrong tables: {tables_used}")
    else:
        print(f"❌ SQL Generation Failed: {result.get('error')}")

except Exception as e:
    print(f"❌ Test failed: {e}")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print("If both tests show ✅, vector search is working correctly!")
print()
