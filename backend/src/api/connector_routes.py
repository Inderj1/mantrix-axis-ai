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
import os
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
    sensitive_fields = [
        'password', 'api_key', 'secret', 'credentials', 'private_key',
        'private_key_passphrase', 'oauth_access_token', 'access_token', 'refresh_token',
        'programmatic_access_token'
    ]
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
        "organization_id": connector_doc.get('organization_id'),
        # Schema sync status
        "sync_status": connector_doc.get('sync_status', 'pending'),
        "sync_error": connector_doc.get('sync_error'),
        "sync_started_at": connector_doc.get('sync_started_at'),
        "sync_completed_at": connector_doc.get('sync_completed_at')
    }


async def trigger_pipeline_for_connector(connector_id: str, connector_type: str, organization_id: str):
    """
    Trigger pipeline run for a specific connector to extract schema and build RDF/vectors.

    This function:
    1. Loads connector config from MongoDB (including OAuth credentials)
    2. Decrypts OAuth credentials if applicable
    3. Extracts schema using connector-specific config
    4. Builds RDF triples and vector embeddings
    5. Updates connector metadata with sync status

    Args:
        connector_id: Unique connector identifier
        connector_type: Type of database connector
        organization_id: Organization ID

    Returns:
        Task that runs the pipeline in the background
    """
    import asyncio
    from src.pipeline.multi_db_schema_extractor import MultiDatabaseSchemaExtractor
    from src.pipeline.rdf_builder import RDFBuilder
    from src.db.weaviate_client import WeaviateClient
    from src.core.embeddings import EmbeddingService

    async def run_pipeline():
        sync_error = None
        tables_extracted = 0

        try:
            logger.info(f"Starting pipeline for connector {connector_id} ({connector_type})")

            # Load connector document from MongoDB
            mongodb_client = await get_mongodb_client()
            collection = mongodb_client.db[CONNECTORS_COLLECTION]

            connector_doc = await collection.find_one({'_id': ObjectId(connector_id)})
            if not connector_doc:
                raise ValueError(f"Connector {connector_id} not found")

            # Update sync status to 'syncing'
            await collection.update_one(
                {'_id': ObjectId(connector_id)},
                {'$set': {
                    'sync_status': 'syncing',
                    'sync_started_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }}
            )

            # Build connector config
            config = connector_doc.get('config', {}).copy()

            # Handle OAuth credentials if applicable
            if config.get('auth_method') == 'oauth' and connector_doc.get('oauth_credentials'):
                try:
                    from src.core.google_oauth_service import get_google_oauth_service
                    oauth_service = get_google_oauth_service()
                    decrypted_creds = oauth_service.decrypt_tokens(connector_doc['oauth_credentials'])
                    config['oauth_credentials'] = decrypted_creds
                    logger.info(f"Decrypted OAuth credentials for connector {connector_id}")
                except Exception as e:
                    raise ValueError(f"Failed to decrypt OAuth credentials: {e}")

            # Extract schema using connector-specific config
            extractor = MultiDatabaseSchemaExtractor(organization_id=organization_id)
            tables = extractor.extract_schema_for_connector(
                connector_type=connector_type,
                connector_config=config,
                organization_id=organization_id
            )

            tables_extracted = len(tables)

            if not tables:
                logger.warning(f"No tables extracted for connector {connector_id}")
            else:
                logger.info(f"Extracted {tables_extracted} tables from connector {connector_id}")

                # Build RDF triples using simplified approach
                try:
                    from src.pipeline.schema_extractor import TableSchemaSnapshot, SchemaExtractor
                    from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph

                    # Convert tables to TableSchemaSnapshot objects
                    snapshots = []
                    for table in tables:
                        snapshot = TableSchemaSnapshot(
                            table_name=table['table_name'],
                            database_type=connector_type,
                            organization_id=organization_id,
                            dataset=table.get('dataset', table.get('schema', '')),
                            project=table.get('project', config.get('project_id', '')),
                            description=table.get('description', ''),
                            row_count=table.get('row_count', 0),
                            size_bytes=table.get('size_bytes', 0),
                            created_at=table.get('created_at'),
                            modified_at=table.get('modified_at'),
                            columns=table.get('columns', []),
                            schema_hash=table.get('schema_hash', ''),
                            snapshot_timestamp=datetime.now().isoformat(),
                            version=table.get('version', 1)
                        )
                        snapshots.append(snapshot)

                    # Build RDF using the builder (connector-aware to prevent race conditions)
                    rdf_builder = RDFBuilder()
                    rdf_result = rdf_builder.build_from_snapshots(
                        snapshots,
                        include_stats=True,
                        discover_relationships=True,
                        connector_id=connector_id,
                        database_type=connector_type,
                        organization_id=organization_id
                    )

                    # Save to table_metadata_kg.ttl
                    rdf_builder.export_to_file("table_metadata_kg.ttl", format="turtle")

                    logger.info(
                        f"Built RDF triples for {tables_extracted} tables: "
                        f"{rdf_result.triples_added} triples, {rdf_result.relationships_discovered} relationships"
                    )
                except Exception as e:
                    logger.error(f"Failed to build RDF: {e}")
                    # Continue - don't fail entire pipeline for RDF errors

                # Build vector embeddings (enriched with RDF relationships)
                try:
                    weaviate_client = WeaviateClient()
                    embedding_service = EmbeddingService()

                    # Delete old schemas for this connector before indexing new ones
                    try:
                        deleted_count = weaviate_client.delete_schemas_by_connector(connector_id)
                        logger.info(f"Deleted {deleted_count} old schemas for connector {connector_id}")
                    except Exception as delete_error:
                        logger.warning(f"Failed to delete old schemas: {delete_error}")

                    for table in tables:
                        # Add connector_id to table for Weaviate indexing
                        table['connector_id'] = connector_id

                        # Query RDF for discovered relationships to enrich the vector
                        related_tables_text = ""
                        try:
                            relationships = rdf_builder.query_relationships(table['table_name'])
                            if relationships:
                                # Format: "related to orders via customer_id, related to products via product_id"
                                rel_parts = []
                                for rel in relationships[:5]:  # Limit to top 5 relationships
                                    rel_parts.append(f"{rel['target_table']} via {rel['source_column']}")
                                related_tables_text = f"\nRelated Tables: {', '.join(rel_parts)}"
                        except Exception as rel_error:
                            logger.debug(f"Could not get relationships for {table['table_name']}: {rel_error}")

                        # Generate embedding for table (enriched with relationships)
                        combined_text = f"""
                        Table: {table['table_name']}
                        Dataset: {table.get('dataset', table.get('schema', ''))}
                        Description: {table.get('description', 'No description')}
                        Columns: {', '.join([col['name'] for col in table.get('columns', [])])}{related_tables_text}
                        """
                        embedding = embedding_service.generate_embedding(combined_text)

                        # Index in Weaviate
                        weaviate_client.index_table_schema(table, embedding)

                    logger.info(f"Built vector embeddings for {tables_extracted} tables with connector_id={connector_id}")
                except Exception as e:
                    logger.error(f"Failed to build vectors: {e}")
                    # Continue - don't fail entire pipeline for vector errors

            # Calculate total_size from extracted tables
            total_bytes = sum(table.get('size_bytes', 0) or 0 for table in tables)
            if total_bytes > 0:
                # Format bytes to human-readable string
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if total_bytes < 1024:
                        total_size = f"{total_bytes:.1f} {unit}" if unit != 'B' else f"{total_bytes} {unit}"
                        break
                    total_bytes /= 1024
                else:
                    total_size = f"{total_bytes:.1f} PB"
            else:
                total_size = "Unknown"

            # Update connector metadata with success
            await collection.update_one(
                {'_id': ObjectId(connector_id)},
                {'$set': {
                    'sync_status': 'success',
                    'sync_completed_at': datetime.now().isoformat(),
                    'sync_error': None,
                    'metadata.last_sync': datetime.now().isoformat(),
                    'metadata.table_count': tables_extracted,
                    'metadata.total_size': total_size,
                    'updated_at': datetime.now().isoformat()
                }}
            )

            logger.info(f"Pipeline completed successfully for connector {connector_id}: {tables_extracted} tables")

        except Exception as e:
            sync_error = str(e)
            logger.error(f"Error running pipeline for connector {connector_id}: {e}")

            # Update connector with error status
            try:
                mongodb_client = await get_mongodb_client()
                collection = mongodb_client.db[CONNECTORS_COLLECTION]
                await collection.update_one(
                    {'_id': ObjectId(connector_id)},
                    {'$set': {
                        'sync_status': 'failed',
                        'sync_completed_at': datetime.now().isoformat(),
                        'sync_error': sync_error,
                        'updated_at': datetime.now().isoformat()
                    }}
                )
            except Exception as update_error:
                logger.error(f"Failed to update sync error status: {update_error}")

    # Create background task
    asyncio.create_task(run_pipeline())
    logger.info(f"Pipeline task created for connector {connector_id}")


async def reinitialize_sql_generator(organization_id: str):
    """
    Invalidate SQLGenerator for an organization after connector changes.

    Uses the centralized singleton module which:
    1. Signals invalidation via Redis for cross-worker sync
    2. Clears the local cached instance
    3. New instance is created on next query with updated connector_ids

    Args:
        organization_id: Organization ID
    """
    try:
        from src.core.sql_generator_singleton import invalidate_sql_generator

        logger.info(f"Invalidating SQLGenerator for organization: {organization_id}")

        # Invalidate cached instance - will be recreated on next query
        invalidated = invalidate_sql_generator(organization_id=organization_id)

        if invalidated:
            logger.info(f"SQLGenerator invalidated for organization: {organization_id}")
        else:
            logger.debug(f"No cached SQLGenerator to invalidate for: {organization_id}")

    except Exception as e:
        logger.error(f"Error invalidating SQLGenerator for {organization_id}: {e}")


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

        # Check permissions if user is authenticated (admins can test any connector)
        is_admin = current_user.get("is_admin", False) if current_user else False
        if target_user_id and not is_admin:
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
            },
            # Initialize sync status
            'sync_status': 'pending',
            'sync_error': None,
            'sync_started_at': None,
            'sync_completed_at': None
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

        # Per-type uniqueness: Only one connector per database type can be enabled
        # Auto-deactivate any other connector of same type when enabling
        deactivated_connector_name = None
        if is_enabling:
            connector_type = connector.get('connector_type')
            existing_enabled = await collection.find_one({
                "organization_id": organization_id,
                "connector_type": connector_type,
                "enabled_for_chat": True,
                "_id": {"$ne": ObjectId(connector_id)}  # Exclude self
            })

            if existing_enabled:
                # Auto-deactivate the existing connector of same type
                await collection.update_one(
                    {"_id": existing_enabled["_id"]},
                    {"$set": {"enabled_for_chat": False, "updated_at": datetime.now().isoformat()}}
                )
                deactivated_connector_name = existing_enabled.get("name", str(existing_enabled["_id"]))
                logger.info(
                    f"Auto-deactivated connector '{deactivated_connector_name}' ({connector_type}) "
                    f"to enable connector '{connector.get('name', connector_id)}'"
                )

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

        # If enabling for chat, trigger pipeline to sync schemas
        if is_enabling:
            logger.info(f"Triggering pipeline for newly enabled connector {connector_id}")

            # Trigger pipeline run (runs in background)
            await trigger_pipeline_for_connector(
                connector_id=connector_id,
                connector_type=connector['connector_type'],
                organization_id=organization_id
            )

        # Always invalidate SQLGenerator when chat status changes (enable OR disable)
        # This ensures queries use the updated list of enabled connectors
        if was_enabled != enabled:
            await reinitialize_sql_generator(organization_id)

        # Fetch updated connector
        updated_connector = await collection.find_one({'_id': ObjectId(connector_id)})

        # Include deactivated connector info in response
        response = serialize_connector(updated_connector)
        if deactivated_connector_name:
            response["deactivated_connector"] = deactivated_connector_name
        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error toggling connector for chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str):
    """
    Delete a connector configuration and its associated Weaviate schemas.

    Args:
        connector_id: Unique connector identifier

    Returns:
        Success message
    """
    try:
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Fetch connector first to get organization_id for invalidation
        connector = await collection.find_one({'_id': ObjectId(connector_id)})
        organization_id = connector.get('organization_id', 'default') if connector else 'default'

        # Delete from MongoDB
        result = await collection.delete_one({'_id': ObjectId(connector_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")

        # Clean up Weaviate schemas for this connector
        schemas_deleted = 0
        try:
            from src.db.weaviate_client import WeaviateClient
            weaviate_client = WeaviateClient()
            schemas_deleted = weaviate_client.delete_schemas_by_connector(connector_id)
            logger.info(f"Deleted {schemas_deleted} Weaviate schemas for connector {connector_id}")
        except Exception as e:
            logger.warning(f"Failed to delete Weaviate schemas for connector {connector_id}: {e}")

        # Invalidate SQLGenerator to pick up connector deletion
        await reinitialize_sql_generator(organization_id)

        logger.info(f"Deleted connector: {connector_id}")

        return {
            'success': True,
            'message': f'Connector {connector_id} deleted successfully',
            'schemas_deleted': schemas_deleted
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

        # Build config for testing
        config = connector['config'].copy()

        # For OAuth connectors, decrypt and include OAuth credentials
        if config.get('auth_method') == 'oauth' and connector.get('oauth_credentials'):
            try:
                from src.core.google_oauth_service import get_google_oauth_service
                oauth_service = get_google_oauth_service()
                decrypted_creds = oauth_service.decrypt_tokens(connector['oauth_credentials'])
                config['oauth_credentials'] = decrypted_creds
            except Exception as e:
                logger.error(f"Failed to decrypt OAuth credentials: {e}")
                return ConnectorTestResponse(
                    success=False,
                    connector_type=connector['connector_type'],
                    message="Failed to decrypt OAuth credentials",
                    error=str(e)
                )

        # Test the connection
        result = ConnectorFactory.test_connection(
            connector_type=connector['connector_type'],
            config=config
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

        # Invalidate SQLGenerator to pick up connector change
        await reinitialize_sql_generator(org_id)

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
    dataset_id: str,
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
        dataset_id: BigQuery dataset ID
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
            dataset_id=dataset_id,
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
                'dataset_id': dataset_id,
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
            },
            # Initialize sync status
            'sync_status': 'pending',
            'sync_error': None,
            'sync_started_at': None,
            'sync_completed_at': None
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


# =====================================================
# Admin/Utility Endpoints
# =====================================================

@router.post("/{connector_id}/sync")
async def sync_connector(
    connector_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Manually trigger schema sync for a specific connector.

    This endpoint:
    1. Finds the connector in MongoDB
    2. Triggers the pipeline to extract schema and build RDF/vectors
    3. Returns immediately (sync runs in background)

    Args:
        connector_id: Connector ID
        current_user: Current authenticated user

    Returns:
        Sync initiation status
    """
    try:
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Get user's organization
        org_id = current_user.get('organization_id', 'default')

        # Verify connector exists and belongs to user's organization
        connector = await collection.find_one({
            "_id": ObjectId(connector_id),
            "organization_id": org_id
        })

        if not connector:
            raise HTTPException(
                status_code=404,
                detail="Connector not found or access denied"
            )

        # Check if already syncing
        if connector.get('sync_status') == 'syncing':
            raise HTTPException(
                status_code=400,
                detail="Sync already in progress"
            )

        # Trigger pipeline
        await trigger_pipeline_for_connector(
            connector_id=connector_id,
            connector_type=connector['connector_type'],
            organization_id=org_id
        )

        logger.info(
            f"Sync initiated for connector",
            connector_id=connector_id,
            user_id=current_user.get('id'),
            organization_id=org_id
        )

        return {
            "success": True,
            "connector_id": connector_id,
            "message": "Sync initiated. Check connector status for progress."
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error initiating sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/clear-schema-cache")
async def clear_schema_cache(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Clear all schema cache data (admin only).

    This endpoint clears:
    1. Weaviate vector embeddings (TableSchemas collection)
    2. Redis SQL cache
    3. Jena RDF table metadata (by deleting table_metadata_kg.ttl)

    Use this when schema data is stale or corrupted.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Cleared data statistics
    """
    import os
    results = {
        "weaviate_cleared": False,
        "redis_cleared": False,
        "jena_cleared": False,
        "errors": []
    }

    # Clear Weaviate schemas
    try:
        from src.db.weaviate_client import WeaviateClient
        weaviate_client = WeaviateClient()
        weaviate_client.delete_all_schemas()
        results["weaviate_cleared"] = True
        logger.info("Cleared Weaviate schemas")
    except Exception as e:
        results["errors"].append(f"Weaviate: {str(e)}")
        logger.error(f"Failed to clear Weaviate: {e}")

    # Clear Redis SQL cache
    try:
        from src.core.cache_manager import CacheManager
        from src.config import settings
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port
        )
        deleted = cache_manager.clear_all_caches()
        results["redis_cleared"] = True
        results["redis_keys_deleted"] = deleted
        logger.info(f"Cleared {deleted} Redis cache keys")
    except Exception as e:
        results["errors"].append(f"Redis: {str(e)}")
        logger.error(f"Failed to clear Redis: {e}")

    # Clear Jena table metadata file
    try:
        table_metadata_file = "table_metadata_kg.ttl"
        if os.path.exists(table_metadata_file):
            os.remove(table_metadata_file)
            results["jena_cleared"] = True
            logger.info(f"Deleted {table_metadata_file}")
        else:
            results["jena_cleared"] = True
            results["jena_note"] = "File did not exist"
    except Exception as e:
        results["errors"].append(f"Jena: {str(e)}")
        logger.error(f"Failed to clear Jena: {e}")

    logger.info(
        "Schema cache cleared",
        results=results,
        user_id=current_user.get('id')
    )

    return {
        "success": len(results["errors"]) == 0,
        "message": "Schema cache cleared" if len(results["errors"]) == 0 else "Partial success",
        "details": results
    }


@router.post("/admin/resync-schemas")
async def resync_all_schemas(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Clear all Weaviate schemas and re-sync from all active connectors (admin only).

    This endpoint:
    1. Clears all TableSchema objects in Weaviate
    2. Clears Redis SQL cache (to prevent stale cache hits)
    3. Re-runs pipeline for each enabled connector
    4. Returns status of resync operations

    Use this when schema data is completely out of sync or after switching connectors.

    Args:
        current_user: Current authenticated admin user

    Returns:
        Resync status with details per connector
    """
    results = {
        "weaviate_cleared": False,
        "redis_cleared": False,
        "connectors_synced": [],
        "errors": []
    }

    # Step 1: Clear all Weaviate schemas
    try:
        from src.db.weaviate_client import WeaviateClient
        weaviate_client = WeaviateClient()
        weaviate_client.delete_all_schemas()
        results["weaviate_cleared"] = True
        logger.info("Cleared all Weaviate schemas for resync")
    except Exception as e:
        results["errors"].append(f"Weaviate clear: {str(e)}")
        logger.error(f"Failed to clear Weaviate for resync: {e}")

    # Step 2: Clear Redis SQL cache
    try:
        from src.core.cache_manager import CacheManager
        from src.config import settings
        cache_manager = CacheManager(
            host=settings.redis_host,
            port=settings.redis_port
        )
        deleted = cache_manager.clear_all_caches()
        results["redis_cleared"] = True
        results["redis_keys_deleted"] = deleted
        logger.info(f"Cleared {deleted} Redis cache keys for resync")
    except Exception as e:
        results["errors"].append(f"Redis clear: {str(e)}")
        logger.error(f"Failed to clear Redis for resync: {e}")

    # Step 3: Get all enabled connectors and trigger pipeline for each
    try:
        mongodb_client = await get_mongodb_client()
        collection = mongodb_client.db[CONNECTORS_COLLECTION]

        # Find all enabled connectors
        cursor = collection.find({
            "enabled_for_chat": True,
            "status": {"$in": ["connected", "active"]}
        })

        async for connector in cursor:
            connector_id = str(connector['_id'])
            connector_type = connector['connector_type']
            org_id = connector.get('organization_id', 'default')

            try:
                # Trigger pipeline for this connector
                await trigger_pipeline_for_connector(
                    connector_id=connector_id,
                    connector_type=connector_type,
                    organization_id=org_id
                )
                results["connectors_synced"].append({
                    "id": connector_id,
                    "name": connector.get('name', 'Unknown'),
                    "type": connector_type,
                    "organization_id": org_id,
                    "status": "pipeline_triggered"
                })
                logger.info(f"Triggered resync for connector {connector_id} ({connector.get('name')})")
            except Exception as e:
                results["connectors_synced"].append({
                    "id": connector_id,
                    "name": connector.get('name', 'Unknown'),
                    "type": connector_type,
                    "status": "failed",
                    "error": str(e)
                })
                results["errors"].append(f"Connector {connector_id}: {str(e)}")
                logger.error(f"Failed to trigger resync for connector {connector_id}: {e}")

    except Exception as e:
        results["errors"].append(f"Connector lookup: {str(e)}")
        logger.error(f"Failed to lookup connectors for resync: {e}")

    logger.info(
        "Schema resync initiated",
        results=results,
        user_id=current_user.get('id')
    )

    return {
        "success": len(results["errors"]) == 0,
        "message": f"Resync initiated for {len(results['connectors_synced'])} connectors",
        "details": results
    }


@router.post("/admin/recreate-weaviate-collection")
async def recreate_weaviate_collection(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Recreate the Weaviate TableSchemas collection with updated schema (admin only).

    Use this when the collection schema is outdated (e.g., missing connector_id property).
    After recreating, you should resync all connectors.
    """
    try:
        from src.db.weaviate_client import WeaviateClient
        weaviate_client = WeaviateClient()
        weaviate_client.recreate_collection()

        logger.info(
            "Weaviate collection recreated",
            user_id=current_user.get('id')
        )

        return {
            "success": True,
            "message": "Weaviate collection recreated with updated schema. Please resync connectors."
        }
    except Exception as e:
        logger.error(f"Failed to recreate Weaviate collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/diagnostics")
async def get_schema_diagnostics(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Get diagnostic information about Weaviate and Jena schema data (admin only).

    Returns counts and samples of indexed schemas to verify data integrity.
    """
    results = {
        "weaviate": {
            "connected": False,
            "total_schemas": 0,
            "schemas_with_connector_id": 0,
            "schemas_by_connector": {},
            "sample_schemas": []
        },
        "jena": {
            "connected": False,
            "triple_count": 0,
            "tables_in_graph": 0
        },
        "errors": []
    }

    # Check Weaviate
    try:
        from src.db.weaviate_client import WeaviateClient

        weaviate_client = WeaviateClient()
        results["weaviate"]["connected"] = True

        collection = weaviate_client.client.collections.get(weaviate_client.collection_name)

        # Get total count
        total_response = collection.aggregate.over_all(total_count=True)
        results["weaviate"]["total_schemas"] = total_response.total_count or 0

        # Get sample schemas (first 5)
        sample_response = collection.query.fetch_objects(
            limit=5,
            return_properties=["table_name", "database_type", "organization_id", "connector_id"]
        )
        for obj in sample_response.objects:
            results["weaviate"]["sample_schemas"].append({
                "table_name": obj.properties.get("table_name"),
                "database_type": obj.properties.get("database_type"),
                "organization_id": obj.properties.get("organization_id"),
                "connector_id": obj.properties.get("connector_id")
            })

        # Group by connector_id and calculate total schemas with connector_id
        # Note: We sum per-connector counts instead of using not_equal("") filter
        # which fails with Weaviate stopwords error
        schemas_with_connector_count = 0
        mongodb_client = await get_mongodb_client()
        connectors_coll = mongodb_client.db[CONNECTORS_COLLECTION]
        async for connector in connectors_coll.find({}):
            connector_id = str(connector['_id'])
            count = weaviate_client.get_schema_count_by_connector(connector_id)
            if count > 0:
                results["weaviate"]["schemas_by_connector"][connector.get('name', connector_id)] = count
                schemas_with_connector_count += count

        results["weaviate"]["schemas_with_connector_id"] = schemas_with_connector_count

    except Exception as e:
        results["errors"].append(f"Weaviate: {str(e)}")
        logger.error(f"Weaviate diagnostic failed: {e}")

    # Check Jena
    try:
        from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph, JENA_BACKEND
        import os

        results["jena"]["backend"] = JENA_BACKEND

        # For PostgreSQL backend, get authoritative count from database
        if JENA_BACKEND == "postgres":
            try:
                from src.core.knowledge_graph.jena_postgres_store import JenaPostgresStore
                graph_id = os.getenv("JENA_GRAPH_ID", "global")
                store = JenaPostgresStore(graph_id=graph_id)
                pg_status = store.health_check()
                results["jena"]["postgres"] = pg_status

                # Use PostgreSQL count as authoritative
                results["jena"]["connected"] = pg_status.get("connected", False)
                results["jena"]["triple_count"] = pg_status.get("triple_count", 0)
                results["jena"]["graph_id"] = graph_id

                # Count unique tables from database if we have triples
                if pg_status.get("triple_count", 0) > 0:
                    try:
                        # Query unique table subjects from PostgreSQL by RDF type
                        # Uses type predicate to count only actual Table entities, not columns
                        table_query = """
                            SELECT COUNT(DISTINCT subject) as count
                            FROM rdf_triples
                            WHERE graph_id = %s
                              AND predicate = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                              AND object LIKE '%%#Table'
                        """
                        from src.db.postgresql_client import PostgreSQLClient
                        db_client = PostgreSQLClient()
                        table_results = db_client.execute_query(table_query, (graph_id,))
                        results["jena"]["tables_in_graph"] = table_results[0]['count'] if table_results else 0
                    except Exception as e:
                        logger.warning(f"Failed to count tables in Jena: {e}")
                        results["jena"]["tables_in_graph"] = 0

            except Exception as e:
                results["errors"].append(f"Jena PostgreSQL: {str(e)}")
                logger.error(f"Jena PostgreSQL diagnostic failed: {e}")
        else:
            # For non-PostgreSQL backends, use in-memory graph
            jena_client = get_jena_knowledge_graph()
            if jena_client and jena_client.graph:
                results["jena"]["connected"] = True
                results["jena"]["triple_count"] = len(jena_client.graph)

                # Count unique tables by RDF type (not by name pattern)
                tables = set()
                for s, p, o in jena_client.graph:
                    # Only count subjects that have rdf:type of Table
                    if "type" in str(p).lower() and str(o).endswith("#Table"):
                        tables.add(str(s))
                results["jena"]["tables_in_graph"] = len(tables)

    except Exception as e:
        results["errors"].append(f"Jena: {str(e)}")
        logger.error(f"Jena diagnostic failed: {e}")

    return {
        "success": len(results["errors"]) == 0,
        "diagnostics": results
    }


@router.get("/admin/rdf-tables")
async def list_rdf_tables(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    List all tables in the Jena RDF store (admin only).

    This endpoint helps debug RDF indexing issues by showing exactly which
    tables are stored in the knowledge graph.

    Returns:
        List of tables with their metadata (name, database_type, organization_id, etc.)
    """
    from src.core.knowledge_graph.jena_singleton import JENA_BACKEND

    results = {
        "backend": JENA_BACKEND,
        "tables": [],
        "table_count": 0,
        "errors": []
    }

    try:
        if JENA_BACKEND == "postgres":
            from src.db.postgresql_client import PostgreSQLClient
            db_client = PostgreSQLClient()
            graph_id = os.getenv("JENA_GRAPH_ID", "global")

            # Query all table subjects and their metadata
            query = """
                WITH table_subjects AS (
                    SELECT DISTINCT subject
                    FROM rdf_triples
                    WHERE graph_id = %s
                      AND predicate = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
                      AND object LIKE '%%#Table'
                )
                SELECT
                    ts.subject,
                    MAX(CASE WHEN rt.predicate LIKE '%%tableName' THEN rt.object END) as table_name,
                    MAX(CASE WHEN rt.predicate LIKE '%%databaseType' THEN rt.object END) as database_type,
                    MAX(CASE WHEN rt.predicate LIKE '%%organizationId' THEN rt.object END) as organization_id,
                    MAX(CASE WHEN rt.predicate LIKE '%%dataset' THEN rt.object END) as dataset,
                    MAX(CASE WHEN rt.predicate LIKE '%%project' THEN rt.object END) as project,
                    MAX(CASE WHEN rt.predicate LIKE '%%rowCount' THEN rt.object END) as row_count
                FROM table_subjects ts
                LEFT JOIN rdf_triples rt ON ts.subject = rt.subject AND rt.graph_id = %s
                GROUP BY ts.subject
                ORDER BY ts.subject
            """

            table_results = db_client.execute_query(query, (graph_id, graph_id))

            for row in table_results:
                table_info = {
                    "subject_uri": row['subject'],
                    "table_name": row.get('table_name'),
                    "database_type": row.get('database_type'),
                    "organization_id": row.get('organization_id'),
                    "dataset": row.get('dataset'),
                    "project": row.get('project'),
                    "row_count": row.get('row_count')
                }
                results["tables"].append(table_info)

            results["table_count"] = len(results["tables"])
            results["graph_id"] = graph_id

        else:
            # For non-PostgreSQL backends, use in-memory graph
            from src.core.knowledge_graph.jena_singleton import get_jena_knowledge_graph
            from rdflib.namespace import RDF
            from rdflib import Namespace

            FIN = Namespace("http://example.com/finance#")
            SCHEMA = Namespace("http://schema.org/")

            jena_client = get_jena_knowledge_graph()
            if jena_client and jena_client.graph:
                for s, p, o in jena_client.graph.triples((None, RDF.type, FIN.Table)):
                    table_uri = str(s)
                    table_info = {
                        "subject_uri": table_uri,
                        "table_name": None,
                        "database_type": None,
                        "organization_id": None
                    }

                    # Get table name
                    for _, _, name in jena_client.graph.triples((s, SCHEMA.tableName, None)):
                        table_info["table_name"] = str(name)

                    # Get database type
                    for _, _, db_type in jena_client.graph.triples((s, SCHEMA.databaseType, None)):
                        table_info["database_type"] = str(db_type)

                    # Get organization ID
                    for _, _, org_id in jena_client.graph.triples((s, SCHEMA.organizationId, None)):
                        table_info["organization_id"] = str(org_id)

                    results["tables"].append(table_info)

                results["table_count"] = len(results["tables"])

    except Exception as e:
        results["errors"].append(str(e))
        logger.error(f"Failed to list RDF tables: {e}")

    return {
        "success": len(results["errors"]) == 0,
        "rdf_tables": results
    }


@router.post("/admin/test-vector-search")
async def test_vector_search(
    query: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Test vector search with different connector configurations (admin only).

    This endpoint helps diagnose why vector search might not return results from
    all enabled connectors.

    Args:
        query: The search query to test (e.g., "clients", "customers")

    Returns:
        Results from:
        - Combined search (all connectors)
        - Per-connector search (each connector separately)
    """
    organization_id = current_user.get("organization_id", "default")
    results = {
        "query": query,
        "organization_id": organization_id,
        "embedding_provider": None,
        "embedding_dimension": None,
        "combined_search": [],
        "per_connector_search": {},
        "analysis": {},
        "errors": []
    }

    try:
        from src.db.weaviate_client import WeaviateClient
        from src.core.embeddings import EmbeddingService

        # Initialize services
        weaviate_client = WeaviateClient()
        embedding_service = EmbeddingService()

        results["embedding_provider"] = embedding_service.provider_type
        results["embedding_dimension"] = embedding_service.dimension

        # Generate embedding for query
        embedding = embedding_service.generate_embedding(query)

        # Get enabled connectors for this organization
        mongodb_client = await get_mongodb_client()
        connectors_coll = mongodb_client.db[CONNECTORS_COLLECTION]

        enabled_connectors = []
        async for connector in connectors_coll.find({
            "organization_id": organization_id,
            "enabled_for_chat": True
        }):
            enabled_connectors.append({
                "id": str(connector['_id']),
                "name": connector.get('name', 'Unknown'),
                "type": connector.get('connector_type', 'unknown')
            })

        if not enabled_connectors:
            results["errors"].append("No enabled connectors found for organization")
            return results

        connector_ids = [c["id"] for c in enabled_connectors]

        # Test 1: Combined search (current behavior)
        combined_results = weaviate_client.search_similar_tables(
            query_embedding=embedding,
            limit=10,
            connector_ids=connector_ids,
            organization_id=organization_id
        )

        for r in combined_results:
            results["combined_search"].append({
                "table_name": r.get("table_name"),
                "database_type": r.get("database_type"),
                "connector_id": r.get("connector_id"),
                "distance": round(r.get("distance", 0), 4) if r.get("distance") else None
            })

        # Test 2: Per-connector search
        for connector in enabled_connectors:
            connector_results = weaviate_client.search_similar_tables(
                query_embedding=embedding,
                limit=5,
                connector_id=connector["id"],
                organization_id=organization_id
            )

            results["per_connector_search"][connector["name"]] = {
                "connector_id": connector["id"],
                "connector_type": connector["type"],
                "tables": [
                    {
                        "table_name": r.get("table_name"),
                        "distance": round(r.get("distance", 0), 4) if r.get("distance") else None
                    }
                    for r in connector_results
                ]
            }

        # Analysis
        db_types_in_combined = list(set(r.get("database_type") for r in combined_results if r.get("database_type")))
        results["analysis"] = {
            "enabled_connectors": len(enabled_connectors),
            "connector_types": [c["type"] for c in enabled_connectors],
            "combined_search_count": len(combined_results),
            "db_types_in_combined_results": db_types_in_combined,
            "all_connectors_represented": len(db_types_in_combined) == len(set(c["type"] for c in enabled_connectors)),
            "recommendation": None
        }

        # Add recommendation if not all connectors represented
        if not results["analysis"]["all_connectors_represented"]:
            missing_types = set(c["type"] for c in enabled_connectors) - set(db_types_in_combined)
            results["analysis"]["missing_connector_types"] = list(missing_types)
            results["analysis"]["recommendation"] = (
                f"Vector search is biased towards {db_types_in_combined}. "
                f"Tables from {list(missing_types)} are not making it into top results. "
                f"Consider implementing per-connector search to ensure all databases are represented."
            )

    except Exception as e:
        results["errors"].append(f"Error: {str(e)}")
        logger.error(f"Vector search test failed: {e}")

    return results
