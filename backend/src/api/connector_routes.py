"""
Database Connector API Routes

Endpoints for managing external database connectors.
Allows users to configure, test, and manage connections to BigQuery, Snowflake, PostgreSQL, etc.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime
import structlog
from bson import ObjectId

from ..db.connector_factory import ConnectorFactory
from ..db.mongodb_client import get_mongodb_client
from .models import (
    ConnectorConfigRequest,
    ConnectorTestRequest,
    ConnectorTestResponse,
    ConnectorResponse,
    ConnectorListResponse,
    ConnectorUpdateRequest
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# MongoDB collection for connector configurations
CONNECTORS_COLLECTION = "database_connectors"


def sanitize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive information from config for API responses.

    Args:
        config: Full configuration dictionary

    Returns:
        Sanitized config with sensitive fields masked
    """
    sensitive_fields = ['password', 'api_key', 'secret', 'credentials', 'private_key']
    sanitized = config.copy()

    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***"

    return sanitized


def serialize_connector(connector_doc: Dict[str, Any]) -> ConnectorResponse:
    """
    Convert MongoDB document to ConnectorResponse model.

    Args:
        connector_doc: MongoDB connector document

    Returns:
        ConnectorResponse model instance
    """
    return ConnectorResponse(
        connector_id=str(connector_doc['_id']),
        connector_type=connector_doc['connector_type'],
        name=connector_doc['name'],
        status=connector_doc.get('status', 'disconnected'),
        created_at=connector_doc['created_at'],
        updated_at=connector_doc['updated_at'],
        config_summary=sanitize_config(connector_doc.get('config', {}))
    )


@router.get("/types")
async def get_connector_types():
    """
    Get list of supported connector types and their availability.

    Returns:
        Dictionary mapping connector types to availability status and config templates
    """
    try:
        supported_types = ConnectorFactory.get_supported_types()

        # Get config templates for each type
        type_details = {}
        for connector_type, available in supported_types.items():
            if available:
                try:
                    template = ConnectorFactory.get_config_template(connector_type)
                    type_details[connector_type] = {
                        'available': available,
                        'required_fields': template['required_fields'],
                        'optional_fields': template['optional_fields']
                    }
                except Exception as e:
                    logger.warning(f"Failed to get template for {connector_type}: {e}")
                    type_details[connector_type] = {
                        'available': available,
                        'error': str(e)
                    }
            else:
                type_details[connector_type] = {
                    'available': False,
                    'message': 'Connector not available (missing dependencies)'
                }

        return {
            'success': True,
            'connector_types': type_details
        }

    except Exception as e:
        logger.error(f"Error getting connector types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=ConnectorTestResponse)
async def test_connector(request: ConnectorTestRequest):
    """
    Test a database connector configuration without saving.

    This endpoint validates credentials and connectivity by attempting
    to connect to the database and execute a simple query.

    Args:
        request: Connector test request with type and config

    Returns:
        Test results including success status and connection metadata
    """
    try:
        logger.info(
            f"Testing {request.connector_type} connector",
            connector_type=request.connector_type
        )

        # Test the connection
        result = ConnectorFactory.test_connection(
            connector_type=request.connector_type,
            config=request.config
        )

        return ConnectorTestResponse(
            success=result['success'],
            connector_type=request.connector_type,
            message=result['message'],
            connection_time_ms=result.get('connection_time_ms'),
            metadata=result.get('metadata'),
            error=result.get('error')
        )

    except ValueError as e:
        logger.warning(f"Invalid connector configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error testing connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(request: ConnectorConfigRequest):
    """
    Create and save a new database connector configuration.

    Args:
        request: Connector configuration request

    Returns:
        Created connector details
    """
    try:
        # Validate configuration
        is_valid, error_msg = ConnectorFactory.validate_config(
            request.connector_type,
            request.config
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Test the connection before saving
        test_result = ConnectorFactory.test_connection(
            connector_type=request.connector_type,
            config=request.config
        )

        if not test_result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result.get('error', 'Unknown error')}"
            )

        # Save to MongoDB
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        connector_doc = {
            'connector_type': request.connector_type,
            'name': request.name,
            'config': request.config,
            'status': 'connected',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'last_tested': datetime.now().isoformat(),
            'test_result': {
                'success': True,
                'connection_time_ms': test_result.get('connection_time_ms')
            }
        }

        result = collection.insert_one(connector_doc)
        connector_doc['_id'] = result.inserted_id

        logger.info(
            f"Created {request.connector_type} connector: {request.name}",
            connector_id=str(result.inserted_id)
        )

        return serialize_connector(connector_doc)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error creating connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ConnectorListResponse)
async def list_connectors():
    """
    List all configured database connectors.

    Returns:
        List of all connector configurations (with sensitive data masked)
    """
    try:
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        connectors = list(collection.find())

        connector_responses = [serialize_connector(conn) for conn in connectors]

        return ConnectorListResponse(
            connectors=connector_responses,
            total_count=len(connector_responses)
        )

    except Exception as e:
        logger.error(f"Error listing connectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector(connector_id: str):
    """
    Get details for a specific connector.

    Args:
        connector_id: Unique connector identifier

    Returns:
        Connector details (with sensitive data masked)
    """
    try:
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        connector = collection.find_one({'_id': ObjectId(connector_id)})

        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        return serialize_connector(connector)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(connector_id: str, request: ConnectorUpdateRequest):
    """
    Update an existing connector configuration.

    Args:
        connector_id: Unique connector identifier
        request: Update request with optional name and config changes

    Returns:
        Updated connector details
    """
    try:
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        # Find existing connector
        connector = collection.find_one({'_id': ObjectId(connector_id)})
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        # Build update document
        update_doc = {'updated_at': datetime.now().isoformat()}

        if request.name:
            update_doc['name'] = request.name

        if request.config:
            # Merge with existing config
            updated_config = {**connector.get('config', {}), **request.config}

            # Test the updated configuration
            test_result = ConnectorFactory.test_connection(
                connector_type=connector['connector_type'],
                config=updated_config
            )

            if not test_result['success']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Connection test failed: {test_result.get('error', 'Unknown error')}"
                )

            update_doc['config'] = updated_config
            update_doc['status'] = 'connected'
            update_doc['last_tested'] = datetime.now().isoformat()
            update_doc['test_result'] = {
                'success': True,
                'connection_time_ms': test_result.get('connection_time_ms')
            }

        # Update in database
        collection.update_one(
            {'_id': ObjectId(connector_id)},
            {'$set': update_doc}
        )

        # Fetch updated connector
        updated_connector = collection.find_one({'_id': ObjectId(connector_id)})

        logger.info(f"Updated connector: {connector_id}")

        return serialize_connector(updated_connector)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error updating connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """
    Delete a connector configuration.

    Args:
        connector_id: Unique connector identifier

    Returns:
        Success message
    """
    try:
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        result = collection.delete_one({'_id': ObjectId(connector_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        logger.info(f"Deleted connector: {connector_id}")

        return {
            'success': True,
            'message': f'Connector {connector_id} deleted successfully'
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error deleting connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{connector_id}/test", response_model=ConnectorTestResponse)
async def test_existing_connector(connector_id: str):
    """
    Test an existing connector configuration.

    Args:
        connector_id: Unique connector identifier

    Returns:
        Test results
    """
    try:
        mongo_client = get_mongodb_client()
        db = mongo_client.get_database()
        collection = db[CONNECTORS_COLLECTION]

        connector = collection.find_one({'_id': ObjectId(connector_id)})
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        # Test the connection
        result = ConnectorFactory.test_connection(
            connector_type=connector['connector_type'],
            config=connector['config']
        )

        # Update test results in database
        collection.update_one(
            {'_id': ObjectId(connector_id)},
            {
                '$set': {
                    'last_tested': datetime.now().isoformat(),
                    'status': 'connected' if result['success'] else 'error',
                    'test_result': {
                        'success': result['success'],
                        'connection_time_ms': result.get('connection_time_ms'),
                        'error': result.get('error')
                    }
                }
            }
        )

        return ConnectorTestResponse(
            success=result['success'],
            connector_type=connector['connector_type'],
            message=result['message'],
            connection_time_ms=result.get('connection_time_ms'),
            metadata=result.get('metadata'),
            error=result.get('error')
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error testing connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))
