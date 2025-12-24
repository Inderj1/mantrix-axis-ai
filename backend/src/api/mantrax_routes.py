"""
Mantrax Agent API Routes

API endpoints for interacting with the Mantrax agent system.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import structlog
from pydantic import BaseModel

from src.agents.mantrax import ResultsFormatterAgent

logger = structlog.get_logger()
router = APIRouter(tags=["mantrax"])

# Initialize agents
results_formatter = ResultsFormatterAgent()


class FormatResultsRequest(BaseModel):
    """Request model for formatting results."""
    query: str
    sql: Optional[str] = None  # Optional for multi-database queries where SQL is per-connector
    results: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None  # For personalized insights
    # LLM chart recommendation (highest priority - from SQL generation)
    recommended_chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None  # {"x_axis_column": "date", "y_axis_column": "revenue"}
    # Chart intelligence from backend's ColumnMetadataService (fallback)
    chart_recommendations: Optional[List[str]] = None
    dimensions: Optional[List[str]] = None
    measures: Optional[List[str]] = None
    time_columns: Optional[List[str]] = None


class FormatResultsResponse(BaseModel):
    """Response model for formatted results."""
    summary: str
    components: List[Dict[str, Any]]


@router.post("/format-results", response_model=FormatResultsResponse)
async def format_results(request: FormatResultsRequest) -> FormatResultsResponse:
    """
    Format query results using the ResultsFormatter agent.
    
    This endpoint takes raw query results and transforms them into
    a structured presentation with insights, charts, and summaries.
    """
    try:
        logger.info("Formatting results", row_count=len(request.results))
        
        # Call the results formatter agent
        formatted = results_formatter.format_results(
            query=request.query,
            sql=request.sql,
            results=request.results,
            metadata=request.metadata,
            user_id=request.user_id,
            recommended_chart_type=request.recommended_chart_type,  # LLM's primary choice
            chart_config=request.chart_config,  # LLM's axis hints
            chart_recommendations=request.chart_recommendations,  # Column-based fallback
            dimensions=request.dimensions,
            measures=request.measures,
            time_columns=request.time_columns
        )
        
        # Check for errors
        if formatted.get("status") == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to format results: {formatted.get('error', 'Unknown error')}"
            )
        
        return FormatResultsResponse(
            summary=formatted.get("summary", ""),
            components=formatted.get("components", [])
        )
        
    except Exception as e:
        logger.error(f"Failed to format results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """List all available Mantrax agents."""
    return {
        "agents": [
            {
                "name": "ResultsFormatter",
                "description": "Formats query results into various presentation formats with insights",
                "status": "active"
            }
        ]
    }


@router.get("/agents/{agent_name}/history")
async def get_agent_history(agent_name: str, limit: int = 10) -> Dict[str, Any]:
    """Get execution history for a specific agent."""
    if agent_name == "ResultsFormatter":
        history = results_formatter.get_execution_history(limit=limit)
        return {
            "agent": agent_name,
            "history": history,
            "total_executions": len(results_formatter.execution_history)
        }
    else:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")