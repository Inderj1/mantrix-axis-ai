"""
Narrative Routes - API endpoints for AI-generated dashboard narratives.

Endpoints:
- POST /api/v1/dashboards/{id}/narrative - Generate full dashboard narrative
- POST /api/v1/dashboards/{id}/summary - Generate executive summary only
- POST /api/v1/widgets/{id}/insight - Generate widget insight
- POST /api/v1/narrative/trend - Generate trend analysis
- POST /api/v1/narrative/anomaly - Generate anomaly explanation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import structlog

from src.db.mongodb_client import get_mongodb_client, MongoDBClient
from src.api.middleware.cognito_auth import get_current_user
from src.core.dashboard_narrative_generator import get_narrative_generator

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["narratives"])


# Request/Response Models
class TimePeriod(BaseModel):
    """Time period specification."""
    start: Optional[str] = None
    end: Optional[str] = None


class NarrativeRequest(BaseModel):
    """Request for dashboard narrative generation."""
    time_period: Optional[TimePeriod] = None
    include_widget_insights: bool = Field(default=True)
    max_widgets: int = Field(default=10, ge=1, le=20)


class WidgetInsightRequest(BaseModel):
    """Request for widget insight generation."""
    widget_type: str
    widget_title: str
    metric_name: str
    current_data: Dict[str, Any]
    historical_data: Optional[Dict[str, Any]] = None


class TrendAnalysisRequest(BaseModel):
    """Request for trend analysis."""
    metric_name: str
    data_points: List[Dict[str, Any]]
    time_period: str


class AnomalyNarrativeRequest(BaseModel):
    """Request for anomaly narrative."""
    widget_title: str
    metric_name: str
    expected_value: Any
    actual_value: Any
    deviation_percentage: float
    timestamp: str
    historical_context: Optional[str] = None


class ExecutiveSummaryResponse(BaseModel):
    """Response for executive summary."""
    summary: str
    key_metrics: List[Dict[str, Any]]
    highlights: List[str]
    concerns: List[str]
    recommendations: List[str]
    generated_at: str
    dashboard_name: str


class WidgetInsightResponse(BaseModel):
    """Response for widget insight."""
    insight: str
    trend: str
    confidence: str
    comparison: Optional[str]
    widget_title: str
    generated_at: str


class FullNarrativeResponse(BaseModel):
    """Response for full dashboard narrative."""
    dashboard_id: str
    dashboard_name: str
    executive_summary: Dict[str, Any]
    widget_insights: List[Dict[str, Any]]
    generated_at: str
    widget_count: int
    insights_generated: int


# Endpoints

@router.post("/dashboards/{dashboard_id}/narrative", response_model=FullNarrativeResponse)
async def generate_dashboard_narrative(
    dashboard_id: str,
    request: NarrativeRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate a complete narrative for a dashboard.

    This includes an executive summary and insights for each widget.
    """
    # Get dashboard from MongoDB
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check access permissions
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    org_id = current_user.get("custom:organization_id", "default")

    if dashboard.get("owner_id") != user_id and dashboard.get("organization_id") != org_id:
        if not dashboard.get("is_public", False):
            raise HTTPException(status_code=403, detail="Access denied")

    # Get widgets with data
    widgets = dashboard.get("widgets", [])

    # Limit widgets for processing
    widgets_to_process = widgets[:request.max_widgets]

    # Generate narrative
    generator = get_narrative_generator()
    time_period_dict = None
    if request.time_period:
        time_period_dict = {
            "start": request.time_period.start,
            "end": request.time_period.end
        }

    if request.include_widget_insights:
        result = await generator.generate_full_dashboard_narrative(
            dashboard_id=dashboard_id,
            dashboard_name=dashboard.get("name", "Untitled Dashboard"),
            dashboard_description=dashboard.get("description", ""),
            widgets=widgets_to_process,
            time_period=time_period_dict
        )
    else:
        # Just executive summary
        summary = await generator.generate_executive_summary(
            dashboard_name=dashboard.get("name", "Untitled Dashboard"),
            dashboard_description=dashboard.get("description", ""),
            widgets=widgets_to_process,
            time_period=time_period_dict
        )
        result = {
            "dashboard_id": dashboard_id,
            "dashboard_name": dashboard.get("name", "Untitled Dashboard"),
            "executive_summary": summary,
            "widget_insights": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "widget_count": len(widgets),
            "insights_generated": 0
        }

    logger.info(
        "dashboard_narrative_generated",
        dashboard_id=dashboard_id,
        user_id=user_id,
        widget_count=len(widgets_to_process)
    )

    return FullNarrativeResponse(**result)


@router.post("/dashboards/{dashboard_id}/summary", response_model=ExecutiveSummaryResponse)
async def generate_executive_summary(
    dashboard_id: str,
    request: NarrativeRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate only the executive summary for a dashboard.

    Faster than full narrative as it doesn't generate individual widget insights.
    """
    # Get dashboard from MongoDB
    dashboard = await mongodb.dashboards.find_one({"_id": dashboard_id})

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Check access
    user_id = current_user.get("sub", current_user.get("username", "anonymous"))
    org_id = current_user.get("custom:organization_id", "default")

    if dashboard.get("owner_id") != user_id and dashboard.get("organization_id") != org_id:
        if not dashboard.get("is_public", False):
            raise HTTPException(status_code=403, detail="Access denied")

    widgets = dashboard.get("widgets", [])[:request.max_widgets]

    generator = get_narrative_generator()
    time_period_dict = None
    if request.time_period:
        time_period_dict = {
            "start": request.time_period.start,
            "end": request.time_period.end
        }

    result = await generator.generate_executive_summary(
        dashboard_name=dashboard.get("name", "Untitled Dashboard"),
        dashboard_description=dashboard.get("description", ""),
        widgets=widgets,
        time_period=time_period_dict
    )

    logger.info(
        "executive_summary_generated",
        dashboard_id=dashboard_id,
        user_id=user_id
    )

    return ExecutiveSummaryResponse(**result)


@router.post("/widgets/insight", response_model=WidgetInsightResponse)
async def generate_widget_insight(
    request: WidgetInsightRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate an insight for a specific widget.

    Can be called independently for any widget data.
    """
    generator = get_narrative_generator()

    result = await generator.generate_widget_insight(
        widget_type=request.widget_type,
        widget_title=request.widget_title,
        metric_name=request.metric_name,
        current_data=request.current_data,
        historical_data=request.historical_data
    )

    logger.info(
        "widget_insight_generated",
        widget_title=request.widget_title,
        user_id=current_user.get("sub")
    )

    return WidgetInsightResponse(**result)


@router.post("/narrative/trend")
async def generate_trend_analysis(
    request: TrendAnalysisRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate trend analysis for time series data.

    Analyzes direction, strength, seasonality, and provides narrative.
    """
    generator = get_narrative_generator()

    result = await generator.generate_trend_analysis(
        metric_name=request.metric_name,
        data_points=request.data_points,
        time_period=request.time_period
    )

    logger.info(
        "trend_analysis_generated",
        metric=request.metric_name,
        data_points=len(request.data_points),
        user_id=current_user.get("sub")
    )

    return result


@router.post("/narrative/anomaly")
async def generate_anomaly_narrative(
    request: AnomalyNarrativeRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate an explanation for a detected anomaly.

    Provides severity, headline, explanation, impact, and suggested action.
    """
    generator = get_narrative_generator()

    result = await generator.generate_anomaly_narrative(
        widget_title=request.widget_title,
        metric_name=request.metric_name,
        expected_value=request.expected_value,
        actual_value=request.actual_value,
        deviation_percentage=request.deviation_percentage,
        timestamp=request.timestamp,
        historical_context=request.historical_context
    )

    logger.info(
        "anomaly_narrative_generated",
        widget=request.widget_title,
        deviation=request.deviation_percentage,
        user_id=current_user.get("sub")
    )

    return result


@router.post("/narrative/compare")
async def generate_comparative_analysis(
    comparison_type: str,
    categories: List[str],
    comparison_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate comparative analysis between categories or segments.

    Identifies winner, laggard, and provides gap analysis.
    """
    generator = get_narrative_generator()

    result = await generator.generate_comparative_analysis(
        comparison_type=comparison_type,
        categories=categories,
        comparison_data=comparison_data
    )

    logger.info(
        "comparative_analysis_generated",
        comparison_type=comparison_type,
        category_count=len(categories),
        user_id=current_user.get("sub")
    )

    return result


# Background task for caching narratives
async def cache_narrative_background(
    dashboard_id: str,
    narrative: Dict[str, Any],
    mongodb: MongoDBClient
):
    """Cache generated narrative for faster subsequent access."""
    try:
        await mongodb.db["narrative_cache"].update_one(
            {"dashboard_id": dashboard_id},
            {
                "$set": {
                    "dashboard_id": dashboard_id,
                    "narrative": narrative,
                    "cached_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        logger.info("narrative_cached", dashboard_id=dashboard_id)
    except Exception as e:
        logger.error(f"Failed to cache narrative: {e}")


@router.get("/dashboards/{dashboard_id}/narrative/cached")
async def get_cached_narrative(
    dashboard_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get cached narrative if available.

    Returns cached narrative or 404 if not cached.
    Useful for quick loading while fresh narrative generates in background.
    """
    cached = await mongodb.db["narrative_cache"].find_one({"dashboard_id": dashboard_id})

    if not cached:
        raise HTTPException(status_code=404, detail="No cached narrative found")

    return {
        "dashboard_id": dashboard_id,
        "narrative": cached.get("narrative"),
        "cached_at": cached.get("cached_at"),
        "is_cached": True
    }
