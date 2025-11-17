"""
Database Permissions API Routes

Endpoints for managing user database permissions and access control.
Allows admins to grant/revoke database access, check permissions, and view audit logs.
"""
from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional, List
import structlog

from ..db.connector_factory import ConnectorFactory, get_permissions_manager
from ..core.database_permissions import AccessLevel
from ..core.permissions_storage import get_permissions_storage
from .models import (
    GrantPermissionRequest,
    RevokePermissionRequest,
    UserPermissionsResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    AllowedDatabasesResponse,
    AuditLogResponse
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/permissions", tags=["permissions"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract user ID from authorization header.

    In production, this would validate JWT token and extract user ID.
    For now, this is a placeholder that can be extended with Clerk integration.

    Args:
        authorization: Authorization header value

    Returns:
        User ID or None
    """
    # TODO: Integrate with Clerk authentication
    # For now, return a placeholder or extract from header
    if authorization and authorization.startswith("Bearer "):
        # In production, decode JWT and extract user_id
        return "current_user_id"
    return None


@router.get("/databases/available")
async def get_available_databases(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Get list of databases available to a user.

    Returns information about which databases the user has access to,
    along with their access levels and database availability status.

    Args:
        user_id: Optional user ID (defaults to current user)
        organization_id: Optional organization ID
        authorization: Authorization header

    Returns:
        Dictionary with allowed databases and details
    """
    try:
        # Use provided user_id or extract from auth token
        target_user_id = user_id or get_current_user_id(authorization)

        if not target_user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID required. Provide user_id parameter or valid authorization header."
            )

        # Get supported types with user permissions
        database_details = ConnectorFactory.get_supported_types_for_user(
            user_id=target_user_id,
            organization_id=organization_id
        )

        # Filter to only allowed databases
        allowed_databases = [
            db_type for db_type, details in database_details.items()
            if details.get('has_access', False) and details.get('available', False)
        ]

        logger.info(
            f"Retrieved available databases for user {target_user_id}",
            user_id=target_user_id,
            databases=allowed_databases
        )

        return AllowedDatabasesResponse(
            user_id=target_user_id,
            organization_id=organization_id,
            allowed_databases=allowed_databases,
            database_details=database_details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(request: PermissionCheckRequest):
    """
    Check if a user has specific database access.

    Verifies whether a user has the required access level for a given database type.

    Args:
        request: Permission check request with user_id, database_type, and required_level

    Returns:
        Permission check result with has_access boolean and details
    """
    try:
        # Check user access
        has_access = ConnectorFactory.check_user_access(
            user_id=request.user_id,
            database_type=request.database_type,
            required_level=request.required_level,
            organization_id=request.organization_id
        )

        # Get actual access level
        permissions_manager = get_permissions_manager()
        user_perms = permissions_manager.get_user_permissions(
            request.user_id,
            request.organization_id
        )

        access_level = AccessLevel.NONE.value
        if user_perms:
            access_level = user_perms.get_access_level(request.database_type)

        message = (
            f"User has {access_level} access to {request.database_type}"
            if has_access
            else f"User does not have {request.required_level} access to {request.database_type}"
        )

        logger.info(
            f"Permission check: {request.user_id} -> {request.database_type}",
            user_id=request.user_id,
            database_type=request.database_type,
            has_access=has_access,
            access_level=access_level
        )

        return PermissionCheckResponse(
            has_access=has_access,
            user_id=request.user_id,
            database_type=request.database_type,
            access_level=access_level,
            required_level=request.required_level,
            message=message
        )

    except Exception as e:
        logger.error(f"Error checking permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: str,
    organization_id: Optional[str] = None
):
    """
    Get all database permissions for a specific user.

    Returns complete permission configuration including access levels,
    rate limits, and allowed schemas/tables for each database.

    Args:
        user_id: User ID
        organization_id: Optional organization ID

    Returns:
        User's complete permission configuration
    """
    try:
        permissions_manager = get_permissions_manager()
        user_perms = permissions_manager.get_user_permissions(user_id, organization_id)

        if not user_perms:
            raise HTTPException(
                status_code=404,
                detail=f"No permissions found for user {user_id}"
            )

        # Convert to response model
        permissions_dict = {
            db_type: perm.to_dict()
            for db_type, perm in user_perms.permissions.items()
        }

        logger.info(f"Retrieved permissions for user {user_id}", user_id=user_id)

        return UserPermissionsResponse(
            user_id=user_perms.user_id,
            organization_id=user_perms.organization_id,
            permissions=permissions_dict,
            is_admin=user_perms.is_admin,
            created_at=user_perms.created_at,
            updated_at=user_perms.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grant", status_code=status.HTTP_201_CREATED)
async def grant_permission(
    request: GrantPermissionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Grant database permission to a user.

    Allows admins to grant specific database access to users with configurable
    access levels, rate limits, and schema/table restrictions.

    Args:
        request: Grant permission request with user_id and permission details
        authorization: Authorization header (used to identify granting admin)

    Returns:
        Success message with granted permission details
    """
    try:
        # Get user who is granting permission (from auth token)
        granted_by = get_current_user_id(authorization) or "system"

        # Grant permission
        permissions_manager = get_permissions_manager()

        success = permissions_manager.grant_permission(
            user_id=request.user_id,
            database_type=request.permission.database_type,
            access_level=request.permission.access_level,
            granted_by=granted_by,
            organization_id=request.organization_id,
            max_queries_per_day=request.permission.max_queries_per_day,
            max_rows_per_query=request.permission.max_rows_per_query,
            allowed_schemas=request.permission.allowed_schemas,
            allowed_tables=request.permission.allowed_tables,
            expires_at=request.permission.expires_at
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to grant permission"
            )

        logger.info(
            f"Granted {request.permission.access_level} access to {request.permission.database_type} for user {request.user_id}",
            user_id=request.user_id,
            database_type=request.permission.database_type,
            access_level=request.permission.access_level,
            granted_by=granted_by
        )

        return {
            "success": True,
            "message": f"Granted {request.permission.access_level} access to {request.permission.database_type}",
            "user_id": request.user_id,
            "database_type": request.permission.database_type,
            "access_level": request.permission.access_level
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revoke")
async def revoke_permission(
    request: RevokePermissionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Revoke database permission from a user.

    Removes a user's access to a specific database type.

    Args:
        request: Revoke permission request with user_id and database_type
        authorization: Authorization header (used to identify revoking admin)

    Returns:
        Success message
    """
    try:
        # Get user who is revoking permission
        revoked_by = get_current_user_id(authorization) or "system"

        # Revoke permission
        permissions_manager = get_permissions_manager()

        success = permissions_manager.revoke_permission(
            user_id=request.user_id,
            database_type=request.database_type,
            revoked_by=revoked_by,
            organization_id=request.organization_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"No permission found to revoke for user {request.user_id} and database {request.database_type}"
            )

        logger.info(
            f"Revoked access to {request.database_type} for user {request.user_id}",
            user_id=request.user_id,
            database_type=request.database_type,
            revoked_by=revoked_by
        )

        return {
            "success": True,
            "message": f"Revoked access to {request.database_type}",
            "user_id": request.user_id,
            "database_type": request.database_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking permission: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    user_id: Optional[str] = None,
    limit: int = 100
):
    """
    Get permission change audit log.

    Returns history of permission grants, revocations, and modifications.

    Args:
        user_id: Optional user ID to filter logs
        limit: Maximum number of entries to return (default: 100)

    Returns:
        List of audit log entries
    """
    try:
        storage = get_permissions_storage()
        entries = storage.get_audit_log(user_id=user_id, limit=limit)

        logger.info(
            f"Retrieved {len(entries)} audit log entries",
            user_id=user_id,
            count=len(entries)
        )

        return AuditLogResponse(
            entries=entries,
            total_count=len(entries)
        )

    except Exception as e:
        logger.error(f"Error getting audit log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/{database_type}/users")
async def list_users_with_access(
    database_type: str,
    organization_id: Optional[str] = None
):
    """
    List all users who have access to a specific database.

    Useful for admins to see who has permissions for a given database type.

    Args:
        database_type: Database type (bigquery, snowflake, etc.)
        organization_id: Optional organization ID filter

    Returns:
        List of user IDs with access
    """
    try:
        storage = get_permissions_storage()
        user_ids = storage.list_users_with_access(
            database_type=database_type,
            organization_id=organization_id
        )

        logger.info(
            f"Found {len(user_ids)} users with access to {database_type}",
            database_type=database_type,
            count=len(user_ids)
        )

        return {
            "success": True,
            "database_type": database_type,
            "users": user_ids,
            "total_count": len(user_ids)
        }

    except Exception as e:
        logger.error(f"Error listing users with access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
