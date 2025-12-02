"""
Multi-Database Schema Extractor

Extracts schemas from all configured databases using the ConnectorFactory.
Extends the single-database SchemaExtractor to support multiple database sources.

Key Features:
- Extract schemas from BigQuery, Snowflake, PostgreSQL, Redshift, Databricks
- Add source_database_type to each table's metadata
- Parallel extraction from multiple databases
- Unified schema format across all database types
- Error handling and fallback for unavailable databases

Author: Mantrix Axis AI
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from src.db.connector_factory import ConnectorFactory
from src.core.cache_manager import CacheManager
from src.config import settings

logger = structlog.get_logger()


class MultiDatabaseSchemaExtractor:
    """
    Extract schemas from all configured databases.

    Uses ConnectorFactory to dynamically discover and connect to available databases.
    Each extracted table schema includes source_database_type for multi-DB awareness.

    Usage:
        extractor = MultiDatabaseSchemaExtractor()
        all_schemas = extractor.extract_all_schemas()
        table_count = extractor.get_table_count_by_database()
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None, organization_id: str = None):
        """
        Initialize multi-database schema extractor.

        Args:
            cache_manager: Optional cache manager for schema caching
            organization_id: Organization ID for multi-tenancy
        """
        self.factory = ConnectorFactory()
        self.cache_manager = cache_manager
        self.schema_cache_prefix = "multi_db_schema:"
        self.organization_id = organization_id or settings.get('DEFAULT_ORG_ID', 'default')

    def extract_all_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract schemas from all available databases.

        Returns:
            Dictionary mapping database type to list of table schemas:
            {
                "bigquery": [table1, table2, ...],
                "snowflake": [table1, table2, ...],
                "postgresql": [table1, table2, ...],
                ...
            }

        Each table schema includes:
            - table_name: str
            - database: str (project/database name)
            - schema: str (dataset/schema name)
            - source_database_type: str ("bigquery", "snowflake", etc.)
            - description: Optional[str]
            - columns: List[Dict] (name, type, mode/nullable, description)
            - row_count: int
            - size_bytes: int (if available)
            - created_at: Optional[str]
            - modified_at: Optional[str]
        """
        results = {}

        # Get list of available databases from factory
        available_databases = self.factory.get_supported_types()

        logger.info(
            "Starting multi-database schema extraction",
            available_databases=available_databases
        )

        for db_type, is_available in available_databases.items():
            if not is_available:
                logger.debug(f"Skipping {db_type} (not available)")
                results[db_type] = []
                continue

            try:
                logger.info(f"Extracting schema from {db_type}")

                # Create connector for this database type
                connector = self._create_connector(db_type)

                if connector is None:
                    logger.warning(f"Could not create connector for {db_type} (not configured)")
                    results[db_type] = []
                    continue

                # Extract schema using the connector
                tables = self._extract_database_schema(connector, db_type)

                # Add source_database_type and organization_id to each table
                for table in tables:
                    table["source_database_type"] = db_type
                    table["organization_id"] = self.organization_id

                results[db_type] = tables
                logger.info(
                    f"Extracted {len(tables)} tables from {db_type}",
                    db_type=db_type,
                    table_count=len(tables)
                )

            except Exception as e:
                logger.error(
                    f"Failed to extract schema from {db_type}: {e}",
                    db_type=db_type,
                    error=str(e),
                    exc_info=True
                )
                results[db_type] = []

        # Log summary
        total_tables = sum(len(tables) for tables in results.values())
        logger.info(
            "Multi-database schema extraction complete",
            total_tables=total_tables,
            databases=list(results.keys())
        )

        return results

    def _create_connector(self, db_type: str):
        """
        Create connector for a specific database type.

        Args:
            db_type: Database type string

        Returns:
            Database connector instance or None if not configured
        """
        try:
            # Build config based on database type and settings
            if db_type == 'bigquery':
                config = {
                    'project_id': settings.google_cloud_project,
                    'dataset_id': settings.bigquery_dataset,
                    'credentials_path': settings.google_application_credentials
                }
            elif db_type == 'snowflake':
                if not settings.snowflake_account:
                    return None
                config = {
                    'account': settings.snowflake_account,
                    'user': settings.snowflake_user,
                    'password': settings.snowflake_password,
                    'warehouse': settings.snowflake_warehouse,
                    'database': settings.snowflake_database,
                    'schema': settings.snowflake_schema
                }
            elif db_type == 'postgresql':
                if not settings.external_postgres_host:
                    return None
                config = {
                    'host': settings.external_postgres_host,
                    'port': settings.external_postgres_port,
                    'database': settings.external_postgres_database,
                    'user': settings.external_postgres_user,
                    'password': settings.external_postgres_password,
                    'schema': settings.external_postgres_schema
                }
            elif db_type == 'redshift':
                if not settings.redshift_host:
                    return None
                config = {
                    'host': settings.redshift_host,
                    'port': settings.redshift_port,
                    'database': settings.redshift_database,
                    'user': settings.redshift_user,
                    'password': settings.redshift_password,
                    'schema': settings.redshift_schema
                }
            elif db_type == 'databricks':
                if not settings.databricks_server_hostname:
                    return None
                config = {
                    'server_hostname': settings.databricks_server_hostname,
                    'http_path': settings.databricks_http_path,
                    'access_token': settings.databricks_access_token,
                    'catalog': settings.databricks_catalog,
                    'schema': settings.databricks_schema
                }
            else:
                logger.warning(f"Unknown database type: {db_type}")
                return None

            # Create connector using factory
            connector = self.factory.create_connector(db_type, config)
            return connector

        except ValueError as e:
            # Not configured
            logger.debug(f"{db_type} not configured: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating {db_type} connector: {e}")
            return None

    def _extract_database_schema(self, connector, db_type: str) -> List[Dict[str, Any]]:
        """
        Extract schema from a database connector.

        Args:
            connector: Database connector instance
            db_type: Database type string

        Returns:
            List of table schemas
        """
        try:
            # Get list of tables
            tables = connector.list_tables()

            if not tables:
                logger.warning(f"No tables found in {db_type}")
                return []

            # Extract schema for each table
            table_schemas = []
            for table_name in tables[:100]:  # Limit to 100 tables to avoid timeout
                try:
                    schema = connector.get_table_schema(table_name)
                    table_schemas.append(schema)
                except Exception as e:
                    logger.warning(
                        f"Failed to get schema for {table_name}: {e}",
                        table=table_name,
                        db_type=db_type
                    )
                    continue

            return table_schemas

        except Exception as e:
            logger.error(f"Failed to extract schema: {e}")
            raise

    def get_table_count_by_database(self) -> Dict[str, int]:
        """
        Get table counts across all databases.

        Returns:
            Dictionary mapping database type to table count:
            {"bigquery": 150, "snowflake": 75, ...}
        """
        schemas = self.extract_all_schemas()
        return {db: len(tables) for db, tables in schemas.items()}

    def get_all_tables_flat(self) -> List[Dict[str, Any]]:
        """
        Get all tables from all databases as a flat list.

        Returns:
            Flat list of all table schemas with source_database_type field
        """
        schemas = self.extract_all_schemas()
        all_tables = []

        for db_type, tables in schemas.items():
            all_tables.extend(tables)

        return all_tables

    def extract_schemas_for_types(self, db_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract schemas only for specific database types.

        Args:
            db_types: List of database type strings

        Returns:
            Dictionary mapping database type to list of table schemas
        """
        all_schemas = self.extract_all_schemas()
        return {
            db_type: all_schemas.get(db_type, [])
            for db_type in db_types
        }

    def extract_schema_for_connector(
        self,
        connector_type: str,
        connector_config: Dict[str, Any],
        organization_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Extract schema from a specific connector configuration.

        This method is used when extracting schema for a specific connector
        (e.g., OAuth-authenticated BigQuery connector) rather than using
        environment variables.

        Args:
            connector_type: Type of database connector (bigquery, snowflake, etc.)
            connector_config: Full configuration for the connector including credentials
            organization_id: Organization ID for multi-tenancy

        Returns:
            List of table schemas with source_database_type and organization_id
        """
        org_id = organization_id or self.organization_id

        logger.info(
            f"Extracting schema for connector",
            connector_type=connector_type,
            organization_id=org_id
        )

        connector = None
        try:
            # Create connector using factory with provided config
            connector = self.factory.create_connector(connector_type, connector_config)

            if connector is None:
                logger.error(f"Could not create connector for {connector_type}")
                return []

            # Connect to the database
            logger.info(f"Connecting to {connector_type} database...")
            connector.connect()
            logger.info(f"Successfully connected to {connector_type} database")

            # Extract schema using the connector
            tables = self._extract_database_schema(connector, connector_type)

            # Add source_database_type and organization_id to each table
            for table in tables:
                table["source_database_type"] = connector_type
                table["organization_id"] = org_id

            logger.info(
                f"Extracted {len(tables)} tables from {connector_type} connector",
                connector_type=connector_type,
                table_count=len(tables),
                organization_id=org_id
            )

            return tables

        except Exception as e:
            logger.error(
                f"Failed to extract schema for connector: {e}",
                connector_type=connector_type,
                error=str(e),
                exc_info=True
            )
            return []

        finally:
            # Clean up connection
            try:
                if connector is not None:
                    connector.disconnect()
                    logger.info(f"Disconnected from {connector_type} database")
            except Exception as cleanup_error:
                logger.warning(f"Error during connector cleanup: {cleanup_error}")
