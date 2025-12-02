"""
AI Agent for intelligent SQL error correction.

Instead of regex-based pattern matching, this agent uses LLM to understand
the full context (question, SQL, error, schema, database type) and generate
appropriate corrections.
"""

from typing import Dict, Any, List, Optional
import structlog
import json
import re

logger = structlog.get_logger()


class ErrorCorrectionAgent:
    """
    AI Agent that analyzes SQL execution errors and suggests corrections
    using full context awareness of the question, SQL, error, schema, and database type.
    """

    def __init__(self, llm_client):
        """
        Initialize the agent with an LLM client.

        Args:
            llm_client: The LLMClient instance for making LLM calls
        """
        self.llm_client = llm_client

    def analyze_and_correct(
        self,
        original_question: str,
        failed_sql: str,
        error_message: str,
        table_schemas: List[Dict[str, Any]],
        database_type: str,
        connector_id: str = None
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze error and generate corrected SQL.

        Args:
            original_question: What the user originally asked
            failed_sql: The SQL that failed to execute
            error_message: The error from the database
            table_schemas: Actual schema from Weaviate (columns, types, descriptions)
            database_type: Target database for dialect-specific corrections (bigquery, snowflake, postgresql, redshift, databricks)
            connector_id: Optional connector ID for context

        Returns:
            {
                "error_category": str,  # schema|syntax|type|aggregation|function|permission|resource|unknown
                "corrected_sql": str,
                "analysis": str,  # Human-readable explanation of what went wrong
                "changes_made": List[str],  # e.g., ["Replaced 'launch_date' with 'created_at'"]
                "confidence": float,  # 0.0 to 1.0
                "should_retry": bool,
                "requires_user_action": bool,
                "user_message": str  # Optional message for user if action needed
            }
        """
        try:
            logger.info(
                "Error correction agent analyzing failure",
                database_type=database_type,
                error_preview=error_message[:100] if error_message else "No error"
            )

            # Build the comprehensive prompt
            prompt = self._build_correction_prompt(
                original_question=original_question,
                failed_sql=failed_sql,
                error_message=error_message,
                table_schemas=table_schemas,
                database_type=database_type
            )

            # Call the LLM
            response = self._call_llm(prompt)

            # Parse the response
            result = self._parse_response(response, failed_sql)

            logger.info(
                "Error correction agent result",
                error_category=result.get("error_category"),
                confidence=result.get("confidence"),
                should_retry=result.get("should_retry"),
                changes_count=len(result.get("changes_made", []))
            )

            return result

        except Exception as e:
            logger.error(f"Error correction agent failed: {e}", exc_info=True)
            return {
                "error_category": "unknown",
                "corrected_sql": None,
                "analysis": f"Failed to analyze error: {str(e)}",
                "changes_made": [],
                "confidence": 0.0,
                "should_retry": False,
                "requires_user_action": False,
                "user_message": None
            }

    def _build_correction_prompt(
        self,
        original_question: str,
        failed_sql: str,
        error_message: str,
        table_schemas: List[Dict[str, Any]],
        database_type: str
    ) -> str:
        """Build the comprehensive correction prompt for the LLM."""

        schema_details = self._format_schemas(table_schemas)
        db_type_upper = database_type.upper() if database_type else "SQL"

        prompt = f"""You are a SQL error correction specialist for {db_type_upper} databases. A query failed to execute.

## User's Original Question
{original_question}

## Generated SQL (Failed)
```sql
{failed_sql}
```

## Error Message
{error_message}

## Database Type
{database_type} (use correct SQL dialect for this database)

## Available Table Schema
{schema_details}

## Common Error Categories to Consider

1. **Schema Errors**: Column/table doesn't exist, wrong table name
2. **Syntax Errors**: Database-specific SQL dialect issues
   - BigQuery: Use backticks for identifiers, STRUCT syntax, UNNEST for arrays
   - Snowflake: Double quotes for case-sensitive identifiers, FLATTEN for arrays
   - PostgreSQL: Standard SQL, double quotes for identifiers
   - Redshift: PostgreSQL-based but different functions (GETDATE vs NOW)
   - Databricks: Spark SQL syntax, EXPLODE for arrays
3. **Type Errors**: Comparing incompatible types, wrong date formats
4. **Aggregation Errors**: Missing GROUP BY, invalid HAVING
5. **Function Errors**: Using function not available in this database
6. **Permission Errors**: Table/schema access denied
7. **Resource Errors**: Query too complex, timeout, data too large

## Your Task
1. Analyze the error message and identify the root cause
2. Check if it's a schema issue (column/table doesn't exist)
3. Check if it's a syntax issue (wrong SQL dialect)
4. Check if it's a type/format issue
5. Generate corrected SQL that:
   - Achieves the user's original intent
   - Uses correct syntax for {database_type}
   - Uses only columns that exist in the schema
6. Explain what went wrong and how you fixed it

## Output Format (JSON only, no markdown)
{{
    "error_category": "schema|syntax|type|aggregation|function|permission|resource|unknown",
    "analysis": "Detailed explanation of what went wrong",
    "corrected_sql": "SELECT ... (the fixed query, or null if unfixable)",
    "changes_made": [
        "Specific change 1",
        "Specific change 2"
    ],
    "confidence": 0.85,
    "should_retry": true,
    "requires_user_action": false,
    "user_message": "Optional message if user needs to take action"
}}

## Confidence Guidelines
- 0.9+: Direct fix (typo, simple column rename with clear match)
- 0.7-0.9: Confident correction (clear mapping to existing column)
- 0.5-0.7: Best guess (multiple possibilities, picked most likely)
- <0.5: Uncertain (may need user clarification)

## When NOT to retry (should_retry: false)
- Permission errors (user needs to fix access)
- Resource limits (query needs restructuring by user)
- Ambiguous user intent (multiple interpretations possible)
- No clear fix available

Respond with ONLY the JSON object, no markdown code blocks or other text."""

        return prompt

    def _format_schemas(self, schemas: List[Dict[str, Any]]) -> str:
        """Format schemas for the prompt with full detail."""
        if not schemas:
            return "No schema information available"

        formatted_parts = []
        for schema in schemas:
            table_name = schema.get("table_name", "Unknown")
            columns = schema.get("columns", [])

            # Format table header
            parts = [f"### Table: {table_name}"]

            # Format columns with types and descriptions
            if columns:
                parts.append("Columns:")
                for col in columns:
                    col_name = col.get("name", "unknown")
                    col_type = col.get("type", "unknown")
                    col_desc = col.get("description", "")

                    col_line = f"  - {col_name} ({col_type})"
                    if col_desc:
                        col_line += f": {col_desc}"
                    parts.append(col_line)

            formatted_parts.append("\n".join(parts))

        return "\n\n".join(formatted_parts)

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the correction prompt."""
        try:
            if self.llm_client.use_openai:
                response = self.llm_client.client.chat.completions.create(
                    model=self.llm_client.model,
                    messages=[
                        {"role": "system", "content": "You are a SQL error correction specialist. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            else:
                response = self.llm_client.client.messages.create(
                    model=self.llm_client.model,
                    max_tokens=2000,
                    temperature=0,
                    system="You are a SQL error correction specialist. Respond only with valid JSON.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
        except Exception as e:
            logger.error(f"LLM call failed in error correction agent: {e}")
            raise

    def _parse_response(self, response_text: str, original_sql: str) -> Dict[str, Any]:
        """Parse the LLM response into structured result."""
        try:
            # Clean the response - remove any markdown formatting
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Remove markdown code blocks
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)

            result = json.loads(cleaned)

            # Validate and normalize the result
            return {
                "error_category": result.get("error_category", "unknown"),
                "corrected_sql": result.get("corrected_sql"),
                "analysis": result.get("analysis", "No analysis provided"),
                "changes_made": result.get("changes_made", []),
                "confidence": float(result.get("confidence", 0.0)),
                "should_retry": bool(result.get("should_retry", False)),
                "requires_user_action": bool(result.get("requires_user_action", False)),
                "user_message": result.get("user_message")
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}", response_preview=response_text[:200])

            # Try to extract SQL from the response if it contains one
            sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
            extracted_sql = sql_match.group(1) if sql_match else None

            return {
                "error_category": "unknown",
                "corrected_sql": extracted_sql,
                "analysis": "Failed to parse structured response from LLM",
                "changes_made": [],
                "confidence": 0.3 if extracted_sql else 0.0,
                "should_retry": bool(extracted_sql),
                "requires_user_action": False,
                "user_message": None
            }
