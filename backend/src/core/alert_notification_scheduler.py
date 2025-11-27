"""
Alert Notification Scheduler - Sends notifications for triggered alerts.

This scheduler:
1. Checks pulse_alerts for undelivered alerts
2. Gets user notification preferences from MongoDB
3. Sends email notifications via EmailService
4. Logs delivery status to PostgreSQL
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
import structlog

from src.config import settings
from src.core.email_service import get_email_service, EmailResult
from src.db.postgresql_client import PostgreSQLClient
from src.db.mongodb_client import get_mongodb_client

logger = structlog.get_logger()


class AlertNotificationScheduler:
    """
    Background scheduler for sending alert notifications.

    Runs continuously and processes undelivered alerts based on user preferences.
    Supports:
    - Email notifications
    - Delivery logging
    - Retry logic for failed deliveries
    """

    def __init__(self):
        self.check_interval = settings.alert_check_interval_seconds
        self.batch_size = settings.alert_notification_batch_size
        self.max_retries = settings.alert_retry_max_attempts
        self.retry_delay = settings.alert_retry_delay_seconds

        self.email_service = get_email_service()
        self.running = False

        # Initialize PostgreSQL client
        try:
            self.pg_client = PostgreSQLClient(database="customer_analytics")
            logger.info("PostgreSQL client initialized for Alert Notification Scheduler")
        except Exception as e:
            logger.warning(f"PostgreSQL not available for Alert Notification Scheduler: {e}")
            self.pg_client = None

        self._pg_unavailable_logged = False
        self._email_unavailable_logged = False

    async def start(self):
        """Start the notification scheduler."""
        logger.info("Starting Alert Notification Scheduler...")
        self.running = True

        # Ensure delivery log table exists
        await self._ensure_delivery_table()

        while self.running:
            try:
                await self._check_and_notify()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in alert notification loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the notification scheduler."""
        logger.info("Stopping Alert Notification Scheduler...")
        self.running = False

    async def _ensure_delivery_table(self):
        """Ensure the alert_delivery_log table exists."""
        if not self.pg_client:
            return

        try:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS alert_delivery_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                alert_id UUID NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                delivery_method VARCHAR(50) NOT NULL,
                recipient VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                CONSTRAINT fk_alert FOREIGN KEY (alert_id)
                    REFERENCES pulse_alerts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_delivery_log_alert_id
                ON alert_delivery_log(alert_id);

            CREATE INDEX IF NOT EXISTS idx_delivery_log_user_id
                ON alert_delivery_log(user_id);

            CREATE INDEX IF NOT EXISTS idx_delivery_log_status
                ON alert_delivery_log(status);
            """
            self.pg_client.execute_query(create_table_sql, fetch=False)
            logger.info("Alert delivery log table ensured")
        except Exception as e:
            logger.warning(f"Could not create alert_delivery_log table: {e}")

    async def _check_and_notify(self):
        """Check for undelivered alerts and send notifications."""
        if not self.pg_client:
            if not self._pg_unavailable_logged:
                logger.info("PostgreSQL not available - Alert notifications disabled")
                self._pg_unavailable_logged = True
            return

        if not self.email_service.is_configured():
            if not self._email_unavailable_logged:
                logger.info("Email service not configured - Alert notifications disabled")
                self._email_unavailable_logged = True
            return

        # Get undelivered alerts
        alerts = self._get_undelivered_alerts()

        if not alerts:
            return

        logger.info(f"Processing {len(alerts)} undelivered alerts")

        # Process each alert
        for alert in alerts:
            try:
                await self._process_alert(alert)
            except Exception as e:
                logger.error(f"Failed to process alert {alert.get('id')}: {e}")

    def _get_undelivered_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts that haven't been delivered yet."""
        try:
            query = """
            SELECT
                pa.id as alert_id,
                pa.monitor_id,
                pa.user_id,
                pa.title,
                pa.message,
                pa.severity,
                pa.triggered_at,
                pa.alert_data,
                pm.name as monitor_name
            FROM pulse_alerts pa
            JOIN pulse_monitors pm ON pa.monitor_id = pm.id
            WHERE pa.acknowledged = false
              AND NOT EXISTS (
                  SELECT 1 FROM alert_delivery_log dl
                  WHERE dl.alert_id = pa.id
                    AND dl.status = 'sent'
              )
              AND (
                  NOT EXISTS (
                      SELECT 1 FROM alert_delivery_log dl
                      WHERE dl.alert_id = pa.id
                        AND dl.status = 'failed'
                        AND dl.retry_count >= %s
                  )
              )
            ORDER BY pa.triggered_at DESC
            LIMIT %s
            """

            alerts = self.pg_client.execute_query(
                query,
                params=(self.max_retries, self.batch_size)
            )
            return alerts or []
        except Exception as e:
            logger.error(f"Failed to get undelivered alerts: {e}")
            return []

    async def _process_alert(self, alert: Dict[str, Any]):
        """Process a single alert and send notifications."""
        alert_id = alert["alert_id"]
        user_id = alert["user_id"]

        # Get user notification preferences from MongoDB
        preferences = await self._get_user_preferences(user_id)

        if not preferences:
            logger.debug(f"No notification preferences for user {user_id}")
            return

        # Check if user wants email notifications
        if preferences.get("email_enabled", True):
            email = preferences.get("email")
            if email:
                await self._send_email_notification(alert, email, preferences)

    async def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user notification preferences from MongoDB."""
        try:
            mongodb = get_mongodb_client()
            prefs = await mongodb.notification_preferences.find_one({"user_id": user_id})

            if prefs:
                return {
                    "email": prefs.get("email"),
                    "email_enabled": prefs.get("email_enabled", True),
                    "severity_filter": prefs.get("severity_filter", ["info", "warning", "critical"]),
                    "quiet_hours": prefs.get("quiet_hours"),
                    "digest_mode": prefs.get("digest_mode", False)
                }

            # Return default preferences if none found (use user_id as email for demo)
            return {
                "email": None,  # Would need to fetch from user service
                "email_enabled": True,
                "severity_filter": ["warning", "critical"],
                "quiet_hours": None,
                "digest_mode": False
            }
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None

    async def _send_email_notification(
        self,
        alert: Dict[str, Any],
        email: str,
        preferences: Dict[str, Any]
    ):
        """Send email notification for an alert."""
        alert_id = alert["alert_id"]
        severity = alert.get("severity", "warning")

        # Check severity filter
        severity_filter = preferences.get("severity_filter", ["warning", "critical"])
        if severity not in severity_filter:
            logger.debug(f"Alert {alert_id} severity {severity} filtered out for user")
            return

        # Check quiet hours
        if self._is_quiet_hours(preferences.get("quiet_hours")):
            logger.debug(f"Quiet hours active, deferring alert {alert_id}")
            return

        # Prepare alert data for email
        alert_data = alert.get("alert_data", {})
        if isinstance(alert_data, str):
            import json
            try:
                alert_data = json.loads(alert_data)
            except:
                alert_data = {}

        # Build dashboard URL (if available)
        dashboard_url = None  # Would need to look up associated dashboard

        # Send email
        result = await self.email_service.send_alert_email(
            recipient=email,
            alert_name=alert.get("title", alert.get("monitor_name", "Alert")),
            alert_message=alert.get("message", "An alert was triggered."),
            alert_data=alert_data,
            dashboard_url=dashboard_url,
            severity=severity
        )

        # Log delivery
        self._log_delivery(
            alert_id=alert_id,
            user_id=alert["user_id"],
            method="email",
            recipient=email,
            result=result
        )

    def _is_quiet_hours(self, quiet_hours: Optional[Dict]) -> bool:
        """Check if current time is within quiet hours."""
        if not quiet_hours:
            return False

        try:
            now = datetime.now()
            start_hour = quiet_hours.get("start", 22)  # Default 10 PM
            end_hour = quiet_hours.get("end", 7)       # Default 7 AM

            current_hour = now.hour

            if start_hour > end_hour:
                # Quiet hours span midnight (e.g., 22:00 - 07:00)
                return current_hour >= start_hour or current_hour < end_hour
            else:
                # Quiet hours within same day
                return start_hour <= current_hour < end_hour
        except Exception:
            return False

    def _log_delivery(
        self,
        alert_id: str,
        user_id: str,
        method: str,
        recipient: str,
        result: EmailResult
    ):
        """Log delivery attempt to PostgreSQL."""
        try:
            # Get current retry count
            retry_query = """
            SELECT COALESCE(MAX(retry_count), 0) as retry_count
            FROM alert_delivery_log
            WHERE alert_id = %s AND user_id = %s AND delivery_method = %s
            """
            retry_result = self.pg_client.execute_query(
                retry_query,
                params=(alert_id, user_id, method)
            )
            retry_count = retry_result[0]["retry_count"] if retry_result else 0

            # Insert delivery log
            insert_query = """
            INSERT INTO alert_delivery_log (
                id, alert_id, user_id, delivery_method, recipient,
                status, sent_at, error_message, retry_count
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            self.pg_client.execute_query(
                insert_query,
                params=(
                    str(uuid.uuid4()),
                    alert_id,
                    user_id,
                    method,
                    recipient,
                    "sent" if result.success else "failed",
                    datetime.now(timezone.utc),
                    result.error,
                    retry_count + (0 if result.success else 1)
                ),
                fetch=False
            )

            logger.info(
                "alert_delivery_logged",
                alert_id=alert_id,
                method=method,
                status="sent" if result.success else "failed",
                retry_count=retry_count
            )
        except Exception as e:
            logger.error(f"Failed to log delivery: {e}")


# Singleton instance
_scheduler_instance: Optional[AlertNotificationScheduler] = None


def get_alert_notification_scheduler() -> AlertNotificationScheduler:
    """Get or create the singleton alert notification scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = AlertNotificationScheduler()
    return _scheduler_instance
