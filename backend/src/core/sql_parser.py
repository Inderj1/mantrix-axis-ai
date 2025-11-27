"""
Simple SQL Parser

Basic SQL parsing for table extraction and query analysis.
Not a full parser - just enough for cross-database validation.
"""

import re
from typing import Dict, List, Set, Optional
import structlog

logger = structlog.get_logger()


class SQLParser:
    """
    Basic SQL parser for extracting tables and analyzing query structure.

    This is a simplified parser that handles common SQL patterns.
    For production, consider using sqlparse or another full parser.
    """

    def __init__(self):
        """Initialize the parser."""
        self.table_patterns = [
            # FROM clause
            (r'\bFROM\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'from'),
            # JOIN clauses
            (r'\bJOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            (r'\bLEFT\s+JOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            (r'\bRIGHT\s+JOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            (r'\bINNER\s+JOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            (r'\bOUTER\s+JOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            (r'\bCROSS\s+JOIN\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'join'),
            # INTO clause (INSERT)
            (r'\bINTO\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'into'),
            # UPDATE clause
            (r'\bUPDATE\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'update'),
            # DELETE FROM clause
            (r'\bDELETE\s+FROM\s+([`"\[]?[\w]+[`"\]]?(?:\.\w+)?)', 'delete'),
        ]

    def parse(self, query: str) -> Dict[str, any]:
        """
        Parse SQL query and extract information.

        Args:
            query: SQL query string

        Returns:
            Dictionary with parsed information:
            - tables: List of table names found
            - operation: Type of SQL operation (SELECT, INSERT, UPDATE, DELETE)
            - has_joins: Whether query contains JOINs
            - has_subquery: Whether query contains subqueries
            - has_union: Whether query contains UNIONs
        """
        result = {
            'tables': [],
            'operation': self._detect_operation(query),
            'has_joins': False,
            'has_subquery': False,
            'has_union': False,
            'table_contexts': {}  # Maps table to context (from, join, etc.)
        }

        # Extract tables
        tables, contexts = self._extract_tables(query)
        result['tables'] = list(tables)
        result['table_contexts'] = contexts

        # Detect query features
        result['has_joins'] = self._has_joins(query)
        result['has_subquery'] = self._has_subquery(query)
        result['has_union'] = self._has_union(query)

        return result

    def _detect_operation(self, query: str) -> str:
        """Detect the main SQL operation type."""
        query_upper = query.upper().strip()

        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        elif query_upper.startswith('CREATE'):
            return 'CREATE'
        elif query_upper.startswith('DROP'):
            return 'DROP'
        elif query_upper.startswith('ALTER'):
            return 'ALTER'
        elif query_upper.startswith('WITH'):
            # CTE - check what follows
            if 'SELECT' in query_upper:
                return 'SELECT'
            elif 'INSERT' in query_upper:
                return 'INSERT'
            elif 'UPDATE' in query_upper:
                return 'UPDATE'
            elif 'DELETE' in query_upper:
                return 'DELETE'
        return 'UNKNOWN'

    def _extract_tables(self, query: str) -> tuple[Set[str], Dict[str, str]]:
        """
        Extract table names from query.

        Returns:
            Tuple of (set of table names, dict mapping table to context)
        """
        tables = set()
        contexts = {}

        # Remove string literals to avoid false matches
        clean_query = self._remove_string_literals(query)

        for pattern, context in self.table_patterns:
            matches = re.findall(pattern, clean_query, re.IGNORECASE)
            for match in matches:
                table = self._clean_table_name(match)
                if table and not self._is_keyword(table):
                    tables.add(table)
                    if table not in contexts:
                        contexts[table] = context

        # Handle CTEs (WITH clause)
        cte_tables = self._extract_cte_tables(query)
        tables.update(cte_tables)
        for cte in cte_tables:
            contexts[cte] = 'cte'

        return tables, contexts

    def _extract_cte_tables(self, query: str) -> Set[str]:
        """Extract CTE (Common Table Expression) names."""
        cte_tables = set()

        # Pattern for WITH clause
        with_pattern = r'\bWITH\s+(\w+)\s+AS\s*\('
        matches = re.findall(with_pattern, query, re.IGNORECASE)
        cte_tables.update(matches)

        # Pattern for multiple CTEs
        multi_cte_pattern = r',\s*(\w+)\s+AS\s*\('
        matches = re.findall(multi_cte_pattern, query, re.IGNORECASE)
        cte_tables.update(matches)

        return cte_tables

    def _clean_table_name(self, table: str) -> str:
        """Clean and normalize table name."""
        # Remove quotes, brackets
        table = re.sub(r'[`"\[\]]', '', table)

        # Handle database.table or schema.table notation
        if '.' in table:
            parts = table.split('.')
            # Return just the table name (last part)
            return parts[-1]

        return table.strip()

    def _remove_string_literals(self, query: str) -> str:
        """Remove string literals from query to avoid false matches."""
        # Remove single-quoted strings
        query = re.sub(r"'[^']*'", "''", query)
        # Remove double-quoted strings (in some dialects these are strings)
        query = re.sub(r'"[^"]*"', '""', query)
        return query

    def _is_keyword(self, word: str) -> bool:
        """Check if word is a SQL keyword (not a table name)."""
        keywords = {
            'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
            'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'AS',
            'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'UNION', 'ALL',
            'DISTINCT', 'VALUES', 'SET', 'NULL', 'TRUE', 'FALSE', 'CASE', 'WHEN',
            'THEN', 'ELSE', 'END', 'WITH', 'RECURSIVE', 'DUAL', 'SYSIBM', 'SYSTEM'
        }
        return word.upper() in keywords

    def _has_joins(self, query: str) -> bool:
        """Check if query contains JOIN clauses."""
        join_pattern = r'\b(LEFT|RIGHT|INNER|OUTER|CROSS|FULL)?\s*JOIN\b'
        return bool(re.search(join_pattern, query, re.IGNORECASE))

    def _has_subquery(self, query: str) -> bool:
        """Check if query contains subqueries."""
        # Simple check for nested parentheses with SELECT
        clean_query = self._remove_string_literals(query)

        # Count SELECT keywords
        select_count = len(re.findall(r'\bSELECT\b', clean_query, re.IGNORECASE))

        # If more than one SELECT, likely has subquery
        if select_count > 1:
            return True

        # Check for subquery patterns
        subquery_patterns = [
            r'\(\s*SELECT\b',  # (SELECT ...
            r'\bIN\s*\(\s*SELECT\b',  # IN (SELECT ...
            r'\bEXISTS\s*\(\s*SELECT\b',  # EXISTS (SELECT ...
            r'=\s*\(\s*SELECT\b',  # = (SELECT ... (scalar subquery)
        ]

        for pattern in subquery_patterns:
            if re.search(pattern, clean_query, re.IGNORECASE):
                return True

        return False

    def _has_union(self, query: str) -> bool:
        """Check if query contains UNION."""
        union_pattern = r'\bUNION(\s+ALL)?\b'
        return bool(re.search(union_pattern, query, re.IGNORECASE))

    def extract_table_aliases(self, query: str) -> Dict[str, str]:
        """
        Extract table aliases from query.

        Returns:
            Dictionary mapping alias to table name
        """
        aliases = {}

        # Patterns for table aliases
        alias_patterns = [
            # FROM table AS alias
            r'\bFROM\s+([`"\[]?[\w]+[`"\]]?)\s+AS\s+(\w+)',
            # FROM table alias (without AS)
            r'\bFROM\s+([`"\[]?[\w]+[`"\]]?)\s+(\w+)(?:\s+WHERE|\s+JOIN|\s+LEFT|\s+RIGHT|\s+INNER|\s+,|\s*$)',
            # JOIN table AS alias
            r'\bJOIN\s+([`"\[]?[\w]+[`"\]]?)\s+AS\s+(\w+)',
            # JOIN table alias (without AS)
            r'\bJOIN\s+([`"\[]?[\w]+[`"\]]?)\s+(\w+)(?:\s+ON)',
        ]

        clean_query = self._remove_string_literals(query)

        for pattern in alias_patterns:
            matches = re.findall(pattern, clean_query, re.IGNORECASE)
            for table, alias in matches:
                table = self._clean_table_name(table)
                if not self._is_keyword(alias):
                    aliases[alias] = table

        return aliases

    def get_referenced_columns(self, query: str) -> Dict[str, List[str]]:
        """
        Extract columns referenced in the query grouped by table.

        Returns:
            Dictionary mapping table/alias to list of columns
        """
        columns_by_table = {}

        # Pattern for table.column references
        column_pattern = r'(\w+)\.(\w+)'
        matches = re.findall(column_pattern, query)

        for table_or_alias, column in matches:
            if not self._is_keyword(table_or_alias):
                if table_or_alias not in columns_by_table:
                    columns_by_table[table_or_alias] = []
                if column not in columns_by_table[table_or_alias]:
                    columns_by_table[table_or_alias].append(column)

        return columns_by_table