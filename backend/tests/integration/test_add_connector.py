#!/usr/bin/env python3
"""
Quick script to add a test connector to MongoDB for testing the Control Center.
"""

import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
DATABASE_NAME = 'mantrix_axis_ai'
CONNECTORS_COLLECTION = 'database_connectors'

async def add_test_connector():
    """Add a test BigQuery connector to MongoDB."""

    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    collection = db[CONNECTORS_COLLECTION]

    # Check if test connector already exists
    existing = await collection.find_one({'name': 'Test BigQuery Connector'})
    if existing:
        print(f"Test connector already exists with ID: {existing['_id']}")
        return

    # Create test connector document
    test_connector = {
        'connector_type': 'bigquery',
        'name': 'Test BigQuery Connector',
        'config': {
            'project_id': os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project'),
            'dataset_id': os.getenv('BIGQUERY_DATASET', 'test-dataset'),
            'credentials_json': '{"type": "service_account", "project_id": "test"}'  # Sanitized
        },
        'status': 'connected',
        'organization_id': 'default',  # Default organization
        'enabled_for_chat': True,  # Enable for chat
        'metadata': {
            'table_count': 42,
            'total_size': '1.2 TB',
            'last_sync': datetime.now().isoformat()
        },
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'last_tested': datetime.now().isoformat(),
        'test_result': {
            'success': True,
            'connection_time_ms': 245
        }
    }

    # Insert the connector
    result = await collection.insert_one(test_connector)
    print(f"✅ Added test connector with ID: {result.inserted_id}")

    # Add a second test connector (PostgreSQL)
    postgres_connector = {
        'connector_type': 'postgresql',
        'name': 'Test PostgreSQL Database',
        'config': {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'hidden'  # Sanitized
        },
        'status': 'connected',
        'organization_id': 'default',
        'enabled_for_chat': False,  # Not enabled for chat
        'metadata': {
            'table_count': 15,
            'total_size': '256 MB',
            'last_sync': datetime.now().isoformat()
        },
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    result2 = await collection.insert_one(postgres_connector)
    print(f"✅ Added PostgreSQL test connector with ID: {result2.inserted_id}")

    # Add a disconnected Snowflake connector
    snowflake_connector = {
        'connector_type': 'snowflake',
        'name': 'Snowflake Analytics',
        'config': {
            'account': 'test-account',
            'warehouse': 'COMPUTE_WH',
            'database': 'ANALYTICS',
            'username': 'test_user'
        },
        'status': 'disconnected',
        'organization_id': 'default',
        'enabled_for_chat': False,
        'metadata': {
            'table_count': 0,
            'total_size': 'Unknown',
            'last_sync': None
        },
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    result3 = await collection.insert_one(snowflake_connector)
    print(f"✅ Added Snowflake test connector with ID: {result3.inserted_id}")

    # List all connectors
    print("\n📊 All connectors in database:")
    async for connector in collection.find({'organization_id': 'default'}):
        print(f"  - {connector['name']} ({connector['connector_type']}): {connector['status']}")
        print(f"    Chat enabled: {connector.get('enabled_for_chat', False)}")

    client.close()

if __name__ == "__main__":
    asyncio.run(add_test_connector())