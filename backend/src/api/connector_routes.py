"""
Database Connector API Routes

Endpoints for managing external database connectors.
Allows users to configure, test, and manage connections to BigQuery, Snowflake, PostgreSQL, etc.

Permissions:
- GET /types: Optional auth (filters by user permissions if authenticated)
- POST /test: Optional auth (checks permissions if authenticated)
- POST /, PUT /, DELETE /: Require authentication
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from bson import ObjectId

from ..db.connector_factory import ConnectorFactory
from ..db.mongodb_client import get_mongodb_client
from ..api.middleware.cognito_auth import (
    get_optional_user,
    require_auth,
    require_admin
)
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


def serialize_connector(connector_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB document to API response format.

    Args:
        connector_doc: MongoDB connector document

    Returns:
        Dictionary with connector data for frontend
    """
    return {
        "id": str(connector_doc['_id']),  # Frontend expects 'id', not 'connector_id'
        "connector_type": connector_doc['connector_type'],
        "name": connector_doc['name'],
        "status": connector_doc.get('status', 'disconnected'),
        "created_at": connector_doc['created_at'],
        "updated_at": connector_doc['updated_at'],
        "config": sanitize_config(connector_doc.get('config', {})),  # Frontend expects 'config'
        "enabled_for_chat": connector_doc.get('enabled_for_chat', False),  # Add chat enablement flag
        "metadata": {
            "table_count": connector_doc.get('metadata', {}).get('table_count', 0),
            "total_size": connector_doc.get('metadata', {}).get('total_size', 'Unknown'),
            "last_sync": connector_doc.get('metadata', {}).get('last_sync')
        },
        "organization_id": connector_doc.get('organization_id')
    }


async def trigger_pipeline_for_connector(connector_id: str, connector_type: str, organization_id: str):
    """
    Trigger pipeline run for a specific connector to extract schema and build RDF/vectors.

    Args:
        connector_id: Unique connector identifier
        connector_type: Type of database connector
        organization_id: Organization ID

    Returns:
        Task that runs the pipeline in the background
    """
    import asyncio
    from src.pipeline.orchestrator import PipelineOrchestrator

    async def run_pipeline():
        try:
            logger.info(f"Starting pipeline for connector {connector_id} ({connector_type})")

            # Run pipeline in background
            orchestrator = PipelineOrchestrator()
            run = orchestrator.execute_pipeline(
                incremental=True,
                force_refresh=False
            )

            # Update connector metadata with results
            mongodb_client = await get_mongodb_client()
            collection = mongodb_client.db[CONNECTORS_COLLECTION]

            await collection.update_one(
                {'_id': ObjectId(connector_id)},
                {'$set': {
                    'metadata.last_sync': datetime.now().isoformat(),
                    'metadata.table_count': run.tables_processed if hasattr(run, 'tables_processed') else 0,
                    'updated_at': datetime.now().isoformat()
                }}
            )

            logger.info(f"Pipeline completed for connector {connector_id}")

        except Exception as e:
            logger.error(f"Error running pipeline for connector {connector_id}: {e}")

    # Create background task
    asyncio.create_task(run_pipeline())
    logger.info(f"Pipeline task created for connector {connector_id}")


async def reinitialize_sql_generator(organization_id: str):
    """
    Reinitialize SQLGenerator for an organization after database changes.

    Args:
        organization_id: Organization ID
    """
    try:
        from src.api.routes import get_sql_generator

        logger.info(f"Reinitializing SQLGenerator for organization: {organization_id}")

        # Force reinitialization by creating new instance
        generator = get_sql_generator(organization_id=organization_id)

        logger.info(f"SQLGenerator reinitialized for organization: {organization_id}")

    except Exception as e:
        logger.error(f"Error reinitializing SQLGenerator for {organization_id}: {e}")


@router.get("/types")
async def get_connector_types(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Get list of supported connector types filtered by user permissions.

    Optional authentication: Works with or without auth token.
    If authenticated, filters connectors by user's database permissions.

    Args:
        user_id: Optional user ID (defaults to current authenticated user)
        organization_id: Optional organization ID
        current_user: Current authenticated user (auto-injected)

    Returns:
        Dictionary mapping connector types to availability status, permissions, and config templates
    """
    try:
        # Determine target user and organization
        if current_user:
            target_user_id = user_id or current_user["id"]
            target_org_id = organization_id or current_user.get("organization_id")
        else:
            target_user_id = user_id
            target_org_id = organization_id

        # If no user_id provided, return all types without permission filtering
        if not target_user_id:
            logger.info("No user_id provided, returning all connector types without permission filtering")
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

        # Get permission-filtered connector types for user
        type_details = ConnectorFactory.get_supported_types_for_user(
            user_id=target_user_id,
            organization_id=target_org_id
        )

        # Add config templates for accessible types
        for connector_type, details in type_details.items():
            if details.get('available') and details.get('has_access'):
                try:
                    template = ConnectorFactory.get_config_template(connector_type)
                    details['required_fields'] = template['required_fields']
                    details['optional_fields'] = template['optional_fields']
                except Exception as e:
                    logger.warning(f"Failed to get template for {connector_type}: {e}")
                    details['error'] = str(e)

        logger.info(
            f"Retrieved connector types for user {target_user_id}",
            user_id=target_user_id
        )

        return {
            'success': True,
            'user_id': target_user_id,
            'connector_types': type_details
        }

    except Exception as e:
        logger.error(f"Error getting connector types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=ConnectorTestResponse)
async def test_connector(
    request: ConnectorTestRequest,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Test a database connector configuration without saving.

    This endpoint validates credentials and connectivity by attempting
    to connect to the database and execute a simple query.

    Optional authentication: Works with or without auth token.
    Permission checking: If authenticated, user must have at least READ access to the database type.

    Args:
        request: Connector test request with type and config
        user_id: Optional user ID (defaults to current authenticated user)
        organization_id: Optional organization ID
        current_user: Current authenticated user (auto-injected)

    Returns:
        Test results including success status and connection metadata
    """
    try:
        # Determine target user and organization
        if current_user:
            target_user_id = user_id or current_user["id"]
            target_org_id = organization_id or current_user.get("organization_id")
        else:
            target_user_id = user_id
            target_org_id = organization_id

        # Check permissions if user is authenticated
        if target_user_id:
            has_access = ConnectorFactory.check_user_access(
                user_id=target_user_id,
                database_type=request.connector_type,
                required_level="read",  # Require at least READ access to test
                organization_id=target_org_id
            )

            if not has_access:
                logger.warning(
                    f"User {target_user_id} attempted to test {request.connector_type} without permission",
                    user_id=target_user_id,
                    database_type=request.connector_type
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"You do not have permission to test {request.connector_type} connectors"
                )

        logger.info(
            f"Testing {request.connector_type} connector",
            connector_type=request.connector_type,
            user_id=target_user_id
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

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning(f"Invalid connector configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error testing connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connector(
    request: ConnectorConfigRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Create and save a new database connector configuration.

    Args:
        request: Connector configuration request
        current_user: Current authenticated user

    Returns:
        Created connector details
    """
    try:
        # Get organization_id from user context
        organization_id = None
        if current_user:
            organization_id = current_user.get('organization_id')

        # Use default organization if not specified
        if not organization_id:
            organization_id = 'default'

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

        # Save to MongoDB using async access
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        connector_doc = {
            'connector_type': request.connector_type,
            'name': request.name,
            'config': request.config,
            'status': 'connected',
            'organization_id': organization_id,  # Add organization_id
            'enabled_for_chat': False,  # Default to false
            'metadata': {  # Add metadata object
                'table_count': 0,
                'total_size': 'Unknown',
                'last_sync': None
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'last_tested': datetime.now().isoformat(),
            'test_result': {
                'success': True,
                'connection_time_ms': test_result.get('connection_time_ms')
            }
        }

        result = await collection.insert_one(connector_doc)
        connector_doc['_id'] = result.inserted_id

        logger.info(
            f"Created {request.connector_type} connector: {request.name}",
            connector_id=str(result.inserted_id),
            organization_id=organization_id
        )

        # Trigger pipeline run for the new connector (runs in background)
        await trigger_pipeline_for_connector(
            connector_id=str(result.inserted_id),
            connector_type=request.connector_type,
            organization_id=organization_id
        )

        # Reinitialize SQLGenerator for the organization
        await reinitialize_sql_generator(organization_id)

        return serialize_connector(connector_doc)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error creating connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_connectors(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    List all configured database connectors for the user's organization.

    Returns:
        List of all connector configurations (with sensitive data masked)
    """
    try:
        # Get organization_id from user context
        organization_id = None
        if current_user:
            organization_id = current_user.get('organization_id')

        # Use default organization if not specified
        if not organization_id:
            organization_id = 'default'

        # Use async MongoDB access
        mongodb_client = await get_mongodb_client()
        connectors_collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Filter by organization_id
        query = {"organization_id": organization_id}
        cursor = connectors_collection.find(query)
        connectors = await cursor.to_list(length=None)

        # Serialize connectors for frontend
        connector_responses = [serialize_connector(conn) for conn in connectors]

        return {
            "connectors": connector_responses,
            "total_count": len(connector_responses)
        }

    except Exception as e:
        logger.error(f"Error listing connectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_connectors_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Get overall status of database connectors for the organization.

    Returns aggregate status including total count, connected count, and chat-enabled count.
    """
    try:
        # Get organization_id from user context
        organization_id = None
        if current_user:
            organization_id = current_user.get('organization_id')

        if not organization_id:
            organization_id = 'default'

        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Get counts for this organization
        total_count = await collection.count_documents({"organization_id": organization_id})
        connected_count = await collection.count_documents({
            "organization_id": organization_id,
            "status": "connected"
        })
        chat_enabled_count = await collection.count_documents({
            "organization_id": organization_id,
            "enabled_for_chat": True
        })

        # Get list of connector summaries
        cursor = collection.find({"organization_id": organization_id})
        connectors = []
        async for doc in cursor:
            connectors.append({
                "id": str(doc['_id']),
                "name": doc.get('name', 'Unnamed'),
                "connector_type": doc['connector_type'],
                "status": doc.get('status', 'unknown'),
                "enabled_for_chat": doc.get('enabled_for_chat', False)
            })

        return {
            "success": True,
            "organization_id": organization_id,
            "total_count": total_count,
            "connected_count": connected_count,
            "chat_enabled_count": chat_enabled_count,
            "connectors": connectors
        }

    except Exception as e:
        logger.error(f"Error getting connector status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-enabled")
async def get_chat_enabled_connectors(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get list of connectors enabled for chat queries.

    Args:
        current_user: Current authenticated user

    Returns:
        List of enabled connectors
    """
    try:
        mongodb_client = await get_mongodb_client()
        connectors_collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Get user's organization
        org_id = current_user.get('organization_id', 'default')

        # Find enabled connectors for this organization
        cursor = connectors_collection.find({
            "organization_id": org_id,
            "enabled_for_chat": True,
            "status": "connected"  # Only return connected databases
        })

        connectors = []
        async for doc in cursor:
            connectors.append({
                "connector_id": str(doc['_id']),
                "connector_type": doc['connector_type'],
                "name": doc['name'],
                "enabled_at": doc.get('enabled_at'),
                "config_summary": sanitize_config(doc.get('config', {}))
            })

        # Get max allowed from settings
        from ..config import settings
        max_databases = getattr(settings, 'MAX_CHAT_DATABASES', 2)

        return {
            "connectors": connectors,
            "count": len(connectors),
            "max_allowed": max_databases
        }

    except Exception as e:
        logger.error(f"Error getting chat-enabled connectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connector_id}")
async def get_connector(
    connector_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Get details for a specific connector.

    Args:
        connector_id: Unique connector identifier
        current_user: Current authenticated user

    Returns:
        Connector details (with sensitive data masked)
    """
    try:
        # Get organization_id from user context
        organization_id = None
        if current_user:
            organization_id = current_user.get('organization_id')

        # Use default organization if not specified
        if not organization_id:
            organization_id = 'default'

        # Use async MongoDB access
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Find connector with organization filter
        connector = await collection.find_one({
            '_id': ObjectId(connector_id),
            'organization_id': organization_id
        })

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
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Find existing connector
        connector = await collection.find_one({'_id': ObjectId(connector_id)})
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
        await collection.update_one(
            {'_id': ObjectId(connector_id)},
            {'$set': update_doc}
        )

        # Fetch updated connector
        updated_connector = await collection.find_one({'_id': ObjectId(connector_id)})

        logger.info(f"Updated connector: {connector_id}")

        return serialize_connector(updated_connector)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error updating connector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{connector_id}/toggle-chat")
async def toggle_connector_for_chat(
    connector_id: str,
    enabled: bool,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Toggle a connector's chat enablement status.
    When enabled, triggers pipeline run and SQLGenerator reinitialization.

    Args:
        connector_id: Unique connector identifier
        enabled: Whether to enable or disable for chat
        current_user: Current authenticated user

    Returns:
        Updated connector details
    """
    try:
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Find existing connector
        connector = await collection.find_one({'_id': ObjectId(connector_id)})
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        # Get organization_id
        organization_id = connector.get('organization_id', 'default')

        # Check if status is changing
        was_enabled = connector.get('enabled_for_chat', False)
        is_enabling = enabled and not was_enabled

        # Update the enabled_for_chat flag
        await collection.update_one(
            {'_id': ObjectId(connector_id)},
            {'$set': {
                'enabled_for_chat': enabled,
                'updated_at': datetime.now().isoformat()
            }}
        )

        logger.info(
            f"Toggled connector {connector_id} for chat",
            enabled=enabled,
            organization_id=organization_id
        )

        # If enabling for chat, trigger pipeline and reinitialize SQLGenerator
        if is_enabling:
            logger.info(f"Triggering pipeline for newly enabled connector {connector_id}")

            # Trigger pipeline run (runs in background)
            await trigger_pipeline_for_connector(
                connector_id=connector_id,
                connector_type=connector['connector_type'],
                organization_id=organization_id
            )

            # Reinitialize SQLGenerator
            await reinitialize_sql_generator(organization_id)

        # Fetch updated connector
        updated_connector = await collection.find_one({'_id': ObjectId(connector_id)})

        return serialize_connector(updated_connector)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error toggling connector for chat: {e}")
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
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        result = await collection.delete_one({'_id': ObjectId(connector_id)})

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
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        connector = await collection.find_one({'_id': ObjectId(connector_id)})
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        # Test the connection
        result = ConnectorFactory.test_connection(
            connector_type=connector['connector_type'],
            config=connector['config']
        )

        # Update test results in database
        await collection.update_one(
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


@router.patch("/{connector_id}/toggle-chat")
async def toggle_chat_enabled(
    connector_id: str,
    enabled: bool,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Toggle whether a database connector is enabled for chat queries.

    Args:
        connector_id: Connector ID
        enabled: Whether to enable or disable for chat
        current_user: Current authenticated user

    Returns:
        Success status and updated connector info
    """
    try:
        mongodb_client = await get_mongodb_client()
        connectors_collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Get user's organization
        org_id = current_user.get('organization_id', 'default')

        # Verify connector belongs to user's organization
        connector = await connectors_collection.find_one({
            "_id": ObjectId(connector_id),
            "organization_id": org_id
        })

        if not connector:
            raise HTTPException(
                status_code=404,
                detail="Connector not found or access denied"
            )

        # Check if trying to enable
        if enabled:
            # Count currently enabled databases for this organization
            enabled_count = await connectors_collection.count_documents({
                "organization_id": org_id,
                "enabled_for_chat": True
            })

            # Get max allowed from settings (default to 2)
            from ..config import settings
            max_databases = getattr(settings, 'MAX_CHAT_DATABASES', 2)

            if enabled_count >= max_databases:
                raise HTTPException(
                    status_code=400,
                    detail=f"Maximum {max_databases} databases can be enabled for chat. Disable another database first."
                )

        # Update the connector
        result = await connectors_collection.update_one(
            {"_id": ObjectId(connector_id)},
            {
                "$set": {
                    "enabled_for_chat": enabled,
                    "enabled_at": datetime.utcnow() if enabled else None,
                    "enabled_by": current_user.get('id') if enabled else None,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to update connector"
            )

        logger.info(
            f"Toggled chat enabled for connector",
            connector_id=connector_id,
            enabled=enabled,
            user_id=current_user.get('id'),
            organization_id=org_id
        )

        return {
            "success": True,
            "connector_id": connector_id,
            "enabled_for_chat": enabled,
            "message": f"Connector {'enabled' if enabled else 'disabled'} for chat"
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error toggling chat enabled: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# BigQuery OAuth Endpoints (for keyless authentication)
# =====================================================

@router.get("/bigquery/oauth/status")
async def get_bigquery_oauth_status():
    """
    Check if BigQuery OAuth is configured and available.

    Returns:
        OAuth configuration status
    """
    try:
        from src.core.google_oauth_service import get_google_oauth_service
        from src.config import settings

        oauth_service = get_google_oauth_service()

        return {
            "success": True,
            "oauth_enabled": oauth_service.is_configured(),
            "wif_enabled": True,  # WIF is always available if google-auth is installed
            "mantrix_aws_account_id": settings.mantrix_aws_account_id,
            **oauth_service.get_oauth_config()
        }

    except Exception as e:
        logger.error(f"Error checking OAuth status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bigquery/oauth/authorize")
async def initiate_bigquery_oauth(
    redirect_uri: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Initiate Google OAuth flow for BigQuery access.

    Generates an authorization URL that the frontend should open in a popup.

    Args:
        redirect_uri: Optional custom redirect URI
        current_user: Current authenticated user

    Returns:
        Authorization URL and state token
    """
    try:
        from src.core.google_oauth_service import get_google_oauth_service

        oauth_service = get_google_oauth_service()

        if not oauth_service.is_configured():
            raise HTTPException(
                status_code=400,
                detail="Google OAuth is not configured. Contact administrator."
            )

        organization_id = current_user.get('organization_id', 'default')
        user_id = current_user.get('id')

        authorization_url, state = oauth_service.generate_authorization_url(
            organization_id=organization_id,
            user_id=user_id,
            redirect_uri=redirect_uri
        )

        logger.info(
            f"Generated OAuth authorization URL",
            user_id=user_id,
            organization_id=organization_id
        )

        return {
            "success": True,
            "authorization_url": authorization_url,
            "state": state
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bigquery/oauth/callback")
async def bigquery_oauth_callback(
    code: str,
    state: str,
    error: Optional[str] = None
):
    """
    Handle Google OAuth callback.

    This endpoint receives the authorization code from Google after user consent.
    The frontend should intercept this in the popup and send the code to complete the flow.

    Args:
        code: Authorization code from Google
        state: State token for CSRF protection
        error: Error message if authorization failed

    Returns:
        HTML page that posts result to parent window
    """
    from fastapi.responses import HTMLResponse

    if error:
        # Authorization failed
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <script>
                window.opener.postMessage({{
                    type: 'oauth_error',
                    error: '{error}'
                }}, window.location.origin);
                window.close();
            </script>
            <p>Authorization failed: {error}</p>
            <p>You can close this window.</p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    # Success - send code to parent window
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>OAuth Success</title></head>
    <body>
        <script>
            window.opener.postMessage({{
                type: 'oauth_success',
                code: '{code}',
                state: '{state}'
            }}, window.location.origin);
            window.close();
        </script>
        <p>Authorization successful!</p>
        <p>You can close this window.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/bigquery/oauth/complete")
async def complete_bigquery_oauth(
    code: str,
    state: str,
    project_id: str,
    dataset: str,
    name: str,
    location: Optional[str] = "US",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Complete the OAuth flow and create a BigQuery connector.

    Exchanges the authorization code for tokens and saves the connector.

    Args:
        code: Authorization code from Google
        state: State token for CSRF protection
        project_id: GCP project ID
        dataset: BigQuery dataset name
        name: Friendly name for the connector
        location: BigQuery location (default: US)
        current_user: Current authenticated user

    Returns:
        Created connector details
    """
    try:
        from src.core.google_oauth_service import get_google_oauth_service

        oauth_service = get_google_oauth_service()

        # Validate state token
        state_data = oauth_service.validate_state(state)
        if not state_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OAuth state token"
            )

        organization_id = current_user.get('organization_id', 'default')

        # Exchange code for tokens
        token_info = oauth_service.exchange_code_for_tokens(code)

        # Encrypt tokens for storage
        encrypted_tokens = oauth_service.encrypt_tokens(token_info)

        # Test the connection before saving
        from src.db.connectors.bigquery_connector import BigQueryConnector, AUTH_METHOD_OAUTH

        test_connector = BigQueryConnector(
            project_id=project_id,
            dataset_id=dataset,
            auth_method=AUTH_METHOD_OAUTH,
            oauth_credentials=token_info  # Use unencrypted for testing
        )

        try:
            test_connector.connect()
            # Execute test query
            test_result = test_connector.execute_query("SELECT 1 AS test")
            test_connector.disconnect()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {e}"
            )

        # Save to MongoDB
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        connector_doc = {
            'connector_type': 'bigquery',
            'name': name,
            'config': {
                'project_id': project_id,
                'dataset': dataset,
                'location': location,
                'auth_method': AUTH_METHOD_OAUTH
            },
            'oauth_credentials': encrypted_tokens,
            'status': 'connected',
            'organization_id': organization_id,
            'enabled_for_chat': False,
            'metadata': {
                'table_count': 0,
                'total_size': 'Unknown',
                'last_sync': None,
                'oauth_user_email': token_info.get('user_email')
            },
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'last_tested': datetime.now().isoformat(),
            'test_result': {
                'success': True
            }
        }

        result = await collection.insert_one(connector_doc)
        connector_doc['_id'] = result.inserted_id

        logger.info(
            f"Created BigQuery connector with OAuth: {name}",
            connector_id=str(result.inserted_id),
            organization_id=organization_id
        )

        # Trigger pipeline run
        await trigger_pipeline_for_connector(
            connector_id=str(result.inserted_id),
            connector_type='bigquery',
            organization_id=organization_id
        )

        # Reinitialize SQLGenerator
        await reinitialize_sql_generator(organization_id)

        return serialize_connector(connector_doc)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error completing OAuth flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
