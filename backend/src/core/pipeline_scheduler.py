"""
Pipeline Scheduler: Daily execution of build-time pipeline

Runs the schema extraction, RDF building, and vector indexing pipeline
on a daily schedule to keep the knowledge graph and embeddings up to date.
"""
import asyncio
import structlog
from datetime import datetime, time, timedelta
from typing import Optional

logger = structlog.get_logger()


class PipelineScheduler:
    """
    Background scheduler for daily pipeline execution.
    Runs the build-time pipeline at a specified time each day.
    """

    def __init__(
        self,
        execution_time: time = time(2, 0),  # Default: 2:00 AM
        check_interval: int = 300  # Check every 5 minutes
    ):
        """
        Args:
            execution_time: Time of day to run the pipeline (default: 2:00 AM)
            check_interval: How often to check if it's time to run (in seconds)
        """
        self.execution_time = execution_time
        self.check_interval = check_interval
        self.running = False
        self.last_run_date: Optional[datetime] = None
        self._orchestrator = None

    def _get_orchestrator(self):
        """Lazy load orchestrator to avoid initialization issues."""
        if self._orchestrator is None:
            from src.pipeline.orchestrator import PipelineOrchestrator
            self._orchestrator = PipelineOrchestrator()
        return self._orchestrator

    async def start(self):
        """Start the scheduler."""
        logger.info(
            "Starting Pipeline Scheduler",
            execution_time=self.execution_time.strftime("%H:%M")
        )
        self.running = True

        while self.running:
            try:
                await self._check_and_execute()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error("Error in pipeline scheduler loop", error=str(e))
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping Pipeline Scheduler")
        self.running = False

    async def _check_and_execute(self):
        """Check if it's time to run the pipeline and execute if needed."""
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()

        # Check if we've already run today
        if self.last_run_date == current_date:
            return

        # Check if it's past the execution time
        if current_time >= self.execution_time:
            logger.info(
                "Daily pipeline execution starting",
                scheduled_time=self.execution_time.strftime("%H:%M"),
                actual_time=current_time.strftime("%H:%M:%S")
            )

            try:
                await self._execute_pipeline()
                self.last_run_date = current_date
                logger.info(
                    "Daily pipeline execution completed",
                    execution_date=current_date.isoformat()
                )
            except Exception as e:
                logger.error(
                    "Daily pipeline execution failed",
                    error=str(e),
                    execution_date=current_date.isoformat()
                )
                # Still mark as run to avoid repeated failures
                self.last_run_date = current_date

    async def _execute_pipeline(self):
        """Execute the pipeline in a separate thread to avoid blocking."""
        # Run in executor since pipeline is synchronous
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_pipeline_sync)

    def _run_pipeline_sync(self):
        """Synchronous pipeline execution."""
        try:
            orchestrator = self._get_orchestrator()

            # Execute with incremental mode (only process changed tables)
            pipeline_run = orchestrator.execute_pipeline(incremental=True)

            if pipeline_run:
                logger.info(
                    "Pipeline completed successfully",
                    run_id=pipeline_run.run_id,
                    status=pipeline_run.status,
                    tables_processed=pipeline_run.tables_processed,
                    duration_seconds=pipeline_run.duration_seconds
                )
            else:
                logger.warning("Pipeline returned None - may have been skipped")

        except Exception as e:
            logger.error("Pipeline execution failed", error=str(e))
            raise

    def get_next_run_time(self) -> datetime:
        """Get the next scheduled run time."""
        now = datetime.now()
        next_run = datetime.combine(now.date(), self.execution_time)

        # If we've already passed today's execution time, schedule for tomorrow
        if now.time() >= self.execution_time or now.date() == self.last_run_date:
            next_run += timedelta(days=1)

        return next_run


# Global scheduler instance
_scheduler: Optional[PipelineScheduler] = None


def get_pipeline_scheduler(
    execution_time: time = time(2, 0),
    check_interval: int = 300
) -> PipelineScheduler:
    """
    Get or create the global pipeline scheduler instance.

    Args:
        execution_time: Time of day to run the pipeline (default: 2:00 AM)
        check_interval: How often to check if it's time to run (in seconds, default: 5 minutes)

    Returns:
        PipelineScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler(
            execution_time=execution_time,
            check_interval=check_interval
        )
    return _scheduler
