from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Allow extra env vars not defined in model
    )

    # Anthropic (for NLP-to-SQL system)
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-opus-4-5-20251101", alias="ANTHROPIC_MODEL")
    anthropic_fast_model: str = Field(default="claude-haiku-4-5-20251001", alias="ANTHROPIC_FAST_MODEL")
    ai_suggestion_timeout_seconds: float = Field(default=5.0, alias="AI_SUGGESTION_TIMEOUT_SECONDS")

    # OpenAI (for embeddings)
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # Google Cloud / BigQuery (optional - only required if using BigQuery)
    google_cloud_project: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(
        None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    bigquery_dataset: Optional[str] = Field(default=None, alias="BIGQUERY_DATASET")
    bigquery_query_timeout_seconds: int = Field(default=60, alias="BIGQUERY_QUERY_TIMEOUT_SECONDS")
    default_query_timeout_seconds: int = Field(default=60, alias="DEFAULT_QUERY_TIMEOUT_SECONDS")

    # BigQuery Workload Identity Federation (for keyless authentication)
    # Clients create a WIF pool in their GCP project that trusts this AWS account
    mantrix_aws_account_id: str = Field(
        default="709141244278",
        alias="MANTRIX_AWS_ACCOUNT_ID",
        description="Mantrix AWS Account ID - share with clients for WIF setup"
    )

    # Google OAuth Configuration (for BigQuery connections without service account keys)
    google_oauth_client_id: Optional[str] = Field(
        None, alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[str] = Field(
        None, alias="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/connectors/bigquery/oauth/callback",
        alias="GOOGLE_OAUTH_REDIRECT_URI"
    )
    # Fernet encryption key for storing OAuth tokens securely (generate with: Fernet.generate_key())
    oauth_encryption_key: Optional[str] = Field(
        None, alias="OAUTH_ENCRYPTION_KEY"
    )

    # Weaviate
    weaviate_url: str = Field(default="http://localhost:8082", alias="WEAVIATE_URL")
    weaviate_api_key: Optional[str] = Field(None, alias="WEAVIATE_API_KEY")

    # Markets.AI API Keys (all free)
    fred_api_key: Optional[str] = Field(None, alias="FRED_API_KEY")
    eia_api_key: Optional[str] = Field(None, alias="EIA_API_KEY")
    bls_api_key: Optional[str] = Field(None, alias="BLS_API_KEY")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_env: str = Field(default="development", alias="API_ENV")

    # Multi-Database Configuration
    max_chat_databases: int = Field(default=2, alias="MAX_CHAT_DATABASES")
    default_org_id: str = Field(default="default", alias="DEFAULT_ORG_ID")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Industry configuration - Disabled (using GL mappings only)
    industry: str = Field(default="gl_mappings", alias="INDUSTRY")
    enable_industry_features: bool = Field(default=False, alias="ENABLE_INDUSTRY_FEATURES")

    # MongoDB Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", alias="MONGODB_URL")

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password123", alias="NEO4J_PASSWORD")
    mongodb_db_name: str = Field(default="nlp_sql_conversations", alias="MONGODB_DB_NAME")
    mongodb_database: str = Field(default="nlp_sql_conversations", alias="MONGODB_DATABASE")
    mongodb_conversations_collection: str = Field(
        default="conversations", alias="MONGODB_CONVERSATIONS_COLLECTION"
    )

    # Redis Cache Configuration
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_url: Optional[str] = Field(None, alias="REDIS_URL")  # For cloud deployments
    redis_decode_responses: bool = Field(default=True, alias="REDIS_DECODE_RESPONSES")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # Cache TTL settings (in seconds)
    cache_ttl_sql_frequent: int = Field(
        default=7 * 24 * 60 * 60, alias="CACHE_TTL_SQL_FREQUENT"
    )  # 7 days
    cache_ttl_sql_infrequent: int = Field(
        default=24 * 60 * 60, alias="CACHE_TTL_SQL_INFREQUENT"
    )  # 1 day
    cache_ttl_schema: int = Field(default=24 * 60 * 60, alias="CACHE_TTL_SCHEMA")  # 24 hours
    cache_ttl_embedding: int = Field(
        default=30 * 24 * 60 * 60, alias="CACHE_TTL_EMBEDDING"
    )  # 30 days
    cache_ttl_validation: int = Field(default=60 * 60, alias="CACHE_TTL_VALIDATION")  # 1 hour
    cache_ttl_result: int = Field(default=5 * 60, alias="CACHE_TTL_RESULT")  # 5 minutes
    cache_ttl_session: int = Field(default=24 * 60 * 60, alias="CACHE_TTL_SESSION")  # 24 hours

    # Cache feature flags
    cache_enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    cache_sql_enabled: bool = Field(default=True, alias="CACHE_SQL_ENABLED")
    cache_schema_enabled: bool = Field(default=True, alias="CACHE_SCHEMA_ENABLED")
    cache_embedding_enabled: bool = Field(default=True, alias="CACHE_EMBEDDING_ENABLED")
    cache_validation_enabled: bool = Field(default=True, alias="CACHE_VALIDATION_ENABLED")
    cache_result_enabled: bool = Field(
        default=False, alias="CACHE_RESULT_ENABLED"
    )  # Off by default for fresh data
    cache_weaviate_enabled: bool = Field(
        default=True, alias="CACHE_WEAVIATE_ENABLED"
    )  # Cache Weaviate vector search results

    # Cache quality settings
    cache_execution_threshold_ms: int = Field(
        default=30000, alias="CACHE_EXECUTION_THRESHOLD_MS"
    )  # 30 seconds - queries slower than this get reduced TTL
    cache_min_confidence: float = Field(
        default=0.7, alias="CACHE_MIN_CONFIDENCE"
    )  # Minimum LLM confidence score to cache
    cache_max_rows_threshold: int = Field(
        default=1000000, alias="CACHE_MAX_ROWS_THRESHOLD"
    )  # 1M rows - queries returning more marked as suspect
    cache_validation_required: bool = Field(
        default=True, alias="CACHE_VALIDATION_REQUIRED"
    )  # Require successful BigQuery validation before caching
    cache_execution_test_required: bool = Field(
        default=True, alias="CACHE_EXECUTION_TEST_REQUIRED"
    )  # Require successful test execution before caching
    cache_invalidate_on_pipeline: bool = Field(
        default=True, alias="CACHE_INVALIDATE_ON_PIPELINE"
    )  # Automatically invalidate cache when pipeline updates schemas
    cache_reject_empty_results: bool = Field(
        default=True, alias="CACHE_REJECT_EMPTY_RESULTS"
    )  # Don't cache queries that return zero results

    # Cache quality tier TTLs (in seconds)
    cache_ttl_gold: int = Field(
        default=7 * 24 * 60 * 60, alias="CACHE_TTL_GOLD"
    )  # 7 days - fast, validated, high confidence
    cache_ttl_silver: int = Field(
        default=3 * 24 * 60 * 60, alias="CACHE_TTL_SILVER"
    )  # 3 days - medium speed, validated
    cache_ttl_bronze: int = Field(
        default=12 * 60 * 60, alias="CACHE_TTL_BRONZE"
    )  # 12 hours - slow but validated

    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="inder", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_database: str = Field(default="customer_analytics", alias="POSTGRES_DATABASE")

    # Query timeout configuration for large tables
    large_table_query_timeout: int = Field(
        default=900, alias="LARGE_TABLE_QUERY_TIMEOUT"
    )  # 15 minutes - timeout for queries on very large tables (>1B rows)
    default_query_timeout: int = Field(
        default=300, alias="DEFAULT_QUERY_TIMEOUT"
    )  # 5 minutes - default timeout for normal queries

    # Query safety configuration
    fail_fast_on_unknown_table_size: bool = Field(
        default=True, alias="FAIL_FAST_ON_UNKNOWN_TABLE_SIZE"
    )  # If true, fail queries on tables with unknown size (forces schema sync first)

    # Snowflake Configuration (optional - only needed if using Snowflake)
    snowflake_account: Optional[str] = Field(None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: Optional[str] = Field(None, alias="SNOWFLAKE_USER")
    snowflake_password: Optional[str] = Field(None, alias="SNOWFLAKE_PASSWORD")
    snowflake_warehouse: Optional[str] = Field(None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: Optional[str] = Field(None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: Optional[str] = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
    snowflake_role: Optional[str] = Field(None, alias="SNOWFLAKE_ROLE")
    # Snowflake authentication method: 'password' (default), 'keypair', or 'pat'
    snowflake_auth_method: str = Field(default="password", alias="SNOWFLAKE_AUTH_METHOD")

    # External PostgreSQL Configuration (for customer databases, separate from internal)
    external_postgres_host: Optional[str] = Field(None, alias="EXTERNAL_POSTGRES_HOST")
    external_postgres_port: Optional[int] = Field(default=5432, alias="EXTERNAL_POSTGRES_PORT")
    external_postgres_database: Optional[str] = Field(None, alias="EXTERNAL_POSTGRES_DATABASE")
    external_postgres_user: Optional[str] = Field(None, alias="EXTERNAL_POSTGRES_USER")
    external_postgres_password: Optional[str] = Field(None, alias="EXTERNAL_POSTGRES_PASSWORD")
    external_postgres_schema: Optional[str] = Field(default="public", alias="EXTERNAL_POSTGRES_SCHEMA")
    external_postgres_ssl_mode: Optional[str] = Field(None, alias="EXTERNAL_POSTGRES_SSL_MODE")

    # Redshift Configuration (optional - only needed if using Redshift)
    redshift_host: Optional[str] = Field(None, alias="REDSHIFT_HOST")
    redshift_port: Optional[int] = Field(default=5439, alias="REDSHIFT_PORT")
    redshift_database: Optional[str] = Field(None, alias="REDSHIFT_DATABASE")
    redshift_user: Optional[str] = Field(None, alias="REDSHIFT_USER")
    redshift_password: Optional[str] = Field(None, alias="REDSHIFT_PASSWORD")
    redshift_schema: Optional[str] = Field(default="public", alias="REDSHIFT_SCHEMA")
    redshift_ssl_mode: Optional[str] = Field(default="require", alias="REDSHIFT_SSL_MODE")
    redshift_cluster_identifier: Optional[str] = Field(None, alias="REDSHIFT_CLUSTER_IDENTIFIER")

    # Databricks Configuration (optional - only needed if using Databricks)
    databricks_server_hostname: Optional[str] = Field(None, alias="DATABRICKS_SERVER_HOSTNAME")
    databricks_http_path: Optional[str] = Field(None, alias="DATABRICKS_HTTP_PATH")
    databricks_access_token: Optional[str] = Field(None, alias="DATABRICKS_ACCESS_TOKEN")
    databricks_catalog: Optional[str] = Field(default="main", alias="DATABRICKS_CATALOG")
    databricks_schema: Optional[str] = Field(default="default", alias="DATABRICKS_SCHEMA")

    # Clerk Authentication (Deprecated - use Cognito)
    clerk_secret_key: Optional[str] = Field(None, alias="CLERK_SECRET_KEY")
    production_domain: Optional[str] = Field(None, alias="PRODUCTION_DOMAIN")

    # AWS Cognito Authentication
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    cognito_user_pool_id: Optional[str] = Field(None, alias="COGNITO_USER_POOL_ID")
    cognito_app_client_id: Optional[str] = Field(None, alias="COGNITO_APP_CLIENT_ID")
    cognito_admin_group: str = Field(default="Admins", alias="COGNITO_ADMIN_GROUP")

    # AWS Credentials (for Cognito admin operations)
    aws_profile: Optional[str] = Field(None, alias="AWS_PROFILE")
    aws_access_key_id: Optional[str] = Field(None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = Field(None, alias="AWS_SESSION_TOKEN")

    # S3 Federation Configuration (for 10-100GB+ cross-database JOINs)
    # Default strategy for AWS Marketplace deployment uses Redshift Spectrum
    federation_enabled: bool = Field(default=True, alias="FEDERATION_ENABLED")
    federation_s3_bucket: Optional[str] = Field(None, alias="FEDERATION_S3_BUCKET")
    federation_s3_prefix: str = Field(default="federation", alias="FEDERATION_S3_PREFIX")
    federation_redshift_schema: str = Field(default="federation_temp", alias="FEDERATION_REDSHIFT_SCHEMA")
    federation_chunk_size: int = Field(default=100000, alias="FEDERATION_CHUNK_SIZE")
    federation_ttl_hours: int = Field(default=24, alias="FEDERATION_TTL_HOURS")

    # Database Feature Flags (Global Enable/Disable)
    enable_bigquery: bool = Field(default=True, alias="ENABLE_BIGQUERY")
    enable_snowflake: bool = Field(default=True, alias="ENABLE_SNOWFLAKE")
    enable_postgresql: bool = Field(default=True, alias="ENABLE_POSTGRESQL")
    enable_redshift: bool = Field(default=True, alias="ENABLE_REDSHIFT")
    enable_databricks: bool = Field(default=True, alias="ENABLE_DATABRICKS")

    # Statistics Extraction Configuration (Optimization Intelligence)
    stats_extraction_enabled: bool = Field(
        default=True,
        alias="STATS_EXTRACTION_ENABLED"
    )

    stats_extraction_schedule: str = Field(
        default="weekly",  # Options: "daily", "weekly", "monthly", "manual"
        alias="STATS_EXTRACTION_SCHEDULE"
    )

    stats_extraction_day: int = Field(
        default=0,  # 0 = Sunday, 1 = Monday, ... 6 = Saturday
        alias="STATS_EXTRACTION_DAY"
    )

    stats_extraction_hour: int = Field(
        default=2,  # 2 AM
        alias="STATS_EXTRACTION_HOUR"
    )

    stats_max_age_days: int = Field(
        default=7,  # Re-extract statistics older than 7 days
        alias="STATS_MAX_AGE_DAYS"
    )

    # Sampling configuration (cost optimization)
    stats_use_sampling: bool = Field(
        default=True,
        alias="STATS_USE_SAMPLING"
    )

    stats_sample_percent: int = Field(
        default=10,  # 10% sample for large tables
        alias="STATS_SAMPLE_PERCENT"
    )

    stats_sampling_threshold_gb: float = Field(
        default=10.0,  # Use sampling for tables > 10GB
        alias="STATS_SAMPLING_THRESHOLD_GB"
    )

    # Table filtering for stats extraction
    stats_critical_tables: Optional[str] = Field(
        default=None,  # Comma-separated list of critical tables (if set, only extract for these)
        alias="STATS_CRITICAL_TABLES"
    )

    stats_skip_tables: Optional[str] = Field(
        default=None,  # Comma-separated list of tables to skip
        alias="STATS_SKIP_TABLES"
    )

    # SMTP Email Configuration (for alerts and notifications)
    smtp_enabled: bool = Field(default=False, alias="SMTP_ENABLED")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(None, alias="SMTP_USER")
    smtp_password: Optional[str] = Field(None, alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@mantrix.ai", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Mantrix Axis AI", alias="SMTP_FROM_NAME")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")

    # Alert Notification Settings
    alert_check_interval_seconds: int = Field(default=60, alias="ALERT_CHECK_INTERVAL_SECONDS")
    alert_notification_batch_size: int = Field(default=100, alias="ALERT_NOTIFICATION_BATCH_SIZE")
    alert_retry_max_attempts: int = Field(default=3, alias="ALERT_RETRY_MAX_ATTEMPTS")
    alert_retry_delay_seconds: int = Field(default=300, alias="ALERT_RETRY_DELAY_SECONDS")

    # Jena RDF Storage Configuration
    # Backend options: "redis" (default), "postgres" (persistent), "memory" (single-process)
    jena_backend: str = Field(default="redis", alias="JENA_BACKEND")
    # Graph ID for multi-tenant isolation (default: "global")
    jena_graph_id: str = Field(default="global", alias="JENA_GRAPH_ID")
    # EFS path for RDF backups (optional, e.g., "/mnt/efs/rdf")
    jena_efs_path: Optional[str] = Field(default=None, alias="JENA_EFS_PATH")
    # Enable PostgreSQL persistence (deprecated, use jena_backend="postgres" instead)
    jena_postgres_enabled: bool = Field(default=False, alias="JENA_POSTGRES_ENABLED")


settings = Settings()
