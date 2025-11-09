"""
Conversation Context Manager for handling follow-up questions.

This module enables the system to understand and respond to follow-up questions
by maintaining conversation context across queries.
"""

from typing import Dict, List, Optional, Any, Tuple
import re
from src.models.conversation import Conversation, Message
import structlog

logger = structlog.get_logger()


class ConversationContextManager:
    """Manages conversation context for follow-up question handling."""

    # Patterns that indicate a follow-up question
    FOLLOW_UP_PATTERNS = [
        # Add/Include column patterns
        r'^\s*(add|include|also\s+show|show\s+also)\s+',
        # Modification patterns
        r'^\s*(only|just|filter|where|with)\s+',
        # Sorting patterns
        r'^\s*(sort|order|rank)\s+by\s+',
        # Limit patterns
        r'^\s*(show|expand\s+to|top)\s+\d+',
        # Grouping patterns
        r'^\s*group\s+by\s+',
        # Short contextual requests
        r'^\s*(more|less|details|breakdown|with|and)\s+',
    ]

    def __init__(self):
        """Initialize the context manager."""
        pass

    def is_follow_up(self, question: str) -> bool:
        """
        Detect if a question is a follow-up to a previous query.

        Args:
            question: The user's question

        Returns:
            True if the question appears to be a follow-up
        """
        question_lower = question.lower().strip()

        # Check against follow-up patterns
        for pattern in self.FOLLOW_UP_PATTERNS:
            if re.match(pattern, question_lower):
                logger.info(f"Follow-up detected", pattern=pattern, question=question[:50])
                return True

        # Short questions (< 5 words) are likely follow-ups
        word_count = len(question_lower.split())
        if word_count <= 5:
            logger.info(f"Short question detected as follow-up", word_count=word_count)
            return True

        return False

    def get_context_from_conversation(
        self,
        conversation: Conversation,
        limit: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Extract context from the most recent messages in a conversation.

        Args:
            conversation: The conversation object
            limit: Number of recent messages to consider

        Returns:
            Context dictionary or None if no relevant context found
        """
        if not conversation or not conversation.messages:
            return None

        # Get recent assistant messages (these contain SQL and results)
        assistant_messages = [
            msg for msg in conversation.messages
            if msg.type == "assistant" and msg.sql
        ]

        if not assistant_messages:
            return None

        # Get the most recent message with SQL
        last_message = assistant_messages[-1]

        context = self._extract_context_from_message(last_message)

        # Also get the corresponding user question
        user_messages = [
            msg for msg in conversation.messages
            if msg.type == "user"
        ]

        if user_messages:
            # Find the user message that corresponds to this assistant message
            # It should be right before the assistant message
            for i, msg in enumerate(conversation.messages):
                if msg.id == last_message.id and i > 0:
                    prev_msg = conversation.messages[i-1]
                    if prev_msg.type == "user":
                        context["previous_query"] = prev_msg.content
                        break

        logger.info(
            "Extracted conversation context",
            tables=context.get("tables_used"),
            columns=context.get("columns_selected")
        )

        return context

    def _extract_context_from_message(self, message: Message) -> Dict[str, Any]:
        """
        Extract SQL context from a message.

        Args:
            message: The message to extract context from

        Returns:
            Context dictionary with SQL metadata
        """
        context = {
            "previous_query": None,
            "previous_sql": message.sql,
            "tables_used": [],
            "columns_selected": [],
            "filters_applied": [],
            "limit": None,
            "order_by": []
        }

        # Extract from metadata if available
        if message.metadata:
            context["tables_used"] = message.metadata.get("tables_used", [])
            context["columns_selected"] = message.metadata.get("columns_selected", [])
            context["filters_applied"] = message.metadata.get("filters_applied", [])
            context["limit"] = message.metadata.get("limit")
            context["order_by"] = message.metadata.get("order_by", [])

        # If metadata not available, parse SQL to extract context
        if not context["tables_used"] and message.sql:
            context.update(self._parse_sql_for_context(message.sql))

        return context

    def _parse_sql_for_context(self, sql: str) -> Dict[str, Any]:
        """
        Parse SQL to extract context information.

        Args:
            sql: The SQL query string

        Returns:
            Dictionary with parsed context
        """
        context = {
            "tables_used": [],
            "columns_selected": [],
            "limit": None
        }

        if not sql:
            return context

        # Extract tables from FROM and JOIN clauses
        from_pattern = r'FROM\s+[`"]?[\w.-]+\.[\w.-]+\.(\w+)[`"]?'
        join_pattern = r'JOIN\s+[`"]?[\w.-]+\.[\w.-]+\.(\w+)[`"]?'

        tables = set()
        tables.update(re.findall(from_pattern, sql, re.IGNORECASE))
        tables.update(re.findall(join_pattern, sql, re.IGNORECASE))
        context["tables_used"] = list(tables)

        # Extract columns from SELECT clause
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Simple column extraction (handles basic cases)
            columns = []
            for col in select_clause.split(','):
                col = col.strip()
                # Extract alias if present (... AS column_name)
                alias_match = re.search(r'\s+as\s+(\w+)', col, re.IGNORECASE)
                if alias_match:
                    columns.append(alias_match.group(1))
                else:
                    # Extract column name (last word if qualified)
                    col_name = col.split('.')[-1].strip('`"\'')
                    # Remove function calls
                    col_name = re.sub(r'\(.*?\)', '', col_name).strip()
                    if col_name and col_name.upper() not in ['DISTINCT', 'ALL']:
                        columns.append(col_name)

            context["columns_selected"] = [c for c in columns if c]

        # Extract LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            context["limit"] = int(limit_match.group(1))

        return context

    def classify_follow_up_type(self, question: str) -> str:
        """
        Classify the type of follow-up question.

        Args:
            question: The user's question

        Returns:
            Follow-up type: 'add_column', 'change_filter', 'change_sort',
                           'change_limit', 'add_grouping', 'other'
        """
        question_lower = question.lower().strip()

        # Add/Include column
        if re.match(r'^\s*(add|include|also\s+show|show\s+also)\s+', question_lower):
            return 'add_column'

        # Change filter
        if re.match(r'^\s*(only|just|filter|where|with)\s+', question_lower):
            return 'change_filter'

        # Change sorting
        if re.match(r'^\s*(sort|order|rank)\s+by\s+', question_lower):
            return 'change_sort'

        # Change limit
        if re.match(r'^\s*(show|expand\s+to|top)\s+\d+', question_lower):
            return 'change_limit'

        # Add grouping
        if re.match(r'^\s*group\s+by\s+', question_lower):
            return 'add_grouping'

        return 'other'

    def build_context_prompt(
        self,
        question: str,
        context: Dict[str, Any],
        follow_up_type: str
    ) -> str:
        """
        Build a context-aware prompt for the LLM.

        Args:
            question: The current question
            context: The conversation context
            follow_up_type: Type of follow-up question

        Returns:
            Enhanced prompt with context
        """
        previous_query = context.get("previous_query", "N/A")
        previous_sql = context.get("previous_sql", "")
        tables_used = context.get("tables_used", [])
        columns_selected = context.get("columns_selected", [])
        limit = context.get("limit")

        prompt_parts = []

        prompt_parts.append("⚠️ CONTEXT-AWARE FOLLOW-UP QUERY ⚠️")
        prompt_parts.append("\nThis is a FOLLOW-UP question to a previous query.")
        prompt_parts.append("You MUST maintain the structure of the previous query and ONLY modify what the user requests.\n")

        prompt_parts.append("PREVIOUS QUERY CONTEXT:")
        prompt_parts.append(f"User's Previous Question: \"{previous_query}\"")

        if previous_sql:
            # Show simplified SQL (first 200 chars)
            sql_preview = previous_sql[:200] + "..." if len(previous_sql) > 200 else previous_sql
            prompt_parts.append(f"Previous SQL:\n{sql_preview}")

        if tables_used:
            prompt_parts.append(f"Tables Used: {', '.join(tables_used)}")

        if columns_selected:
            prompt_parts.append(f"Columns Selected: {', '.join(columns_selected)}")

        if limit:
            prompt_parts.append(f"Result Limit: {limit}")

        prompt_parts.append(f"\nNEW REQUEST: \"{question}\"")
        prompt_parts.append(f"Follow-up Type: {follow_up_type}\n")

        # Add specific instructions based on follow-up type
        if follow_up_type == 'add_column':
            prompt_parts.append("INSTRUCTIONS:")
            prompt_parts.append("1. Keep the EXACT SAME base query (same tables, WHERE, ORDER BY, LIMIT)")
            prompt_parts.append("2. ADD ONLY the requested column(s) to the SELECT clause")
            prompt_parts.append("3. If the new column requires a JOIN, add the JOIN but keep existing structure")
            prompt_parts.append("4. DO NOT add any other columns beyond what's requested")
            prompt_parts.append(f"5. Result should have: {', '.join(columns_selected)} + [requested column(s)]")

        elif follow_up_type == 'change_filter':
            prompt_parts.append("INSTRUCTIONS:")
            prompt_parts.append("1. Keep the SAME SELECT clause and table structure")
            prompt_parts.append("2. ADD or MODIFY the WHERE clause with the requested filter")
            prompt_parts.append("3. Maintain existing ORDER BY and LIMIT")

        elif follow_up_type == 'change_sort':
            prompt_parts.append("INSTRUCTIONS:")
            prompt_parts.append("1. Keep the SAME SELECT clause and table structure")
            prompt_parts.append("2. MODIFY only the ORDER BY clause")
            prompt_parts.append("3. Maintain existing WHERE and LIMIT")

        elif follow_up_type == 'change_limit':
            prompt_parts.append("INSTRUCTIONS:")
            prompt_parts.append("1. Keep the EXACT SAME query structure")
            prompt_parts.append("2. MODIFY only the LIMIT clause")

        elif follow_up_type == 'add_grouping':
            prompt_parts.append("INSTRUCTIONS:")
            prompt_parts.append("1. Modify SELECT to include GROUP BY dimension")
            prompt_parts.append("2. Adjust aggregations as needed (SUM, AVG, COUNT)")
            prompt_parts.append("3. Add GROUP BY clause")

        return "\n".join(prompt_parts)
