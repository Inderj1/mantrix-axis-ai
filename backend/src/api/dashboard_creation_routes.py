"""
Dashboard Creation Routes - Conversational dashboard creation via NLP.

Enables users to create dashboards through natural language:
"Create a sales dashboard with revenue by region and customer trends"
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import uuid
import asyncio
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user
from src.core.dashboard_intent_detector import (
    detect_dashboard_intent,
    DashboardIntent,
    DashboardIntentType,
    WidgetDescription
)
from src.core.sql_generator import SQLGenerator
from src.core.column_metadata_service import ColumnMetadataService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboard-creation"])


# Request/Response Models
class ConversationalDashboardRequest(BaseModel):
    """Request model for conversational dashboard creation."""
    query: str = Field(..., description="Natural language request for dashboard creation")
    confirm: bool = Field(default=False, description="Set to True to confirm and create the dashboard")
    preview_id: Optional[str] = Field(default=None, description="Preview ID from a previous preview request")


class WidgetPreview(BaseModel):
    """Preview of a widget that will be created."""
    id: str
    title: str
    query: str
    suggested_chart_type: Optional[str]
    execution_preview: Optional[Dict[str, Any]] = None  # Sample data if confirm=True
    error: Optional[str] = None


class DashboardPreviewResponse(BaseModel):
    """Response for dashboard preview before creation."""
    preview_id: str
    dashboard_name: str
    dashboard_description: Optional[str]
    widgets: List[WidgetPreview]
    global_filters: Dict[str, str]
    confidence: float
    ready_to_create: bool
    message: str


class DashboardCreatedResponse(BaseModel):
    """Response after dashboard is created."""
    dashboard_id: str
    dashboard_name: str
    dashboard_url: str
    widget_count: int
    message: str


# In-memory preview cache (in production, use Redis)
_preview_cache: Dict[str, Dict[str, Any]] = {}


def _get_default_layout(index: int, total: int) -> Dict[str, int]:
    """Generate default widget layout based on position."""
    # 2-column layout for multiple widgets
    cols = 2 if total > 1 else 1
    col_width = 12 // cols

    row = index // cols
    col = index % cols

    return {
        "x": col * col_width,
        "y": row * 3,  # Each row is 3 units high
        "w": col_width,
        "h": 3,
        "min_w": 2,
        "min_h": 2
    }


async def _execute_widget_query(
    widget: WidgetDescription,
    sql_generator: SQLGenerator,
    column_service: ColumnMetadataService
) -> Dict[str, Any]:
    """Execute a widget's query and get chart recommendations."""
    try:
        # Generate and execute SQL
        result = await sql_generator.generate_sql(
            question=widget.query,
            execute=True,
            limit=100  # Limit preview data
        )

        # Get column metadata for chart recommendations
        columns = result.get("execution", {}).get("columns", [])
        metadata = column_service.analyze_columns(columns)

        # Use suggested chart type or get recommendation
        chart_type = widget.suggested_chart_type
        if not chart_type and metadata.get("recommended_charts"):
            chart_type = metadata["recommended_charts"][0]

        return {
            "success": True,
            "data": result.get("execution", {}).get("results", [])[:10],  # First 10 rows for preview
            "row_count": len(result.get("execution", {}).get("results", [])),
            "columns": columns,
            "chart_type": chart_type,
            "chart_recommendations": metadata.get("recommended_charts", []),
            "dimensions": metadata.get("dimensions", []),
            "measures": metadata.get("measures", []),
            "sql": result.get("sql")
        }
    except Exception as e:
        logger.error("widget_query_execution_failed", query=widget.query, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "columns": []
        }


@router.post("/create-from-conversation", response_model=DashboardPreviewResponse)
async def create_dashboard_from_conversation(
    request: ConversationalDashboardRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a dashboard from a natural language description.

    First call (confirm=False): Returns a preview of the dashboard
    Second call (confirm=True, preview_id): Creates the actual dashboard
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    org_id = current_user.get("custom:organization_id", "default")

    # Detect dashboard intent
    intent = detect_dashboard_intent(request.query)

    if intent.intent_type == DashboardIntentType.NONE:
        raise HTTPException(
            status_code=400,
            detail="Could not detect a dashboard creation intent. Try: 'Create a dashboard showing...' or 'Build a sales dashboard with...'"
        )

    # Generate preview ID
    preview_id = request.preview_id or str(uuid.uuid4())[:12]

    # Initialize services
    sql_generator = SQLGenerator()
    column_service = ColumnMetadataService()

    # Process each widget
    widget_previews = []
    all_successful = True

    for i, widget_desc in enumerate(intent.widget_descriptions):
        widget_id = f"w-{uuid.uuid4().hex[:8]}"

        # Execute query to validate and get chart recommendations
        exec_result = await _execute_widget_query(widget_desc, sql_generator, column_service)

        widget_preview = WidgetPreview(
            id=widget_id,
            title=widget_desc.suggested_title or f"Widget {i + 1}",
            query=widget_desc.query,
            suggested_chart_type=exec_result.get("chart_type", widget_desc.suggested_chart_type),
            execution_preview={
                "sample_data": exec_result.get("data", []),
                "row_count": exec_result.get("row_count", 0),
                "columns": exec_result.get("columns", []),
                "chart_recommendations": exec_result.get("chart_recommendations", []),
                "sql": exec_result.get("sql")
            } if exec_result.get("success") else None,
            error=exec_result.get("error")
        )

        widget_previews.append(widget_preview)

        if not exec_result.get("success"):
            all_successful = False

    # Cache the preview for confirmation
    _preview_cache[preview_id] = {
        "intent": intent,
        "widget_previews": widget_previews,
        "user_id": user_id,
        "org_id": org_id,
        "created_at": datetime.now(timezone.utc)
    }

    # Determine message
    if all_successful:
        message = f"Ready to create '{intent.dashboard_name}' with {len(widget_previews)} widget(s). Set confirm=True to create."
    else:
        failed_count = sum(1 for w in widget_previews if w.error)
        message = f"Preview generated with {failed_count} widget(s) having errors. Review and modify queries if needed."

    return DashboardPreviewResponse(
        preview_id=preview_id,
        dashboard_name=intent.dashboard_name or "New Dashboard",
        dashboard_description=intent.dashboard_description,
        widgets=widget_previews,
        global_filters=intent.global_filters,
        confidence=intent.confidence,
        ready_to_create=all_successful,
        message=message
    )


@router.post("/confirm-creation", response_model=DashboardCreatedResponse)
async def confirm_dashboard_creation(
    preview_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Confirm and create a dashboard from a preview.
    """
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    org_id = current_user.get("custom:organization_id", "default")

    # Get cached preview
    cached = _preview_cache.get(preview_id)
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="Preview not found. Please generate a new preview."
        )

    # Verify user
    if cached["user_id"] != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only confirm your own dashboard previews."
        )

    intent: DashboardIntent = cached["intent"]
    widget_previews: List[WidgetPreview] = cached["widget_previews"]

    # Build dashboard document
    dashboard_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    widgets = []
    for i, wp in enumerate(widget_previews):
        if wp.error:
            continue  # Skip widgets with errors

        widgets.append({
            "id": wp.id,
            "type": "chart",
            "title": wp.title,
            "query": wp.query,
            "chart_type": wp.suggested_chart_type or "bar",
            "layout": _get_default_layout(i, len(widget_previews)),
            "filters": None,
            "drill_path": None,
            "config": None,
            "data_cache": wp.execution_preview.get("sample_data") if wp.execution_preview else None
        })

    dashboard_doc = {
        "_id": dashboard_id,
        "name": intent.dashboard_name or "New Dashboard",
        "description": intent.dashboard_description,
        "organization_id": org_id,
        "owner_id": user_id,
        "owner_email": current_user.get("email"),
        "widgets": widgets,
        "global_filters": intent.global_filters,
        "created_at": now,
        "updated_at": now,
        "is_public": False,
        "share_token": None,
        "tags": ["ai-generated"],
        "source": {
            "type": "conversational",
            "original_query": intent.raw_query,
            "created_via": "chat"
        }
    }

    # Insert into MongoDB
    await mongodb.dashboards.insert_one(dashboard_doc)

    # Clean up preview cache
    del _preview_cache[preview_id]

    logger.info(
        "dashboard_created_from_conversation",
        dashboard_id=dashboard_id,
        user_id=user_id,
        widget_count=len(widgets),
        original_query=intent.raw_query
    )

    return DashboardCreatedResponse(
        dashboard_id=dashboard_id,
        dashboard_name=dashboard_doc["name"],
        dashboard_url=f"/dashboards/{dashboard_id}",
        widget_count=len(widgets),
        message=f"Dashboard '{dashboard_doc['name']}' created successfully with {len(widgets)} widget(s)!"
    )


@router.post("/detect-intent")
async def detect_intent(
    query: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Detect if a query contains a dashboard creation intent.
    Used by frontend to show dashboard creation UI.
    """
    intent = detect_dashboard_intent(query)

    return {
        "has_dashboard_intent": intent.intent_type != DashboardIntentType.NONE,
        "intent_type": intent.intent_type.value,
        "confidence": intent.confidence,
        "suggested_name": intent.dashboard_name,
        "widget_count": len(intent.widget_descriptions),
        "widgets": [
            {
                "query": w.query,
                "title": w.suggested_title,
                "chart_type": w.suggested_chart_type
            }
            for w in intent.widget_descriptions
        ]
    }


@router.get("/preview/{preview_id}")
async def get_preview(
    preview_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a cached dashboard preview.
    """
    cached = _preview_cache.get(preview_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Preview not found")

    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    if cached["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    intent = cached["intent"]
    widget_previews = cached["widget_previews"]

    return DashboardPreviewResponse(
        preview_id=preview_id,
        dashboard_name=intent.dashboard_name or "New Dashboard",
        dashboard_description=intent.dashboard_description,
        widgets=widget_previews,
        global_filters=intent.global_filters,
        confidence=intent.confidence,
        ready_to_create=all(not w.error for w in widget_previews),
        message="Cached preview retrieved"
    )


@router.delete("/preview/{preview_id}")
async def cancel_preview(
    preview_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Cancel/delete a dashboard preview.
    """
    cached = _preview_cache.get(preview_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Preview not found")

    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    if cached["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    del _preview_cache[preview_id]

    return {"message": "Preview cancelled", "preview_id": preview_id}
