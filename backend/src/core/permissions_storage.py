"""
Database Permissions Storage Backend

MongoDB-based storage for user database permissions.
Stores permission configurations and provides CRUD operations.

Author: Mantrix Axis AI
"""

from typing import Optional, List, Dict
from datetime import datetime
import structlog
from pymongo import MongoClient

from src.config import settings
from src.core.database_permissions import UserDatabasePermissions, DatabasePermission

logger = structlog.get_logger()


class PermissionsStorageBackend:
    """
    MongoDB storage backend for database permissions.

    Collections:
    - user_database_permissions: User-level permissions
    - organization_database_permissions: Organization-level permissions
    - permission_audit_log: Audit log for permission changes
    """

    def __init__(self):
        """Initialize storage backend with synchronous MongoDB client."""
        try:
            # Use synchronous pymongo client for synchronous code paths
            self.mongodb_client = MongoClient(settings.mongodb_url)
            self.db = self.mongodb_client[settings.mongodb_database]
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.mongodb_client = None
            self.db = None

        if self.db is not None:
            self.user_permissions_collection = self.db["user_database_permissions"]
            self.org_permissions_collection = self.db["organization_database_permissions"]
            self.audit_log_collection = self.db["permission_audit_log"]

            # Create indexes
            self._create_indexes()
        else:
            self.user_permissions_collection = None
            self.org_permissions_collection = None
            self.audit_log_collection = None
            logger.warning("MongoDB client not available, permissions storage disabled")

    def _create_indexes(self):
        """Create indexes for efficient querying."""
        try:
            # User permissions indexes
            self.user_permissions_collection.create_index("user_id", unique=True)
            self.user_permissions_collection.create_index("organization_id")
            self.user_permissions_collection.create_index([
                ("user_id", 1),
                ("organization_id", 1)
            ])

            # Audit log indexes
            self.audit_log_collection.create_index([
                ("user_id", 1),
                ("timestamp", -1)
            ])
            self.audit_log_collection.create_index("timestamp", expireAfterSeconds=31536000)  # 1 year TTL

            logger.info("Created permissions storage indexes")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    def get_user_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[UserDatabasePermissions]:
        """
        Get user's database permissions from storage.

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            UserDatabasePermissions object or None if not found
        """
        if self.db is None:
            return None

        try:
            # Build query
            query = {"user_id": user_id}
            if organization_id:
                query["organization_id"] = organization_id

            # Query database
            doc = self.user_permissions_collection.find_one(query)

            if not doc:
                logger.debug(f"No permissions found for user {user_id}")
                return None

            # Convert to UserDatabasePermissions
            # Remove MongoDB _id field
            doc.pop("_id", None)

            return UserDatabasePermissions.from_dict(doc)

        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}", exc_info=True)
            return None

    def save_user_permissions(
        self,
        permissions: UserDatabasePermissions
    ) -> bool:
        """
        Save user's database permissions to storage.

        Args:
            permissions: UserDatabasePermissions object

        Returns:
            True if successful, False otherwise
        """
        if self.db is None:
            logger.warning("MongoDB not available, cannot save permissions")
            return False

        try:
            # Convert to dict
            doc = permissions.to_dict()

            # Upsert (update or insert)
            query = {"user_id": permissions.user_id}
            if permissions.organization_id:
                query["organization_id"] = permissions.organization_id

            self.user_permissions_collection.update_one(
                query,
                {"$set": doc},
                upsert=True
            )

            logger.info(
                f"Saved permissions for user {permissions.user_id}",
                user_id=permissions.user_id,
                databases=list(permissions.permissions.keys())
            )

            # Log to audit log
            self._log_permission_change(
                user_id=permissions.user_id,
                action="permissions_saved",
                details=doc
            )

            return True

        except Exception as e:
            logger.error(f"Failed to save user permissions: {e}", exc_info=True)
            return False

    def delete_user_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Delete user's database permissions.

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            True if successful, False otherwise
        """
        if self.db is None:
            return False

        try:
            query = {"user_id": user_id}
            if organization_id:
                query["organization_id"] = organization_id

            result = self.user_permissions_collection.delete_one(query)

            if result.deleted_count > 0:
                logger.info(f"Deleted permissions for user {user_id}")

                # Log to audit log
                self._log_permission_change(
                    user_id=user_id,
                    action="permissions_deleted",
                    details={"user_id": user_id, "organization_id": organization_id}
                )

                return True
            else:
                logger.warning(f"No permissions found to delete for user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete user permissions: {e}", exc_info=True)
            return False

    def list_users_with_access(
        self,
        database_type: str,
        organization_id: Optional[str] = None
    ) -> List[str]:
        """
        List all users who have access to a specific database.

        Args:
            database_type: Database type
            organization_id: Optional organization ID filter

        Returns:
            List of user IDs
        """
        if self.db is None:
            return []

        try:
            query = {
                f"permissions.{database_type}.enabled": True,
                f"permissions.{database_type}.access_level": {"$ne": "none"}
            }

            if organization_id:
                query["organization_id"] = organization_id

            docs = self.user_permissions_collection.find(
                query,
                {"user_id": 1, "_id": 0}
            )

            return [doc["user_id"] for doc in docs]

        except Exception as e:
            logger.error(f"Failed to list users with access: {e}", exc_info=True)
            return []

    def get_organization_permissions(
        self,
        organization_id: str
    ) -> Optional[Dict]:
        """
        Get organization-level database permissions.

        Args:
            organization_id: Organization ID

        Returns:
            Organization permissions dict or None
        """
        if self.db is None:
            return None

        try:
            doc = self.org_permissions_collection.find_one(
                {"organization_id": organization_id}
            )

            if doc:
                doc.pop("_id", None)
                return doc
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to get organization permissions: {e}", exc_info=True)
            return None

    def save_organization_permissions(
        self,
        organization_id: str,
        permissions: Dict[str, DatabasePermission]
    ) -> bool:
        """
        Save organization-level database permissions.

        Args:
            organization_id: Organization ID
            permissions: Dict of database_type -> DatabasePermission

        Returns:
            True if successful, False otherwise
        """
        if self.db is None:
            return False

        try:
            doc = {
                "organization_id": organization_id,
                "permissions": {
                    db_type: perm.to_dict()
                    for db_type, perm in permissions.items()
                },
                "updated_at": datetime.utcnow().isoformat()
            }

            self.org_permissions_collection.update_one(
                {"organization_id": organization_id},
                {"$set": doc},
                upsert=True
            )

            logger.info(f"Saved organization permissions for {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save organization permissions: {e}", exc_info=True)
            return False

    def _log_permission_change(
        self,
        user_id: str,
        action: str,
        details: Dict,
        performed_by: Optional[str] = None
    ):
        """
        Log permission change to audit log.

        Args:
            user_id: User ID whose permissions changed
            action: Action performed
            details: Change details
            performed_by: User who performed the action
        """
        if self.db is None:
            return

        try:
            log_entry = {
                "user_id": user_id,
                "action": action,
                "details": details,
                "performed_by": performed_by or "system",
                "timestamp": datetime.utcnow().isoformat()
            }

            self.audit_log_collection.insert_one(log_entry)

        except Exception as e:
            logger.error(f"Failed to log permission change: {e}")

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get permission audit log.

        Args:
            user_id: Optional user ID filter
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        if self.db is None:
            return []

        try:
            query = {}
            if user_id:
                query["user_id"] = user_id

            docs = self.audit_log_collection.find(query).sort("timestamp", -1).limit(limit)

            results = []
            for doc in docs:
                doc.pop("_id", None)
                results.append(doc)

            return results

        except Exception as e:
            logger.error(f"Failed to get audit log: {e}", exc_info=True)
            return []


# Singleton instance
_permissions_storage = None


def get_permissions_storage() -> PermissionsStorageBackend:
    """Get singleton permissions storage backend."""
    global _permissions_storage
    if _permissions_storage is None:
        _permissions_storage = PermissionsStorageBackend()
    return _permissions_storage
