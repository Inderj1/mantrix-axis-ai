"""Dashboard API routes for interactive dashboard management"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import secrets
import uuid
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user, get_optional_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboards"])


# Pydantic Models
class WidgetLayout(BaseModel):
    """Grid layout configuration for a widget"""
    x: int = Field(default=0, description="X position in grid")
    y: int = Field(default=0, description="Y position in grid")
    w: int = Field(default=4, description="Width in grid units")
    h: int = Field(default=3, description="Height in grid units")
    min_w: Optional[int] = Field(default=2, description="Minimum width")
    min_h: Optional[int] = Field(default=2, description="Minimum height")


class WidgetConfig(BaseModel):
    """Configuration for a dashboard widget"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = Field(default="chart", description="Widget type: chart, filter, text, metric")
    title: str = Field(default="New Widget")
    query: Optional[str] = Field(default=None, description="NLP query that generates data")
    chart_type: Optional[str] = Field(default=None, description="Chart type: bar, line, pie, scatter, area, table")
    layout: WidgetLayout = Field(default_factory=WidgetLayout)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Widget-specific filters")
    drill_path: Optional[List[str]] = Field(default=None, description="Drill-down path e.g. ['country', 'region', 'city']")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Additional chart configuration")
    data_cache: Optional[Dict[str, Any]] = Field(default=None, description="Cached query results")


class DashboardCreate(BaseModel):
    """Request model for creating a dashboard"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    widgets: List[WidgetConfig] = Field(default_factory=list)
    global_filters: Optional[Dict[str, Any]] = Field(default=None)
    is_public: bool = Field(default=False)
    tags: Optional[List[str]] = Field(default=None)


class DashboardUpdate(BaseModel):
    """Request model for updating a dashboard"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    widgets: Optional[List[WidgetConfig]] = None
    global_filters: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None


class DashboardResponse(BaseModel):
    """Response model for a dashboard"""
    id: str
    name: str
    description: Optional[str] = None
    organization_id: str
    owner_id: str
    owner_email: Optional[str] = None
    widgets: List[WidgetConfig]
    global_filters: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    is_public: bool
    share_token: Optional[str] = None
    tags: Optional[List[str]] = None


class DrillDownRequest(BaseModel):
    """Request model for drill-down query generation"""
    base_query: str = Field(..., description="Original NLP query")
    drill_dimension: str = Field(..., description="Dimension being drilled into")
    filter_value: str = Field(..., description="Value selected for drill-down")
    next_dimension: str = Field(..., description="Next dimension to group by")


class ShareLinkResponse(BaseModel):
    """Response model for share link generation"""
    share_url: str
    share_token: str


# Helper functions
def serialize_dashboard(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to API response format"""
    if doc is None:
        return None

    doc["id"] = str(doc.pop("_id", doc.get("id", "")))

    # Ensure datetime fields are serializable
    if "created_at" in doc and isinstance(doc["created_at"], datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if "updated_at" in doc and isinstance(doc["updated_at"], datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()

    return doc


# Routes
@router.post("/", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Create a new dashboard"""
    try:
        now = datetime.now(timezone.utc)

        doc = {
            "name": dashboard.name,
            "description": dashboard.description,
            "organization_id": current_user.get("organization_id", "default"),
            "owner_id": current_user.get("id", current_user.get("sub", "unknown")),
            "owner_email": current_user.get("email"),
            "widgets": [w.model_dump() for w in dashboard.widgets],
            "global_filters": dashboard.global_filters,
            "created_at": now,
            "updated_at": now,
            "is_public": dashboard.is_public,
            # Don't include share_token - will be set when sharing is enabled
            # (MongoDB unique index doesn't allow multiple nulls)
            "tags": dashboard.tags or []
        }

        result = await mongodb.db["dashboards"].insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info("Dashboard created",
                   dashboard_id=str(result.inserted_id),
                   owner_id=doc["owner_id"])

        return serialize_dashboard(doc)

    except Exception as e:
        logger.error("Error creating dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create dashboard: {str(e)}")


@router.get("/", response_model=List[DashboardResponse])
async def list_dashboards(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """List dashboards for the current user's organization"""
    try:
        org_id = current_user.get("organization_id", "default")
        user_id = current_user.get("id", current_user.get("sub"))

        # Get dashboards owned by user or public within organization
        cursor = mongodb.db["dashboards"].find({
            "$or": [
                {"owner_id": user_id},
                {"organization_id": org_id, "is_public": True}
            ]
        }).sort("updated_at", -1).skip(skip).limit(limit)

        dashboards = []
        async for doc in cursor:
            dashboards.append(serialize_dashboard(doc))

        return dashboards

    except Exception as e:
        logger.error("Error listing dashboards", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list dashboards: {str(e)}")


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Get a specific dashboard by ID"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        # Check access
        user_id = current_user.get("id", current_user.get("sub"))
        org_id = current_user.get("organization_id", "default")

        if doc["owner_id"] != user_id and not doc.get("is_public"):
            if doc.get("organization_id") != org_id:
                raise HTTPException(status_code=403, detail="Access denied")

        return serialize_dashboard(doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: str,
    updates: DashboardUpdate,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Update a dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        # Check ownership
        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can update this dashboard")

        # Build update document
        update_doc = {"updated_at": datetime.now(timezone.utc)}

        if updates.name is not None:
            update_doc["name"] = updates.name
        if updates.description is not None:
            update_doc["description"] = updates.description
        if updates.widgets is not None:
            update_doc["widgets"] = [w.model_dump() for w in updates.widgets]
        if updates.global_filters is not None:
            update_doc["global_filters"] = updates.global_filters
        if updates.is_public is not None:
            update_doc["is_public"] = updates.is_public
        if updates.tags is not None:
            update_doc["tags"] = updates.tags

        await mongodb.db["dashboards"].update_one(
            {"_id": ObjectId(dashboard_id)},
            {"$set": update_doc}
        )

        # Fetch updated document
        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        logger.info("Dashboard updated", dashboard_id=dashboard_id)

        return serialize_dashboard(doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update dashboard: {str(e)}")


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Delete a dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        # Check ownership
        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can delete this dashboard")

        await mongodb.db["dashboards"].delete_one({"_id": ObjectId(dashboard_id)})

        logger.info("Dashboard deleted", dashboard_id=dashboard_id)

        return {"status": "success", "message": "Dashboard deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete dashboard: {str(e)}")


# Widget management
@router.post("/{dashboard_id}/widgets", response_model=DashboardResponse)
async def add_widget(
    dashboard_id: str,
    widget: WidgetConfig,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Add a widget to a dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can modify this dashboard")

        await mongodb.db["dashboards"].update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$push": {"widgets": widget.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        logger.info("Widget added to dashboard", dashboard_id=dashboard_id, widget_id=widget.id)

        return serialize_dashboard(doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding widget", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to add widget: {str(e)}")


@router.delete("/{dashboard_id}/widgets/{widget_id}")
async def remove_widget(
    dashboard_id: str,
    widget_id: str,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Remove a widget from a dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can modify this dashboard")

        await mongodb.db["dashboards"].update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$pull": {"widgets": {"id": widget_id}},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        logger.info("Widget removed from dashboard", dashboard_id=dashboard_id, widget_id=widget_id)

        return {"status": "success", "message": "Widget removed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error removing widget", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to remove widget: {str(e)}")


# Sharing
@router.post("/{dashboard_id}/share", response_model=ShareLinkResponse)
async def generate_share_link(
    dashboard_id: str,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Generate a shareable link for the dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can share this dashboard")

        # Generate unique share token
        share_token = secrets.token_urlsafe(32)

        await mongodb.db["dashboards"].update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$set": {
                    "share_token": share_token,
                    "is_public": True,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        logger.info("Share link generated", dashboard_id=dashboard_id)

        return {
            "share_url": f"/dashboards/shared/{share_token}",
            "share_token": share_token
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating share link", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate share link: {str(e)}")


@router.delete("/{dashboard_id}/share")
async def revoke_share_link(
    dashboard_id: str,
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Revoke the share link for a dashboard"""
    try:
        from bson import ObjectId

        doc = await mongodb.db["dashboards"].find_one({"_id": ObjectId(dashboard_id)})

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        user_id = current_user.get("id", current_user.get("sub"))
        if doc["owner_id"] != user_id:
            raise HTTPException(status_code=403, detail="Only the owner can manage sharing")

        await mongodb.db["dashboards"].update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$set": {
                    "share_token": None,
                    "is_public": False,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )

        logger.info("Share link revoked", dashboard_id=dashboard_id)

        return {"status": "success", "message": "Share link revoked"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error revoking share link", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to revoke share link: {str(e)}")


@router.get("/shared/{share_token}", response_model=DashboardResponse)
async def get_shared_dashboard(
    share_token: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Access a dashboard via share link (no auth required)"""
    try:
        doc = await mongodb.db["dashboards"].find_one({
            "share_token": share_token,
            "is_public": True
        })

        if not doc:
            raise HTTPException(status_code=404, detail="Dashboard not found or not shared")

        logger.info("Shared dashboard accessed", share_token=share_token[:8] + "...")

        return serialize_dashboard(doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting shared dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get shared dashboard: {str(e)}")


# Drill-down
@router.post("/drill-down")
async def generate_drill_down_query(
    request: DrillDownRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate a drill-down query from a parent query.

    Example:
    - Base: "Show revenue by country"
    - Drill: country="USA", next=region
    - Result: "Show revenue by region WHERE country = 'USA'"
    """
    try:
        from src.core.llm_client import LLMClient
        from src.api.routes import get_sql_generator

        # Use LLM to generate modified query
        llm = LLMClient()

        drill_prompt = f"""
You are helping generate a drill-down query for a business intelligence dashboard.

Original query: {request.base_query}

The user clicked on {request.drill_dimension} = "{request.filter_value}" and wants to drill down to see details by {request.next_dimension}.

Generate a new natural language query that:
1. Filters to only {request.drill_dimension} = "{request.filter_value}"
2. Groups by {request.next_dimension} instead of {request.drill_dimension}
3. Maintains the same metrics/aggregations from the original query

Return ONLY the new query text, nothing else.
"""

        new_query = await llm.generate_text(drill_prompt)
        new_query = new_query.strip().strip('"').strip("'")

        # Execute the drill-down query
        org_id = current_user.get("organization_id", "default")
        sql_generator = await get_sql_generator(org_id)

        result = await sql_generator.generate_sql(new_query)

        logger.info("Drill-down query generated",
                   original_query=request.base_query,
                   drill_dimension=request.drill_dimension,
                   filter_value=request.filter_value)

        return {
            "query": new_query,
            "sql": result.get("sql"),
            "data": result.get("data"),
            "columns": result.get("columns"),
            "drill_level": request.drill_dimension,
            "filter_applied": request.filter_value,
            "next_dimension": request.next_dimension
        }

    except Exception as e:
        logger.error("Error generating drill-down query", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate drill-down query: {str(e)}")


# Dashboard templates
@router.get("/templates/")
async def list_dashboard_templates():
    """List available dashboard templates"""
    templates = [
        {
            "id": "sales-overview",
            "name": "Sales Overview",
            "description": "Revenue, orders, and top products",
            "widgets": [
                {"type": "chart", "chart_type": "line", "title": "Revenue Trend", "query": "Show monthly revenue for the last 12 months"},
                {"type": "chart", "chart_type": "bar", "title": "Top Products", "query": "Show top 10 products by revenue"},
                {"type": "metric", "title": "Total Revenue", "query": "What is the total revenue?"},
                {"type": "chart", "chart_type": "pie", "title": "Revenue by Region", "query": "Show revenue breakdown by region"}
            ]
        },
        {
            "id": "customer-analytics",
            "name": "Customer Analytics",
            "description": "Customer segments, retention, and lifetime value",
            "widgets": [
                {"type": "chart", "chart_type": "bar", "title": "Customer Segments", "query": "Show customer count by segment"},
                {"type": "chart", "chart_type": "line", "title": "New Customers", "query": "Show new customers per month"},
                {"type": "metric", "title": "Customer Count", "query": "How many total customers?"},
                {"type": "chart", "chart_type": "scatter", "title": "RFM Analysis", "query": "Show customers by recency and frequency"}
            ]
        },
        {
            "id": "inventory-status",
            "name": "Inventory Status",
            "description": "Stock levels, turnover, and alerts",
            "widgets": [
                {"type": "chart", "chart_type": "bar", "title": "Stock Levels", "query": "Show current stock levels by category"},
                {"type": "chart", "chart_type": "table", "title": "Low Stock Items", "query": "Show products with stock below reorder point"},
                {"type": "metric", "title": "Total SKUs", "query": "How many unique products in inventory?"},
                {"type": "chart", "chart_type": "line", "title": "Inventory Turnover", "query": "Show monthly inventory turnover rate"}
            ]
        }
    ]

    return templates


@router.post("/from-template/{template_id}", response_model=DashboardResponse)
async def create_from_template(
    template_id: str,
    name: str = Query(..., min_length=1, max_length=200),
    current_user: Dict = Depends(get_current_user),
    mongodb: MongoDBClient = Depends(get_mongodb_client)
):
    """Create a new dashboard from a template"""
    try:
        templates = await list_dashboard_templates()
        template = next((t for t in templates if t["id"] == template_id), None)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Create widgets from template
        widgets = []
        for i, w in enumerate(template["widgets"]):
            widget = WidgetConfig(
                id=str(uuid.uuid4())[:8],
                type=w["type"],
                title=w["title"],
                query=w.get("query"),
                chart_type=w.get("chart_type"),
                layout=WidgetLayout(
                    x=(i % 2) * 6,
                    y=(i // 2) * 3,
                    w=6,
                    h=3
                )
            )
            widgets.append(widget)

        dashboard = DashboardCreate(
            name=name,
            description=template["description"],
            widgets=widgets
        )

        return await create_dashboard(dashboard, current_user, mongodb)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating from template", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create from template: {str(e)}")
