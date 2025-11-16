"""
Debug the structure of schemas being passed to LLM.
"""
import json
from src.core.sql_generator import SQLGenerator

print("=" * 80)
print("DEBUGGING SCHEMA STRUCTURE PASSED TO LLM")
print("=" * 80)

sql_gen = SQLGenerator()

# Get schemas using same method as SQL generator
query = "Show me all GL accounts"
print(f"\nQuery: {query}")

# Step 1: Get relevant schemas
print("\n1. Getting relevant schemas...")
relevant_schemas = sql_gen._get_relevant_schemas(query, limit=3)

print(f"\nGot {len(relevant_schemas)} schemas")

# Check GL_Accounts schema structure
for schema in relevant_schemas:
    if schema.get('table_name') == 'GL_Accounts':
        print(f"\n✓ Found GL_Accounts schema")
        print(f"  Type of schema: {type(schema)}")
        print(f"  Keys in schema: {list(schema.keys())}")

        columns = schema.get('columns', [])
        print(f"\n  Columns field:")
        print(f"    Type: {type(columns)}")
        print(f"    Count: {len(columns)}")

        if columns:
            print(f"\n  First column structure:")
            first_col = columns[0]
            print(f"    Type: {type(first_col)}")

            if isinstance(first_col, dict):
                print(f"    Keys: {list(first_col.keys())}")
                print(f"    Values:")
                for key, value in first_col.items():
                    print(f"      {key}: {value}")
            else:
                print(f"    Value: {first_col}")

        print(f"\n  All columns:")
        for i, col in enumerate(columns):
            if isinstance(col, dict):
                name = col.get('name', 'NO_NAME')
                col_type = col.get('type', 'NO_TYPE')
                nullable = col.get('is_nullable', 'NO_NULLABLE')
                print(f"    {i+1}. {name} ({col_type}) - nullable: {nullable}")
            else:
                print(f"    {i+1}. {col}")

        # Check if there are other GL-related keys
        print(f"\n  Other schema fields:")
        for key in schema:
            if key != 'columns':
                value = schema[key]
                if isinstance(value, (str, int, float, bool)):
                    print(f"    {key}: {value}")
                else:
                    print(f"    {key}: {type(value)}")