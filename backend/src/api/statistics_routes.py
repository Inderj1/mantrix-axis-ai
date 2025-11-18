"""
Statistics Extraction API Routes

Manual control and monitoring of column statistics extraction pipeline.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import structlog

from src.pipeline.orchestrator import PipelineOrchestrator
from src.api.middleware import require_admin
from src.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


class StatisticsExtractionRequest(BaseModel):
    """Request model for manual statistics extraction."""
    tables: Optional[List[str]] = Field(
        None,
        description="Specific tables to extract statistics for (None = all with stale stats)"
    )
    force_refresh: bool = Field(
        False,
        description="Force extraction even for fresh statistics"
    )


class StatisticsStatusResponse(BaseModel):
    """Response model for statistics status."""
    enabled: bool
    schedule: str
    max_age_days: int
    use_sampling: bool
    sample_percent: int
    sampling_threshold_gb: float
    critical_tables: Optional[List[str]]
    skip_tables: Optional[List[str]]


@router.post("/extract", dependencies=[Depends(require_admin)])
async def trigger_statistics_extraction(
    request: StatisticsExtractionRequest
) -> Dict[str, Any]:
    """
    Manually trigger column statistics extraction (ADMIN ONLY).

    This is an expensive operation that scans database tables to extract
    column-level optimization metadata (cardinality, selectivity, indexes).

    **Cost Warning**: This operation scans data and may incur significant
    costs on cloud databases (BigQuery, Snowflake, etc.)

    **Recommended Use**:
    - After adding new tables
    - When statistics are stale (>7 days)
    - During off-peak hours

    **Response**:
    - tables_processed: Number of tables processed
    - statistics_extracted: Number of column statistics extracted
    - duration_seconds: Execution time
    - errors: List of errors encountered
    """
    if not settings.stats_extraction_enabled:
        raise HTTPException(
            status_code=400,
            detail="Statistics extraction is disabled in configuration"
        )

    logger.info(
        f"Manual statistics extraction triggered: "
        f"tables={request.tables or 'all'}, force_refresh={request.force_refresh}"
    )

    try:
        orchestrator = PipelineOrchestrator()

        result = orchestrator.execute_statistics_pipeline(
            tables=request.tables,
            force_refresh=request.force_refresh
        )

        return {
            "status": "completed" if len(result['errors']) == 0 else "completed_with_errors",
            "message": "Statistics extraction completed",
            "run_id": result['run_id'],
            "tables_processed": result['tables_processed'],
            "tables_skipped": result['tables_skipped'],
            "statistics_extracted": result['statistics_extracted'],
            "duration_seconds": result['duration_seconds'],
            "error_count": len(result['errors']),
            "errors": result['errors'][:10]  # Return first 10 errors
        }

    except Exception as e:
        logger.error(f"Statistics extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Statistics extraction failed: {str(e)}"
        )


@router.get("/status")
async def get_statistics_status() -> StatisticsStatusResponse:
    """
    Get current statistics extraction configuration and status.

    Returns:
    - enabled: Whether statistics extraction is enabled
    - schedule: Extraction schedule (daily, weekly, monthly, manual)
    - max_age_days: Maximum age before re-extraction
    - use_sampling: Whether sampling is enabled for large tables
    - sample_percent: Sample percentage for large tables
    - sampling_threshold_gb: Table size threshold for sampling
    - critical_tables: List of critical tables (if configured)
    - skip_tables: List of tables to skip (if configured)
    """
    critical_tables = None
    if settings.stats_critical_tables:
        critical_tables = [t.strip() for t in settings.stats_critical_tables.split(',')]

    skip_tables = None
    if settings.stats_skip_tables:
        skip_tables = [t.strip() for t in settings.stats_skip_tables.split(',')]

    return StatisticsStatusResponse(
        enabled=settings.stats_extraction_enabled,
        schedule=settings.stats_extraction_schedule,
        max_age_days=settings.stats_max_age_days,
        use_sampling=settings.stats_use_sampling,
        sample_percent=settings.stats_sample_percent,
        sampling_threshold_gb=settings.stats_sampling_threshold_gb,
        critical_tables=critical_tables,
        skip_tables=skip_tables
    )


@router.get("/table/{table_name}/age")
async def get_table_statistics_age(table_name: str) -> Dict[str, Any]:
    """
    Get the age of statistics for a specific table.

    Returns:
    - table_name: Name of the table
    - statistics_age_days: Age of statistics in days (None if no stats)
    - needs_update: Whether statistics need updating
    - max_age_days: Configured maximum age
    """
    try:
        orchestrator = PipelineOrchestrator()
        rdf_builder = orchestrator.rdf_builder

        age_days = rdf_builder.get_statistics_age_days(table_name)
        needs_update = rdf_builder.should_update_statistics(table_name)

        return {
            "table_name": table_name,
            "statistics_age_days": age_days,
            "needs_update": needs_update,
            "max_age_days": settings.stats_max_age_days,
            "has_statistics": age_days is not None
        }

    except Exception as e:
        logger.error(f"Failed to get statistics age for {table_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics age: {str(e)}"
        )


@router.get("/tables/stale")
async def get_stale_tables() -> Dict[str, Any]:
    """
    Get list of tables with stale statistics that need updating.

    Returns:
    - stale_tables: List of table names with statistics older than max_age_days
    - total_tables: Total number of tables
    - max_age_days: Configured maximum age
    """
    try:
        orchestrator = PipelineOrchestrator()

        # Get all table snapshots
        all_snapshots = orchestrator.schema_extractor.extract_all_schemas(force_refresh=False)

        stale_tables = []

        for snapshot in all_snapshots:
            if orchestrator.rdf_builder.should_update_statistics(snapshot.table_name):
                age_days = orchestrator.rdf_builder.get_statistics_age_days(snapshot.table_name)
                stale_tables.append({
                    "table_name": snapshot.table_name,
                    "age_days": age_days,
                    "database_type": snapshot.database_type
                })

        return {
            "stale_tables": stale_tables,
            "stale_count": len(stale_tables),
            "total_tables": len(all_snapshots),
            "max_age_days": settings.stats_max_age_days
        }

    except Exception as e:
        logger.error(f"Failed to get stale tables: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stale tables: {str(e)}"
        )
