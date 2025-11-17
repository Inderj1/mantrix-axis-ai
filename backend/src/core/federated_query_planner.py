"""
Federated Query Planner

Plans and optimizes execution of queries spanning multiple databases.
Determines optimal strategy for cross-database JOINs and data movement.
"""
import sqlglot
from sqlglot import parse_one, exp
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class ExecutionStrategy(Enum):
    """Strategy for executing federated queries."""
    SINGLE_DATABASE = "single_database"  # Query uses only one database
    MOVE_TO_PRIMARY = "move_to_primary"  # Fetch from secondary, execute in primary
    DISTRIBUTED = "distributed"  # Execute parts in each DB, merge results
    MATERIALIZE = "materialize"  # Create temp table in one DB, join there


class JoinType(Enum):
    """Type of join operation."""
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"
    CROSS = "CROSS"


@dataclass
class TableReference:
    """Reference to a table in a specific database."""
    database_type: str  # bigquery, snowflake, etc.
    full_name: str  # Full table identifier
    schema: Optional[str] = None
    table: Optional[str] = None
    alias: Optional[str] = None
    estimated_rows: Optional[int] = None
    estimated_size_mb: Optional[float] = None


@dataclass
class QueryStep:
    """A single step in the execution plan."""
    step_number: int
    database_type: str
    sql: str
    description: str
    estimated_cost: float = 0.0
    depends_on: List[int] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """Complete execution plan for a federated query."""
    strategy: ExecutionStrategy
    primary_database: str
    databases_involved: List[str]
    tables_by_database: Dict[str, List[TableReference]]
    steps: List[QueryStep]
    estimated_total_cost: float = 0.0
    estimated_execution_time_seconds: float = 0.0
    data_movement_mb: float = 0.0
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JoinOperation:
    """Represents a JOIN operation between tables."""
    left_table: TableReference
    right_table: TableReference
    join_type: JoinType
    join_condition: str
    estimated_result_rows: Optional[int] = None


class FederatedQueryPlanner:
    """
    Plan execution of queries spanning multiple databases.

    Analyzes queries to determine:
    - Which databases are needed
    - Optimal execution strategy
    - Data movement requirements
    - Cost estimates
    """

    # Cost factors (relative weights)
    COST_NETWORK_TRANSFER_PER_MB = 1.0
    COST_QUERY_EXECUTION_BASE = 5.0
    COST_TEMP_TABLE_CREATION = 10.0
    COST_JOIN_PER_1K_ROWS = 0.1

    def __init__(self, database_metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize the federated query planner.

        Args:
            database_metadata: Optional metadata about tables/databases
                {
                    'bigquery': {
                        'sales.transactions': {
                            'row_count': 1000000,
                            'size_mb': 500
                        }
                    }
                }
        """
        self.database_metadata = database_metadata or {}
        logger.info("FederatedQueryPlanner initialized")

    def analyze_query(
        self,
        sql: str,
        primary_database: str,
        table_database_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a query to determine which databases are needed.

        Args:
            sql: SQL query to analyze
            primary_database: Primary database for execution
            table_database_mapping: Optional mapping of table names to databases
                Example: {'sales': 'bigquery', 'customers': 'snowflake'}

        Returns:
            Dictionary with analysis results:
            {
                'databases': ['bigquery', 'snowflake'],
                'tables_by_database': {
                    'bigquery': [TableReference(...)],
                    'snowflake': [TableReference(...)]
                },
                'has_joins': True,
                'join_operations': [JoinOperation(...)],
                'complexity': 'simple|moderate|complex'
            }
        """
        logger.info("Analyzing query for federated execution", primary_database=primary_database)

        try:
            # Parse the SQL
            parsed = parse_one(sql, read='bigquery')  # Use bigquery as default parser

            # Extract table references
            tables = self._extract_tables(parsed)

            # Map tables to databases
            tables_by_db = self._map_tables_to_databases(
                tables,
                table_database_mapping or {}
            )

            # Detect JOIN operations
            joins = self._detect_joins(parsed, tables_by_db)

            # Determine complexity
            complexity = self._assess_complexity(tables_by_db, joins)

            # Get list of databases involved
            databases = list(tables_by_db.keys())

            analysis = {
                'databases': databases,
                'tables_by_database': tables_by_db,
                'has_joins': len(joins) > 0,
                'join_operations': joins,
                'complexity': complexity,
                'is_federated': len(databases) > 1,
                'primary_database': primary_database
            }

            logger.info(
                "Query analysis complete",
                databases=databases,
                table_count=sum(len(tbls) for tbls in tables_by_db.values()),
                has_joins=len(joins) > 0,
                complexity=complexity
            )

            return analysis

        except Exception as e:
            logger.error("Failed to analyze query", error=str(e))
            raise ValueError(f"Query analysis failed: {str(e)}")

    def create_execution_plan(
        self,
        sql: str,
        primary_database: str,
        table_database_mapping: Optional[Dict[str, str]] = None,
        user_preference: Optional[ExecutionStrategy] = None
    ) -> ExecutionPlan:
        """
        Create optimal execution plan for federated query.

        Args:
            sql: SQL query to execute
            primary_database: Primary database for execution
            table_database_mapping: Mapping of tables to databases
            user_preference: User's preferred execution strategy (optional)

        Returns:
            ExecutionPlan with steps and cost estimates
        """
        logger.info("Creating execution plan", primary_database=primary_database)

        # Analyze the query first
        analysis = self.analyze_query(sql, primary_database, table_database_mapping)

        # If single database, use simple strategy
        if not analysis['is_federated']:
            return self._create_single_database_plan(sql, primary_database, analysis)

        # Determine optimal strategy
        if user_preference:
            strategy = user_preference
        else:
            strategy = self._select_optimal_strategy(analysis)

        # Create plan based on strategy
        if strategy == ExecutionStrategy.MOVE_TO_PRIMARY:
            plan = self._create_move_to_primary_plan(sql, primary_database, analysis)
        elif strategy == ExecutionStrategy.DISTRIBUTED:
            plan = self._create_distributed_plan(sql, primary_database, analysis)
        elif strategy == ExecutionStrategy.MATERIALIZE:
            plan = self._create_materialize_plan(sql, primary_database, analysis)
        else:
            plan = self._create_single_database_plan(sql, primary_database, analysis)

        logger.info(
            "Execution plan created",
            strategy=strategy.value,
            steps=len(plan.steps),
            estimated_cost=plan.estimated_total_cost,
            data_movement_mb=plan.data_movement_mb
        )

        return plan

    def _extract_tables(self, parsed_sql: exp.Expression) -> List[Dict[str, str]]:
        """Extract all table references from parsed SQL."""
        tables = []

        for table in parsed_sql.find_all(exp.Table):
            table_info = {
                'name': table.name,
                'db': table.db or None,
                'catalog': table.catalog or None,
                'alias': table.alias or None,
                'full_name': str(table)
            }
            tables.append(table_info)

        logger.debug(f"Extracted {len(tables)} table references")
        return tables

    def _map_tables_to_databases(
        self,
        tables: List[Dict[str, str]],
        mapping: Dict[str, str]
    ) -> Dict[str, List[TableReference]]:
        """Map tables to their respective databases."""
        tables_by_db = {}

        for table_info in tables:
            table_name = table_info['name']

            # Determine database from mapping or default
            if table_name in mapping:
                db_type = mapping[table_name]
            elif table_info['db'] and table_info['db'] in mapping:
                db_type = mapping[table_info['db']]
            else:
                # Default: assume all tables in primary database if not specified
                db_type = 'unknown'

            # Get metadata if available
            metadata = self.database_metadata.get(db_type, {}).get(table_name, {})

            # Create TableReference
            table_ref = TableReference(
                database_type=db_type,
                full_name=table_info['full_name'],
                schema=table_info['db'],
                table=table_name,
                alias=table_info['alias'],
                estimated_rows=metadata.get('row_count'),
                estimated_size_mb=metadata.get('size_mb')
            )

            if db_type not in tables_by_db:
                tables_by_db[db_type] = []
            tables_by_db[db_type].append(table_ref)

        return tables_by_db

    def _detect_joins(
        self,
        parsed_sql: exp.Expression,
        tables_by_db: Dict[str, List[TableReference]]
    ) -> List[JoinOperation]:
        """Detect JOIN operations in the query."""
        joins = []

        # Find all JOIN expressions
        for join_expr in parsed_sql.find_all(exp.Join):
            # Extract join type
            join_type_str = str(join_expr.side) if join_expr.side else 'INNER'
            try:
                join_type = JoinType[join_type_str.upper()]
            except KeyError:
                join_type = JoinType.INNER

            # Extract join condition
            join_condition = str(join_expr.on) if join_expr.on else ""

            # For now, create a placeholder JoinOperation
            # In a full implementation, we'd match join tables to TableReferences

        logger.debug(f"Detected {len(joins)} JOIN operations")
        return joins

    def _assess_complexity(
        self,
        tables_by_db: Dict[str, List[TableReference]],
        joins: List[JoinOperation]
    ) -> str:
        """Assess query complexity."""
        num_databases = len(tables_by_db)
        num_tables = sum(len(tables) for tables in tables_by_db.values())
        num_joins = len(joins)

        if num_databases == 1 and num_tables <= 2:
            return "simple"
        elif num_databases <= 2 and num_tables <= 4 and num_joins <= 2:
            return "moderate"
        else:
            return "complex"

    def _select_optimal_strategy(self, analysis: Dict[str, Any]) -> ExecutionStrategy:
        """Select optimal execution strategy based on analysis."""
        databases = analysis['databases']
        complexity = analysis['complexity']

        # Single database - no federation needed
        if len(databases) == 1:
            return ExecutionStrategy.SINGLE_DATABASE

        # Simple cross-database query - move to primary
        if complexity == "simple":
            return ExecutionStrategy.MOVE_TO_PRIMARY

        # Moderate complexity - distributed execution
        if complexity == "moderate":
            return ExecutionStrategy.DISTRIBUTED

        # Complex query - materialize approach
        return ExecutionStrategy.MATERIALIZE

    def _create_single_database_plan(
        self,
        sql: str,
        primary_database: str,
        analysis: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create plan for single-database query."""
        step = QueryStep(
            step_number=1,
            database_type=primary_database,
            sql=sql,
            description=f"Execute query in {primary_database}",
            estimated_cost=self.COST_QUERY_EXECUTION_BASE
        )

        return ExecutionPlan(
            strategy=ExecutionStrategy.SINGLE_DATABASE,
            primary_database=primary_database,
            databases_involved=[primary_database],
            tables_by_database=analysis['tables_by_database'],
            steps=[step],
            estimated_total_cost=self.COST_QUERY_EXECUTION_BASE,
            estimated_execution_time_seconds=1.0
        )

    def _create_move_to_primary_plan(
        self,
        sql: str,
        primary_database: str,
        analysis: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create plan to fetch from secondary DBs and execute in primary."""
        steps = []
        data_movement = 0.0

        # Step 1: Fetch data from secondary databases
        step_num = 1
        for db_type, tables in analysis['tables_by_database'].items():
            if db_type != primary_database:
                for table in tables:
                    fetch_sql = f"SELECT * FROM {table.full_name}"
                    steps.append(QueryStep(
                        step_number=step_num,
                        database_type=db_type,
                        sql=fetch_sql,
                        description=f"Fetch {table.table} from {db_type}",
                        estimated_cost=self.COST_QUERY_EXECUTION_BASE
                    ))

                    # Estimate data movement
                    if table.estimated_size_mb:
                        data_movement += table.estimated_size_mb

                    step_num += 1

        # Step 2: Execute main query in primary database
        steps.append(QueryStep(
            step_number=step_num,
            database_type=primary_database,
            sql=sql,
            description=f"Execute joined query in {primary_database}",
            estimated_cost=self.COST_QUERY_EXECUTION_BASE + self.COST_JOIN_PER_1K_ROWS,
            depends_on=list(range(1, step_num))
        ))

        total_cost = (
            len(steps) * self.COST_QUERY_EXECUTION_BASE +
            data_movement * self.COST_NETWORK_TRANSFER_PER_MB
        )

        return ExecutionPlan(
            strategy=ExecutionStrategy.MOVE_TO_PRIMARY,
            primary_database=primary_database,
            databases_involved=analysis['databases'],
            tables_by_database=analysis['tables_by_database'],
            steps=steps,
            estimated_total_cost=total_cost,
            estimated_execution_time_seconds=len(steps) * 2.0,
            data_movement_mb=data_movement
        )

    def _create_distributed_plan(
        self,
        sql: str,
        primary_database: str,
        analysis: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create plan for distributed execution."""
        # Simplified distributed plan
        steps = []

        # Execute sub-queries in each database
        for i, db_type in enumerate(analysis['databases'], 1):
            steps.append(QueryStep(
                step_number=i,
                database_type=db_type,
                sql=f"SELECT * FROM (subquery for {db_type})",
                description=f"Execute partial query in {db_type}",
                estimated_cost=self.COST_QUERY_EXECUTION_BASE
            ))

        # Merge results
        steps.append(QueryStep(
            step_number=len(steps) + 1,
            database_type=primary_database,
            sql="MERGE results",
            description="Merge results from all databases",
            estimated_cost=self.COST_QUERY_EXECUTION_BASE,
            depends_on=list(range(1, len(steps) + 1))
        ))

        return ExecutionPlan(
            strategy=ExecutionStrategy.DISTRIBUTED,
            primary_database=primary_database,
            databases_involved=analysis['databases'],
            tables_by_database=analysis['tables_by_database'],
            steps=steps,
            estimated_total_cost=len(steps) * self.COST_QUERY_EXECUTION_BASE
        )

    def _create_materialize_plan(
        self,
        sql: str,
        primary_database: str,
        analysis: Dict[str, Any]
    ) -> ExecutionPlan:
        """Create plan using materialized temp tables."""
        steps = []

        # Create temp tables for remote data
        for i, (db_type, tables) in enumerate(analysis['tables_by_database'].items(), 1):
            if db_type != primary_database:
                steps.append(QueryStep(
                    step_number=i,
                    database_type=primary_database,
                    sql=f"CREATE TEMP TABLE temp_{db_type} AS (SELECT ...)",
                    description=f"Materialize {db_type} data in {primary_database}",
                    estimated_cost=self.COST_TEMP_TABLE_CREATION
                ))

        # Execute main query
        steps.append(QueryStep(
            step_number=len(steps) + 1,
            database_type=primary_database,
            sql=sql,
            description="Execute query with materialized tables",
            estimated_cost=self.COST_QUERY_EXECUTION_BASE,
            depends_on=list(range(1, len(steps) + 1))
        ))

        return ExecutionPlan(
            strategy=ExecutionStrategy.MATERIALIZE,
            primary_database=primary_database,
            databases_involved=analysis['databases'],
            tables_by_database=analysis['tables_by_database'],
            steps=steps,
            estimated_total_cost=(
                len(steps) * self.COST_TEMP_TABLE_CREATION +
                self.COST_QUERY_EXECUTION_BASE
            )
        )
