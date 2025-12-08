"""API routes for query history - Background query tracking and notifications."""
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Depends, Query
import structlog

from src.api.models import (
    QueryHistoryEntry,
    QueryHistoryListResponse,
    QueryHistoryFullResponse,
    MarkBackgroundRequest,
    NotificationPreferences,
    QueryResultSummary,
    NotificationsSent
)
from src.db.mongodb_client import MongoDBClient, get_mongodb_client
from src.api.middleware.cognito_auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/query-history", tags=["query-history"])


def _doc_to_query_history_entry(doc: dict) -> QueryHistoryEntry:
    """Convert MongoDB document to QueryHistoryEntry model."""
    if not doc:
        return None

    # Convert result_summary if present
    result_summary = None
    if doc.get("result_summary"):
        rs = doc["result_summary"]
        result_summary = QueryResultSummary(
            row_count=rs.get("row_count", 0),
            columns=rs.get("columns", []),
            preview=rs.get("preview", [])
        )

    # Convert notification preferences
    np = doc.get("notification_preferences", {})
    notification_preferences = NotificationPreferences(
        browser=np.get("browser", True),
        email=np.get("email", False)
    )

    # Convert notifications sent
    ns = doc.get("notifications_sent", {})
    notifications_sent = NotificationsSent(
        browser=ns.get("browser", False),
        email=ns.get("email", False),
        email_sent_at=ns.get("email_sent_at").isoformat() if ns.get("email_sent_at") else None
    )

    return QueryHistoryEntry(
        execution_id=doc.get("execution_id", ""),
        user_id=doc.get("user_id", ""),
        organization_id=doc.get("organization_id", ""),
        question=doc.get("question", ""),
        sql=doc.get("sql", ""),
        status=doc.get("status", "running"),
        started_at=doc.get("started_at").isoformat() if doc.get("started_at") else "",
        completed_at=doc.get("completed_at").isoformat() if doc.get("completed_at") else None,
        execution_time_seconds=doc.get("execution_time_seconds"),
        result_summary=result_summary,
        error=doc.get("error"),
        is_background=doc.get("is_background", False),
        notification_preferences=notification_preferences,
        notifications_sent=notifications_sent
    )


@router.get("", response_model=QueryHistoryListResponse)
async def list_query_history(
    status: Optional[str] = Query(None, description="Filter by status: running, complete, error"),
    limit: int = Query(default=20, le=100, description="Maximum number of queries to return"),
    offset: int = Query(default=0, ge=0, description="Number of queries to skip"),
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """List query history for the current user."""
    try:
        user_id = user.get("sub", "default") if user else "default"

        logger.info(
            "Listing query history",
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )

        # Get queries from MongoDB
        query_docs = await db.list_query_history(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset
        )

        # Convert to QueryHistoryEntry models
        queries = [_doc_to_query_history_entry(doc) for doc in query_docs]

        # Get pending count for badge
        pending_count = await db.count_pending_queries(user_id)

        return QueryHistoryListResponse(
            queries=queries,
            total_count=len(queries),
            pending_count=pending_count
        )

    except Exception as e:
        logger.error("Failed to list query history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_queries(
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Get all running/pending queries for the current user (for notification polling)."""
    try:
        user_id = user.get("sub", "default") if user else "default"

        logger.info("Getting pending queries", user_id=user_id)

        # Get pending queries
        query_docs = await db.get_pending_queries(user_id)
        queries = [_doc_to_query_history_entry(doc) for doc in query_docs]

        return {
            "queries": queries,
            "count": len(queries)
        }

    except Exception as e:
        logger.error("Failed to get pending queries", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending/count")
async def get_pending_count(
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Get count of pending queries (for badge display)."""
    try:
        user_id = user.get("sub", "default") if user else "default"
        count = await db.count_pending_queries(user_id)
        return {"count": count}

    except Exception as e:
        logger.error("Failed to get pending count", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}", response_model=QueryHistoryFullResponse)
async def get_query_history(
    execution_id: str,
    include_results: bool = Query(False, description="Include full results in response"),
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Get a specific query from history with optional full results."""
    try:
        user_id = user.get("sub", "default") if user else "default"

        logger.info(
            "Getting query history",
            execution_id=execution_id,
            user_id=user_id,
            include_results=include_results
        )

        # Get query from MongoDB
        doc = await db.get_query_history(execution_id)

        if not doc:
            raise HTTPException(status_code=404, detail=f"Query {execution_id} not found")

        # Verify user owns this query
        if doc.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Convert result_summary if present
        result_summary = None
        if doc.get("result_summary"):
            rs = doc["result_summary"]
            result_summary = QueryResultSummary(
                row_count=rs.get("row_count", 0),
                columns=rs.get("columns", []),
                preview=rs.get("preview", [])
            )

        # Build response
        response = QueryHistoryFullResponse(
            execution_id=doc.get("execution_id", ""),
            status=doc.get("status", "running"),
            question=doc.get("question", ""),
            sql=doc.get("sql", ""),
            result_summary=result_summary,
            execution_time_seconds=doc.get("execution_time_seconds"),
            error=doc.get("error")
        )

        # Include full results if requested and available
        if include_results:
            if doc.get("full_results"):
                response.full_results = doc["full_results"]
            elif doc.get("full_results_s3_key"):
                # TODO: Generate presigned S3 URL
                response.full_results_s3_url = f"s3://{doc['full_results_s3_key']}"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get query history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/background")
async def mark_query_as_background(
    execution_id: str,
    request: MarkBackgroundRequest,
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Mark a running query as background (user navigating away)."""
    try:
        user_id = user.get("sub", "default") if user else "default"

        logger.info(
            "Marking query as background",
            execution_id=execution_id,
            user_id=user_id,
            notification_preferences=request.notification_preferences.model_dump()
        )

        # Get query to verify ownership
        doc = await db.get_query_history(execution_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Query {execution_id} not found")

        if doc.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Update to background mode
        success = await db.update_query_history(
            execution_id=execution_id,
            updates={
                "is_background": True,
                "notification_preferences": request.notification_preferences.model_dump()
            }
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update query")

        return {
            "success": True,
            "message": "Query marked as background",
            "execution_id": execution_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark query as background", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/notification-sent")
async def mark_notification_sent(
    execution_id: str,
    notification_type: str = Query(..., description="Notification type: browser or email"),
    user: Optional[Dict] = Depends(get_current_user),
    db: MongoDBClient = Depends(get_mongodb_client)
):
    """Mark a notification as sent (called by frontend after showing notification)."""
    try:
        user_id = user.get("sub", "default") if user else "default"

        if notification_type not in ["browser", "email"]:
            raise HTTPException(status_code=400, detail="notification_type must be 'browser' or 'email'")

        logger.info(
            "Marking notification sent",
            execution_id=execution_id,
            notification_type=notification_type
        )

        # Verify ownership
        doc = await db.get_query_history(execution_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Query {execution_id} not found")

        if doc.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Mark notification sent
        success = await db.mark_notification_sent(execution_id, notification_type)

        return {
            "success": success,
            "execution_id": execution_id,
            "notification_type": notification_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark notification sent", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
