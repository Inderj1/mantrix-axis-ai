"""
Database Capabilities

Defines what features and capabilities each database supports.
This allows the SQL generator to adapt its output based on the target database.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseCapabilities:
    """
    Defines the capabilities and features supported by a database.

    This allows the SQL generator and query optimizer to adapt their behavior
    based on what the target database supports.
    """

    # Database identification
    database_type: str  # e.g., "bigquery", "snowflake", "postgresql", "redshift", "databricks"
    database_name: str  # Human-readable name

    # SQL dialect features
    supports_ctes: bool = True  # Common Table Expressions (WITH clause)
    supports_window_functions: bool = True  # ROW_NUMBER(), RANK(), etc.
    supports_recursive_ctes: bool = False  # Recursive CTEs
    supports_lateral_joins: bool = False  # LATERAL keyword
    supports_full_outer_join: bool = True  # FULL OUTER JOIN

    # Data type support
    supports_arrays: bool = False  # Array/list data types
    supports_json: bool = True  # JSON data type and functions
    supports_struct: bool = False  # Struct/record types

    # Function support
    date_format_function: str = "FORMAT_DATE"  # e.g., FORMAT_DATE, TO_CHAR, DATE_FORMAT
    string_concat_operator: str = "||"  # e.g., ||, CONCAT, +
    case_insensitive_comparison: bool = False  # Native case-insensitive string comparison

    # Query optimization
    requires_table_qualification: bool = False  # Must qualify tables with dataset/schema
    table_qualification_format: Optional[str] = None  # e.g., "`project.dataset.table`"
    supports_query_hints: bool = False  # Query optimization hints

    # Execution limits
    max_query_timeout_seconds: int = 600  # Maximum query timeout
    max_result_size_mb: int = 10240  # Maximum result size (10GB default)
    supports_pagination: bool = True  # Native pagination support
    pagination_method: str = "limit_offset"  # "limit_offset", "cursor", "page_token"

    # Cost/Performance
    supports_cost_estimation: bool = False  # Can estimate query cost before execution
    supports_dry_run: bool = False  # Can validate queries without executing
    supports_query_cache: bool = True  # Native query result caching

    # Metadata
    supports_information_schema: bool = True  # Has INFORMATION_SCHEMA
    supports_system_tables: bool = True  # Has system catalog tables

    # Authentication
    supports_service_accounts: bool = True  # Supports service account authentication
    supports_user_credentials: bool = True  # Supports user-based authentication

    # Special features
    supports_federated_queries: bool = False  # Can query external data sources
    supports_user_defined_functions: bool = False  # UDFs
    supports_stored_procedures: bool = False  # Stored procedures


# Predefined capabilities for each database type

BIGQUERY_CAPABILITIES = DatabaseCapabilities(
    database_type="bigquery",
    database_name="Google BigQuery",

    # SQL dialect
    supports_ctes=True,
    supports_window_functions=True,
    supports_recursive_ctes=True,
    supports_lateral_joins=False,
    supports_full_outer_join=True,

    # Data types
    supports_arrays=True,
    supports_json=True,
    supports_struct=True,

    # Functions
    date_format_function="FORMAT_DATE",
    string_concat_operator="||",
    case_insensitive_comparison=False,

    # Query optimization
    requires_table_qualification=True,
    table_qualification_format="`{project}.{dataset}.{table}`",
    supports_query_hints=False,

    # Limits
    max_query_timeout_seconds=600,
    max_result_size_mb=10240,
    supports_pagination=True,
    pagination_method="page_token",

    # Cost/Performance
    supports_cost_estimation=True,
    supports_dry_run=True,
    supports_query_cache=True,

    # Metadata
    supports_information_schema=True,
    supports_system_tables=True,

    # Auth
    supports_service_accounts=True,
    supports_user_credentials=True,

    # Special
    supports_federated_queries=True,
    supports_user_defined_functions=True,
    supports_stored_procedures=True,
)


POSTGRESQL_CAPABILITIES = DatabaseCapabilities(
    database_type="postgresql",
    database_name="PostgreSQL",

    # SQL dialect
    supports_ctes=True,
    supports_window_functions=True,
    supports_recursive_ctes=True,
    supports_lateral_joins=True,
    supports_full_outer_join=True,

    # Data types
    supports_arrays=True,
    supports_json=True,
    supports_struct=False,

    # Functions
    date_format_function="TO_CHAR",
    string_concat_operator="||",
    case_insensitive_comparison=True,  # ILIKE operator

    # Query optimization
    requires_table_qualification=False,  # Optional but supported
    table_qualification_format="{schema}.{table}",
    supports_query_hints=False,

    # Limits
    max_query_timeout_seconds=3600,
    max_result_size_mb=None,  # No hard limit
    supports_pagination=True,
    pagination_method="limit_offset",

    # Cost/Performance
    supports_cost_estimation=True,
    supports_dry_run=False,
    supports_query_cache=False,

    # Metadata
    supports_information_schema=True,
    supports_system_tables=True,

    # Auth
    supports_service_accounts=False,
    supports_user_credentials=True,

    # Special
    supports_federated_queries=True,  # Via foreign data wrappers
    supports_user_defined_functions=True,
    supports_stored_procedures=True,
)


SNOWFLAKE_CAPABILITIES = DatabaseCapabilities(
    database_type="snowflake",
    database_name="Snowflake",

    # SQL dialect
    supports_ctes=True,
    supports_window_functions=True,
    supports_recursive_ctes=True,
    supports_lateral_joins=True,
    supports_full_outer_join=True,

    # Data types
    supports_arrays=True,
    supports_json=True,
    supports_struct=True,  # OBJECT and VARIANT types

    # Functions
    date_format_function="TO_CHAR",
    string_concat_operator="||",
    case_insensitive_comparison=False,

    # Query optimization
    requires_table_qualification=True,
    table_qualification_format="{database}.{schema}.{table}",
    supports_query_hints=True,

    # Limits
    max_query_timeout_seconds=7200,
    max_result_size_mb=None,
    supports_pagination=True,
    pagination_method="limit_offset",

    # Cost/Performance
    supports_cost_estimation=False,
    supports_dry_run=False,
    supports_query_cache=True,

    # Metadata
    supports_information_schema=True,
    supports_system_tables=True,

    # Auth
    supports_service_accounts=True,
    supports_user_credentials=True,

    # Special
    supports_federated_queries=True,
    supports_user_defined_functions=True,
    supports_stored_procedures=True,
)


REDSHIFT_CAPABILITIES = DatabaseCapabilities(
    database_type="redshift",
    database_name="Amazon Redshift",

    # SQL dialect
    supports_ctes=True,
    supports_window_functions=True,
    supports_recursive_ctes=False,
    supports_lateral_joins=True,  # Redshift supports LATERAL JOIN
    supports_full_outer_join=True,

    # Data types
    supports_arrays=False,  # Redshift doesn't support native PostgreSQL arrays
    supports_json=True,  # SUPER type for JSON
    supports_struct=False,  # Limited support via SUPER type

    # Functions
    date_format_function="TO_CHAR",
    string_concat_operator="||",
    case_insensitive_comparison=True,  # ILIKE operator

    # Query optimization
    requires_table_qualification=False,  # Optional but supported
    table_qualification_format="{schema}.{table}",
    supports_query_hints=False,

    # Limits
    max_query_timeout_seconds=86400,  # 24 hours
    max_result_size_mb=None,
    supports_pagination=True,
    pagination_method="limit_offset",

    # Cost/Performance
    supports_cost_estimation=False,
    supports_dry_run=False,
    supports_query_cache=True,

    # Metadata
    supports_information_schema=True,
    supports_system_tables=True,

    # Auth
    supports_service_accounts=True,
    supports_user_credentials=True,

    # Special
    supports_federated_queries=True,
    supports_user_defined_functions=True,
    supports_stored_procedures=True,
)


DATABRICKS_CAPABILITIES = DatabaseCapabilities(
    database_type="databricks",
    database_name="Databricks SQL",

    # SQL dialect (Spark SQL)
    supports_ctes=True,
    supports_window_functions=True,
    supports_recursive_ctes=False,
    supports_lateral_joins=True,
    supports_full_outer_join=True,

    # Data types
    supports_arrays=True,
    supports_json=True,
    supports_struct=True,

    # Functions
    date_format_function="DATE_FORMAT",
    string_concat_operator="||",
    case_insensitive_comparison=False,

    # Query optimization
    requires_table_qualification=True,  # Unity Catalog uses three-part names
    table_qualification_format="{catalog}.{schema}.{table}",
    supports_query_hints=True,

    # Limits
    max_query_timeout_seconds=3600,
    max_result_size_mb=None,
    supports_pagination=True,
    pagination_method="limit_offset",

    # Cost/Performance
    supports_cost_estimation=False,
    supports_dry_run=False,
    supports_query_cache=True,

    # Metadata
    supports_information_schema=True,
    supports_system_tables=True,

    # Auth
    supports_service_accounts=True,
    supports_user_credentials=True,

    # Special
    supports_federated_queries=True,
    supports_user_defined_functions=True,
    supports_stored_procedures=False,
)


# Map database types to their capabilities
CAPABILITIES_MAP = {
    "bigquery": BIGQUERY_CAPABILITIES,
    "postgresql": POSTGRESQL_CAPABILITIES,
    "snowflake": SNOWFLAKE_CAPABILITIES,
    "redshift": REDSHIFT_CAPABILITIES,
    "databricks": DATABRICKS_CAPABILITIES,
}


def get_database_capabilities(database_type: str) -> DatabaseCapabilities:
    """
    Get the capabilities for a specific database type.

    Args:
        database_type: Database type (e.g., "bigquery", "snowflake")

    Returns:
        DatabaseCapabilities object

    Raises:
        ValueError: If database type is not supported
    """
    if database_type not in CAPABILITIES_MAP:
        raise ValueError(
            f"Unsupported database type: {database_type}. "
            f"Supported types: {list(CAPABILITIES_MAP.keys())}"
        )

    return CAPABILITIES_MAP[database_type]
