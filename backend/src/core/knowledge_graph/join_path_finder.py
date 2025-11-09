"""
Join Path Finder using Jena/RDF Knowledge Graph.

Automatically discovers join paths between tables based on the RDF metadata.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class JoinPath:
    """Represents a join path between two tables."""
    source_table: str
    target_table: str
    join_column: str
    column_type: str
    join_type: str = "LEFT"  # Default to LEFT JOIN

    def to_sql(self) -> str:
        """Generate SQL JOIN clause."""
        return f"{self.join_type} JOIN {self.target_table} ON {self.source_table}.{self.join_column} = {self.target_table}.{self.join_column}"


@dataclass
class MultiHopPath:
    """Represents a multi-hop join path through intermediate tables."""
    path: List[JoinPath]
    tables_involved: List[str]
    total_hops: int

    def to_sql_joins(self) -> List[str]:
        """Generate list of SQL JOIN clauses."""
        return [jp.to_sql() for jp in self.path]


class JoinPathFinder:
    """Find join paths between tables using Jena knowledge graph."""

    def __init__(self, knowledge_graph):
        """
        Initialize join path finder.

        Args:
            knowledge_graph: JenaKnowledgeGraph instance
        """
        self.kg = knowledge_graph
        self.FIN = knowledge_graph.FIN

    def find_direct_join(self, table1: str, table2: str) -> List[JoinPath]:
        """
        Find direct join paths between two tables.

        Args:
            table1: Source table name
            table2: Target table name

        Returns:
            List of possible JoinPath objects
        """
        query = f"""
        PREFIX fin: <http://example.com/finance#>

        SELECT ?joinColumn ?columnType ?joinType
        WHERE {{
            ?rel a fin:TableRelationship ;
                 fin:joinColumn ?joinColumn ;
                 fin:columnType ?columnType ;
                 fin:sourceTable ?source ;
                 fin:targetTable ?target .

            OPTIONAL {{ ?rel fin:joinType ?joinType }}

            ?source fin:tableName "{table1}" .
            ?target fin:tableName "{table2}" .
        }}
        """

        results = self.kg.query(query)

        join_paths = []
        for row in results:
            join_paths.append(JoinPath(
                source_table=table1,
                target_table=table2,
                join_column=str(row['joinColumn']),
                column_type=str(row['columnType']),
                join_type=str(row.get('joinType', 'LEFT'))
            ))

        logger.info(
            "Direct join paths found",
            table1=table1,
            table2=table2,
            count=len(join_paths)
        )

        return join_paths

    def find_multi_hop_paths(
        self,
        start_table: str,
        end_table: str,
        max_hops: int = 3
    ) -> List[MultiHopPath]:
        """
        Find multi-hop join paths between two tables.

        Uses breadth-first search to find paths through intermediate tables.

        Args:
            start_table: Starting table name
            end_table: Target table name
            max_hops: Maximum number of hops allowed

        Returns:
            List of MultiHopPath objects
        """
        # BFS to find all paths
        paths_found: List[MultiHopPath] = []
        queue: List[Tuple[str, List[JoinPath], Set[str]]] = [(start_table, [], {start_table})]

        while queue:
            current_table, path_so_far, visited = queue.pop(0)

            # If we reached the target, save this path
            if current_table == end_table and path_so_far:
                multi_hop = MultiHopPath(
                    path=path_so_far,
                    tables_involved=[start_table] + [jp.target_table for jp in path_so_far],
                    total_hops=len(path_so_far)
                )
                paths_found.append(multi_hop)
                continue

            # If we've reached max hops, stop exploring this path
            if len(path_so_far) >= max_hops:
                continue

            # Find all tables we can join to from current_table
            neighbors = self._get_connected_tables(current_table)

            for neighbor_table, join_info in neighbors.items():
                # Skip if already visited
                if neighbor_table in visited:
                    continue

                # Create new path with this join
                new_path = path_so_far + [JoinPath(
                    source_table=current_table,
                    target_table=neighbor_table,
                    join_column=join_info['join_column'],
                    column_type=join_info['column_type'],
                    join_type=join_info.get('join_type', 'LEFT')
                )]

                # Add to queue
                queue.append((
                    neighbor_table,
                    new_path,
                    visited | {neighbor_table}
                ))

        logger.info(
            "Multi-hop paths found",
            start_table=start_table,
            end_table=end_table,
            paths_count=len(paths_found),
            max_hops=max_hops
        )

        return paths_found

    def _get_connected_tables(self, table_name: str) -> Dict[str, Dict[str, str]]:
        """
        Get all tables that can be joined from the given table.

        Args:
            table_name: Source table name

        Returns:
            Dict mapping table names to join information
        """
        query = f"""
        PREFIX fin: <http://example.com/finance#>

        SELECT ?targetTable ?joinColumn ?columnType ?joinType
        WHERE {{
            ?rel a fin:TableRelationship ;
                 fin:joinColumn ?joinColumn ;
                 fin:columnType ?columnType ;
                 fin:sourceTable ?source ;
                 fin:targetTable ?target .

            OPTIONAL {{ ?rel fin:joinType ?joinType }}

            ?source fin:tableName "{table_name}" .
            ?target fin:tableName ?targetTable .
        }}
        """

        results = self.kg.query(query)

        connected = {}
        for row in results:
            target = str(row['targetTable'])
            connected[target] = {
                'join_column': str(row['joinColumn']),
                'column_type': str(row['columnType']),
                'join_type': str(row.get('joinType', 'LEFT'))
            }

        return connected

    def recommend_join_order(self, tables: List[str]) -> List[JoinPath]:
        """
        Recommend optimal join order for a list of tables.

        Uses a greedy approach to minimize the number of rows processed:
        1. Start with the largest fact table
        2. Join dimension tables in order of smallest to largest

        Args:
            tables: List of table names to join

        Returns:
            Ordered list of JoinPath objects
        """
        if len(tables) < 2:
            return []

        # Get table metadata (row counts, fact vs dimension)
        table_info = {}
        for table_name in tables:
            info = self._get_table_info(table_name)
            table_info[table_name] = info

        # Separate fact and dimension tables
        fact_tables = [t for t, info in table_info.items() if info.get('is_fact', False)]
        dim_tables = [t for t, info in table_info.items() if info.get('is_dimension', False)]
        other_tables = [t for t in tables if t not in fact_tables and t not in dim_tables]

        # Start with largest fact table (or largest table if no facts)
        if fact_tables:
            base_table = max(fact_tables, key=lambda t: table_info[t].get('row_count', 0))
        else:
            base_table = max(tables, key=lambda t: table_info[t].get('row_count', 0))

        # Sort dimension tables by row count (smallest first for better performance)
        remaining_tables = [t for t in tables if t != base_table]
        remaining_tables.sort(key=lambda t: table_info[t].get('row_count', float('inf')))

        # Build join order
        join_order: List[JoinPath] = []
        joined_tables = {base_table}

        for target_table in remaining_tables:
            # Find join from any already-joined table to this table
            best_join = None
            for source_table in joined_tables:
                joins = self.find_direct_join(source_table, target_table)
                if joins:
                    best_join = joins[0]  # Take first available join
                    break

                # Try reverse direction
                joins = self.find_direct_join(target_table, source_table)
                if joins:
                    # Swap direction
                    best_join = JoinPath(
                        source_table=source_table,
                        target_table=target_table,
                        join_column=joins[0].join_column,
                        column_type=joins[0].column_type,
                        join_type=joins[0].join_type
                    )
                    break

            if best_join:
                join_order.append(best_join)
                joined_tables.add(target_table)

        logger.info(
            "Join order recommended",
            base_table=base_table,
            total_joins=len(join_order),
            tables=len(tables)
        )

        return join_order

    def _get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get metadata about a table.

        Args:
            table_name: Table name

        Returns:
            Dict with table metadata (row_count, is_fact, is_dimension)
        """
        query = f"""
        PREFIX fin: <http://example.com/finance#>

        SELECT ?rowCount ?isFactTable ?isDimensionTable
        WHERE {{
            ?table a fin:Table ;
                   fin:tableName "{table_name}" .

            OPTIONAL {{ ?table fin:rowCount ?rowCount }}
            OPTIONAL {{ ?table fin:isFactTable ?isFactTable }}
            OPTIONAL {{ ?table fin:isDimensionTable ?isDimensionTable }}
        }}
        LIMIT 1
        """

        results = self.kg.query(query)

        if results:
            row = results[0]
            return {
                'row_count': int(row.get('rowCount', 0)),
                'is_fact': row.get('isFactTable', False),
                'is_dimension': row.get('isDimensionTable', False)
            }

        return {'row_count': 0, 'is_fact': False, 'is_dimension': False}

    def get_join_summary(self, tables: List[str]) -> str:
        """
        Generate a human-readable summary of how tables can be joined.

        Args:
            tables: List of table names

        Returns:
            String summary
        """
        if len(tables) < 2:
            return "Need at least 2 tables to generate join summary."

        join_order = self.recommend_join_order(tables)

        summary_lines = [
            f"Join Order for {len(tables)} tables:",
            ""
        ]

        if join_order:
            base_table = join_order[0].source_table
            summary_lines.append(f"Base Table: {base_table}")
            summary_lines.append("")

            for i, join_path in enumerate(join_order, 1):
                summary_lines.append(
                    f"{i}. {join_path.join_type} JOIN {join_path.target_table} "
                    f"ON {join_path.source_table}.{join_path.join_column} = "
                    f"{join_path.target_table}.{join_path.join_column}"
                )
        else:
            summary_lines.append("⚠️  No join paths found. Tables may not be related.")

        return "\n".join(summary_lines)
