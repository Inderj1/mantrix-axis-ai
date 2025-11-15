"""
API routes for pipeline management and monitoring.

Provides endpoints to:
- Trigger manual pipeline execution
- Monitor pipeline status
- View pipeline history
- Get pipeline run details
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from src.pipeline.orchestrator import PipelineOrchestrator, PipelineRun

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# Global orchestrator instance
_orchestrator: Optional[PipelineOrchestrator] = None


def get_orchestrator() -> PipelineOrchestrator:
    """Get or create the global pipeline orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator()
    return _orchestrator


# Request/Response Models
class PipelineExecuteRequest(BaseModel):
    """Request to execute the pipeline."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "incremental": True,
                "table_names": None
            }
        }
    )

    incremental: bool = Field(
        True,
        description="If True, only process changed tables. If False, full refresh."
    )
    table_names: Optional[List[str]] = Field(
        None,
        description="Optional list of specific tables to process. If None, process all tables."
    )


class PipelineRunResponse(BaseModel):
    """Response containing pipeline run details."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "pipeline_20250115_143022",
                "status": "completed",
                "start_time": "2025-01-15T14:30:22",
                "end_time": "2025-01-15T14:35:45",
                "duration_seconds": 323.5,
                "tables_processed": 14,
                "changes_detected": 3,
                "errors": [],
                "phase_stats": {
                    "schema_extraction": {"duration": 45.2, "tables": 14},
                    "rdf_building": {"duration": 12.3, "triples": 1520},
                    "vector_building": {"duration": 266.0, "vectors": 14}
                }
            }
        }
    )

    run_id: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[float]
    tables_processed: int
    changes_detected: int
    errors: List[str]
    phase_stats: Dict[str, Any]


class PipelineStatusResponse(BaseModel):
    """Response containing current pipeline status."""
    is_running: bool
    current_run_id: Optional[str]
    current_phase: Optional[str]
    last_run: Optional[PipelineRunResponse]
    next_scheduled_run: Optional[str]


# Endpoints
@router.post("/execute", response_model=PipelineRunResponse)
async def execute_pipeline(
    request: PipelineExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    Manually trigger pipeline execution.

    This endpoint triggers the build-time pipeline that:
    1. Extracts schemas from BigQuery
    2. Builds RDF triples for semantic relationships
    3. Generates enriched vector embeddings

    The pipeline can run incrementally (only changed tables) or as a full refresh.
    """
    try:
        orchestrator = get_orchestrator()

        logger.info(
            "Manual pipeline execution triggered",
            incremental=request.incremental,
            table_names=request.table_names
        )

        # Execute pipeline
        pipeline_run = orchestrator.execute_pipeline(
            incremental=request.incremental,
            tables=request.table_names
        )

        if pipeline_run is None:
            raise HTTPException(
                status_code=500,
                detail="Pipeline execution failed to start"
            )

        # Convert to response model
        response = _pipeline_run_to_response(pipeline_run)

        logger.info(
            "Pipeline execution completed",
            run_id=pipeline_run.run_id,
            status=pipeline_run.status,
            duration=pipeline_run.duration_seconds
        )

        return response

    except Exception as e:
        logger.error("Pipeline execution failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current pipeline status.

    Returns information about:
    - Whether a pipeline is currently running
    - Current run details if running
    - Last completed run details
    - Next scheduled run time
    """
    try:
        orchestrator = get_orchestrator()

        # Get last run from history
        history = orchestrator.get_run_history(limit=1)
        last_run = None
        if history:
            last_run = _pipeline_run_to_response(history[0])

        # Get next scheduled run time from scheduler
        next_scheduled = None
        try:
            from src.core.pipeline_scheduler import get_pipeline_scheduler
            scheduler = get_pipeline_scheduler()
            next_run_time = scheduler.get_next_run_time()
            next_scheduled = next_run_time.isoformat()
        except Exception as e:
            logger.warning("Could not get next scheduled run time", error=str(e))

        # For now, we don't track "currently running" state
        # This could be enhanced with a state manager
        response = PipelineStatusResponse(
            is_running=False,
            current_run_id=None,
            current_phase=None,
            last_run=last_run,
            next_scheduled_run=next_scheduled
        )

        return response

    except Exception as e:
        logger.error("Failed to get pipeline status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline status: {str(e)}"
        )


@router.get("/history", response_model=List[PipelineRunResponse])
async def get_pipeline_history(limit: int = 10):
    """
    Get pipeline execution history.

    Args:
        limit: Maximum number of runs to return (default: 10)

    Returns:
        List of recent pipeline runs, most recent first
    """
    try:
        orchestrator = get_orchestrator()

        history = orchestrator.get_run_history(limit=limit)

        response = [_pipeline_run_to_response(run) for run in history]

        return response

    except Exception as e:
        logger.error("Failed to get pipeline history", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline history: {str(e)}"
        )


@router.get("/run/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: str):
    """
    Get details for a specific pipeline run.

    Args:
        run_id: Pipeline run ID (e.g., "pipeline_20250115_143022")

    Returns:
        Detailed information about the pipeline run
    """
    try:
        orchestrator = get_orchestrator()

        # Search history for the run
        history = orchestrator.get_run_history(limit=100)
        pipeline_run = next((run for run in history if run.run_id == run_id), None)

        if pipeline_run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pipeline run not found: {run_id}"
            )

        response = _pipeline_run_to_response(pipeline_run)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get pipeline run", run_id=run_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline run: {str(e)}"
        )


@router.get("/summary")
async def get_pipeline_summary():
    """
    Get a summary of the latest pipeline execution.

    Returns a human-readable text summary of the most recent pipeline run,
    including statistics and any errors.
    """
    try:
        orchestrator = get_orchestrator()

        history = orchestrator.get_run_history(limit=1)
        if not history:
            return {
                "summary": "No pipeline runs found",
                "has_run": False
            }

        latest_run = history[0]
        summary = orchestrator.get_summary(latest_run)

        return {
            "summary": summary,
            "has_run": True,
            "run_id": latest_run.run_id,
            "status": latest_run.status
        }

    except Exception as e:
        logger.error("Failed to get pipeline summary", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline summary: {str(e)}"
        )


# Helper Functions
def _pipeline_run_to_response(pipeline_run: PipelineRun) -> PipelineRunResponse:
    """Convert PipelineRun to PipelineRunResponse."""
    # Get status value (handle both enum and string)
    status_value = pipeline_run.status.value if hasattr(pipeline_run.status, 'value') else pipeline_run.status

    # Build phase_stats from individual results
    phase_stats = {}
    if pipeline_run.schema_extraction_result:
        phase_stats['schema_extraction'] = pipeline_run.schema_extraction_result
    if pipeline_run.rdf_build_result:
        phase_stats['rdf_building'] = pipeline_run.rdf_build_result
    if pipeline_run.vector_build_result:
        phase_stats['vector_building'] = pipeline_run.vector_build_result

    return PipelineRunResponse(
        run_id=pipeline_run.run_id,
        status=status_value,
        start_time=pipeline_run.start_time if pipeline_run.start_time else "",
        end_time=pipeline_run.end_time if pipeline_run.end_time else None,
        duration_seconds=pipeline_run.duration_seconds,
        tables_processed=pipeline_run.tables_processed,
        changes_detected=pipeline_run.changes_detected,
        errors=pipeline_run.errors,
        phase_stats=phase_stats
    )
