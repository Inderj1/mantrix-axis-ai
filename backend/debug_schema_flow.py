"""
Debug the schema flow from Weaviate to LLM.
"""
import json
from src.core.sql_generator import SQLGenerator
from src.core.embeddings import EmbeddingService

print("=" * 80)
print("DEBUGGING SCHEMA FLOW FOR GL_ACCOUNTS")
print("=" * 80)

# Initialize
sql_gen = SQLGenerator()
embedding_service = EmbeddingService()

# Step 1: Check what Weaviate returns for GL query
print("\n1. Testing Weaviate vector search for 'GL accounts'...")
query_embedding = embedding_service.generate_embedding("Show me all GL accounts")
similar_tables = sql_gen.vector_client.search_similar_tables(query_embedding, limit=3)

for i, table in enumerate(similar_tables, 1):
    print(f"\nResult {i}: {table['table_name']}")
    print(f"  Distance: {table['distance']}")
    print(f"  Columns in result: {len(table.get('columns', []))}")
    if table['table_name'] == 'GL_Accounts':
        print(f"\n  GL_Accounts columns:")
        for col in table.get('columns', []):
            if isinstance(col, dict):
                print(f"    - {col.get('name', 'N/A')}: {col.get('type', 'N/A')}")
            else:
                print(f"    - {col}")

# Step 2: Check what _get_relevant_schemas returns
print("\n" + "=" * 80)
print("2. Testing _get_relevant_schemas method...")
relevant_schemas = sql_gen._get_relevant_schemas("Show me all GL accounts", limit=3)

print(f"\nGot {len(relevant_schemas)} schemas")
for schema in relevant_schemas:
    if schema.get('table_name') == 'GL_Accounts':
        print(f"\nGL_Accounts schema from _get_relevant_schemas:")
        print(f"  Table: {schema.get('table_name')}")
        print(f"  Columns: {len(schema.get('columns', []))}")
        if schema.get('columns'):
            print("\n  Column details:")
            for col in schema['columns'][:5]:  # Show first 5
                if isinstance(col, dict):
                    print(f"    - {col.get('name', 'N/A')}: {col.get('type', 'N/A')}")
                else:
                    print(f"    - {col}")

# Step 3: Check what prompt is being built
print("\n" + "=" * 80)
print("3. Checking prompt construction...")

# Get the prompt that would be sent to LLM
query = "Show me all GL accounts"
print(f"\nQuery: {query}")

# We need to see what _build_prompt creates
# This is a private method, so let's trace through generate_sql

print("\nGenerating SQL to see what happens...")
result = sql_gen.generate_sql(query=query, use_vector_search=True)

print(f"\n✓ SQL generated")
print(f"Tables used: {result.get('tables_used', [])}")
print(f"\nGenerated SQL (first 200 chars):")
print(result['sql'][:200])