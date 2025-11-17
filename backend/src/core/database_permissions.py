"""
Database Permissions and Feature Flags System

Controls which databases are accessible to which users/organizations.
Supports per-user, per-organization, and global database access control.

Key Features:
- User-level database permissions
- Organization-level database permissions
- Role-based access control (admin, user, viewer)
- Feature flag-based database enablement
- Audit logging for permission changes
- Default permissions for new users

Author: Mantrix Axis AI
"""

from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import structlog

from src.config import settings

logger = structlog.get_logger()


class DatabaseType(str, Enum):
    """Supported database types"""
    BIGQUERY = "bigquery"
    SNOWFLAKE = "snowflake"
    POSTGRESQL = "postgresql"
    REDSHIFT = "redshift"
    DATABRICKS = "databricks"


class AccessLevel(str, Enum):
    """Database access levels"""
    NONE = "none"  # No access
    READ = "read"  # Read-only queries
    WRITE = "write"  # Read + Write operations
    ADMIN = "admin"  # Full access including schema modifications


@dataclass
class DatabasePermission:
    """Permission for a specific database"""
    database_type: str
    access_level: str
    enabled: bool = True
    max_queries_per_day: Optional[int] = None  # Rate limiting
    max_rows_per_query: Optional[int] = None  # Result size limiting
    allowed_schemas: Optional[List[str]] = None  # Schema-level filtering
    allowed_tables: Optional[List[str]] = None  # Table-level filtering
    granted_at: Optional[str] = None
    granted_by: Optional[str] = None
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'DatabasePermission':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class UserDatabasePermissions:
    """Database permissions for a specific user"""
    user_id: str
    organization_id: Optional[str] = None
    permissions: Dict[str, DatabasePermission] = None  # db_type -> permission
    is_admin: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def has_access(self, database_type: str) -> bool:
        """Check if user has any access to a database"""
        perm = self.permissions.get(database_type)
        if not perm:
            return False
        return perm.enabled and perm.access_level != AccessLevel.NONE.value

    def get_access_level(self, database_type: str) -> str:
        """Get user's access level for a database"""
        perm = self.permissions.get(database_type)
        if not perm or not perm.enabled:
            return AccessLevel.NONE.value
        return perm.access_level

    def can_read(self, database_type: str) -> bool:
        """Check if user can read from a database"""
        level = self.get_access_level(database_type)
        return level in [AccessLevel.READ.value, AccessLevel.WRITE.value, AccessLevel.ADMIN.value]

    def can_write(self, database_type: str) -> bool:
        """Check if user can write to a database"""
        level = self.get_access_level(database_type)
        return level in [AccessLevel.WRITE.value, AccessLevel.ADMIN.value]

    def is_database_admin(self, database_type: str) -> bool:
        """Check if user is admin for a database"""
        level = self.get_access_level(database_type)
        return level == AccessLevel.ADMIN.value

    def get_allowed_databases(self) -> List[str]:
        """Get list of databases user has access to"""
        return [
            db_type
            for db_type, perm in self.permissions.items()
            if perm.enabled and perm.access_level != AccessLevel.NONE.value
        ]

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "permissions": {
                db_type: perm.to_dict()
                for db_type, perm in self.permissions.items()
            },
            "is_admin": self.is_admin,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'UserDatabasePermissions':
        """Create from dictionary"""
        permissions = {
            db_type: DatabasePermission.from_dict(perm_data)
            for db_type, perm_data in data.get("permissions", {}).items()
        }
        return cls(
            user_id=data["user_id"],
            organization_id=data.get("organization_id"),
            permissions=permissions,
            is_admin=data.get("is_admin", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class DatabasePermissionsManager:
    """
    Manages database permissions for users and organizations.

    Supports:
    - Global feature flags (enable/disable databases system-wide)
    - Organization-level permissions
    - User-level permissions
    - Default permissions for new users
    - Permission inheritance (user < org < global)

    Usage:
        manager = DatabasePermissionsManager()
        allowed_dbs = manager.get_allowed_databases(user_id="user123")
        can_access = manager.check_access(user_id="user123", database_type="bigquery")
    """

    def __init__(self, storage_backend=None):
        """
        Initialize permissions manager.

        Args:
            storage_backend: Optional storage backend (defaults to MongoDB)
        """
        self.storage_backend = storage_backend
        self._global_feature_flags = self._load_global_feature_flags()

    def _load_global_feature_flags(self) -> Dict[str, bool]:
        """
        Load global feature flags from environment/config.

        These control which databases are enabled system-wide.
        """
        return {
            DatabaseType.BIGQUERY.value: getattr(settings, 'enable_bigquery', True),
            DatabaseType.SNOWFLAKE.value: getattr(settings, 'enable_snowflake', bool(settings.snowflake_account)),
            DatabaseType.POSTGRESQL.value: getattr(settings, 'enable_postgresql', bool(settings.external_postgres_host)),
            DatabaseType.REDSHIFT.value: getattr(settings, 'enable_redshift', bool(settings.redshift_host)),
            DatabaseType.DATABRICKS.value: getattr(settings, 'enable_databricks', bool(settings.databricks_server_hostname)),
        }

    def is_database_globally_enabled(self, database_type: str) -> bool:
        """Check if a database is enabled globally"""
        return self._global_feature_flags.get(database_type, False)

    def get_globally_enabled_databases(self) -> List[str]:
        """Get list of globally enabled databases"""
        return [
            db_type
            for db_type, enabled in self._global_feature_flags.items()
            if enabled
        ]

    def check_access(
        self,
        user_id: str,
        database_type: str,
        required_level: str = AccessLevel.READ.value,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has access to a database with required level.

        Args:
            user_id: User ID
            database_type: Database type (bigquery, snowflake, etc.)
            required_level: Required access level (read, write, admin)
            organization_id: Optional organization ID

        Returns:
            True if user has access, False otherwise
        """
        # Check global feature flag first
        if not self.is_database_globally_enabled(database_type):
            logger.debug(
                f"Database {database_type} is globally disabled",
                database_type=database_type
            )
            return False

        # Get user permissions
        user_perms = self.get_user_permissions(user_id, organization_id)

        if not user_perms:
            logger.debug(
                f"No permissions found for user {user_id}",
                user_id=user_id,
                database_type=database_type
            )
            return False

        # Check if user has access
        user_level = user_perms.get_access_level(database_type)

        # Define level hierarchy
        level_hierarchy = {
            AccessLevel.NONE.value: 0,
            AccessLevel.READ.value: 1,
            AccessLevel.WRITE.value: 2,
            AccessLevel.ADMIN.value: 3
        }

        user_level_value = level_hierarchy.get(user_level, 0)
        required_level_value = level_hierarchy.get(required_level, 1)

        has_access = user_level_value >= required_level_value

        logger.debug(
            f"Access check for {user_id}: {database_type}",
            user_id=user_id,
            database_type=database_type,
            user_level=user_level,
            required_level=required_level,
            has_access=has_access
        )

        return has_access

    def get_allowed_databases(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        min_access_level: str = AccessLevel.READ.value
    ) -> List[str]:
        """
        Get list of databases user has access to.

        Args:
            user_id: User ID
            organization_id: Optional organization ID
            min_access_level: Minimum required access level

        Returns:
            List of database type strings
        """
        # Start with globally enabled databases
        globally_enabled = set(self.get_globally_enabled_databases())

        # Get user permissions
        user_perms = self.get_user_permissions(user_id, organization_id)

        if not user_perms:
            logger.warning(f"No permissions found for user {user_id}")
            return []

        # Filter by user's access level
        allowed = []
        for db_type in globally_enabled:
            if self.check_access(user_id, db_type, min_access_level, organization_id):
                allowed.append(db_type)

        return allowed

    def get_user_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> Optional[UserDatabasePermissions]:
        """
        Get user's database permissions.

        Args:
            user_id: User ID
            organization_id: Optional organization ID

        Returns:
            UserDatabasePermissions object or None
        """
        # TODO: Implement storage backend integration
        # For now, return default permissions

        # Check if storage backend is available
        if self.storage_backend:
            return self.storage_backend.get_user_permissions(user_id, organization_id)

        # Return default permissions (all databases with READ access)
        return self._get_default_permissions(user_id, organization_id)

    def _get_default_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None
    ) -> UserDatabasePermissions:
        """
        Get default permissions for a new user.

        By default, users get READ access to all globally enabled databases.
        """
        permissions = {}

        for db_type in DatabaseType:
            if self.is_database_globally_enabled(db_type.value):
                permissions[db_type.value] = DatabasePermission(
                    database_type=db_type.value,
                    access_level=AccessLevel.READ.value,
                    enabled=True,
                    granted_at=datetime.utcnow().isoformat(),
                    granted_by="system"
                )

        return UserDatabasePermissions(
            user_id=user_id,
            organization_id=organization_id,
            permissions=permissions,
            is_admin=False
        )

    def grant_permission(
        self,
        user_id: str,
        database_type: str,
        access_level: str,
        granted_by: str,
        organization_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Grant database permission to a user.

        Args:
            user_id: User ID
            database_type: Database type
            access_level: Access level (read, write, admin)
            granted_by: User ID who granted the permission
            organization_id: Optional organization ID
            **kwargs: Additional permission settings (max_queries_per_day, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing permissions or create new
            user_perms = self.get_user_permissions(user_id, organization_id)
            if not user_perms:
                user_perms = UserDatabasePermissions(
                    user_id=user_id,
                    organization_id=organization_id,
                    permissions={}
                )

            # Create permission
            permission = DatabasePermission(
                database_type=database_type,
                access_level=access_level,
                enabled=True,
                granted_at=datetime.utcnow().isoformat(),
                granted_by=granted_by,
                **kwargs
            )

            # Update permissions
            user_perms.permissions[database_type] = permission
            user_perms.updated_at = datetime.utcnow().isoformat()

            # Save to storage
            if self.storage_backend:
                self.storage_backend.save_user_permissions(user_perms)

            logger.info(
                f"Granted {access_level} access to {database_type} for user {user_id}",
                user_id=user_id,
                database_type=database_type,
                access_level=access_level,
                granted_by=granted_by
            )

            return True

        except Exception as e:
            logger.error(f"Failed to grant permission: {e}", exc_info=True)
            return False

    def revoke_permission(
        self,
        user_id: str,
        database_type: str,
        revoked_by: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Revoke database permission from a user.

        Args:
            user_id: User ID
            database_type: Database type
            revoked_by: User ID who revoked the permission
            organization_id: Optional organization ID

        Returns:
            True if successful, False otherwise
        """
        try:
            user_perms = self.get_user_permissions(user_id, organization_id)
            if not user_perms or database_type not in user_perms.permissions:
                logger.warning(f"No permission to revoke for {user_id}/{database_type}")
                return False

            # Set access level to NONE and disable
            user_perms.permissions[database_type].enabled = False
            user_perms.permissions[database_type].access_level = AccessLevel.NONE.value
            user_perms.updated_at = datetime.utcnow().isoformat()

            # Save to storage
            if self.storage_backend:
                self.storage_backend.save_user_permissions(user_perms)

            logger.info(
                f"Revoked access to {database_type} for user {user_id}",
                user_id=user_id,
                database_type=database_type,
                revoked_by=revoked_by
            )

            return True

        except Exception as e:
            logger.error(f"Failed to revoke permission: {e}", exc_info=True)
            return False
