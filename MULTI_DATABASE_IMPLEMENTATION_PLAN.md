# Multi-Database Implementation Plan

## Implementation Status

**Last Updated**: November 17, 2025

### ✅ Completed (As of Nov 17, 2025)

**Authentication & Permissions (Nov 16-17)**:
- ✅ AWS Cognito authentication system
  - JWT token validation via JWKS
  - User groups (Admins, Users)
  - Multi-tenant support with organization_id
  - Test admin user created and working
- ✅ Database permissions system (`backend/src/core/database_permissions.py`)
  - Permission levels: none, read, write, admin
  - Organization-level isolation
  - User and admin role management
- ✅ Connector infrastructure (`backend/src/db/connectors/`)
  - Base connector interface (`base_connector.py`)
  - Connector factory with permission enforcement
  - Feature flag system for database access control

**Database Connectors (Nov 16-17)**:
- ✅ BigQuery connector (`bigquery_connector.py`) **ENHANCED Nov 17**
  - Fully conforms to BaseDatabaseConnector interface
  - Native pagination with page tokens
  - Cost estimation via dry-run
  - Auto-qualification of table names
  - Backward compatibility maintained
- ✅ PostgreSQL connector (`postgresql_connector.py`)
  - Full CRUD operations
  - Schema extraction
  - Connection testing
- ✅ Amazon Redshift connector (`redshift_connector.py`)
  - PostgreSQL-compatible implementation
  - Redshift-specific optimizations
- ✅ Databricks connector (`databricks_connector.py`)
  - Spark SQL support
  - Catalog/schema navigation
- ✅ Snowflake connector (`snowflake_connector.py`)
  - Three-level namespace (database.schema.table)
  - Key-pair and password authentication
  - Warehouse management
  - Full schema introspection

**API Routes**:
- ✅ `/api/v1/permissions/*` - Permission management (admin-only)
- ✅ `/api/v1/connectors/*` - Connector type listing and testing

**Git Commits**:
- `c29085b` - fix: Correct Cognito token validation (client_id vs aud)
- `358dea8` - feat: Implement AWS Cognito authentication for ECS deployment
- `671ff01` - feat: Add comprehensive database permissions and feature flag system

### 🚧 In Progress

**Phase 1: Basic Multi-Database Support**:
- ✅ Snowflake client implementation (COMPLETED Nov 17)
- ✅ Enhanced BigQuery client to conform to base interface (COMPLETED Nov 17)
- ⏳ Multi-database schema pipeline (NOT STARTED)
- 📋 Database factory integration with LLM/SQL generator (PLANNED - see DATABASE_FACTORY_INTEGRATION_PLAN.md)

### 📋 Not Started

**Phase 1 Remaining**:
- Base database client abstraction (partially done via connectors)
- Multi-DB schema extractor
- Updated Weaviate schema storage with DB source tracking

**Phase 2**: All tasks (cross-database queries, SQL dialect translation, etc.)

**Phase 3**: All tasks (materialized views, cost tracking, monitoring)

---

## Database Configuration Guide

This section provides environment variable setup for all supported database connectors.

### Snowflake Configuration

Snowflake connector supports both password and key-pair authentication. Configure via environment variables or pass credentials directly to the connector.

**Required Environment Variables:**
```bash
# Snowflake Account (e.g., 'xy12345.us-east-1' or 'orgname-accountname')
SNOWFLAKE_ACCOUNT=your-account-identifier

# User authentication
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password

# Warehouse (compute cluster)
SNOWFLAKE_WAREHOUSE=your_warehouse_name

# Optional: Database and schema (defaults to PUBLIC schema if not specified)
SNOWFLAKE_DATABASE=your_database_name
SNOWFLAKE_SCHEMA=PUBLIC

# Optional: Role (uses account default if not specified)
SNOWFLAKE_ROLE=your_role_name
```

**Alternative: Key-Pair Authentication (More Secure)**
```python
from src.db.connectors import SnowflakeConnector

# Load private key
with open('path/to/rsa_key.p8', 'rb') as key_file:
    private_key = key_file.read()

connector = SnowflakeConnector(
    account='xy12345.us-east-1',
    user='your_username',
    private_key=private_key,
    warehouse='COMPUTE_WH',
    database='MY_DATABASE'
)
```

### PostgreSQL Configuration

For customer PostgreSQL databases (separate from internal app database):

```bash
# External PostgreSQL (customer databases)
EXTERNAL_POSTGRES_HOST=your-external-host
EXTERNAL_POSTGRES_PORT=5432
EXTERNAL_POSTGRES_USER=customer_user
EXTERNAL_POSTGRES_PASSWORD=customer_password
EXTERNAL_POSTGRES_DATABASE=customer_db

# SSL Mode (optional): disable, allow, prefer, require, verify-ca, verify-full
EXTERNAL_POSTGRES_SSL_MODE=require
```

### Amazon Redshift Configuration

```bash
REDSHIFT_HOST=your-cluster.region.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password
REDSHIFT_DATABASE=your_database
REDSHIFT_SCHEMA=public  # Optional

# Optional: Cluster identifier for management operations
REDSHIFT_CLUSTER_IDENTIFIER=your-cluster-name
```

### Databricks Configuration

Databricks uses personal access tokens or service principal authentication:

```bash
# Server hostname (e.g., 'dbc-12345678-90ab.cloud.databricks.com')
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com

# HTTP path from SQL warehouse or cluster (e.g., '/sql/1.0/warehouses/abc123')
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your_warehouse_id

# Personal Access Token or Service Principal Token
DATABRICKS_ACCESS_TOKEN=dapi...your_token

# Optional: Unity Catalog and schema
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=default
```

### BigQuery Configuration

BigQuery uses Google Cloud service account authentication:

```bash
# GCP Project ID
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Default dataset
BIGQUERY_DATASET=your_dataset_name

# Path to service account JSON key file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional: Location/region
BIGQUERY_LOCATION=US
```

### Testing Connector Configuration

Use the connector factory to test connections before deploying:

```python
from src.db.connector_factory import ConnectorFactory

# Test Snowflake connection
config = {
    'account': 'xy12345.us-east-1',
    'user': 'test_user',
    'password': 'test_password',
    'warehouse': 'COMPUTE_WH'
}

result = ConnectorFactory.test_connection('snowflake', config)
print(f"Connection test: {result['success']}")
print(f"Message: {result['message']}")
print(f"Time: {result['connection_time_ms']}ms")
```

### Permission Configuration

After configuring database credentials, grant users permission to access databases:

```bash
# Example: Grant read access to Snowflake for a user
curl -X POST http://localhost:8000/api/v1/permissions/grant \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "permission": {
      "database_type": "snowflake",
      "access_level": "read"
    }
  }'
```

**Access Levels:**
- `none`: No access (default)
- `read`: Can query data (SELECT)
- `write`: Can modify data (INSERT, UPDATE, DELETE)
- `admin`: Full access (includes DDL operations)

---

## Executive Summary

This document outlines a comprehensive 3-phase plan to extend Mantrix Axis AI from a BigQuery-only system to a multi-database platform supporting Snowflake, PostgreSQL, Amazon Redshift, and Databricks. The implementation prioritizes smart cross-database query execution, cost optimization, and production-grade reliability.

**Current State**: BigQuery + Snowflake + PostgreSQL + Redshift + Databricks connectors with Cognito authentication and permission system

**Target State**: Unified SQL generation supporting 5 databases with intelligent query routing, cross-database joins, and materialized view abstraction

**Timeline**: 15-17 weeks (3.5-4 months)
**Actual Progress**: ~2 weeks completed (all database connectors + auth infrastructure)

**Phases**:
1. **Phase 1** (5 weeks): Basic Multi-Database Support - **45% Complete**
2. **Phase 2** (4-6 weeks): Advanced Cross-Database Features - **0% Complete**
3. **Phase 3** (4-6 weeks): Production Hardening - **0% Complete**

---

## Table of Contents

1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Phase 1: Basic Multi-Database Support (5 weeks)](#phase-1-basic-multi-database-support-5-weeks)
3. [Phase 2: Advanced Cross-Database Features (4-6 weeks)](#phase-2-advanced-cross-database-features-4-6-weeks)
4. [Phase 3: Production Hardening (4-6 weeks)](#phase-3-production-hardening-4-6-weeks)
5. [Risk Assessment and Mitigation](#risk-assessment-and-mitigation)
6. [Success Metrics](#success-metrics)
7. [Testing Strategy](#testing-strategy)
8. [Rollout Plan](#rollout-plan)

---

## Current Architecture Analysis

### Existing Components (BigQuery-Centric)

**Database Layer**:
- `backend/src/db/bigquery.py` - BigQuery client (26KB)
- `backend/src/db/postgresql_client.py` - PostgreSQL client (26KB, limited usage)
- No Snowflake, Redshift, or Databricks clients

**Schema Management**:
- `backend/src/pipeline/schema_extractor.py` - BigQuery schema extraction
- `backend/src/db/weaviate_client.py` - Vector storage for table schemas
- `backend/src/pipeline/rdf_builder.py` - RDF graph for table relationships

**SQL Generation**:
- `backend/src/core/sql_generator.py` - LLM-based SQL generation (orchestrator)
- `backend/src/core/llm_client.py` - Anthropic Claude integration (68KB)
- Assumes BigQuery SQL dialect

**Caching**:
- `backend/src/core/cache_manager.py` - Redis-based multi-tier caching
- Smart caching with quality gates (recently implemented)

**Knowledge Graph**:
- `backend/src/core/knowledge_graph/jena_client.py` - RDF triple store
- `backend/src/core/knowledge_graph/join_path_finder.py` - Automatic JOIN discovery

### Key Gaps for Multi-Database Support

1. **No Base Database Client Abstraction**
   - Each database client has different interfaces
   - No common interface for execute_query(), get_schema(), validate_sql()

2. **BigQuery-Specific SQL Dialect**
   - LLM prompts assume BigQuery syntax
   - No dialect translation layer

3. **Single-Database Schema Pipeline**
   - Schema extractor only works with BigQuery
   - Weaviate stores schemas without database source differentiation

4. **No Cross-Database Query Engine**
   - Cannot execute queries spanning multiple databases
   - No strategy for cross-database JOINs

5. **Single-Database Caching**
   - Cache keys don't include database identifier
   - No multi-database cache invalidation

---

## Phase 1: Basic Multi-Database Support (5 weeks)

**Goal**: Enable SQL generation and execution for Snowflake, PostgreSQL, Redshift, and Databricks as independent data sources.

### Week 1: Base Abstraction Layer

#### Task 1.1: Create Base Database Client Interface

**File**: `backend/src/db/base_client.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum

class DatabaseType(Enum):
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    POSTGRESQL = "postgresql"
    REDSHIFT = "redshift"
    DATABRICKS = "databricks"

class SQLDialect(Enum):
    STANDARD = "standard"
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    POSTGRESQL = "postgresql"
    REDSHIFT = "redshift"  # Based on PostgreSQL
    DATABRICKS = "databricks"  # Spark SQL

class BaseDatabaseClient(ABC):
    """
    Abstract base class for all database clients.
    Ensures consistent interface across all databases.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_type = self._get_db_type()
        self.dialect = self._get_dialect()

    @abstractmethod
    def _get_db_type(self) -> DatabaseType:
        """Return the database type enum."""
        pass

    @abstractmethod
    def _get_dialect(self) -> SQLDialect:
        """Return the SQL dialect enum."""
        pass

    @abstractmethod
    def execute_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        timeout_seconds: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query string
            params: Optional query parameters
            timeout_seconds: Query timeout

        Returns:
            List of row dictionaries

        Raises:
            DatabaseExecutionError: If query fails
        """
        pass

    @abstractmethod
    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL syntax without executing.

        Returns:
            {
                "valid": bool,
                "error": Optional[str],
                "metadata": Optional[Dict]
            }
        """
        pass

    @abstractmethod
    def get_schema(
        self,
        database: Optional[str] = None,
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract database schema metadata.

        Returns:
            {
                "tables": [
                    {
                        "name": str,
                        "database": str,
                        "schema": str,
                        "columns": List[Dict],
                        "row_count": int,
                        "size_bytes": int
                    }
                ]
            }
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test database connectivity."""
        pass

    @abstractmethod
    def get_cost_estimate(self, sql: str) -> Dict[str, Any]:
        """
        Estimate query execution cost.

        Returns:
            {
                "estimated_cost_usd": float,
                "estimated_bytes_processed": int,
                "estimated_rows_scanned": int
            }
        """
        pass

    def get_capabilities(self) -> Dict[str, bool]:
        """Return database capability flags."""
        return {
            "supports_dry_run": False,
            "supports_cost_estimation": False,
            "supports_materialized_views": False,
            "supports_transactions": True,
            "supports_window_functions": True,
            "supports_cte": True,
            "supports_json": False,
            "supports_array": False,
            "max_query_size_mb": 10
        }
```

**Deliverable**: Base class with full interface definition

**Testing**: Unit tests for interface compliance

---

#### Task 1.2: Refactor Existing BigQuery Client

**File**: `backend/src/db/bigquery.py` (MODIFY)

```python
from src.db.base_client import BaseDatabaseClient, DatabaseType, SQLDialect

class BigQueryClient(BaseDatabaseClient):
    """BigQuery implementation of BaseDatabaseClient."""

    def _get_db_type(self) -> DatabaseType:
        return DatabaseType.BIGQUERY

    def _get_dialect(self) -> SQLDialect:
        return SQLDialect.BIGQUERY

    def execute_query(self, sql: str, params=None, timeout_seconds=None) -> List[Dict]:
        # Existing implementation
        pass

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """Use BigQuery dry run for validation."""
        try:
            query_job = self.client.query(sql, dry_run=True, use_query_cache=False)
            return {
                "valid": True,
                "error": None,
                "metadata": {
                    "total_bytes_processed": query_job.total_bytes_processed,
                    "estimated_cost_usd": (query_job.total_bytes_processed / 1e12) * 5.0
                }
            }
        except Exception as e:
            return {"valid": False, "error": str(e), "metadata": None}

    def get_schema(self, database=None, schema=None) -> Dict:
        # Existing schema extraction logic
        pass

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "supports_dry_run": True,
            "supports_cost_estimation": True,
            "supports_materialized_views": True,
            "supports_transactions": False,
            "supports_window_functions": True,
            "supports_cte": True,
            "supports_json": True,
            "supports_array": True,
            "max_query_size_mb": 100
        }
```

**Deliverable**: BigQuery client conforming to base interface

**Testing**: All existing BigQuery tests pass

---

### Week 2: Snowflake Integration

#### Task 2.1: Implement Snowflake Client

**File**: `backend/src/db/snowflake_client.py` (NEW)

```python
from src.db.base_client import BaseDatabaseClient, DatabaseType, SQLDialect
import snowflake.connector
from snowflake.connector import DictCursor
import logging

logger = logging.getLogger(__name__)

class SnowflakeClient(BaseDatabaseClient):
    """Snowflake database client implementation."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = self._create_connection()

    def _get_db_type(self) -> DatabaseType:
        return DatabaseType.SNOWFLAKE

    def _get_dialect(self) -> SQLDialect:
        return SQLDialect.SNOWFLAKE

    def _create_connection(self):
        """Create Snowflake connection."""
        return snowflake.connector.connect(
            user=self.config.get("user"),
            password=self.config.get("password"),
            account=self.config.get("account"),
            warehouse=self.config.get("warehouse"),
            database=self.config.get("database"),
            schema=self.config.get("schema"),
            role=self.config.get("role")
        )

    def execute_query(self, sql: str, params=None, timeout_seconds=None) -> List[Dict]:
        """Execute query on Snowflake."""
        try:
            cursor = self.connection.cursor(DictCursor)

            if timeout_seconds:
                cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout_seconds}")

            cursor.execute(sql, params or {})
            results = cursor.fetchall()
            cursor.close()

            logger.info(f"Snowflake query returned {len(results)} rows")
            return results
        except Exception as e:
            logger.error(f"Snowflake execution error: {e}")
            raise

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL using EXPLAIN.
        Note: Snowflake doesn't have true dry-run like BigQuery.
        """
        try:
            cursor = self.connection.cursor()
            explain_sql = f"EXPLAIN {sql}"
            cursor.execute(explain_sql)
            explain_result = cursor.fetchall()
            cursor.close()

            return {
                "valid": True,
                "error": None,
                "metadata": {"explain_plan": str(explain_result)}
            }
        except Exception as e:
            return {"valid": False, "error": str(e), "metadata": None}

    def get_schema(self, database=None, schema=None) -> Dict:
        """Extract Snowflake schema metadata."""
        db = database or self.config.get("database")
        sch = schema or self.config.get("schema")

        # Get all tables
        tables_query = f"""
        SELECT
            table_catalog as database_name,
            table_schema as schema_name,
            table_name,
            row_count,
            bytes
        FROM {db}.INFORMATION_SCHEMA.TABLES
        WHERE table_schema = '{sch}'
        AND table_type = 'BASE TABLE'
        """

        cursor = self.connection.cursor(DictCursor)
        cursor.execute(tables_query)
        tables = cursor.fetchall()

        result_tables = []
        for table in tables:
            # Get columns for each table
            columns_query = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                comment
            FROM {db}.INFORMATION_SCHEMA.COLUMNS
            WHERE table_schema = '{sch}'
            AND table_name = '{table['TABLE_NAME']}'
            ORDER BY ordinal_position
            """

            cursor.execute(columns_query)
            columns = cursor.fetchall()

            result_tables.append({
                "name": table["TABLE_NAME"],
                "database": table["DATABASE_NAME"],
                "schema": table["SCHEMA_NAME"],
                "columns": [
                    {
                        "name": col["COLUMN_NAME"],
                        "type": col["DATA_TYPE"],
                        "nullable": col["IS_NULLABLE"] == "YES",
                        "default": col["COLUMN_DEFAULT"],
                        "description": col["COMMENT"]
                    }
                    for col in columns
                ],
                "row_count": table.get("ROW_COUNT", 0),
                "size_bytes": table.get("BYTES", 0)
            })

        cursor.close()
        return {"tables": result_tables}

    def test_connection(self) -> bool:
        """Test Snowflake connection."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Snowflake connection test failed: {e}")
            return False

    def get_cost_estimate(self, sql: str) -> Dict[str, Any]:
        """
        Estimate Snowflake query cost.
        Note: Snowflake charges by warehouse time, not bytes scanned.
        """
        # This is a rough estimate based on query profile
        # Real cost depends on warehouse size and execution time
        return {
            "estimated_cost_usd": 0.0,  # Requires execution to measure
            "estimated_bytes_processed": 0,
            "estimated_rows_scanned": 0,
            "note": "Snowflake uses compute credits, not bytes-based pricing"
        }

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "supports_dry_run": False,  # No true dry-run
            "supports_cost_estimation": False,  # Requires execution
            "supports_materialized_views": True,
            "supports_transactions": True,
            "supports_window_functions": True,
            "supports_cte": True,
            "supports_json": True,
            "supports_array": True,
            "max_query_size_mb": 10
        }
```

**Configuration**: Add to `backend/src/config.py`

```python
# Snowflake Configuration
snowflake_account: Optional[str] = Field(None, alias="SNOWFLAKE_ACCOUNT")
snowflake_user: Optional[str] = Field(None, alias="SNOWFLAKE_USER")
snowflake_password: Optional[str] = Field(None, alias="SNOWFLAKE_PASSWORD")
snowflake_warehouse: str = Field(default="COMPUTE_WH", alias="SNOWFLAKE_WAREHOUSE")
snowflake_database: Optional[str] = Field(None, alias="SNOWFLAKE_DATABASE")
snowflake_schema: str = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
snowflake_role: str = Field(default="ACCOUNTADMIN", alias="SNOWFLAKE_ROLE")
```

**Dependencies**: Add to `requirements.txt`

```
snowflake-connector-python>=3.0.0
```

**Deliverable**: Fully functional Snowflake client

**Testing**: Connection test, schema extraction test, simple query execution

---

### Week 3: PostgreSQL Enhancement + Redshift Client

#### Task 3.1: Enhance PostgreSQL Client

**File**: `backend/src/db/postgresql_client.py` (MODIFY)

Currently exists but needs to conform to base interface.

```python
from src.db.base_client import BaseDatabaseClient, DatabaseType, SQLDialect
import psycopg2
from psycopg2.extras import RealDictCursor

class PostgreSQLClient(BaseDatabaseClient):
    """PostgreSQL database client (also works for Redshift with modifications)."""

    def _get_db_type(self) -> DatabaseType:
        return DatabaseType.POSTGRESQL

    def _get_dialect(self) -> SQLDialect:
        return SQLDialect.POSTGRESQL

    def execute_query(self, sql: str, params=None, timeout_seconds=None) -> List[Dict]:
        """Execute PostgreSQL query."""
        conn = psycopg2.connect(**self._get_connection_params())

        if timeout_seconds:
            cursor = conn.cursor()
            cursor.execute(f"SET statement_timeout = {timeout_seconds * 1000}")

        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql, params or {})
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return [dict(row) for row in results]

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate using EXPLAIN."""
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql}")
            cursor.fetchall()
            cursor.close()
            conn.close()
            return {"valid": True, "error": None, "metadata": None}
        except Exception as e:
            return {"valid": False, "error": str(e), "metadata": None}

    def get_schema(self, database=None, schema=None) -> Dict:
        """Extract PostgreSQL schema from information_schema."""
        # Similar to Snowflake implementation
        # Use INFORMATION_SCHEMA.TABLES and INFORMATION_SCHEMA.COLUMNS
        pass

    # ... other methods
```

**Deliverable**: Enhanced PostgreSQL client with full base interface

---

#### Task 3.2: Implement Redshift Client

**File**: `backend/src/db/redshift_client.py` (NEW)

```python
from src.db.postgresql_client import PostgreSQLClient
from src.db.base_client import DatabaseType, SQLDialect

class RedshiftClient(PostgreSQLClient):
    """
    Amazon Redshift client.
    Inherits from PostgreSQL since Redshift is PostgreSQL-compatible.
    """

    def _get_db_type(self) -> DatabaseType:
        return DatabaseType.REDSHIFT

    def _get_dialect(self) -> SQLDialect:
        return SQLDialect.REDSHIFT

    def get_cost_estimate(self, sql: str) -> Dict[str, Any]:
        """
        Redshift cost is based on cluster uptime, not query-specific.
        Use EXPLAIN to estimate query complexity.
        """
        try:
            conn = psycopg2.connect(**self._get_connection_params())
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {sql}")
            explain_output = cursor.fetchall()
            cursor.close()
            conn.close()

            # Parse EXPLAIN output for cost estimate
            # Redshift EXPLAIN shows query plan steps
            return {
                "estimated_cost_usd": 0.0,  # Cluster-based pricing
                "estimated_bytes_processed": 0,
                "estimated_rows_scanned": 0,
                "explain_plan": str(explain_output)
            }
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return {"estimated_cost_usd": 0.0}

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "supports_dry_run": False,
            "supports_cost_estimation": False,
            "supports_materialized_views": True,
            "supports_transactions": True,
            "supports_window_functions": True,
            "supports_cte": True,
            "supports_json": True,  # Limited JSON support
            "supports_array": False,  # No native arrays
            "max_query_size_mb": 16
        }
```

**Configuration**: Add to `config.py`

```python
# Redshift Configuration
redshift_host: Optional[str] = Field(None, alias="REDSHIFT_HOST")
redshift_port: int = Field(default=5439, alias="REDSHIFT_PORT")
redshift_database: Optional[str] = Field(None, alias="REDSHIFT_DATABASE")
redshift_user: Optional[str] = Field(None, alias="REDSHIFT_USER")
redshift_password: Optional[str] = Field(None, alias="REDSHIFT_PASSWORD")
```

**Dependencies**:
```
psycopg2-binary>=2.9.0  # Already in requirements.txt
```

**Deliverable**: Redshift client (PostgreSQL subclass)

**Testing**: Connection test against Redshift cluster

---

### Week 4: Databricks Integration

#### Task 4.1: Implement Databricks Client

**File**: `backend/src/db/databricks_client.py` (NEW)

```python
from src.db.base_client import BaseDatabaseClient, DatabaseType, SQLDialect
from databricks import sql
import logging

logger = logging.getLogger(__name__)

class DatabricksClient(BaseDatabaseClient):
    """Databricks SQL Warehouse client (Spark SQL)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = self._create_connection()

    def _get_db_type(self) -> DatabaseType:
        return DatabaseType.DATABRICKS

    def _get_dialect(self) -> SQLDialect:
        return SQLDialect.DATABRICKS

    def _create_connection(self):
        """Create Databricks SQL connection."""
        return sql.connect(
            server_hostname=self.config.get("server_hostname"),
            http_path=self.config.get("http_path"),
            access_token=self.config.get("access_token")
        )

    def execute_query(self, sql_query: str, params=None, timeout_seconds=None) -> List[Dict]:
        """Execute Databricks SQL query."""
        cursor = self.connection.cursor()
        cursor.execute(sql_query, params or {})

        # Fetch column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch rows and convert to dictionaries
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))

        cursor.close()
        logger.info(f"Databricks query returned {len(results)} rows")
        return results

    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate using EXPLAIN."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"EXPLAIN {sql}")
            explain_result = cursor.fetchall()
            cursor.close()

            return {"valid": True, "error": None, "metadata": {"explain": str(explain_result)}}
        except Exception as e:
            return {"valid": False, "error": str(e), "metadata": None}

    def get_schema(self, database=None, schema=None) -> Dict:
        """Extract Databricks catalog metadata."""
        catalog = database or self.config.get("catalog", "main")
        schema_name = schema or self.config.get("schema", "default")

        # Get tables using INFORMATION_SCHEMA
        tables_query = f"""
        SELECT
            table_catalog,
            table_schema,
            table_name,
            table_type
        FROM {catalog}.information_schema.tables
        WHERE table_schema = '{schema_name}'
        """

        cursor = self.connection.cursor()
        cursor.execute(tables_query)
        tables = cursor.fetchall()

        result_tables = []
        for table_row in tables:
            table_name = table_row[2]

            # Get columns using DESCRIBE
            describe_query = f"DESCRIBE {catalog}.{schema_name}.{table_name}"
            cursor.execute(describe_query)
            columns_raw = cursor.fetchall()

            columns = [
                {
                    "name": col[0],
                    "type": col[1],
                    "nullable": col[2] == "YES" if len(col) > 2 else True,
                    "description": col[3] if len(col) > 3 else None
                }
                for col in columns_raw
                if not col[0].startswith("#")  # Skip partition info
            ]

            result_tables.append({
                "name": table_name,
                "database": catalog,
                "schema": schema_name,
                "columns": columns,
                "row_count": 0,  # Would need COUNT(*) query
                "size_bytes": 0
            })

        cursor.close()
        return {"tables": result_tables}

    def test_connection(self) -> bool:
        """Test Databricks connection."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Databricks connection test failed: {e}")
            return False

    def get_cost_estimate(self, sql: str) -> Dict[str, Any]:
        """Databricks charges by DBU (Databricks Units) usage."""
        return {
            "estimated_cost_usd": 0.0,
            "estimated_bytes_processed": 0,
            "estimated_rows_scanned": 0,
            "note": "Databricks uses DBU-based pricing"
        }

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "supports_dry_run": False,
            "supports_cost_estimation": False,
            "supports_materialized_views": False,  # Use Delta Live Tables instead
            "supports_transactions": True,  # Delta Lake
            "supports_window_functions": True,
            "supports_cte": True,
            "supports_json": True,
            "supports_array": True,
            "max_query_size_mb": 20
        }
```

**Configuration**: Add to `config.py`

```python
# Databricks Configuration
databricks_server_hostname: Optional[str] = Field(None, alias="DATABRICKS_SERVER_HOSTNAME")
databricks_http_path: Optional[str] = Field(None, alias="DATABRICKS_HTTP_PATH")
databricks_access_token: Optional[str] = Field(None, alias="DATABRICKS_ACCESS_TOKEN")
databricks_catalog: str = Field(default="main", alias="DATABRICKS_CATALOG")
databricks_schema: str = Field(default="default", alias="DATABRICKS_SCHEMA")
```

**Dependencies**:
```
databricks-sql-connector>=2.0.0
```

**Deliverable**: Databricks client with Spark SQL support

**Testing**: Connection test, schema extraction

---

### Week 5: Database Factory + Multi-DB Schema Pipeline

#### Task 5.1: Create Database Client Factory

**File**: `backend/src/db/database_factory.py` (NEW)

```python
from typing import Optional
from src.db.base_client import BaseDatabaseClient, DatabaseType
from src.db.bigquery import BigQueryClient
from src.db.snowflake_client import SnowflakeClient
from src.db.postgresql_client import PostgreSQLClient
from src.db.redshift_client import RedshiftClient
from src.db.databricks_client import DatabricksClient
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseFactory:
    """Factory for creating database clients based on configuration."""

    _clients = {}  # Singleton cache

    @classmethod
    def get_client(cls, db_type: DatabaseType) -> BaseDatabaseClient:
        """
        Get or create a database client.

        Args:
            db_type: Database type enum

        Returns:
            Database client instance

        Raises:
            ValueError: If database not configured
        """
        # Check cache
        if db_type in cls._clients:
            return cls._clients[db_type]

        # Create client based on type
        if db_type == DatabaseType.BIGQUERY:
            client = cls._create_bigquery_client()
        elif db_type == DatabaseType.SNOWFLAKE:
            client = cls._create_snowflake_client()
        elif db_type == DatabaseType.POSTGRESQL:
            client = cls._create_postgresql_client()
        elif db_type == DatabaseType.REDSHIFT:
            client = cls._create_redshift_client()
        elif db_type == DatabaseType.DATABRICKS:
            client = cls._create_databricks_client()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        # Cache and return
        cls._clients[db_type] = client
        logger.info(f"Created {db_type.value} client")
        return client

    @classmethod
    def _create_bigquery_client(cls) -> BigQueryClient:
        config = {
            "project": settings.google_cloud_project,
            "dataset": settings.bigquery_dataset,
            "credentials_path": settings.google_application_credentials,
            "timeout": settings.bigquery_query_timeout_seconds
        }
        return BigQueryClient(config)

    @classmethod
    def _create_snowflake_client(cls) -> SnowflakeClient:
        if not settings.snowflake_account:
            raise ValueError("Snowflake not configured (SNOWFLAKE_ACCOUNT missing)")

        config = {
            "account": settings.snowflake_account,
            "user": settings.snowflake_user,
            "password": settings.snowflake_password,
            "warehouse": settings.snowflake_warehouse,
            "database": settings.snowflake_database,
            "schema": settings.snowflake_schema,
            "role": settings.snowflake_role
        }
        return SnowflakeClient(config)

    @classmethod
    def _create_postgresql_client(cls) -> PostgreSQLClient:
        config = {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_database,
            "user": settings.postgres_user,
            "password": settings.postgres_password
        }
        return PostgreSQLClient(config)

    @classmethod
    def _create_redshift_client(cls) -> RedshiftClient:
        if not settings.redshift_host:
            raise ValueError("Redshift not configured (REDSHIFT_HOST missing)")

        config = {
            "host": settings.redshift_host,
            "port": settings.redshift_port,
            "database": settings.redshift_database,
            "user": settings.redshift_user,
            "password": settings.redshift_password
        }
        return RedshiftClient(config)

    @classmethod
    def _create_databricks_client(cls) -> DatabricksClient:
        if not settings.databricks_server_hostname:
            raise ValueError("Databricks not configured (DATABRICKS_SERVER_HOSTNAME missing)")

        config = {
            "server_hostname": settings.databricks_server_hostname,
            "http_path": settings.databricks_http_path,
            "access_token": settings.databricks_access_token,
            "catalog": settings.databricks_catalog,
            "schema": settings.databricks_schema
        }
        return DatabricksClient(config)

    @classmethod
    def get_available_databases(cls) -> List[DatabaseType]:
        """Return list of configured databases."""
        available = []

        if settings.google_cloud_project:
            available.append(DatabaseType.BIGQUERY)
        if settings.snowflake_account:
            available.append(DatabaseType.SNOWFLAKE)
        if settings.postgres_host:
            available.append(DatabaseType.POSTGRESQL)
        if settings.redshift_host:
            available.append(DatabaseType.REDSHIFT)
        if settings.databricks_server_hostname:
            available.append(DatabaseType.DATABRICKS)

        return available

    @classmethod
    def clear_cache(cls):
        """Clear client cache (for testing)."""
        cls._clients = {}
```

**Deliverable**: Centralized database client factory

**Testing**: Test client creation for all database types

---

#### Task 5.2: Extend Schema Pipeline for Multi-Database

**File**: `backend/src/pipeline/multi_db_schema_extractor.py` (NEW)

```python
from typing import List, Dict
from src.db.database_factory import DatabaseFactory, DatabaseType
from src.db.base_client import BaseDatabaseClient
import logging

logger = logging.getLogger(__name__)

class MultiDatabaseSchemaExtractor:
    """Extract schemas from all configured databases."""

    def __init__(self):
        self.factory = DatabaseFactory()

    def extract_all_schemas(self) -> Dict[str, List[Dict]]:
        """
        Extract schemas from all available databases.

        Returns:
            {
                "bigquery": [table1, table2, ...],
                "snowflake": [table1, table2, ...],
                ...
            }
        """
        results = {}

        for db_type in self.factory.get_available_databases():
            try:
                logger.info(f"Extracting schema from {db_type.value}")
                client = self.factory.get_client(db_type)
                schema_data = client.get_schema()

                # Add database source to each table
                for table in schema_data.get("tables", []):
                    table["source_database_type"] = db_type.value

                results[db_type.value] = schema_data.get("tables", [])
                logger.info(f"Extracted {len(results[db_type.value])} tables from {db_type.value}")

            except Exception as e:
                logger.error(f"Failed to extract schema from {db_type.value}: {e}")
                results[db_type.value] = []

        return results

    def get_table_count_by_database(self) -> Dict[str, int]:
        """Get table counts across all databases."""
        schemas = self.extract_all_schemas()
        return {db: len(tables) for db, tables in schemas.items()}
```

**Deliverable**: Multi-database schema extraction

**Integration**: Update `PipelineOrchestrator` to use this

---

#### Task 5.3: Update Weaviate Schema Storage

**File**: `backend/src/db/weaviate_client.py` (MODIFY)

Add `source_database` field to table schema:

```python
def create_table_schema(self, table_data: Dict) -> None:
    """Store table schema with source database identifier."""

    properties = {
        "table_name": table_data["name"],
        "dataset": table_data.get("schema", ""),
        "project": table_data.get("database", ""),
        "source_database_type": table_data.get("source_database_type", "bigquery"),  # NEW
        "description": table_data.get("description", ""),
        "columns": json.dumps(table_data.get("columns", [])),
        "row_count": table_data.get("row_count", 0)
    }

    self.client.data_object.create(
        class_name="TableSchema",
        data_object=properties
    )
```

Update Weaviate class definition to include `source_database_type` property.

**Deliverable**: Multi-database aware vector storage

---

### Phase 1 Deliverables Summary

**Code**:
- ✅ Base database client abstraction (`base_client.py`)
- ✅ 5 database clients (BigQuery, Snowflake, PostgreSQL, Redshift, Databricks)
- ✅ Database factory (`database_factory.py`)
- ✅ Multi-DB schema extractor (`multi_db_schema_extractor.py`)
- ✅ Updated Weaviate storage with DB source tracking

**Configuration**:
- ✅ Environment variables for all 5 databases
- ✅ Connection management in `config.py`

**Testing**:
- ✅ Unit tests for base client interface
- ✅ Connection tests for all databases
- ✅ Schema extraction tests
- ✅ Simple query execution tests

**Documentation**:
- ✅ Database setup guides for each platform
- ✅ Configuration examples
- ✅ API documentation

---

## Phase 2: Advanced Cross-Database Features (4-6 weeks)

**Goal**: Enable intelligent cross-database query execution with performance optimization and data movement strategies.

### Week 6-7: Cross-Database Query Architecture

#### Task 6.1: SQL Dialect Translator

**File**: `backend/src/core/sql_dialect_translator.py` (NEW)

```python
from src.db.base_client import SQLDialect
from typing import Dict, Any
import sqlglot

class SQLDialectTranslator:
    """
    Translate SQL between different database dialects.
    Uses sqlglot for AST-based translation.
    """

    DIALECT_MAP = {
        SQLDialect.BIGQUERY: "bigquery",
        SQLDialect.SNOWFLAKE: "snowflake",
        SQLDialect.POSTGRESQL: "postgres",
        SQLDialect.REDSHIFT: "redshift",
        SQLDialect.DATABRICKS: "databricks"
    }

    def translate(
        self,
        sql: str,
        from_dialect: SQLDialect,
        to_dialect: SQLDialect
    ) -> str:
        """
        Translate SQL from one dialect to another.

        Args:
            sql: Source SQL query
            from_dialect: Source database dialect
            to_dialect: Target database dialect

        Returns:
            Translated SQL string
        """
        if from_dialect == to_dialect:
            return sql

        try:
            # Parse SQL using source dialect
            ast = sqlglot.parse_one(
                sql,
                read=self.DIALECT_MAP[from_dialect]
            )

            # Generate SQL using target dialect
            translated = ast.sql(
                dialect=self.DIALECT_MAP[to_dialect],
                pretty=True
            )

            return translated
        except Exception as e:
            raise ValueError(f"SQL translation failed: {e}")

    def get_compatibility_report(
        self,
        sql: str,
        source_dialect: SQLDialect,
        target_dialects: List[SQLDialect]
    ) -> Dict[str, Any]:
        """
        Check SQL compatibility across multiple dialects.

        Returns:
            {
                "snowflake": {"compatible": True, "translation": "..."},
                "postgresql": {"compatible": False, "error": "..."}
            }
        """
        results = {}

        for target_dialect in target_dialects:
            try:
                translated = self.translate(sql, source_dialect, target_dialect)
                results[target_dialect.value] = {
                    "compatible": True,
                    "translation": translated,
                    "error": None
                }
            except Exception as e:
                results[target_dialect.value] = {
                    "compatible": False,
                    "translation": None,
                    "error": str(e)
                }

        return results
```

**Dependencies**:
```
sqlglot>=18.0.0
```

**Deliverable**: SQL dialect translation capability

**Testing**: Translate BigQuery → Snowflake, Snowflake → PostgreSQL, etc.

---

#### Task 6.2: Cross-Database Query Strategy Selector

**File**: `backend/src/core/cross_db_query_strategy.py` (NEW)

```python
from enum import Enum
from typing import List, Dict, Any
from src.db.base_client import DatabaseType

class CrossDBJoinStrategy(Enum):
    """Strategies for executing cross-database queries."""

    IN_MEMORY = "in_memory"  # Fetch both tables, join locally
    STAGING_TABLE = "staging_table"  # Copy smaller table to larger DB
    QUERY_PUSHDOWN = "query_pushdown"  # Push filter to source, then join
    CLOUD_STORAGE = "cloud_storage"  # Export to GCS/S3, load to target
    FEDERATED = "federated"  # Use database federation features

class CrossDBQueryStrategy:
    """
    Determine optimal strategy for cross-database queries.
    """

    # Size thresholds (bytes)
    IN_MEMORY_THRESHOLD = 100 * 1024 * 1024  # 100 MB
    STAGING_TABLE_THRESHOLD = 1 * 1024 * 1024 * 1024  # 1 GB

    def __init__(self):
        pass

    def select_strategy(
        self,
        source_db: DatabaseType,
        target_db: DatabaseType,
        source_table_size: int,
        target_table_size: int,
        query_complexity: str  # "simple", "medium", "complex"
    ) -> CrossDBJoinStrategy:
        """
        Select optimal cross-DB join strategy.

        Decision matrix:
        - Both < 100MB → IN_MEMORY
        - One < 1GB → STAGING_TABLE (copy smaller to larger)
        - Both > 1GB → CLOUD_STORAGE
        - Special: BigQuery + Snowflake → FEDERATED (if available)
        """

        # Strategy 1: In-memory join (both datasets small)
        if (source_table_size < self.IN_MEMORY_THRESHOLD and
            target_table_size < self.IN_MEMORY_THRESHOLD):
            return CrossDBJoinStrategy.IN_MEMORY

        # Strategy 2: Staging table (one dataset small-medium)
        if (source_table_size < self.STAGING_TABLE_THRESHOLD or
            target_table_size < self.STAGING_TABLE_THRESHOLD):
            return CrossDBJoinStrategy.STAGING_TABLE

        # Strategy 3: Cloud storage (both datasets large)
        return CrossDBJoinStrategy.CLOUD_STORAGE

    def estimate_cost(
        self,
        strategy: CrossDBJoinStrategy,
        source_db: DatabaseType,
        target_db: DatabaseType,
        data_size_bytes: int
    ) -> Dict[str, float]:
        """
        Estimate execution cost for a given strategy.

        Returns:
            {
                "execution_cost_usd": 0.05,
                "data_transfer_cost_usd": 0.02,
                "storage_cost_usd": 0.01,
                "total_cost_usd": 0.08
            }
        """
        # Cost estimation logic based on cloud pricing
        # This is a simplified example

        if strategy == CrossDBJoinStrategy.IN_MEMORY:
            return {
                "execution_cost_usd": 0.0,  # Local processing
                "data_transfer_cost_usd": 0.0,
                "storage_cost_usd": 0.0,
                "total_cost_usd": 0.0
            }

        elif strategy == CrossDBJoinStrategy.STAGING_TABLE:
            # Estimate based on data size and target DB costs
            gb = data_size_bytes / (1024 ** 3)
            return {
                "execution_cost_usd": gb * 0.02,  # Query cost
                "data_transfer_cost_usd": gb * 0.09,  # GCP egress
                "storage_cost_usd": gb * 0.02,  # Temporary storage
                "total_cost_usd": gb * 0.13
            }

        elif strategy == CrossDBJoinStrategy.CLOUD_STORAGE:
            gb = data_size_bytes / (1024 ** 3)
            return {
                "execution_cost_usd": gb * 0.05,
                "data_transfer_cost_usd": gb * 0.09,
                "storage_cost_usd": gb * 0.023,  # GCS/S3 storage
                "total_cost_usd": gb * 0.163
            }

        return {"total_cost_usd": 0.0}
```

**Deliverable**: Strategy selection algorithm

**Testing**: Unit tests for strategy selection with various table sizes

---

### Week 8-9: In-Memory and Staging Table Execution

#### Task 8.1: In-Memory Join Executor

**File**: `backend/src/core/cross_db_executors/in_memory_executor.py` (NEW)

```python
import pandas as pd
from typing import List, Dict, Any
from src.db.base_client import BaseDatabaseClient

class InMemoryJoinExecutor:
    """
    Execute cross-database joins in-memory using Pandas.
    Suitable for small-medium datasets (<100MB per table).
    """

    def execute_cross_db_join(
        self,
        left_client: BaseDatabaseClient,
        left_sql: str,
        right_client: BaseDatabaseClient,
        right_sql: str,
        join_type: str,  # "INNER", "LEFT", "RIGHT", "OUTER"
        join_columns: Dict[str, str]  # {"left_col": "right_col"}
    ) -> List[Dict[str, Any]]:
        """
        Execute cross-database join in-memory.

        Steps:
        1. Fetch left dataset
        2. Fetch right dataset
        3. Convert to Pandas DataFrames
        4. Perform join
        5. Return results as list of dicts
        """

        # Fetch both datasets
        left_data = left_client.execute_query(left_sql)
        right_data = right_client.execute_query(right_sql)

        # Convert to DataFrames
        left_df = pd.DataFrame(left_data)
        right_df = pd.DataFrame(right_data)

        # Perform join
        if join_type.upper() == "INNER":
            result_df = pd.merge(
                left_df,
                right_df,
                left_on=list(join_columns.keys()),
                right_on=list(join_columns.values()),
                how="inner"
            )
        elif join_type.upper() == "LEFT":
            result_df = pd.merge(
                left_df,
                right_df,
                left_on=list(join_columns.keys()),
                right_on=list(join_columns.values()),
                how="left"
            )
        # ... other join types

        # Convert back to list of dicts
        return result_df.to_dict(orient="records")
```

**Dependencies**:
```
pandas>=1.5.0
```

**Deliverable**: In-memory join execution

**Testing**: Join BigQuery + Snowflake datasets in-memory

---

#### Task 8.2: Staging Table Manager

**File**: `backend/src/core/cross_db_executors/staging_table_executor.py` (NEW)

```python
from typing import List, Dict, Any
from src.db.base_client import BaseDatabaseClient
import uuid

class StagingTableExecutor:
    """
    Execute cross-database queries using staging tables.

    Strategy:
    1. Identify smaller table
    2. Create temporary table in larger database
    3. Copy data from smaller table
    4. Execute join in larger database
    5. Cleanup staging table
    """

    def execute_with_staging(
        self,
        small_client: BaseDatabaseClient,
        small_sql: str,
        large_client: BaseDatabaseClient,
        large_table: str,
        join_sql_template: str  # SQL with {{staging_table}} placeholder
    ) -> List[Dict[str, Any]]:
        """
        Execute cross-DB query using staging table.
        """

        # Generate unique staging table name
        staging_table = f"temp_staging_{uuid.uuid4().hex[:8]}"

        try:
            # Step 1: Fetch data from smaller database
            small_data = small_client.execute_query(small_sql)

            # Step 2: Create staging table in larger database
            self._create_staging_table(large_client, staging_table, small_data)

            # Step 3: Insert data into staging table
            self._insert_staging_data(large_client, staging_table, small_data)

            # Step 4: Execute join using staging table
            join_sql = join_sql_template.replace("{{staging_table}}", staging_table)
            results = large_client.execute_query(join_sql)

            return results

        finally:
            # Step 5: Cleanup - drop staging table
            try:
                large_client.execute_query(f"DROP TABLE IF EXISTS {staging_table}")
            except Exception as e:
                logger.warning(f"Failed to drop staging table {staging_table}: {e}")

    def _create_staging_table(
        self,
        client: BaseDatabaseClient,
        table_name: str,
        sample_data: List[Dict]
    ):
        """Create staging table based on sample data schema."""
        if not sample_data:
            raise ValueError("Cannot create staging table from empty dataset")

        # Infer schema from first row
        first_row = sample_data[0]
        columns = []

        for col_name, value in first_row.items():
            # Infer SQL type from Python type
            if isinstance(value, int):
                col_type = "BIGINT"
            elif isinstance(value, float):
                col_type = "FLOAT64"
            elif isinstance(value, bool):
                col_type = "BOOLEAN"
            else:
                col_type = "STRING"

            columns.append(f"{col_name} {col_type}")

        create_sql = f"CREATE TEMP TABLE {table_name} ({', '.join(columns)})"
        client.execute_query(create_sql)

    def _insert_staging_data(
        self,
        client: BaseDatabaseClient,
        table_name: str,
        data: List[Dict]
    ):
        """Bulk insert data into staging table."""
        # This is database-specific
        # BigQuery: Use streaming insert or load from JSON
        # Snowflake: Use COPY INTO from staged file
        # For simplicity, use INSERT statements (inefficient for large datasets)

        for row in data:
            columns = list(row.keys())
            values = list(row.values())

            # Create parameterized INSERT
            placeholders = ", ".join(["?" for _ in values])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            client.execute_query(insert_sql, params=values)
```

**Deliverable**: Staging table execution

**Testing**: Copy PostgreSQL table to BigQuery, execute join

---

### Week 10-11: Query Pushdown + Parallel Execution

#### Task 10.1: Query Pushdown Optimizer

**File**: `backend/src/core/query_pushdown_optimizer.py` (NEW)

```python
import sqlglot
from typing import Dict, List

class QueryPushdownOptimizer:
    """
    Optimize cross-database queries by pushing filters/aggregations to source.

    Example:
    Original: SELECT * FROM bigquery.sales JOIN snowflake.customers WHERE customer_id = 123
    Optimized:
        - BigQuery: SELECT * FROM sales WHERE customer_id = 123
        - Snowflake: SELECT * FROM customers WHERE customer_id = 123
        - Join locally
    """

    def analyze_query(self, sql: str) -> Dict[str, Any]:
        """
        Analyze SQL query to identify pushdown opportunities.

        Returns:
            {
                "filters": [{"column": "customer_id", "operator": "=", "value": 123}],
                "aggregations": ["SUM(revenue)"],
                "limit": 100,
                "pushdown_possible": True
            }
        """
        ast = sqlglot.parse_one(sql)

        # Extract WHERE clause filters
        filters = []
        for where in ast.find_all(sqlglot.exp.Where):
            # Parse filter conditions
            # This is simplified - real implementation needs recursive parsing
            filters.append(str(where))

        # Extract aggregations
        aggregations = [str(agg) for agg in ast.find_all(sqlglot.exp.AggFunc)]

        # Extract LIMIT
        limit_clause = ast.find(sqlglot.exp.Limit)
        limit_value = int(limit_clause.expression.this) if limit_clause else None

        return {
            "filters": filters,
            "aggregations": aggregations,
            "limit": limit_value,
            "pushdown_possible": len(filters) > 0 or len(aggregations) > 0
        }

    def push_filters_to_source(
        self,
        source_sql: str,
        filters: List[str]
    ) -> str:
        """
        Add filters to source query.

        Example:
        Input: SELECT * FROM sales
        Filters: ["customer_id = 123", "date >= '2024-01-01'"]
        Output: SELECT * FROM sales WHERE customer_id = 123 AND date >= '2024-01-01'
        """
        ast = sqlglot.parse_one(source_sql)

        # Add WHERE clause with filters
        for filter_str in filters:
            filter_ast = sqlglot.parse_one(f"SELECT * FROM t WHERE {filter_str}").find(sqlglot.exp.Where)
            ast = ast.where(filter_ast.this)

        return ast.sql()
```

**Deliverable**: Query pushdown optimization

**Testing**: Verify filters are pushed to source queries

---

#### Task 10.2: Parallel Query Executor

**File**: `backend/src/core/parallel_query_executor.py` (NEW)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from src.db.base_client import BaseDatabaseClient

class ParallelQueryExecutor:
    """
    Execute multiple database queries in parallel.
    """

    def __init__(self, max_workers: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute_parallel(
        self,
        queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in parallel.

        Args:
            queries: [
                {"client": bigquery_client, "sql": "SELECT ...", "id": "bq_query"},
                {"client": snowflake_client, "sql": "SELECT ...", "id": "sf_query"}
            ]

        Returns:
            [
                {"id": "bq_query", "results": [...], "duration_ms": 123},
                {"id": "sf_query", "results": [...], "duration_ms": 456}
            ]
        """
        loop = asyncio.get_event_loop()

        async def execute_single(query_config):
            client = query_config["client"]
            sql = query_config["sql"]
            query_id = query_config["id"]

            import time
            start = time.time()

            # Execute in thread pool (since clients are sync)
            results = await loop.run_in_executor(
                self.executor,
                client.execute_query,
                sql
            )

            duration_ms = (time.time() - start) * 1000

            return {
                "id": query_id,
                "results": results,
                "duration_ms": duration_ms,
                "row_count": len(results)
            }

        # Execute all queries concurrently
        tasks = [execute_single(q) for q in queries]
        results = await asyncio.gather(*tasks)

        return results
```

**Deliverable**: Parallel query execution

**Testing**: Execute 3 queries (BigQuery, Snowflake, PostgreSQL) in parallel

---

### Week 11-12: Cloud Storage Integration

#### Task 11.1: Cloud Storage Transfer Manager

**File**: `backend/src/core/cloud_storage_transfer.py` (NEW)

```python
from google.cloud import storage as gcs_storage
import boto3
from typing import List, Dict, Any
import json

class CloudStorageTransfer:
    """
    Handle large dataset transfers via cloud storage.

    Workflow:
    1. Export source table to GCS/S3
    2. Load from GCS/S3 into target database
    3. Execute query in target database
    4. Cleanup temporary files
    """

    def __init__(self):
        self.gcs_client = gcs_storage.Client()
        self.s3_client = boto3.client('s3')

    def export_to_gcs(
        self,
        source_client: BaseDatabaseClient,
        source_sql: str,
        gcs_bucket: str,
        gcs_path: str
    ) -> str:
        """
        Export query results to Google Cloud Storage.

        Returns:
            GCS URI (gs://bucket/path)
        """
        # Execute query
        results = source_client.execute_query(source_sql)

        # Convert to newline-delimited JSON
        ndjson_data = "\n".join([json.dumps(row) for row in results])

        # Upload to GCS
        bucket = self.gcs_client.bucket(gcs_bucket)
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(ndjson_data, content_type="application/json")

        gcs_uri = f"gs://{gcs_bucket}/{gcs_path}"
        logger.info(f"Exported {len(results)} rows to {gcs_uri}")
        return gcs_uri

    def load_from_gcs_to_bigquery(
        self,
        bigquery_client,
        gcs_uri: str,
        target_table: str
    ):
        """Load data from GCS into BigQuery."""
        from google.cloud import bigquery

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )

        load_job = bigquery_client.client.load_table_from_uri(
            gcs_uri,
            target_table,
            job_config=job_config
        )

        load_job.result()  # Wait for completion
        logger.info(f"Loaded {load_job.output_rows} rows into {target_table}")

    def load_from_s3_to_snowflake(
        self,
        snowflake_client,
        s3_uri: str,
        target_table: str
    ):
        """Load data from S3 into Snowflake."""
        copy_sql = f"""
        COPY INTO {target_table}
        FROM '{s3_uri}'
        FILE_FORMAT = (TYPE = 'JSON')
        ON_ERROR = 'ABORT_STATEMENT'
        """

        snowflake_client.execute_query(copy_sql)
        logger.info(f"Loaded data from {s3_uri} into {target_table}")
```

**Dependencies**:
```
google-cloud-storage>=2.10.0
boto3>=1.28.0
```

**Deliverable**: Cloud storage transfer capability

**Testing**: Export BigQuery → GCS, load GCS → Snowflake

---

### Phase 2 Deliverables Summary

**Code**:
- ✅ SQL dialect translator (`sql_dialect_translator.py`)
- ✅ Cross-DB strategy selector (`cross_db_query_strategy.py`)
- ✅ In-memory join executor
- ✅ Staging table executor
- ✅ Query pushdown optimizer
- ✅ Parallel query executor
- ✅ Cloud storage transfer manager

**Capabilities**:
- ✅ Execute queries across any 2 databases
- ✅ Intelligent strategy selection (in-memory vs staging vs cloud)
- ✅ Cost estimation for cross-DB queries
- ✅ Performance optimization via pushdown

**Testing**:
- ✅ Cross-DB join tests (all combinations)
- ✅ Performance benchmarks
- ✅ Cost estimation validation

---

## Phase 3: Production Hardening (4-6 weeks)

**Goal**: Production-grade reliability, monitoring, cost optimization, and materialized view abstraction.

### Week 13-14: Materialized View Abstraction Layer

#### Task 13.1: Base Materialized View Interface

**File**: `backend/src/optimization/base_mv_client.py` (NEW)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

class MVRefreshMode(Enum):
    MANUAL = "manual"
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    INCREMENTAL = "incremental"

class BaseMaterializedViewClient(ABC):
    """
    Abstract base class for materialized view management.
    Provides database-agnostic MV operations.
    """

    @abstractmethod
    def create_mv(
        self,
        mv_name: str,
        query: str,
        refresh_mode: MVRefreshMode = MVRefreshMode.MANUAL,
        refresh_interval_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create materialized view.

        Returns:
            {
                "mv_name": str,
                "status": "created",
                "size_bytes": int,
                "last_refresh": datetime
            }
        """
        pass

    @abstractmethod
    def refresh_mv(self, mv_name: str, incremental: bool = False) -> Dict[str, Any]:
        """
        Refresh materialized view.

        Returns:
            {
                "status": "refreshed",
                "rows_updated": int,
                "duration_seconds": float
            }
        """
        pass

    @abstractmethod
    def drop_mv(self, mv_name: str) -> bool:
        """Drop materialized view."""
        pass

    @abstractmethod
    def list_mvs(self) -> List[Dict[str, Any]]:
        """
        List all materialized views.

        Returns:
            [
                {
                    "name": str,
                    "size_bytes": int,
                    "last_refresh": datetime,
                    "refresh_mode": str
                }
            ]
        """
        pass

    @abstractmethod
    def get_mv_info(self, mv_name: str) -> Dict[str, Any]:
        """Get detailed MV metadata."""
        pass
```

**Deliverable**: Base MV interface

---

#### Task 13.2: Database-Specific MV Implementations

**BigQuery Materialized Views**:

```python
# backend/src/optimization/bigquery_mv_client.py

class BigQueryMVClient(BaseMaterializedViewClient):
    """BigQuery materialized view management."""

    def create_mv(self, mv_name, query, refresh_mode, refresh_interval_hours):
        """
        BigQuery MVs are always auto-refreshing.
        """
        create_sql = f"CREATE MATERIALIZED VIEW {mv_name} AS {query}"

        if refresh_interval_hours:
            # BigQuery doesn't support custom intervals
            # MVs refresh automatically based on base table changes
            pass

        self.client.query(create_sql).result()

        return {"mv_name": mv_name, "status": "created"}

    def refresh_mv(self, mv_name, incremental=False):
        """BigQuery MVs refresh automatically - manual refresh not needed."""
        # Can't manually refresh BigQuery MVs
        return {"status": "auto-refresh", "note": "BigQuery MVs refresh automatically"}
```

**Snowflake Materialized Views**:

```python
# backend/src/optimization/snowflake_mv_client.py

class SnowflakeMVClient(BaseMaterializedViewClient):
    """Snowflake materialized view management."""

    def create_mv(self, mv_name, query, refresh_mode, refresh_interval_hours):
        """
        Snowflake MVs require manual refresh or use dynamic tables.
        """
        if refresh_mode == MVRefreshMode.SCHEDULED:
            # Use dynamic table (Snowflake's auto-refreshing MV)
            create_sql = f"""
            CREATE DYNAMIC TABLE {mv_name}
            TARGET_LAG = '{refresh_interval_hours} hours'
            WAREHOUSE = compute_wh
            AS {query}
            """
        else:
            # Standard materialized view (manual refresh)
            create_sql = f"CREATE MATERIALIZED VIEW {mv_name} AS {query}"

        self.connection.cursor().execute(create_sql)
        return {"mv_name": mv_name, "status": "created"}

    def refresh_mv(self, mv_name, incremental=False):
        """Manually refresh Snowflake MV."""
        # Snowflake doesn't have REFRESH - need to recreate or use tasks
        refresh_sql = f"""
        CREATE OR REPLACE MATERIALIZED VIEW {mv_name} AS
        SELECT * FROM {mv_name}_base
        """

        start = time.time()
        self.connection.cursor().execute(refresh_sql)
        duration = time.time() - start

        return {"status": "refreshed", "duration_seconds": duration}
```

**Deliverable**: MV implementations for all 5 databases

**Testing**: Create, refresh, drop MVs on all platforms

---

### Week 15: Cost Tracking and Optimization

#### Task 15.1: Cost Tracking System

**File**: `backend/src/monitoring/cost_tracker.py` (NEW)

```python
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json

class CostTracker:
    """
    Track query execution costs across all databases.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.COST_PREFIX = "cost:query:"

    def record_query_cost(
        self,
        query_id: str,
        database_type: str,
        cost_breakdown: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        """
        Record query cost.

        Args:
            query_id: Unique query identifier
            database_type: "bigquery", "snowflake", etc.
            cost_breakdown: {
                "execution_cost_usd": 0.05,
                "data_transfer_cost_usd": 0.02,
                "storage_cost_usd": 0.01
            }
            metadata: {
                "sql": "SELECT ...",
                "duration_ms": 1234,
                "bytes_processed": 1000000,
                "user": "user@example.com"
            }
        """
        cost_record = {
            "query_id": query_id,
            "database_type": database_type,
            "timestamp": datetime.now().isoformat(),
            "cost_breakdown": cost_breakdown,
            "total_cost_usd": sum(cost_breakdown.values()),
            "metadata": metadata
        }

        # Store in Redis with 90-day TTL
        key = f"{self.COST_PREFIX}{query_id}"
        self.redis.setex(key, 90 * 24 * 60 * 60, json.dumps(cost_record))

        # Also add to daily aggregate
        self._update_daily_aggregate(database_type, cost_record["total_cost_usd"])

    def _update_daily_aggregate(self, database_type: str, cost: float):
        """Update daily cost aggregates."""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"cost:daily:{database_type}:{today}"

        # Increment daily cost
        self.redis.incrbyfloat(key, cost)
        self.redis.expire(key, 90 * 24 * 60 * 60)  # 90-day TTL

    def get_daily_costs(
        self,
        start_date: datetime,
        end_date: datetime,
        database_type: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get daily cost breakdown.

        Returns:
            {
                "2024-11-01": 12.34,
                "2024-11-02": 15.67,
                ...
            }
        """
        costs = {}
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")

            if database_type:
                key = f"cost:daily:{database_type}:{date_str}"
                cost = self.redis.get(key)
                costs[date_str] = float(cost) if cost else 0.0
            else:
                # Aggregate across all databases
                total = 0.0
                for db in ["bigquery", "snowflake", "postgresql", "redshift", "databricks"]:
                    key = f"cost:daily:{db}:{date_str}"
                    cost = self.redis.get(key)
                    total += float(cost) if cost else 0.0
                costs[date_str] = total

            current_date += timedelta(days=1)

        return costs

    def get_most_expensive_queries(
        self,
        limit: int = 10,
        database_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get top N most expensive queries."""
        # Scan all cost records
        pattern = f"{self.COST_PREFIX}*"
        expensive_queries = []

        for key in self.redis.scan_iter(match=pattern):
            cost_data = json.loads(self.redis.get(key))

            if database_type and cost_data["database_type"] != database_type:
                continue

            expensive_queries.append(cost_data)

        # Sort by total cost descending
        expensive_queries.sort(key=lambda x: x["total_cost_usd"], reverse=True)

        return expensive_queries[:limit]
```

**Deliverable**: Cost tracking and reporting

**Testing**: Record costs, generate reports

---

#### Task 15.2: Cost Optimization Advisor

**File**: `backend/src/monitoring/cost_optimizer.py` (NEW)

```python
class CostOptimizationAdvisor:
    """
    Analyze query patterns and suggest cost optimizations.
    """

    def analyze_query_costs(
        self,
        cost_tracker: CostTracker,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze costs and provide recommendations.

        Returns:
            {
                "total_cost_usd": 456.78,
                "cost_by_database": {...},
                "optimization_opportunities": [
                    {
                        "type": "cache_candidate",
                        "query": "SELECT ...",
                        "current_cost_per_execution": 0.50,
                        "execution_count": 100,
                        "total_cost": 50.00,
                        "recommendation": "Cache this query - executed 100 times"
                    },
                    {
                        "type": "mv_candidate",
                        "query": "SELECT ...",
                        "current_cost": 5.00,
                        "execution_count": 50,
                        "recommendation": "Create materialized view - expensive and frequent"
                    }
                ],
                "estimated_savings_usd": 125.00
            }
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get expensive queries
        expensive = cost_tracker.get_most_expensive_queries(limit=100)

        opportunities = []

        # Identify cache candidates (frequent queries)
        query_frequency = {}
        for query_cost in expensive:
            sql = query_cost["metadata"]["sql"]
            if sql not in query_frequency:
                query_frequency[sql] = {"count": 0, "total_cost": 0.0}
            query_frequency[sql]["count"] += 1
            query_frequency[sql]["total_cost"] += query_cost["total_cost_usd"]

        # Find queries executed > 10 times
        for sql, stats in query_frequency.items():
            if stats["count"] > 10:
                opportunities.append({
                    "type": "cache_candidate",
                    "query": sql[:100] + "...",
                    "current_cost_per_execution": stats["total_cost"] / stats["count"],
                    "execution_count": stats["count"],
                    "total_cost": stats["total_cost"],
                    "recommendation": f"Cache this query - executed {stats['count']} times, cost ${stats['total_cost']:.2f}",
                    "estimated_savings": stats["total_cost"] * 0.9  # 90% savings from caching
                })

        # Estimate total savings
        total_savings = sum(opp["estimated_savings"] for opp in opportunities)

        return {
            "total_cost_usd": sum(q["total_cost_usd"] for q in expensive),
            "optimization_opportunities": opportunities,
            "estimated_savings_usd": total_savings
        }
```

**Deliverable**: Cost optimization recommendations

**Testing**: Generate recommendations from sample cost data

---

### Week 16: Advanced Monitoring and Observability

#### Task 16.1: Multi-Database Metrics Collector

**File**: `backend/src/monitoring/metrics_collector.py` (NEW)

```python
from dataclasses import dataclass
from typing import Dict, List
import time

@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    query_id: str
    database_type: str
    sql: str
    duration_ms: float
    bytes_processed: int
    rows_returned: int
    cost_usd: float
    cache_hit: bool
    error: Optional[str] = None

class MetricsCollector:
    """
    Collect and aggregate query metrics across all databases.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.METRICS_PREFIX = "metrics:query:"

    def record_query_metrics(self, metrics: QueryMetrics):
        """Record query execution metrics."""
        metrics_dict = {
            "query_id": metrics.query_id,
            "database_type": metrics.database_type,
            "sql": metrics.sql[:500],  # Truncate long queries
            "duration_ms": metrics.duration_ms,
            "bytes_processed": metrics.bytes_processed,
            "rows_returned": metrics.rows_returned,
            "cost_usd": metrics.cost_usd,
            "cache_hit": metrics.cache_hit,
            "error": metrics.error,
            "timestamp": datetime.now().isoformat()
        }

        # Store individual metric
        key = f"{self.METRICS_PREFIX}{metrics.query_id}"
        self.redis.setex(key, 30 * 24 * 60 * 60, json.dumps(metrics_dict))

        # Update aggregates
        self._update_aggregates(metrics)

    def _update_aggregates(self, metrics: QueryMetrics):
        """Update aggregate metrics."""
        hour_key = datetime.now().strftime("%Y-%m-%d-%H")

        # Database-specific aggregates
        db_prefix = f"metrics:agg:{metrics.database_type}:{hour_key}"

        # Increment query count
        self.redis.incr(f"{db_prefix}:query_count")

        # Add to duration sum (for average calculation)
        self.redis.incrbyfloat(f"{db_prefix}:duration_sum", metrics.duration_ms)

        # Track errors
        if metrics.error:
            self.redis.incr(f"{db_prefix}:error_count")

        # Track cache hits
        if metrics.cache_hit:
            self.redis.incr(f"{db_prefix}:cache_hit_count")

        # Set TTL on aggregate keys
        for key in [
            f"{db_prefix}:query_count",
            f"{db_prefix}:duration_sum",
            f"{db_prefix}:error_count",
            f"{db_prefix}:cache_hit_count"
        ]:
            self.redis.expire(key, 90 * 24 * 60 * 60)

    def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Get real-time performance metrics.

        Returns:
            {
                "overall": {
                    "queries_per_hour": 1234,
                    "avg_duration_ms": 567,
                    "cache_hit_rate": 0.75,
                    "error_rate": 0.02
                },
                "by_database": {
                    "bigquery": {...},
                    "snowflake": {...}
                },
                "slow_queries": [...]
            }
        """
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")

        overall_metrics = {
            "queries_per_hour": 0,
            "avg_duration_ms": 0,
            "cache_hit_rate": 0,
            "error_rate": 0
        }

        by_database = {}

        for db in ["bigquery", "snowflake", "postgresql", "redshift", "databricks"]:
            prefix = f"metrics:agg:{db}:{current_hour}"

            query_count = int(self.redis.get(f"{prefix}:query_count") or 0)
            duration_sum = float(self.redis.get(f"{prefix}:duration_sum") or 0)
            error_count = int(self.redis.get(f"{prefix}:error_count") or 0)
            cache_hit_count = int(self.redis.get(f"{prefix}:cache_hit_count") or 0)

            if query_count > 0:
                db_metrics = {
                    "query_count": query_count,
                    "avg_duration_ms": duration_sum / query_count,
                    "error_rate": error_count / query_count,
                    "cache_hit_rate": cache_hit_count / query_count
                }

                by_database[db] = db_metrics

                # Update overall
                overall_metrics["queries_per_hour"] += query_count
                overall_metrics["avg_duration_ms"] += duration_sum

        # Calculate overall averages
        if overall_metrics["queries_per_hour"] > 0:
            overall_metrics["avg_duration_ms"] /= overall_metrics["queries_per_hour"]

        return {
            "overall": overall_metrics,
            "by_database": by_database,
            "timestamp": datetime.now().isoformat()
        }
```

**Deliverable**: Comprehensive metrics collection

**Integration**: Add to all query execution paths

---

#### Task 16.2: Health Check and Alerting

**File**: `backend/src/monitoring/health_checker.py` (NEW)

```python
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class DatabaseHealthChecker:
    """Monitor health of all database connections."""

    def __init__(self, database_factory):
        self.factory = database_factory

    def check_all_databases(self) -> Dict[str, Any]:
        """
        Check health of all configured databases.

        Returns:
            {
                "overall_status": "healthy",
                "databases": {
                    "bigquery": {
                        "status": "healthy",
                        "latency_ms": 123,
                        "last_check": "2024-11-16T12:00:00"
                    },
                    ...
                }
            }
        """
        results = {}
        unhealthy_count = 0

        for db_type in self.factory.get_available_databases():
            try:
                client = self.factory.get_client(db_type)

                # Test connectivity with latency measurement
                start = time.time()
                is_connected = client.test_connection()
                latency_ms = (time.time() - start) * 1000

                if is_connected:
                    status = HealthStatus.HEALTHY if latency_ms < 1000 else HealthStatus.DEGRADED
                else:
                    status = HealthStatus.UNHEALTHY
                    unhealthy_count += 1

                results[db_type.value] = {
                    "status": status.value,
                    "latency_ms": latency_ms,
                    "last_check": datetime.now().isoformat()
                }

            except Exception as e:
                results[db_type.value] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                unhealthy_count += 1

        # Determine overall status
        if unhealthy_count == 0:
            overall_status = HealthStatus.HEALTHY
        elif unhealthy_count < len(results):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY

        return {
            "overall_status": overall_status.value,
            "databases": results,
            "timestamp": datetime.now().isoformat()
        }
```

**API Endpoint**: `GET /api/v1/health/databases`

**Deliverable**: Health monitoring system

**Testing**: Simulate database failures, verify alerts

---

### Week 17: Auto-Scaling and Resource Management

#### Task 17.1: Query Queue Manager

**File**: `backend/src/core/query_queue_manager.py` (NEW)

```python
import asyncio
from queue import PriorityQueue
from typing import Dict, Any

class QueryPriority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1
    CRITICAL = 0

class QueryQueueManager:
    """
    Manage query execution queue with priority and concurrency limits.
    """

    def __init__(self, max_concurrent_queries: int = 10):
        self.max_concurrent = max_concurrent_queries
        self.queue = PriorityQueue()
        self.active_queries = {}
        self.semaphore = asyncio.Semaphore(max_concurrent_queries)

    async def submit_query(
        self,
        query_id: str,
        client: BaseDatabaseClient,
        sql: str,
        priority: QueryPriority = QueryPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Submit query for execution with priority.

        Returns query results when execution completes.
        """
        # Add to queue
        self.queue.put((priority.value, query_id, client, sql))

        # Wait for execution slot
        async with self.semaphore:
            # Execute query
            results = await self._execute_query(query_id, client, sql)
            return results

    async def _execute_query(
        self,
        query_id: str,
        client: BaseDatabaseClient,
        sql: str
    ) -> Dict[str, Any]:
        """Execute query and track status."""
        self.active_queries[query_id] = {
            "status": "running",
            "start_time": datetime.now()
        }

        try:
            # Execute in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                client.execute_query,
                sql
            )

            self.active_queries[query_id]["status"] = "completed"
            return {"status": "success", "results": results}

        except Exception as e:
            self.active_queries[query_id]["status"] = "failed"
            return {"status": "error", "error": str(e)}

        finally:
            # Cleanup
            del self.active_queries[query_id]

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "queue_size": self.queue.qsize(),
            "active_queries": len(self.active_queries),
            "max_concurrent": self.max_concurrent,
            "available_slots": self.max_concurrent - len(self.active_queries)
        }
```

**Deliverable**: Query queue management

**Testing**: Submit 100 queries, verify concurrency limits

---

### Phase 3 Deliverables Summary

**Code**:
- ✅ Materialized view abstraction layer
- ✅ Cost tracking and optimization advisor
- ✅ Advanced metrics collection
- ✅ Health monitoring and alerting
- ✅ Query queue management

**Monitoring**:
- ✅ Real-time performance dashboard
- ✅ Cost breakdown by database
- ✅ Health status for all databases
- ✅ Query queue visibility

**Production Features**:
- ✅ Auto-scaling query execution
- ✅ Cost optimization recommendations
- ✅ Comprehensive observability

---

## Risk Assessment and Mitigation

### High-Risk Areas

**Risk 1: Cross-Database Query Performance**
- **Impact**: HIGH - Slow cross-DB joins could make system unusable
- **Mitigation**:
  - Implement aggressive query pushdown
  - Cache cross-DB query results
  - Provide cost estimates before execution
  - Add query timeouts

**Risk 2: Database-Specific SQL Dialects**
- **Impact**: MEDIUM - SQL translation errors could cause query failures
- **Mitigation**:
  - Use sqlglot library (battle-tested)
  - Extensive testing for all dialect pairs
  - Fallback to database-specific SQL generation

**Risk 3: Data Transfer Costs**
- **Impact**: HIGH - Large cross-DB transfers could be expensive
- **Mitigation**:
  - Strategy selector prevents expensive operations
  - Cost warnings before execution
  - Query result size limits
  - Monitoring and alerts

**Risk 4: Authentication and Credentials**
- **Impact**: MEDIUM - Managing 5 database credentials
- **Mitigation**:
  - Use environment variables
  - Support for secret management services (GCP Secret Manager, AWS Secrets Manager)
  - Credential rotation procedures

---

## Success Metrics

### Phase 1 Success Criteria
- ✅ All 5 database clients pass connection tests
- ✅ Schema extraction works for all databases
- ✅ Simple queries execute successfully on all platforms
- ✅ Vector storage includes database source

### Phase 2 Success Criteria
- ✅ Cross-database queries execute in <30s (for small datasets)
- ✅ Strategy selector chooses optimal approach 95%+ of time
- ✅ Cost estimates within 20% of actual costs
- ✅ Parallel execution 3x faster than sequential

### Phase 3 Success Criteria
- ✅ 99.9% uptime for all database connections
- ✅ Cost optimization identifies 20%+ savings opportunities
- ✅ Query queue prevents system overload
- ✅ Materialized views reduce query costs by 50%+

---

## Testing Strategy

### Unit Tests
- Database client interface compliance
- SQL dialect translation
- Strategy selection logic
- Cost estimation accuracy

### Integration Tests
- End-to-end query execution (all databases)
- Cross-database joins (all combinations)
- Schema pipeline with multiple databases
- Cache integration with multi-DB

### Performance Tests
- Query execution benchmarks
- Cross-DB join performance
- Parallel execution scaling
- Large dataset transfers

### Cost Tests
- Track costs for representative workload
- Validate cost estimates vs actuals
- Test cost optimization recommendations

---

## Rollout Plan

### Phase 1 Rollout (Week 5)
1. Deploy to staging environment
2. Test all database connections
3. Run schema pipeline
4. Execute 100 test queries per database
5. Monitor for errors

### Phase 2 Rollout (Week 12)
1. Enable cross-DB queries for internal users
2. Monitor performance and costs
3. Collect feedback on strategy selection
4. Tune thresholds based on real usage

### Phase 3 Rollout (Week 17)
1. Enable production monitoring
2. Activate cost tracking
3. Deploy health checks
4. Launch query queue
5. Full production release

---

## Appendix A: Environment Variables

```bash
# === BigQuery ===
GOOGLE_CLOUD_PROJECT=your-project
BIGQUERY_DATASET=your-dataset
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json
BIGQUERY_QUERY_TIMEOUT_SECONDS=60

# === Snowflake ===
SNOWFLAKE_ACCOUNT=your-account.snowflakecomputing.com
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# === PostgreSQL ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your-database
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password

# === Redshift ===
REDSHIFT_HOST=your-cluster.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=your-database
REDSHIFT_USER=your-user
REDSHIFT_PASSWORD=your-password

# === Databricks ===
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=your-access-token
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=default

# === Cloud Storage ===
GCS_BUCKET=your-gcs-bucket
S3_BUCKET=your-s3-bucket
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

---

## Appendix B: Dependencies

```txt
# Phase 1 Dependencies
snowflake-connector-python>=3.0.0
psycopg2-binary>=2.9.0
databricks-sql-connector>=2.0.0

# Phase 2 Dependencies
sqlglot>=18.0.0
pandas>=1.5.0
google-cloud-storage>=2.10.0
boto3>=1.28.0

# Phase 3 Dependencies
prometheus-client>=0.17.0  # For metrics export
```

---

## Document Version

- **Version**: 1.0
- **Date**: 2025-11-16
- **Author**: Mantrix Axis AI Team
- **Status**: APPROVED FOR IMPLEMENTATION

---

**END OF IMPLEMENTATION PLAN**
