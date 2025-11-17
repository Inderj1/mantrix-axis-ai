from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Anthropic (for NLP-to-SQL system)
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929", alias="ANTHROPIC_MODEL")

    # OpenAI (for embeddings)
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )

    # Google Cloud / BigQuery
    google_cloud_project: str = Field(..., alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(
        None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    bigquery_dataset: str = Field(..., alias="BIGQUERY_DATASET")
    bigquery_query_timeout_seconds: int = Field(default=60, alias="BIGQUERY_QUERY_TIMEOUT_SECONDS")
    default_query_timeout_seconds: int = Field(default=60, alias="DEFAULT_QUERY_TIMEOUT_SECONDS")

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

    # Snowflake Configuration (optional - only needed if using Snowflake)
    snowflake_account: Optional[str] = Field(None, alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: Optional[str] = Field(None, alias="SNOWFLAKE_USER")
    snowflake_password: Optional[str] = Field(None, alias="SNOWFLAKE_PASSWORD")
    snowflake_warehouse: Optional[str] = Field(None, alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: Optional[str] = Field(None, alias="SNOWFLAKE_DATABASE")
    snowflake_schema: Optional[str] = Field(default="PUBLIC", alias="SNOWFLAKE_SCHEMA")
    snowflake_role: Optional[str] = Field(None, alias="SNOWFLAKE_ROLE")

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

    # Clerk Authentication
    clerk_secret_key: Optional[str] = Field(None, alias="CLERK_SECRET_KEY")
    production_domain: Optional[str] = Field(None, alias="PRODUCTION_DOMAIN")


settings = Settings()
