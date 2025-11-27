"""
Sharing Routes - API endpoints for advanced dashboard sharing.

Endpoints:
- POST /api/v1/dashboards/{id}/share - Share dashboard with users/groups
- GET /api/v1/dashboards/{id}/permissions - Get sharing permissions
- PUT /api/v1/dashboards/{id}/permissions - Update permissions
- DELETE /api/v1/dashboards/{id}/permissions/{user_id} - Remove user access
- POST /api/v1/dashboards/{id}/share-link - Generate shareable link
- DELETE /api/v1/dashboards/{id}/share-link - Revoke share link
- GET /api/v1/shared/{token} - Access shared dashboard via token
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import secrets
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user
from src.core.email_service import get_email_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["sharing"])


# Enums
class PermissionLevel(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


class ShareType(str, Enum):
    USER = "user"
    GROUP = "group"
    PUBLIC = "public"


# Request/Response Models
class ShareRequest(BaseModel):
    """Request to share a dashboard with users or groups."""
    email: Optional[EmailStr] = None
    user_id: Optional[str] = None
    group_id: Optional[str] = None
    permission: PermissionLevel = PermissionLevel.VIEW
    message: Optional[str] = Field(None, max_length=500)
    send_notification: bool = True


class BulkShareRequest(BaseModel):
    """Request to share with multiple users/groups."""
    shares: List[ShareRequest]


class PermissionEntry(BaseModel):
    """A single permission entry."""
    id: str
    type: ShareType
    identifier: str  # email, user_id, or group_id
    display_name: Optional[str]
    permission: PermissionLevel
    granted_by: str
    granted_at: datetime


class PermissionsResponse(BaseModel):
    """Response containing all permissions for a dashboard."""
    dashboard_id: str
    owner_id: str
    owner_name: Optional[str]
    is_public: bool
    share_token: Optional[str]
    share_url: Optional[str]
    permissions: List[PermissionEntry]


class ShareLinkResponse(BaseModel):
    """Response for share link generation."""
    dashboard_id: str
    share_token: str
    share_url: str
    expires_at: Optional[datetime]
    permission: PermissionLevel


class SharedDashboardResponse(BaseModel):
    """Response for accessing a shared dashboard."""
    dashboard_id: str
    dashboard_name: str
    permission: PermissionLevel
    shared_by: Optional[str]
    widgets: List[Dict[str, Any]]


# Endpoints

@router.post("/dashboards/{dashboard_id}/share")
async def share_dashboard(
    dashboard_id: str,
    request: ShareRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Share a dashboard with a user or group.

    Sends an email invitation if send_notification is True.
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get dashboard
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check ownership or admin permission
    if not _has_admin_access(dashboard, user_id):
        raise HTTPException(status_code=403, detail="Only owners and admins can share")

    # Determine share target
    share_type = None
    identifier = None
    display_name = None

    if request.email:
        share_type = ShareType.USER
        identifier = request.email
        display_name = request.email
    elif request.user_id:
        share_type = ShareType.USER
        identifier = request.user_id
        display_name = request.user_id  # Could lookup name from user service
    elif request.group_id:
        share_type = ShareType.GROUP
        identifier = request.group_id
        display_name = request.group_id

    if not share_type:
        raise HTTPException(status_code=400, detail="Must provide email, user_id, or group_id")

    # Create permission entry
    permission_entry = {
        "id": str(uuid.uuid4()),
        "type": share_type.value,
        "identifier": identifier,
        "display_name": display_name,
        "permission": request.permission.value,
        "granted_by": user_id,
        "granted_at": datetime.now(timezone.utc)
    }

    # Get or create permissions document
    perms_doc = await mongodb.dashboard_permissions.find_one({"dashboard_id": dashboard_id})

    if perms_doc:
        # Update existing, checking for duplicates
        existing = next(
            (p for p in perms_doc.get("permissions", []) if p["identifier"] == identifier),
            None
        )
        if existing:
            # Update existing permission
            await mongodb.dashboard_permissions.update_one(
                {"dashboard_id": dashboard_id, "permissions.identifier": identifier},
                {
                    "$set": {
                        "permissions.$.permission": request.permission.value,
                        "permissions.$.granted_at": datetime.now(timezone.utc),
                        "permissions.$.granted_by": user_id,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        else:
            # Add new permission
            await mongodb.dashboard_permissions.update_one(
                {"dashboard_id": dashboard_id},
                {
                    "$push": {"permissions": permission_entry},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
    else:
        # Create new permissions document
        await mongodb.dashboard_permissions.insert_one({
            "dashboard_id": dashboard_id,
            "owner_id": dashboard.get("owner_id"),
            "permissions": [permission_entry],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

    # Send notification email if requested
    if request.send_notification and request.email:
        email_service = get_email_service()
        if email_service.is_configured():
            # Build dashboard URL - would use config in production
            dashboard_url = f"https://app.mantrix.ai/dashboards/{dashboard_id}"

            await email_service.send_share_invitation(
                recipient=request.email,
                dashboard_name=dashboard.get("name", "Dashboard"),
                shared_by=current_user.get("email", current_user.get("name", "A colleague")),
                permission=request.permission.value,
                dashboard_url=dashboard_url,
                message=request.message
            )

    logger.info(
        "dashboard_shared",
        dashboard_id=dashboard_id,
        shared_with=identifier,
        permission=request.permission.value,
        by_user=user_id
    )

    return {
        "success": True,
        "dashboard_id": dashboard_id,
        "shared_with": identifier,
        "permission": request.permission.value
    }


@router.post("/dashboards/{dashboard_id}/share/bulk")
async def bulk_share_dashboard(
    dashboard_id: str,
    request: BulkShareRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Share a dashboard with multiple users/groups at once."""
    results = []

    for share in request.shares:
        try:
            result = await share_dashboard(
                dashboard_id=dashboard_id,
                request=share,
                mongodb=mongodb,
                current_user=current_user
            )
            results.append({"success": True, **result})
        except HTTPException as e:
            results.append({
                "success": False,
                "identifier": share.email or share.user_id or share.group_id,
                "error": e.detail
            })

    return {
        "dashboard_id": dashboard_id,
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r.get("success"))
    }


@router.get("/dashboards/{dashboard_id}/permissions", response_model=PermissionsResponse)
async def get_dashboard_permissions(
    dashboard_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Get all sharing permissions for a dashboard."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get dashboard
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check access - owner, admin, or at least view permission
    if not _has_view_access(dashboard, user_id, mongodb):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get permissions
    perms_doc = await mongodb.dashboard_permissions.find_one({"dashboard_id": dashboard_id})

    permissions = []
    if perms_doc:
        for p in perms_doc.get("permissions", []):
            permissions.append(PermissionEntry(
                id=p["id"],
                type=ShareType(p["type"]),
                identifier=p["identifier"],
                display_name=p.get("display_name"),
                permission=PermissionLevel(p["permission"]),
                granted_by=p["granted_by"],
                granted_at=p["granted_at"]
            ))

    # Build share URL if token exists
    share_url = None
    if perms_doc and perms_doc.get("share_token"):
        share_url = f"https://app.mantrix.ai/shared/{perms_doc['share_token']}"

    return PermissionsResponse(
        dashboard_id=dashboard_id,
        owner_id=dashboard.get("owner_id"),
        owner_name=dashboard.get("owner_name"),
        is_public=dashboard.get("is_public", False),
        share_token=perms_doc.get("share_token") if perms_doc else None,
        share_url=share_url,
        permissions=permissions
    )


@router.delete("/dashboards/{dashboard_id}/permissions/{permission_id}")
async def remove_permission(
    dashboard_id: str,
    permission_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Remove a user's or group's access to a dashboard."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get dashboard
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check admin access
    if not _has_admin_access(dashboard, user_id):
        raise HTTPException(status_code=403, detail="Only owners and admins can modify permissions")

    # Remove permission
    result = await mongodb.dashboard_permissions.update_one(
        {"dashboard_id": dashboard_id},
        {
            "$pull": {"permissions": {"id": permission_id}},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Permission not found")

    logger.info(
        "permission_removed",
        dashboard_id=dashboard_id,
        permission_id=permission_id,
        by_user=user_id
    )

    return {"success": True, "message": "Permission removed"}


@router.post("/dashboards/{dashboard_id}/share-link", response_model=ShareLinkResponse)
async def generate_share_link(
    dashboard_id: str,
    permission: PermissionLevel = PermissionLevel.VIEW,
    expires_hours: Optional[int] = None,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate a shareable link for a dashboard.

    Anyone with the link can access with the specified permission level.
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get dashboard
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check admin access
    if not _has_admin_access(dashboard, user_id):
        raise HTTPException(status_code=403, detail="Only owners and admins can create share links")

    # Generate token
    share_token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = None
    if expires_hours:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

    # Update permissions document
    await mongodb.dashboard_permissions.update_one(
        {"dashboard_id": dashboard_id},
        {
            "$set": {
                "share_token": share_token,
                "share_token_permission": permission.value,
                "share_token_expires": expires_at,
                "share_token_created_by": user_id,
                "share_token_created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )

    # Also update dashboard document for quick lookup
    await mongodb.dashboards.update_one(
        {"_id": dashboard_id},
        {"$set": {"share_token": share_token}}
    )

    share_url = f"https://app.mantrix.ai/shared/{share_token}"

    logger.info(
        "share_link_generated",
        dashboard_id=dashboard_id,
        permission=permission.value,
        expires_at=expires_at,
        by_user=user_id
    )

    return ShareLinkResponse(
        dashboard_id=dashboard_id,
        share_token=share_token,
        share_url=share_url,
        expires_at=expires_at,
        permission=permission
    )


@router.delete("/dashboards/{dashboard_id}/share-link")
async def revoke_share_link(
    dashboard_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Revoke the shareable link for a dashboard."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get dashboard
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check admin access
    if not _has_admin_access(dashboard, user_id):
        raise HTTPException(status_code=403, detail="Only owners and admins can revoke share links")

    # Remove share token
    await mongodb.dashboard_permissions.update_one(
        {"dashboard_id": dashboard_id},
        {
            "$unset": {
                "share_token": "",
                "share_token_permission": "",
                "share_token_expires": "",
                "share_token_created_by": "",
                "share_token_created_at": ""
            },
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    await mongodb.dashboards.update_one(
        {"_id": dashboard_id},
        {"$unset": {"share_token": ""}}
    )

    logger.info(
        "share_link_revoked",
        dashboard_id=dashboard_id,
        by_user=user_id
    )

    return {"success": True, "message": "Share link revoked"}


@router.get("/shared/{token}")
async def access_shared_dashboard(
    token: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """
    Access a dashboard via share token.

    No authentication required - anyone with the link can access.
    """
    # Find dashboard by share token
    dashboard = await mongodb.dashboards.find_one({"share_token": token})

    if not dashboard:
        raise HTTPException(status_code=404, detail="Shared dashboard not found or link expired")

    # Get permissions to check expiration
    perms_doc = await mongodb.dashboard_permissions.find_one({"dashboard_id": dashboard["_id"]})

    if perms_doc:
        expires_at = perms_doc.get("share_token_expires")
        if expires_at and expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Share link has expired")

        permission = perms_doc.get("share_token_permission", "view")
    else:
        permission = "view"

    logger.info(
        "shared_dashboard_accessed",
        dashboard_id=dashboard["_id"],
        token_prefix=token[:8]
    )

    return SharedDashboardResponse(
        dashboard_id=dashboard["_id"],
        dashboard_name=dashboard.get("name", "Shared Dashboard"),
        permission=PermissionLevel(permission),
        shared_by=perms_doc.get("share_token_created_by") if perms_doc else None,
        widgets=dashboard.get("widgets", [])
    )


@router.put("/dashboards/{dashboard_id}/public")
async def toggle_public_access(
    dashboard_id: str,
    is_public: bool,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Toggle public access for a dashboard within the organization."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    if not _has_admin_access(dashboard, user_id):
        raise HTTPException(status_code=403, detail="Only owners and admins can change public access")

    await mongodb.dashboards.update_one(
        {"_id": dashboard_id},
        {
            "$set": {
                "is_public": is_public,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    logger.info(
        "public_access_toggled",
        dashboard_id=dashboard_id,
        is_public=is_public,
        by_user=user_id
    )

    return {"success": True, "is_public": is_public}


# Helper functions

def _has_admin_access(dashboard: Dict, user_id: str) -> bool:
    """Check if user has admin access to dashboard."""
    return dashboard.get("owner_id") == user_id


async def _has_view_access(dashboard: Dict, user_id: str, mongodb: MongoDBClient) -> bool:
    """Check if user has at least view access to dashboard."""
    # Owner always has access
    if dashboard.get("owner_id") == user_id:
        return True

    # Public dashboards in same org
    if dashboard.get("is_public"):
        return True

    # Check explicit permissions
    perms_doc = await mongodb.dashboard_permissions.find_one({"dashboard_id": dashboard["_id"]})
    if perms_doc:
        for p in perms_doc.get("permissions", []):
            if p["identifier"] == user_id:
                return True

    return False
