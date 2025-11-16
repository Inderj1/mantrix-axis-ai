"""
Pytest configuration and shared fixtures for all tests.
"""
import pytest
import sys
from pathlib import Path

# Add backend/src to Python path so imports work
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

# Shared fixtures

@pytest.fixture(scope="session")
def sql_generator():
    """Shared SQL generator instance for tests."""
    from src.core.sql_generator import SQLGenerator
    return SQLGenerator()

@pytest.fixture(scope="session")
def cache_manager():
    """Shared cache manager instance for tests."""
    from src.core.cache_manager import CacheManager
    return CacheManager()

@pytest.fixture(scope="session")
def bigquery_client():
    """Shared BigQuery client for integration tests."""
    from src.db.bigquery import BigQueryClient
    from src.config import settings
    
    config = {
        "project": settings.google_cloud_project,
        "dataset": settings.bigquery_dataset,
        "credentials_path": settings.google_application_credentials,
        "timeout": settings.bigquery_query_timeout_seconds
    }
    return BigQueryClient(config)

@pytest.fixture(scope="function")
def clear_cache():
    """Fixture to clear cache before each test."""
    from src.core.cache_manager import CacheManager
    cache = CacheManager()
    cache.clear_all_caches()
    yield
    # Cleanup after test if needed

@pytest.fixture(scope="session")
def sample_queries():
    """Common test queries."""
    return [
        "Show me all GL accounts",
        "What is the total revenue by customer?",
        "Show sales trends by month",
        "What products have the highest sales?",
        "Show customer segments and their performance"
    ]

@pytest.fixture(scope="session")
def sample_invalid_queries():
    """Invalid queries for negative testing."""
    return [
        "SELECT * FROM nonexistent_table",
        "SELECT nonexistent_column FROM GL_Accounts",
        "INVALID SQL SYNTAX HERE"
    ]

# Knowledge Graph fixtures

@pytest.fixture(scope="session")
def knowledge_graph():
    """Load Apache Jena knowledge graph for testing."""
    from rdflib import Graph, Namespace
    import os

    graph = Graph()
    FIN = Namespace("http://example.com/finance#")
    graph.bind("fin", FIN)

    # Try to load knowledge graph file if it exists
    kg_file = "table_metadata_kg.ttl"
    if os.path.exists(kg_file):
        graph.parse(kg_file, format="turtle")

    return graph

@pytest.fixture(scope="session")
def graph(knowledge_graph):
    """Alias for knowledge_graph fixture (for backward compatibility)."""
    return knowledge_graph

@pytest.fixture
def table1():
    """First table name for join path testing."""
    return "Customer_Master"

@pytest.fixture
def table2():
    """Second table name for join path testing."""
    return "transaction_data"

# Pytest configuration
def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (multi-component)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full workflows)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (>10s)"
    )
    config.addinivalue_line(
        "markers", "requires_db: Tests that require database access"
    )
