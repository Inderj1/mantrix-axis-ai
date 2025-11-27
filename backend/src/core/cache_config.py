"""
Cache Configuration Constants
Lightweight configuration file with no heavy dependencies
"""

# Cache Key Prefixes
PREFIX_SQL = "sql_cache:"
PREFIX_SCHEMA = "schema_cache:"
PREFIX_EMBEDDING = "embedding_cache:"
PREFIX_VALIDATION = "validation_cache:"

# TTL Values (in seconds)
TTL_SQL_FREQUENT = 604800  # 7 days - for frequently used SQL queries
TTL_SQL_INFREQUENT = 86400  # 1 day - for infrequent SQL queries
TTL_SCHEMA = 86400  # 24 hours - for schema metadata
TTL_EMBEDDING = 2592000  # 30 days - for vector embeddings
TTL_VALIDATION = 3600  # 1 hour - for validation results

# Cache Configuration
CACHE_CONFIGS = {
    "sql_generation": {
        "id": "sql_generation",
        "name": "SQL Generation",
        "description": "Generated SQL queries from natural language",
        "prefix": PREFIX_SQL,
        "ttl_seconds": TTL_SQL_FREQUENT,
    },
    "schema": {
        "id": "schema",
        "name": "Schema Cache",
        "description": "Database table schemas and metadata",
        "prefix": PREFIX_SCHEMA,
        "ttl_seconds": TTL_SCHEMA,
    },
    "embedding": {
        "id": "embedding",
        "name": "Embeddings",
        "description": "Vector embeddings for semantic search",
        "prefix": PREFIX_EMBEDDING,
        "ttl_seconds": TTL_EMBEDDING,
    },
    "validation": {
        "id": "validation",
        "name": "Validation Cache",
        "description": "Query validation results",
        "prefix": PREFIX_VALIDATION,
        "ttl_seconds": TTL_VALIDATION,
    },
}
