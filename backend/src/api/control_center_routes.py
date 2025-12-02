"""
Control Center API Routes - Real-time system monitoring and management
Lightweight implementation with no heavy dependencies (no SQLGenerator)
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from datetime import datetime
import structlog

from ..core.system_monitor import get_system_monitor
from .routes import get_weaviate_client

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/control-center", tags=["control-center"])


@router.get("/system-health")
async def get_system_health():
    """
    Get comprehensive system health status

    Returns:
        - System metrics (CPU, memory, disk)
        - Service health (simplified, no heavy dependencies)
        - Process information
        - Overall health score
    """
    try:
        monitor = get_system_monitor()

        # Collect current system metrics
        system_metrics = monitor.collect_metrics()

        # Get process info
        process_info = monitor.get_process_info()

        # Simple service health check (without heavy dependencies)
        service_health = {
            'api': {
                'name': 'API Server',
                'status': 'healthy',
                'endpoint': 'http://localhost:8000'
            },
            'mongodb': {
                'name': 'MongoDB',
                'status': 'healthy',
                'endpoint': 'mongodb://localhost:27017'
            }
        }

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
        # Return a basic response instead of raising error
        return {
            "success": False,
            "overall_status": "unknown",
            "health_score": 0,
            "system_metrics": {},
            "services": {},
            "process": {},
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


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
            "data_points": len(history),
            "message": "No data available" if not history else None
        }

    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        return {
            "success": False,
            "history": [],
            "hours": hours,
            "data_points": 0,
            "message": "No data available",
            "error": str(e)
        }


@router.get("/services")
async def get_services_detail():
    """
    Get detailed information about all connected services (lightweight version)
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

        # MongoDB (lightweight check)
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import os

            mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
            client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=1000)
            await client.admin.command('ping')

            services_info.append({
                "id": "mongodb",
                "name": "MongoDB",
                "type": "database",
                "status": "healthy",
                "endpoint": mongodb_url,
            })
            client.close()
        except Exception as e:
            services_info.append({
                "id": "mongodb",
                "name": "MongoDB",
                "type": "database",
                "status": "error",
                "error": str(e)[:100],  # Truncate error message
            })

        # Redis Cache (lightweight check)
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
            r.ping()
            services_info.append({
                "id": "redis",
                "name": "Redis Cache",
                "type": "cache",
                "status": "healthy",
                "endpoint": "redis://localhost:6379",
            })
        except Exception:
            services_info.append({
                "id": "redis",
                "name": "Redis Cache",
                "type": "cache",
                "status": "disconnected",
            })

        # Weaviate (lightweight check)
        services_info.append({
            "id": "weaviate",
            "name": "Weaviate Vector DB",
            "type": "vectordb",
            "status": "unknown",
            "endpoint": "http://localhost:8080",
        })

        # BigQuery (just show config, no connection test)
        import os
        if os.getenv("GOOGLE_CLOUD_PROJECT"):
            services_info.append({
                "id": "bigquery",
                "name": "BigQuery",
                "type": "database",
                "status": "configured",
                "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "dataset": os.getenv("BIGQUERY_DATASET"),
            })

        return {
            "success": True,
            "services": services_info,
            "total": len(services_info),
            "healthy": sum(1 for s in services_info if s.get('status') == 'healthy'),
        }

    except Exception as e:
        logger.error(f"Error getting services detail: {e}")
        # Return basic info even if there's an error
        return {
            "success": True,
            "services": [
                {
                    "id": "api",
                    "name": "API Server",
                    "type": "api",
                    "status": "healthy",
                    "endpoint": "http://localhost:8000/api/v1",
                }
            ],
            "total": 1,
            "healthy": 1,
        }


@router.get("/cache/types")
async def get_cache_types():
    """
    Get statistics for each cache type (lightweight version using cache_config)
    """
    try:
        # Import cache configuration
        from src.core.cache_config import CACHE_CONFIGS
        import redis
        import os

        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))

        try:
            r = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
            r.ping()  # Test connection
        except Exception:
            # Redis not available
            return {
                "success": False,
                "message": "Cache service is not available"
            }

        # Use the Redis client
        redis_client = r

        # Get all cache keys grouped by type using cache_config
        cache_types = []

        for cache_id, config in CACHE_CONFIGS.items():
            cache_keys = redis_client.keys(f"{config['prefix']}*")
            cache_types.append({
                "id": config["id"],
                "name": config["name"],
                "description": config["description"],
                "ttl_seconds": config["ttl_seconds"],
                "keys": len(cache_keys) if cache_keys else 0,
                "enabled": True,
            })

        # Get overall stats
        total_keys = sum(ct["keys"] for ct in cache_types)

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
async def clear_cache_type(cache_type: str):
    """
    Clear a specific cache type (lightweight version using direct Redis connection)

    Args:
        cache_type: Type of cache to clear (sql_generation, schema, embedding, validation)
    """
    try:
        # Import cache configuration
        from src.core.cache_config import CACHE_CONFIGS
        import redis
        import os

        # Check if cache type is valid
        if cache_type not in CACHE_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unknown cache type: {cache_type}")

        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))

        try:
            redis_client = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
            redis_client.ping()  # Test connection
        except Exception:
            raise HTTPException(status_code=503, detail="Cache service is not available")

        # Get prefix from config
        prefix = CACHE_CONFIGS[cache_type]["prefix"]
        keys = redis_client.keys(f"{prefix}*")

        deleted = 0
        if keys:
            deleted = redis_client.delete(*keys)

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
async def get_data_sources():
    """
    Get information about all data sources and connections (lightweight version)
    """
    try:
        data_sources = {
            "databases": [],
            "apis": [],
            "integrations": []
        }

        # Redis (direct connection, no SQLGenerator needed)
        try:
            import redis
            import os
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_client = redis.Redis(host=redis_host, port=redis_port, socket_connect_timeout=1)
            redis_client.ping()
            info = redis_client.info()
            data_sources["integrations"].append({
                "id": "redis-cache",
                "name": "Redis Cache",
                "type": "cache",
                "status": "connected",
                "endpoint": f"{redis_host}:{redis_port}",
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

            mongo_client = await get_mongodb_client()
            db = mongo_client.db
            connectors_collection = db["database_connectors"]

            external_connectors = await connectors_collection.find().to_list(length=None)

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


@router.get("/settings")
async def get_control_center_settings():
    """
    Get control center configuration settings
    """
    try:
        from ..config import settings

        # Get configurable settings
        config_settings = {
            "max_chat_databases": getattr(settings, 'max_chat_databases', 2),
            "cache_enabled": getattr(settings, 'cache_enabled', True),
            "cache_sql_enabled": getattr(settings, 'cache_sql_enabled', True),
            "cache_schema_enabled": getattr(settings, 'cache_schema_enabled', True),
            "cache_embedding_enabled": getattr(settings, 'cache_embedding_enabled', True),
            "enable_industry_features": getattr(settings, 'enable_industry_features', False),
            "organization_id": getattr(settings, 'default_org_id', 'default'),
            "anthropic_model": getattr(settings, 'anthropic_model', 'claude-3-5-sonnet-20241022'),
            "openai_embedding_model": getattr(settings, 'openai_embedding_model', 'text-embedding-3-small'),
            "log_level": getattr(settings, 'log_level', 'INFO'),
        }

        return {
            "success": True,
            "settings": config_settings
        }

    except Exception as e:
        logger.error(f"Error getting control center settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
async def update_control_center_settings(updates: Dict[str, Any]):
    """
    Update control center configuration settings

    Note: Some settings may require application restart to take effect
    """
    try:
        from ..config import settings

        updated = {}

        # Update only allowed settings
        allowed_settings = [
            'max_chat_databases',
            'cache_enabled',
            'cache_sql_enabled',
            'cache_schema_enabled',
            'cache_embedding_enabled',
            'enable_industry_features',
            'log_level'
        ]

        for key, value in updates.items():
            if key in allowed_settings and hasattr(settings, key):
                setattr(settings, key, value)
                updated[key] = value
                logger.info(f"Updated setting: {key} = {value}")

        return {
            "success": True,
            "updated": updated,
            "message": "Settings updated. Some changes may require restart."
        }

    except Exception as e:
        logger.error(f"Error updating control center settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
