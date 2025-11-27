"""
Comments Routes - API endpoints for dashboard comments and annotations.

Endpoints:
- POST /api/v1/dashboards/{id}/comments - Add a comment
- GET /api/v1/dashboards/{id}/comments - List comments
- PUT /api/v1/comments/{id} - Update a comment
- DELETE /api/v1/comments/{id} - Delete a comment
- POST /api/v1/comments/{id}/reply - Reply to a comment
- POST /api/v1/widgets/{id}/annotations - Add widget annotation
- GET /api/v1/widgets/{id}/annotations - Get widget annotations
- DELETE /api/v1/annotations/{id} - Delete annotation
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import uuid
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["comments"])


# Enums
class CommentType(str, Enum):
    GENERAL = "general"
    INSIGHT = "insight"
    QUESTION = "question"
    ACTION_ITEM = "action_item"


class AnnotationType(str, Enum):
    NOTE = "note"
    HIGHLIGHT = "highlight"
    FLAG = "flag"
    TREND = "trend"


# Request/Response Models
class CommentCreate(BaseModel):
    """Request to create a comment."""
    content: str = Field(..., min_length=1, max_length=2000)
    widget_id: Optional[str] = None  # If commenting on specific widget
    comment_type: CommentType = CommentType.GENERAL
    mentions: List[str] = Field(default_factory=list)  # User IDs to mention


class CommentUpdate(BaseModel):
    """Request to update a comment."""
    content: str = Field(..., min_length=1, max_length=2000)


class CommentReply(BaseModel):
    """Request to reply to a comment."""
    content: str = Field(..., min_length=1, max_length=2000)
    mentions: List[str] = Field(default_factory=list)


class CommentResponse(BaseModel):
    """Response for a single comment."""
    id: str
    dashboard_id: str
    widget_id: Optional[str]
    content: str
    comment_type: CommentType
    author_id: str
    author_name: str
    author_email: Optional[str]
    mentions: List[str]
    thread_id: Optional[str]  # Parent comment ID for threads
    reply_count: int
    created_at: datetime
    updated_at: datetime
    is_edited: bool


class CommentListResponse(BaseModel):
    """Response for listing comments."""
    dashboard_id: str
    comments: List[CommentResponse]
    total: int


class AnnotationCreate(BaseModel):
    """Request to create a widget annotation."""
    content: str = Field(..., min_length=1, max_length=500)
    annotation_type: AnnotationType = AnnotationType.NOTE
    position: Optional[Dict[str, float]] = None  # x, y coordinates on widget
    data_point: Optional[Dict[str, Any]] = None  # Specific data point being annotated


class AnnotationResponse(BaseModel):
    """Response for a widget annotation."""
    id: str
    widget_id: str
    dashboard_id: str
    content: str
    annotation_type: AnnotationType
    position: Optional[Dict[str, float]]
    data_point: Optional[Dict[str, Any]]
    author_id: str
    author_name: str
    created_at: datetime


# Endpoints - Comments

@router.post("/dashboards/{dashboard_id}/comments", response_model=CommentResponse)
async def create_comment(
    dashboard_id: str,
    request: CommentCreate,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Add a comment to a dashboard.

    Can optionally be attached to a specific widget.
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    user_name = current_user.get("name", current_user.get("email", "Anonymous"))
    user_email = current_user.get("email")

    # Verify dashboard exists
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Create comment
    comment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    comment_doc = {
        "_id": comment_id,
        "dashboard_id": dashboard_id,
        "widget_id": request.widget_id,
        "content": request.content,
        "comment_type": request.comment_type.value,
        "author_id": user_id,
        "author_name": user_name,
        "author_email": user_email,
        "mentions": request.mentions,
        "thread_id": None,  # Not a reply
        "reply_count": 0,
        "created_at": now,
        "updated_at": now,
        "is_edited": False
    }

    await mongodb.dashboard_comments.insert_one(comment_doc)

    logger.info(
        "comment_created",
        comment_id=comment_id,
        dashboard_id=dashboard_id,
        widget_id=request.widget_id,
        author=user_id
    )

    return CommentResponse(**{**comment_doc, "id": comment_id})


@router.get("/dashboards/{dashboard_id}/comments", response_model=CommentListResponse)
async def list_comments(
    dashboard_id: str,
    widget_id: Optional[str] = None,
    include_replies: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    List comments for a dashboard.

    Can filter by widget_id to get comments for a specific widget.
    """
    # Build query
    query = {"dashboard_id": dashboard_id}

    if widget_id:
        query["widget_id"] = widget_id

    if not include_replies:
        query["thread_id"] = None

    # Get comments
    cursor = mongodb.dashboard_comments.find(query).sort(
        "created_at", -1
    ).skip(skip).limit(limit)

    comments = []
    async for doc in cursor:
        comments.append(CommentResponse(
            id=doc["_id"],
            dashboard_id=doc["dashboard_id"],
            widget_id=doc.get("widget_id"),
            content=doc["content"],
            comment_type=CommentType(doc.get("comment_type", "general")),
            author_id=doc["author_id"],
            author_name=doc["author_name"],
            author_email=doc.get("author_email"),
            mentions=doc.get("mentions", []),
            thread_id=doc.get("thread_id"),
            reply_count=doc.get("reply_count", 0),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            is_edited=doc.get("is_edited", False)
        ))

    # Get total count
    total = await mongodb.dashboard_comments.count_documents(query)

    return CommentListResponse(
        dashboard_id=dashboard_id,
        comments=comments,
        total=total
    )


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    request: CommentUpdate,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Update a comment's content."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get comment
    comment = await mongodb.dashboard_comments.find_one({"_id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership
    if comment["author_id"] != user_id:
        raise HTTPException(status_code=403, detail="Can only edit your own comments")

    # Update
    now = datetime.now(timezone.utc)
    await mongodb.dashboard_comments.update_one(
        {"_id": comment_id},
        {
            "$set": {
                "content": request.content,
                "updated_at": now,
                "is_edited": True
            }
        }
    )

    # Return updated comment
    comment["content"] = request.content
    comment["updated_at"] = now
    comment["is_edited"] = True

    logger.info("comment_updated", comment_id=comment_id, by_user=user_id)

    return CommentResponse(
        id=comment["_id"],
        dashboard_id=comment["dashboard_id"],
        widget_id=comment.get("widget_id"),
        content=comment["content"],
        comment_type=CommentType(comment.get("comment_type", "general")),
        author_id=comment["author_id"],
        author_name=comment["author_name"],
        author_email=comment.get("author_email"),
        mentions=comment.get("mentions", []),
        thread_id=comment.get("thread_id"),
        reply_count=comment.get("reply_count", 0),
        created_at=comment["created_at"],
        updated_at=comment["updated_at"],
        is_edited=comment["is_edited"]
    )


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a comment and its replies."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get comment
    comment = await mongodb.dashboard_comments.find_one({"_id": comment_id})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check ownership or dashboard admin
    dashboard = await mongodb.dashboards.find_one({"_id": comment["dashboard_id"]})
    is_dashboard_owner = dashboard and dashboard.get("owner_id") == user_id

    if comment["author_id"] != user_id and not is_dashboard_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    # Delete comment and all replies
    await mongodb.dashboard_comments.delete_many({
        "$or": [
            {"_id": comment_id},
            {"thread_id": comment_id}
        ]
    })

    # If this was a reply, decrement parent's reply count
    if comment.get("thread_id"):
        await mongodb.dashboard_comments.update_one(
            {"_id": comment["thread_id"]},
            {"$inc": {"reply_count": -1}}
        )

    logger.info("comment_deleted", comment_id=comment_id, by_user=user_id)

    return {"success": True, "message": "Comment deleted"}


@router.post("/comments/{comment_id}/reply", response_model=CommentResponse)
async def reply_to_comment(
    comment_id: str,
    request: CommentReply,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Reply to an existing comment."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    user_name = current_user.get("name", current_user.get("email", "Anonymous"))
    user_email = current_user.get("email")

    # Get parent comment
    parent = await mongodb.dashboard_comments.find_one({"_id": comment_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent comment not found")

    # Create reply
    reply_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Use root thread ID if replying to a reply
    thread_id = parent.get("thread_id") or parent["_id"]

    reply_doc = {
        "_id": reply_id,
        "dashboard_id": parent["dashboard_id"],
        "widget_id": parent.get("widget_id"),
        "content": request.content,
        "comment_type": parent.get("comment_type", "general"),
        "author_id": user_id,
        "author_name": user_name,
        "author_email": user_email,
        "mentions": request.mentions,
        "thread_id": thread_id,
        "reply_count": 0,
        "created_at": now,
        "updated_at": now,
        "is_edited": False
    }

    await mongodb.dashboard_comments.insert_one(reply_doc)

    # Increment reply count on root comment
    await mongodb.dashboard_comments.update_one(
        {"_id": thread_id},
        {"$inc": {"reply_count": 1}}
    )

    logger.info(
        "comment_reply_created",
        reply_id=reply_id,
        parent_id=comment_id,
        thread_id=thread_id,
        author=user_id
    )

    return CommentResponse(**{**reply_doc, "id": reply_id})


@router.get("/comments/{comment_id}/replies", response_model=List[CommentResponse])
async def get_comment_replies(
    comment_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Get all replies to a comment."""
    cursor = mongodb.dashboard_comments.find(
        {"thread_id": comment_id}
    ).sort("created_at", 1)

    replies = []
    async for doc in cursor:
        replies.append(CommentResponse(
            id=doc["_id"],
            dashboard_id=doc["dashboard_id"],
            widget_id=doc.get("widget_id"),
            content=doc["content"],
            comment_type=CommentType(doc.get("comment_type", "general")),
            author_id=doc["author_id"],
            author_name=doc["author_name"],
            author_email=doc.get("author_email"),
            mentions=doc.get("mentions", []),
            thread_id=doc.get("thread_id"),
            reply_count=doc.get("reply_count", 0),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            is_edited=doc.get("is_edited", False)
        ))

    return replies


# Endpoints - Annotations

@router.post("/widgets/{widget_id}/annotations", response_model=AnnotationResponse)
async def create_annotation(
    widget_id: str,
    request: AnnotationCreate,
    dashboard_id: str = Query(..., description="Dashboard containing the widget"),
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Add an annotation to a widget.

    Annotations can be positioned on the widget and linked to specific data points.
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    user_name = current_user.get("name", current_user.get("email", "Anonymous"))

    # Verify dashboard exists
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Create annotation
    annotation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    annotation_doc = {
        "_id": annotation_id,
        "widget_id": widget_id,
        "dashboard_id": dashboard_id,
        "content": request.content,
        "annotation_type": request.annotation_type.value,
        "position": request.position,
        "data_point": request.data_point,
        "author_id": user_id,
        "author_name": user_name,
        "created_at": now
    }

    # Store in separate annotations collection
    await mongodb.db["dashboard_annotations"].insert_one(annotation_doc)

    logger.info(
        "annotation_created",
        annotation_id=annotation_id,
        widget_id=widget_id,
        dashboard_id=dashboard_id,
        author=user_id
    )

    return AnnotationResponse(**{**annotation_doc, "id": annotation_id})


@router.get("/widgets/{widget_id}/annotations", response_model=List[AnnotationResponse])
async def get_widget_annotations(
    widget_id: str,
    dashboard_id: str = Query(..., description="Dashboard containing the widget"),
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Get all annotations for a widget."""
    cursor = mongodb.db["dashboard_annotations"].find({
        "widget_id": widget_id,
        "dashboard_id": dashboard_id
    }).sort("created_at", -1)

    annotations = []
    async for doc in cursor:
        annotations.append(AnnotationResponse(
            id=doc["_id"],
            widget_id=doc["widget_id"],
            dashboard_id=doc["dashboard_id"],
            content=doc["content"],
            annotation_type=AnnotationType(doc.get("annotation_type", "note")),
            position=doc.get("position"),
            data_point=doc.get("data_point"),
            author_id=doc["author_id"],
            author_name=doc["author_name"],
            created_at=doc["created_at"]
        ))

    return annotations


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """Delete an annotation."""
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))

    # Get annotation
    annotation = await mongodb.db["dashboard_annotations"].find_one({"_id": annotation_id})
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Check ownership or dashboard admin
    dashboard = await mongodb.dashboards.find_one({"_id": annotation["dashboard_id"]})
    is_dashboard_owner = dashboard and dashboard.get("owner_id") == user_id

    if annotation["author_id"] != user_id and not is_dashboard_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this annotation")

    await mongodb.db["dashboard_annotations"].delete_one({"_id": annotation_id})

    logger.info("annotation_deleted", annotation_id=annotation_id, by_user=user_id)

    return {"success": True, "message": "Annotation deleted"}
