"""
Cross-Database Query Validator

Validates queries to ensure they don't attempt invalid cross-database JOINs.
Provides helpful error messages and suggestions for cross-database scenarios.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import structlog
import re
from dataclasses import dataclass

from src.core.sql_parser import SQLParser

logger = structlog.get_logger()


@dataclass
class CrossDatabaseIssue:
    """Represents a cross-database issue found in a query."""
    issue_type: str  # "join", "subquery", "union"
    tables_involved: List[str]
    databases_involved: List[str]
    severity: str  # "error", "warning"
    message: str
    suggestion: str


@dataclass
class ValidationResult:
    """Result of cross-database validation."""
    is_valid: bool
    is_cross_database: bool
    databases_involved: List[str]
    issues: List[CrossDatabaseIssue]
    can_execute_federated: bool
    suggested_strategy: Optional[str] = None
    rewritten_query: Optional[str] = None


class CrossDatabaseValidator:
    """
    Validates queries for cross-database compatibility.

    Detects when queries attempt to access multiple databases
    and provides appropriate warnings or errors.
    """

    def __init__(self, organization_id: str = None):
        """
        Initialize validator.

        Args:
            organization_id: Organization ID for context
        """
        self.organization_id = organization_id or 'default'
        self.parser = SQLParser()

    def validate_query(
        self,
        query: str,
        selected_databases: List[str],
        table_database_map: Dict[str, str]
    ) -> ValidationResult:
        """
        Validate a query for cross-database issues.

        Args:
            query: SQL query to validate
            selected_databases: List of databases user has selected for querying
            table_database_map: Mapping of table names to their database types

        Returns:
            ValidationResult with validation details
        """
        issues = []
        databases_involved = set()

        # Parse the query to extract tables
        try:
            parsed = self.parser.parse(query)
            tables = parsed.get('tables', [])
        except Exception as e:
            logger.warning(f"Failed to parse query for validation: {e}")
            # If we can't parse, extract tables with regex as fallback
            tables = self._extract_tables_regex(query)

        # Map tables to databases
        for table in tables:
            db = table_database_map.get(table)
            if db:
                databases_involved.add(db)

        # Check if this is cross-database
        is_cross_database = len(databases_involved) > 1

        if is_cross_database:
            # Detect specific cross-database operations
            issues.extend(self._detect_cross_database_joins(query, tables, table_database_map))
            issues.extend(self._detect_cross_database_subqueries(query, tables, table_database_map))
            issues.extend(self._detect_cross_database_unions(query, tables, table_database_map))

        # Determine if we can execute federally
        can_execute_federated = self._can_execute_federated(issues)

        # Suggest strategy if cross-database
        suggested_strategy = None
        if is_cross_database:
            suggested_strategy = self._suggest_execution_strategy(
                query, issues, databases_involved
            )

        # Check if all required databases are selected
        missing_databases = databases_involved - set(selected_databases)
        if missing_databases:
            issues.append(CrossDatabaseIssue(
                issue_type="missing_database",
                tables_involved=[],
                databases_involved=list(missing_databases),
                severity="error",
                message=f"Query requires access to databases not selected: {', '.join(missing_databases)}",
                suggestion=f"Enable these databases in the database selector: {', '.join(missing_databases)}"
            ))

        # Determine overall validity
        is_valid = not any(issue.severity == "error" for issue in issues)

        return ValidationResult(
            is_valid=is_valid,
            is_cross_database=is_cross_database,
            databases_involved=list(databases_involved),
            issues=issues,
            can_execute_federated=can_execute_federated,
            suggested_strategy=suggested_strategy
        )

    def _extract_tables_regex(self, query: str) -> List[str]:
        """Extract table names from query using regex as fallback."""
        tables = set()

        # Common patterns for table references
        patterns = [
            r'FROM\s+(\w+)',
            r'JOIN\s+(\w+)',
            r'INTO\s+(\w+)',
            r'UPDATE\s+(\w+)',
            r'DELETE\s+FROM\s+(\w+)'
        ]

        query_upper = query.upper()
        for pattern in patterns:
            matches = re.findall(pattern, query_upper, re.IGNORECASE)
            tables.update(matches)

        return list(tables)

    def _detect_cross_database_joins(
        self,
        query: str,
        tables: List[str],
        table_database_map: Dict[str, str]
    ) -> List[CrossDatabaseIssue]:
        """Detect cross-database JOINs."""
        issues = []

        # Check for JOIN keywords
        if re.search(r'\bJOIN\b', query, re.IGNORECASE):
            # Group tables by database
            db_tables = {}
            for table in tables:
                db = table_database_map.get(table)
                if db:
                    if db not in db_tables:
                        db_tables[db] = []
                    db_tables[db].append(table)

            if len(db_tables) > 1:
                # Found cross-database JOIN
                all_tables = []
                all_dbs = []
                for db, tbls in db_tables.items():
                    all_tables.extend(tbls)
                    all_dbs.append(db)

                issues.append(CrossDatabaseIssue(
                    issue_type="join",
                    tables_involved=all_tables,
                    databases_involved=all_dbs,
                    severity="warning",
                    message=f"Query contains JOIN across multiple databases: {', '.join(all_dbs)}",
                    suggestion="Consider using federated query execution or staging tables for cross-database JOINs"
                ))

        return issues

    def _detect_cross_database_subqueries(
        self,
        query: str,
        tables: List[str],
        table_database_map: Dict[str, str]
    ) -> List[CrossDatabaseIssue]:
        """Detect cross-database subqueries."""
        issues = []

        # Simple detection for subqueries
        if '(' in query and ')' in query:
            # Check if tables in subqueries are from different databases
            # This is a simplified check - a full SQL parser would be better
            pass

        return issues

    def _detect_cross_database_unions(
        self,
        query: str,
        tables: List[str],
        table_database_map: Dict[str, str]
    ) -> List[CrossDatabaseIssue]:
        """Detect cross-database UNIONs."""
        issues = []

        if re.search(r'\bUNION\b', query, re.IGNORECASE):
            # Check if UNION involves tables from different databases
            db_set = set()
            for table in tables:
                db = table_database_map.get(table)
                if db:
                    db_set.add(db)

            if len(db_set) > 1:
                issues.append(CrossDatabaseIssue(
                    issue_type="union",
                    tables_involved=tables,
                    databases_involved=list(db_set),
                    severity="warning",
                    message=f"Query contains UNION across multiple databases",
                    suggestion="UNION across databases will be executed using federated query approach"
                ))

        return issues

    def _can_execute_federated(self, issues: List[CrossDatabaseIssue]) -> bool:
        """Determine if query can be executed federally."""
        # Can execute if no errors and only certain types of cross-database operations
        if any(issue.severity == "error" for issue in issues):
            return False

        # We can handle JOINs and UNIONs federally
        allowed_types = {"join", "union"}
        for issue in issues:
            if issue.issue_type not in allowed_types and issue.severity != "warning":
                return False

        return True

    def _suggest_execution_strategy(
        self,
        query: str,
        issues: List[CrossDatabaseIssue],
        databases_involved: Set[str]
    ) -> str:
        """Suggest best execution strategy for cross-database query."""

        # Count issue types
        join_count = sum(1 for i in issues if i.issue_type == "join")
        union_count = sum(1 for i in issues if i.issue_type == "union")

        if join_count > 0:
            if len(databases_involved) == 2:
                return "federated_join"
            else:
                return "staging_table"
        elif union_count > 0:
            return "federated_union"
        else:
            return "pushdown"

    def generate_federated_plan(
        self,
        query: str,
        table_database_map: Dict[str, str],
        selected_databases: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a federated execution plan for a cross-database query.

        Args:
            query: SQL query
            table_database_map: Mapping of tables to databases
            selected_databases: List of enabled databases

        Returns:
            Execution plan or None if not possible
        """
        validation = self.validate_query(query, selected_databases, table_database_map)

        if not validation.can_execute_federated:
            return None

        plan = {
            "strategy": validation.suggested_strategy,
            "databases": validation.databases_involved,
            "steps": [],
            "estimated_cost": self._estimate_cost(validation)
        }

        # Generate steps based on strategy
        if validation.suggested_strategy == "federated_join":
            plan["steps"] = self._generate_federated_join_steps(
                query, table_database_map
            )
        elif validation.suggested_strategy == "federated_union":
            plan["steps"] = self._generate_federated_union_steps(
                query, table_database_map
            )
        elif validation.suggested_strategy == "staging_table":
            plan["steps"] = self._generate_staging_table_steps(
                query, table_database_map
            )
        else:
            plan["steps"] = [{"type": "pushdown", "query": query}]

        return plan

    def _generate_federated_join_steps(
        self,
        query: str,
        table_database_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate steps for federated JOIN execution."""
        steps = []

        # Step 1: Identify smaller dimension tables
        # Step 2: Pull dimension data
        # Step 3: Push to fact table database
        # Step 4: Execute JOIN in fact database

        steps.append({
            "step": 1,
            "description": "Analyze table sizes and identify optimal execution location",
            "action": "analyze"
        })

        steps.append({
            "step": 2,
            "description": "Extract smaller tables to staging",
            "action": "extract"
        })

        steps.append({
            "step": 3,
            "description": "Execute JOIN in primary database",
            "action": "execute"
        })

        return steps

    def _generate_federated_union_steps(
        self,
        query: str,
        table_database_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate steps for federated UNION execution."""
        steps = []

        steps.append({
            "step": 1,
            "description": "Execute query parts in respective databases",
            "action": "parallel_execute"
        })

        steps.append({
            "step": 2,
            "description": "Merge results in memory",
            "action": "merge"
        })

        return steps

    def _generate_staging_table_steps(
        self,
        query: str,
        table_database_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Generate steps for staging table approach."""
        steps = []

        steps.append({
            "step": 1,
            "description": "Create staging tables in target database",
            "action": "create_staging"
        })

        steps.append({
            "step": 2,
            "description": "Copy data to staging tables",
            "action": "copy_data"
        })

        steps.append({
            "step": 3,
            "description": "Execute query on staged data",
            "action": "execute"
        })

        steps.append({
            "step": 4,
            "description": "Clean up staging tables",
            "action": "cleanup"
        })

        return steps

    def _estimate_cost(self, validation: ValidationResult) -> float:
        """Estimate relative cost of cross-database execution."""
        base_cost = 1.0

        # Add cost for each database involved
        base_cost *= len(validation.databases_involved)

        # Add cost for each issue
        for issue in validation.issues:
            if issue.issue_type == "join":
                base_cost *= 2.0
            elif issue.issue_type == "union":
                base_cost *= 1.5

        return base_cost