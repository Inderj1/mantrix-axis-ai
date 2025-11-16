"""
Debug what's actually in the prompt sent to the LLM.
"""
import json
from src.core.sql_generator import SQLGenerator

# Monkey patch to capture prompt
original_generate_sql = None
captured_prompt = None

def capture_prompt(self, user_query, table_schemas, **kwargs):
    """Capture the prompt before sending to API."""
    global captured_prompt

    # Build the user prompt
    user_prompt = self._build_user_prompt(
        user_query,
        table_schemas,
        kwargs.get('examples'),
        kwargs.get('financial_context'),
        kwargs.get('business_context'),
        kwargs.get('join_hints'),
        kwargs.get('conversation_context')
    )

    captured_prompt = user_prompt

    # Call original method
    return original_generate_sql(self, user_query, table_schemas, **kwargs)

# Initialize
print("=" * 80)
print("DEBUGGING PROMPT CONTENT")
print("=" * 80)

sql_gen = SQLGenerator()

# Monkey patch the LLM client
from src.core.llm_client import LLMClient
original_generate_sql = LLMClient.generate_sql
LLMClient.generate_sql = capture_prompt

# Generate SQL to capture prompt
query = "Show me all GL accounts"
print(f"\nGenerating SQL for: {query}")

result = sql_gen.generate_sql(query=query, use_vector_search=True)

# Show captured prompt
if captured_prompt:
    print("\n" + "=" * 80)
    print("CAPTURED PROMPT SENT TO LLM:")
    print("=" * 80)

    # Show first 2000 chars to see the schema section
    print(captured_prompt[:2000])

    # Find and show GL_Accounts schema section
    if "GL_Accounts" in captured_prompt:
        gl_start = captured_prompt.find("Table: GL_Accounts")
        if gl_start >= 0:
            gl_end = captured_prompt.find("\nTable:", gl_start + 1)
            if gl_end < 0:
                gl_end = gl_start + 1000
            print("\n" + "=" * 80)
            print("GL_ACCOUNTS SCHEMA IN PROMPT:")
            print("=" * 80)
            print(captured_prompt[gl_start:gl_end])

print("\n" + "=" * 80)
print("GENERATED SQL:")
print("=" * 80)
print(result['sql'])