"""
Amazon Redshift Database Connector

Implements the BaseDatabaseConnector interface for Amazon Redshift.
Inherits from PostgreSQLConnector since Redshift is PostgreSQL-compatible.
"""
from typing import Optional, Dict, Any
import structlog

from .postgresql_connector import PostgreSQLConnector, POSTGRESQL_AVAILABLE
from ..database_capabilities import DatabaseCapabilities, REDSHIFT_CAPABILITIES

logger = structlog.get_logger()


class RedshiftConnector(PostgreSQLConnector):
    """
    Amazon Redshift database connector.

    Inherits from PostgreSQLConnector since Redshift is PostgreSQL-compatible
    (PostgreSQL 8.0.2 fork), with some Redshift-specific differences.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        schema: Optional[str] = "public",
        ssl_mode: Optional[str] = "require",  # Redshift recommends SSL
        cluster_identifier: Optional[str] = None
    ):
        """
        Initialize Redshift connector.

        Args:
            host: Redshift cluster endpoint (e.g., cluster.region.redshift.amazonaws.com)
            port: Redshift port (default: 5439)
            database: Database name
            user: Redshift username
            password: Redshift password
            schema: Schema name (default: public)
            ssl_mode: SSL mode (default: require for Redshift)
            cluster_identifier: Optional cluster identifier for metadata
        """
        if not POSTGRESQL_AVAILABLE:
            raise ImportError(
                "psycopg2 is not installed. "
                "Install it with: pip install psycopg2-binary"
            )

        # Redshift default port is 5439 (not 5432 like PostgreSQL)
        redshift_port = port or 5439

        # Initialize using PostgreSQL parent class
        super().__init__(
            host=host,
            port=redshift_port,
            database=database,
            user=user,
            password=password,
            schema=schema,
            ssl_mode=ssl_mode or "require"
        )

        self.cluster_identifier = cluster_identifier
        self._capabilities = REDSHIFT_CAPABILITIES

        logger.info(
            "Redshift connector initialized",
            host=self.host,
            port=self.port,
            database=self.database,
            cluster=self.cluster_identifier
        )

    def get_cost_estimate(self, query: str) -> Dict[str, Any]:
        """
        Estimate Redshift query cost.

        Note: Redshift uses cluster-based pricing (not query-based like BigQuery).
        Cost is based on cluster uptime, not individual queries.

        Args:
            query: SQL query to estimate

        Returns:
            Dictionary with cost estimate (will be 0.0 for cluster-based pricing)
        """
        try:
            # Use EXPLAIN to get query plan
            cursor = self.connection.cursor()
            cursor.execute(f"EXPLAIN {query}")
            explain_output = cursor.fetchall()
            cursor.close()

            # Parse EXPLAIN output for complexity indicators
            explain_text = '\n'.join([row[0] for row in explain_output])

            return {
                "estimated_cost_usd": 0.0,  # Cluster-based pricing
                "estimated_bytes_processed": 0,
                "estimated_rows_scanned": 0,
                "explain_plan": explain_text,
                "note": "Redshift uses cluster-based pricing. Cost depends on cluster type and uptime."
            }

        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return {
                "estimated_cost_usd": 0.0,
                "error": str(e)
            }

    def get_capabilities(self) -> DatabaseCapabilities:
        """
        Get Redshift capabilities.

        Returns:
            DatabaseCapabilities object for Redshift
        """
        return self._capabilities

    def get_cluster_info(self) -> Dict[str, Any]:
        """
        Get Redshift cluster information.

        Returns:
            Dictionary with cluster details
        """
        if not self.connection:
            return {"error": "Not connected"}

        try:
            # Query Redshift system tables for cluster info
            query = """
            SELECT
                version() as version,
                current_database() as current_database,
                current_schema() as current_schema,
                current_user as current_user
            """

            cursor = self.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()

            return {
                "version": result[0] if result else None,
                "database": result[1] if result else None,
                "schema": result[2] if result else None,
                "user": result[3] if result else None,
                "cluster_identifier": self.cluster_identifier,
                "host": self.host,
                "port": self.port
            }

        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {"error": str(e)}

    def get_table_statistics(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Redshift-specific table statistics.

        Args:
            table_name: Table name
            schema: Schema name (optional)

        Returns:
            Dictionary with table statistics
        """
        if not self.connection:
            raise QueryExecutionError("Redshift connection not established")

        try:
            target_schema = schema or self.schema

            # Query Redshift system tables for table stats
            query = """
            SELECT
                tbl,
                size as size_mb,
                rows,
                sortkey1,
                skew_rows
            FROM svv_table_info
            WHERE schema = %(schema)s
              AND "table" = %(table)s
            """

            cursor = self.connection.cursor()
            cursor.execute(query, {'schema': target_schema, 'table': table_name})
            result = cursor.fetchone()
            cursor.close()

            if result:
                return {
                    "table_id": result[0],
                    "size_mb": result[1],
                    "rows": result[2],
                    "sort_key": result[3],
                    "skew_rows": result[4]
                }
            else:
                return {"error": f"Table {target_schema}.{table_name} not found"}

        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
            return {"error": str(e)}


# Alias for consistency
RedshiftClient = RedshiftConnector
