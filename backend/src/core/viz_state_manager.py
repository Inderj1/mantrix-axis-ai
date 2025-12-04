"""
Visualization State Manager for dashboard state persistence.

Stores dashboard visualization state in Redis for instant restore:
- Active filters and filter values
- Drill-down paths and breadcrumbs
- Widget configurations and cached data
- Cross-filter relationships
"""

import json
import redis
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from src.config import settings

logger = structlog.get_logger()


class VizStateManager:
    """
    Manages visualization state in Redis for instant dashboard restore.

    Supports:
    - Full dashboard state save/restore
    - Per-widget state caching
    - Filter state persistence
    - Drill-down path tracking
    """

    PREFIX = "viz_state:"
    TTL = 86400  # 24 hours - dashboard state expires after this

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize with Redis connection."""
        try:
            if redis_url:
                self.redis = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=0,
                    decode_responses=True
                )
            self.redis.ping()
            self.enabled = True
            logger.info("VizStateManager connected to Redis")
        except Exception as e:
            logger.warning(f"VizStateManager: Redis not available, state persistence disabled: {e}")
            self.redis = None
            self.enabled = False

    def _dashboard_key(self, user_id: str, dashboard_id: str) -> str:
        """Generate Redis key for dashboard state."""
        return f"{self.PREFIX}dashboard:{user_id}:{dashboard_id}"

    def _widget_key(self, user_id: str, dashboard_id: str, widget_id: str) -> str:
        """Generate Redis key for widget state."""
        return f"{self.PREFIX}widget:{user_id}:{dashboard_id}:{widget_id}"

    def _filters_key(self, user_id: str, dashboard_id: str) -> str:
        """Generate Redis key for filter state."""
        return f"{self.PREFIX}filters:{user_id}:{dashboard_id}"

    def save_dashboard_state(
        self,
        user_id: str,
        dashboard_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Save full dashboard state for instant restore.

        Args:
            user_id: User identifier
            dashboard_id: Dashboard identifier
            state: Dashboard state including:
                - filters: Active filter values
                - drill_paths: Current drill-down paths per widget
                - widget_data: Cached widget data
                - layout: Widget positions/sizes
                - view_settings: Zoom, scroll position, etc.

        Returns:
            True if state was saved, False if Redis unavailable
        """
        if not self.enabled:
            return False

        try:
            key = self._dashboard_key(user_id, dashboard_id)
            data = {
                "filters": json.dumps(state.get("filters", {})),
                "drill_paths": json.dumps(state.get("drill_paths", {})),
                "widget_data": json.dumps(state.get("widget_data", {})),
                "layout": json.dumps(state.get("layout", [])),
                "view_settings": json.dumps(state.get("view_settings", {})),
                "updated_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }

            self.redis.hset(key, mapping=data)
            self.redis.expire(key, self.TTL)

            logger.info(
                "Dashboard state saved",
                user_id=user_id,
                dashboard_id=dashboard_id,
                filter_count=len(state.get("filters", {}))
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save dashboard state: {e}")
            return False

    def get_dashboard_state(
        self,
        user_id: str,
        dashboard_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve saved dashboard state for instant restore.

        Args:
            user_id: User identifier
            dashboard_id: Dashboard identifier

        Returns:
            Dashboard state dict or None if not found/expired
        """
        if not self.enabled:
            return None

        try:
            key = self._dashboard_key(user_id, dashboard_id)
            data = self.redis.hgetall(key)

            if not data:
                return None

            # Parse JSON fields
            result = {
                "updated_at": data.get("updated_at"),
                "version": data.get("version", "1.0")
            }

            for field in ["filters", "drill_paths", "widget_data", "layout", "view_settings"]:
                if field in data:
                    try:
                        result[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        result[field] = {}

            logger.info(
                "Dashboard state restored",
                user_id=user_id,
                dashboard_id=dashboard_id
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get dashboard state: {e}")
            return None

    def save_widget_state(
        self,
        user_id: str,
        dashboard_id: str,
        widget_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Save individual widget state.

        Args:
            user_id: User identifier
            dashboard_id: Dashboard identifier
            widget_id: Widget identifier
            state: Widget state including:
                - data: Cached query results
                - drill_path: Current drill-down breadcrumbs
                - chart_config: Chart customizations
                - last_query: Last executed query

        Returns:
            True if state was saved
        """
        if not self.enabled:
            return False

        try:
            key = self._widget_key(user_id, dashboard_id, widget_id)
            data = {
                "data": json.dumps(state.get("data", []), default=str),
                "drill_path": json.dumps(state.get("drill_path", [])),
                "chart_config": json.dumps(state.get("chart_config", {})),
                "last_query": state.get("last_query", ""),
                "updated_at": datetime.utcnow().isoformat()
            }

            self.redis.hset(key, mapping=data)
            self.redis.expire(key, self.TTL)
            return True

        except Exception as e:
            logger.error(f"Failed to save widget state: {e}")
            return False

    def get_widget_state(
        self,
        user_id: str,
        dashboard_id: str,
        widget_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve individual widget state."""
        if not self.enabled:
            return None

        try:
            key = self._widget_key(user_id, dashboard_id, widget_id)
            data = self.redis.hgetall(key)

            if not data:
                return None

            result = {"updated_at": data.get("updated_at")}

            for field in ["data", "drill_path", "chart_config"]:
                if field in data:
                    try:
                        result[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        result[field] = [] if field in ["data", "drill_path"] else {}

            result["last_query"] = data.get("last_query", "")
            return result

        except Exception as e:
            logger.error(f"Failed to get widget state: {e}")
            return None

    def save_filter_state(
        self,
        user_id: str,
        dashboard_id: str,
        filters: Dict[str, Any]
    ) -> bool:
        """
        Save filter state separately for quick access.

        Args:
            user_id: User identifier
            dashboard_id: Dashboard identifier
            filters: Filter values keyed by dimension

        Returns:
            True if filters were saved
        """
        if not self.enabled:
            return False

        try:
            key = self._filters_key(user_id, dashboard_id)
            data = {
                "filters": json.dumps(filters),
                "updated_at": datetime.utcnow().isoformat()
            }

            self.redis.hset(key, mapping=data)
            self.redis.expire(key, self.TTL)
            return True

        except Exception as e:
            logger.error(f"Failed to save filter state: {e}")
            return False

    def get_filter_state(
        self,
        user_id: str,
        dashboard_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve filter state."""
        if not self.enabled:
            return None

        try:
            key = self._filters_key(user_id, dashboard_id)
            data = self.redis.hgetall(key)

            if not data or "filters" not in data:
                return None

            return json.loads(data["filters"])

        except Exception as e:
            logger.error(f"Failed to get filter state: {e}")
            return None

    def clear_dashboard_state(
        self,
        user_id: str,
        dashboard_id: str
    ) -> bool:
        """Clear all state for a dashboard."""
        if not self.enabled:
            return False

        try:
            # Delete main dashboard state
            self.redis.delete(self._dashboard_key(user_id, dashboard_id))
            self.redis.delete(self._filters_key(user_id, dashboard_id))

            # Delete all widget states (scan for pattern)
            pattern = f"{self.PREFIX}widget:{user_id}:{dashboard_id}:*"
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)

            logger.info(
                "Dashboard state cleared",
                user_id=user_id,
                dashboard_id=dashboard_id
            )
            return True

        except Exception as e:
            logger.error(f"Failed to clear dashboard state: {e}")
            return False

    def get_state_stats(self) -> Dict[str, Any]:
        """Get statistics about stored visualization states."""
        if not self.enabled:
            return {"enabled": False}

        try:
            dashboard_count = 0
            widget_count = 0
            filter_count = 0

            for key in self.redis.scan_iter(f"{self.PREFIX}*"):
                if ":dashboard:" in key:
                    dashboard_count += 1
                elif ":widget:" in key:
                    widget_count += 1
                elif ":filters:" in key:
                    filter_count += 1

            return {
                "enabled": True,
                "dashboard_states": dashboard_count,
                "widget_states": widget_count,
                "filter_states": filter_count
            }

        except Exception as e:
            logger.error(f"Failed to get state stats: {e}")
            return {"enabled": True, "error": str(e)}


# Singleton instance
_viz_state_manager: Optional[VizStateManager] = None


def get_viz_state_manager() -> VizStateManager:
    """Get the singleton VizStateManager instance."""
    global _viz_state_manager
    if _viz_state_manager is None:
        _viz_state_manager = VizStateManager(redis_url=settings.redis_url)
    return _viz_state_manager
