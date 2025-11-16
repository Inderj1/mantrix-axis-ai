"""
BigQuery Client - Backward Compatibility Wrapper

This module maintains backward compatibility with existing code that imports BigQueryClient.
The actual implementation has been moved to src.db.connectors.bigquery_connector.BigQueryConnector
which implements the BaseDatabaseConnector interface.

All new code should import from connectors.bigquery_connector, but this wrapper ensures
existing imports continue to work without changes.
"""
# Import the new connector implementation
from .connectors.bigquery_connector import BigQueryConnector

# Export BigQueryClient as an alias for backward compatibility
BigQueryClient = BigQueryConnector

# Export all public members
__all__ = ['BigQueryClient', 'BigQueryConnector']