"""
Enterprise Pulse: Background Scheduler
Executes monitors on their configured schedules
"""
import asyncio
import structlog
from datetime import datetime
from typing import List, Dict, Any
from ..db.postgresql_client import PostgreSQLClient
from .pulse_monitor_service import PulseMonitorService

logger = structlog.get_logger()


class PulseScheduler:
    """
    Background scheduler for executing pulse monitors
    Runs continuously and executes monitors based on their next_run time
    """

    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: How often to check for monitors to execute (in seconds)
        """
        self.check_interval = check_interval
        try:
            self.pg_client = PostgreSQLClient(database="customer_analytics")
            logger.info("PostgreSQL client initialized for Pulse Scheduler")
        except Exception as e:
            logger.warning(f"PostgreSQL not available for Pulse Scheduler: {e}")
            self.pg_client = None
        self.pulse_service = PulseMonitorService()
        self.running = False
        self._pg_unavailable_logged = False  # Track if we've logged the unavailability warning

    async def start(self):
        """Start the scheduler"""
        logger.info("Starting Pulse Scheduler...")
        self.running = True

        while self.running:
            try:
                await self._check_and_execute_monitors()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping Pulse Scheduler...")
        self.running = False

    async def _check_and_execute_monitors(self):
        """Check for monitors that need to run and execute them"""
        # Get monitors that are due to run
        monitors_to_run = self._get_monitors_to_run()

        if not monitors_to_run:
            return

        logger.info(f"Found {len(monitors_to_run)} monitors to execute")

        # Execute monitors concurrently
        tasks = [
            self._execute_monitor_safe(monitor['id'])
            for monitor in monitors_to_run
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    def _get_monitors_to_run(self) -> List[Dict[str, Any]]:
        """Get all enabled monitors where next_run <= now"""
        # Check if PostgreSQL is available
        if not self.pg_client:
            if not self._pg_unavailable_logged:
                logger.info("PostgreSQL not available - Pulse monitoring disabled")
                self._pg_unavailable_logged = True
            return []

        try:
            query = """
            SELECT
                id, user_id, name, natural_language_query,
                sql_query, data_source, alert_condition,
                severity, frequency
            FROM pulse_monitors
            WHERE enabled = true
              AND (next_run IS NULL OR next_run <= CURRENT_TIMESTAMP)
            ORDER BY next_run ASC NULLS FIRST
            LIMIT 100
            """

            monitors = self.pg_client.execute_query(query)
            return monitors or []
        except Exception as e:
            if not self._pg_unavailable_logged:
                logger.warning(f"Failed to query pulse monitors: {e}")
                self._pg_unavailable_logged = True
            return []

    async def _execute_monitor_safe(self, monitor_id: str):
        """Execute a monitor with error handling"""
        try:
            logger.info(f"Executing monitor {monitor_id}")

            # Execute the monitor
            result = await self.pulse_service.execute_monitor(monitor_id)

            # Update next_run time
            self._update_next_run(monitor_id)

            logger.info(
                f"Monitor {monitor_id} executed successfully",
                status=result.get('status'),
                alert_triggered=result.get('alert_triggered', False)
            )

        except Exception as e:
            logger.error(f"Failed to execute monitor {monitor_id}: {e}")
            # Still update next_run to prevent getting stuck
            self._update_next_run(monitor_id)

    def _update_next_run(self, monitor_id: str):
        """Calculate and update next_run time for a monitor"""
        # Check if PostgreSQL is available
        if not self.pg_client:
            return

        try:
            # Get monitor frequency
            query = "SELECT frequency FROM pulse_monitors WHERE id = %s"
            result = self.pg_client.execute_query(query, (monitor_id,))

            if not result:
                return

            frequency = result[0]['frequency']

            # Calculate next run using the Python method
            next_run = self.pulse_service._calculate_next_run(frequency)

            update_query = """
            UPDATE pulse_monitors
            SET
                next_run = %s,
                last_run = CURRENT_TIMESTAMP
            WHERE id = %s
            """

            self.pg_client.execute_query(update_query, (next_run, monitor_id))
            logger.info(f"Updated next_run for monitor {monitor_id} with frequency {frequency}")
        except Exception as e:
            logger.debug(f"Could not update next_run for monitor {monitor_id}: {e}")


# Singleton instance
_scheduler_instance = None


def get_scheduler(check_interval: int = 60) -> PulseScheduler:
    """Get or create the scheduler singleton"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = PulseScheduler(check_interval=check_interval)
    return _scheduler_instance


async def start_scheduler():
    """Start the background scheduler"""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the background scheduler"""
    scheduler = get_scheduler()
    await scheduler.stop()
