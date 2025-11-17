"""
Control Center API Routes - Real-time system monitoring and management
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from datetime import datetime
import structlog

from ..core.system_monitor import get_system_monitor
from ..core.sql_generator import SQLGenerator
from .routes import get_sql_generator, get_weaviate_client

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/control-center", tags=["control-center"])


@router.get("/system-health")
async def get_system_health(
    generator: SQLGenerator = Depends(get_sql_generator)
):
    """
    Get comprehensive system health status

    Returns:
        - System metrics (CPU, memory, disk)
        - Service health (BigQuery, Redis, Weaviate, MongoDB)
        - Process information
        - Overall health score
    """
    try:
        monitor = get_system_monitor()

        # Collect current system metrics
        system_metrics = monitor.collect_metrics()

        # Check service health
        services = {
            'bigquery': generator.bq_client,
            'redis': generator.cache_manager.redis if generator.cache_manager else None,
            'weaviate': get_weaviate_client(),
        }

        service_health = monitor.check_service_health(services)

        # Get process info
        process_info = monitor.get_process_info()

        # Calculate overall health score
        healthy_services = sum(1 for s in service_health.values() if s.get('status') == 'healthy')
        total_services = len(service_health)
        health_score = (healthy_services / total_services * 100) if total_services > 0 else 0

        # Determine overall status
        if health_score >= 90:
            overall_status = 'healthy'
        elif health_score >= 70:
            overall_status = 'warning'
        else:
            overall_status = 'error'

        return {
            "success": True,
            "overall_status": overall_status,
            "health_score": round(health_score, 1),
            "system_metrics": system_metrics,
            "services": service_health,
            "process": process_info,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics-history")
async def get_metrics_history(hours: int = 24):
    """
    Get historical metrics data

    Args:
        hours: Number of hours of history to return (default: 24)
    """
    try:
        monitor = get_system_monitor()
        history = monitor.get_metrics_history(hours=hours)

        return {
            "success": True,
            "history": history,
            "hours": hours,
            "data_points": len(history)
        }

    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def get_services_detail(
    generator: SQLGenerator = Depends(get_sql_generator)
):
    """
    Get detailed information about all connected services
    """
    try:
        services_info = []

        # API Server
        services_info.append({
            "id": "api",
            "name": "API Server",
            "type": "api",
            "status": "healthy",
            "endpoint": "http://localhost:8000/api/v1",
            "version": "0.1.0",
        })

        # BigQuery
        try:
            bq = generator.bq_client
            tables = bq.list_tables()
            services_info.append({
                "id": "bigquery",
                "name": "BigQuery",
                "type": "database",
                "status": "healthy",
                "endpoint": f"Google Cloud Platform",
                "project": bq.project_id,
                "dataset": bq.dataset_id,
                "tables": len(tables),
            })
        except Exception as e:
            services_info.append({
                "id": "bigquery",
                "name": "BigQuery",
                "type": "database",
                "status": "error",
                "error": str(e),
            })

        # Redis Cache
        if generator.cache_manager:
            try:
                redis = generator.cache_manager.redis
                info = redis.info()
                services_info.append({
                    "id": "redis",
                    "name": "Redis Cache",
                    "type": "cache",
                    "status": "healthy",
                    "memory_used_mb": round(info.get('used_memory', 0) / (1024**2), 2),
                    "connected_clients": info.get('connected_clients', 0),
                    "total_commands": info.get('total_commands_processed', 0),
                })
            except Exception as e:
                services_info.append({
                    "id": "redis",
                    "name": "Redis Cache",
                    "type": "cache",
                    "status": "error",
                    "error": str(e),
                })
        else:
            services_info.append({
                "id": "redis",
                "name": "Redis Cache",
                "type": "cache",
                "status": "disabled",
            })

        # Weaviate
        try:
            wv = get_weaviate_client()
            # Weaviate v4 API uses collections instead of schema
            if wv and wv.client:
                # Get list of collections
                collections = list(wv.client.collections.list_all())
                services_info.append({
                    "id": "weaviate",
                    "name": "Weaviate Vector DB",
                    "type": "vectordb",
                    "status": "healthy",
                    "collections": len(collections),
                })
            else:
                services_info.append({
                    "id": "weaviate",
                    "name": "Weaviate Vector DB",
                    "type": "vectordb",
                    "status": "disconnected",
                    "error": "Client not initialized",
                })
        except Exception as e:
            services_info.append({
                "id": "weaviate",
                "name": "Weaviate Vector DB",
                "type": "vectordb",
                "status": "error",
                "error": str(e),
            })

        return {
            "success": True,
            "services": services_info,
            "total": len(services_info),
            "healthy": sum(1 for s in services_info if s.get('status') == 'healthy'),
        }

    except Exception as e:
        logger.error(f"Error getting services detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/types")
async def get_cache_types(
    generator: SQLGenerator = Depends(get_sql_generator)
):
    """
    Get statistics for each cache type
    """
    if not generator.cache_manager:
        raise HTTPException(status_code=503, detail="Cache is not enabled")

    try:
        cache_manager = generator.cache_manager
        redis = cache_manager.redis

        # Get all cache keys grouped by type
        cache_types = []

        # SQL Generation Cache
        sql_keys = redis.keys(f"{cache_manager.PREFIX_SQL}*")
        cache_types.append({
            "id": "sql_generation",
            "name": "SQL Generation",
            "description": "Generated SQL queries from natural language",
            "ttl_seconds": cache_manager.TTL_SQL_FREQUENT,  # Using frequent TTL as primary
            "keys": len(sql_keys) if sql_keys else 0,
            "enabled": True,
        })

        # Schema Cache
        schema_keys = redis.keys(f"{cache_manager.PREFIX_SCHEMA}*")
        cache_types.append({
            "id": "schema",
            "name": "Schema Cache",
            "description": "Database table schemas and metadata",
            "ttl_seconds": cache_manager.TTL_SCHEMA,
            "keys": len(schema_keys) if schema_keys else 0,
            "enabled": True,
        })

        # Embedding Cache
        embedding_keys = redis.keys(f"{cache_manager.PREFIX_EMBEDDING}*")
        cache_types.append({
            "id": "embedding",
            "name": "Embeddings",
            "description": "Vector embeddings for semantic search",
            "ttl_seconds": cache_manager.TTL_EMBEDDING,
            "keys": len(embedding_keys) if embedding_keys else 0,
            "enabled": True,
        })

        # Validation Cache
        validation_keys = redis.keys(f"{cache_manager.PREFIX_VALIDATION}*")
        cache_types.append({
            "id": "validation",
            "name": "Validation Cache",
            "description": "Query validation results",
            "ttl_seconds": cache_manager.TTL_VALIDATION,
            "keys": len(validation_keys) if validation_keys else 0,
            "enabled": True,
        })

        # Get overall stats
        stats = cache_manager.get_stats()

        # Calculate total keys from all cache types
        total_keys = sum(ct["keys"] for ct in cache_types)

        # Get memory info from Redis
        redis_info = stats.get("redis_info", {})
        memory_used_mb = 0
        if "used_memory_human" in redis_info:
            # Parse memory from format like "1.74M" or "156K"
            mem_str = redis_info["used_memory_human"]
            if "M" in mem_str:
                memory_used_mb = float(mem_str.replace("M", ""))
            elif "K" in mem_str:
                memory_used_mb = float(mem_str.replace("K", "")) / 1024
            elif "G" in mem_str:
                memory_used_mb = float(mem_str.replace("G", "")) * 1024

        return {
            "success": True,
            "cache_types": cache_types,
            "total_keys": total_keys,
            "memory_used_mb": round(memory_used_mb, 2),
            "hit_rate": round(stats.get("hit_rate_percent", 0), 1),
        }

    except Exception as e:
        logger.error(f"Error getting cache types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/{cache_type}")
async def clear_cache_type(
    cache_type: str,
    generator: SQLGenerator = Depends(get_sql_generator)
):
    """
    Clear a specific cache type

    Args:
        cache_type: Type of cache to clear (sql_generation, schema, embedding, validation)
    """
    if not generator.cache_manager:
        raise HTTPException(status_code=503, detail="Cache is not enabled")

    try:
        cache_manager = generator.cache_manager
        redis = cache_manager.redis

        # Map cache type to prefix
        prefix_map = {
            "sql_generation": cache_manager.PREFIX_SQL,
            "schema": cache_manager.PREFIX_SCHEMA,
            "embedding": cache_manager.PREFIX_EMBEDDING,
            "validation": cache_manager.PREFIX_VALIDATION,
        }

        if cache_type not in prefix_map:
            raise HTTPException(status_code=400, detail=f"Unknown cache type: {cache_type}")

        prefix = prefix_map[cache_type]
        keys = redis.keys(f"{prefix}*")

        deleted = 0
        if keys:
            deleted = redis.delete(*keys)

        return {
            "success": True,
            "cache_type": cache_type,
            "keys_deleted": deleted,
            "message": f"Cleared {deleted} keys from {cache_type} cache"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache type: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-sources")
async def get_data_sources(
    generator: SQLGenerator = Depends(get_sql_generator)
):
    """
    Get information about all data sources and connections
    """
    try:
        data_sources = {
            "databases": [],
            "apis": [],
            "integrations": []
        }

        # BigQuery
        try:
            bq = generator.bq_client
            tables = bq.list_tables()

            # Get total size (simplified - would need actual query for real size)
            data_sources["databases"].append({
                "id": "bigquery-prod",
                "name": "BigQuery Production",
                "type": "bigquery",
                "status": "connected",
                "host": f"{bq.project_id}.{bq.location}" if hasattr(bq, 'location') else bq.project_id,
                "database": bq.dataset_id,
                "lastSync": "Real-time",
                "tables": len(tables),
                "config": {
                    "project": bq.project_id,
                    "dataset": bq.dataset_id,
                }
            })
        except Exception as e:
            data_sources["databases"].append({
                "id": "bigquery-prod",
                "name": "BigQuery Production",
                "type": "bigquery",
                "status": "disconnected",
                "error": str(e)
            })

        # Redis
        if generator.cache_manager:
            try:
                redis = generator.cache_manager.redis
                info = redis.info()
                data_sources["integrations"].append({
                    "id": "redis-cache",
                    "name": "Redis Cache",
                    "type": "cache",
                    "status": "connected",
                    "endpoint": "localhost:6379",  # Would need to get from config
                    "memory_used_mb": round(info.get('used_memory', 0) / (1024**2), 2),
                    "keys": info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                })
            except Exception as e:
                data_sources["integrations"].append({
                    "id": "redis-cache",
                    "name": "Redis Cache",
                    "type": "cache",
                    "status": "error",
                    "error": str(e)
                })

        # Weaviate
        try:
            wv = get_weaviate_client()
            if wv and wv.client:
                # Weaviate v4 API uses collections instead of schema
                collections = list(wv.client.collections.list_all())
                data_sources["integrations"].append({
                    "id": "weaviate-vector",
                    "name": "Weaviate Vector DB",
                    "type": "vectordb",
                    "status": "healthy",
                    "endpoint": "http://localhost:8080",  # Would need from config
                    "collections": len(collections),
                })
            else:
                data_sources["integrations"].append({
                    "id": "weaviate-vector",
                    "name": "Weaviate Vector DB",
                    "type": "vectordb",
                    "status": "disconnected",
                    "error": "Client not initialized"
                })
        except Exception as e:
            data_sources["integrations"].append({
                "id": "weaviate-vector",
                "name": "Weaviate Vector DB",
                "type": "vectordb",
                "status": "warning",
                "error": str(e)
            })

        # External Database Connectors (from connector management)
        try:
            from ..db.mongodb_client import get_mongodb_client
            from bson import ObjectId

            mongo_client = get_mongodb_client()
            db = mongo_client.get_database()
            connectors_collection = db["database_connectors"]

            external_connectors = list(connectors_collection.find())

            for connector in external_connectors:
                connector_data = {
                    "id": str(connector['_id']),
                    "name": connector['name'],
                    "type": connector['connector_type'],
                    "status": connector.get('status', 'disconnected'),
                    "lastSync": connector.get('last_tested', 'Never'),
                    "config": {
                        # Include non-sensitive config summary
                        k: v for k, v in connector.get('config', {}).items()
                        if k not in ['password', 'api_key', 'secret', 'credentials', 'private_key']
                    }
                }

                # Add type-specific fields
                if connector['connector_type'] == 'snowflake':
                    config = connector.get('config', {})
                    connector_data["host"] = f"{config.get('account', 'unknown')}.snowflakecomputing.com"
                    connector_data["database"] = config.get('database', 'Unknown')
                    connector_data["warehouse"] = config.get('warehouse', 'Unknown')

                elif connector['connector_type'] == 'bigquery':
                    config = connector.get('config', {})
                    connector_data["host"] = config.get('project_id', 'Unknown')
                    connector_data["database"] = config.get('dataset_id', 'Unknown')

                elif connector['connector_type'] == 'postgresql':
                    config = connector.get('config', {})
                    connector_data["host"] = config.get('host', 'Unknown')
                    connector_data["database"] = config.get('database', 'Unknown')
                    connector_data["port"] = config.get('port', 5432)

                data_sources["databases"].append(connector_data)

        except Exception as e:
            logger.warning(f"Could not fetch external connectors: {e}")

        # LLM APIs (from environment/config)
        import os
        if os.getenv("ANTHROPIC_API_KEY"):
            data_sources["apis"].append({
                "id": "anthropic-claude",
                "name": "Anthropic Claude",
                "type": "llm",
                "status": "connected",
                "endpoint": "https://api.anthropic.com/v1",
                "model": "claude-3-5-sonnet-20241022",
            })

        if os.getenv("OPENAI_API_KEY"):
            data_sources["apis"].append({
                "id": "openai-embeddings",
                "name": "OpenAI Embeddings",
                "type": "embeddings",
                "status": "connected",
                "endpoint": "https://api.openai.com/v1",
                "model": "text-embedding-3-small",
            })

        return {
            "success": True,
            "data_sources": data_sources,
            "summary": {
                "total_databases": len(data_sources["databases"]),
                "total_apis": len(data_sources["apis"]),
                "total_integrations": len(data_sources["integrations"]),
                "total_connected": sum(
                    1 for items in data_sources.values()
                    for item in items
                    if item.get('status') in ['connected', 'healthy']
                )
            }
        }

    except Exception as e:
        logger.error(f"Error getting data sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))
