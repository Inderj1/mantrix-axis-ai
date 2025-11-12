"""
Enterprise Pulse: Monitor Service
Leverages existing NLP-to-SQL framework for user-configurable monitoring
"""
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import structlog
from ..db.postgresql_client import PostgreSQLClient
from ..db.bigquery import BigQueryClient
from .sql_generator import SQLGenerator
from .llm_client import LLMClient

logger = structlog.get_logger()


def decimal_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class PulseMonitorService:
    """
    Service for creating and managing monitoring queries
    Uses existing NLP-to-SQL framework
    """

    def __init__(self):
        self.pg_client = PostgreSQLClient(database="customer_analytics")
        self.bq_client = BigQueryClient()
        self.sql_generator = SQLGenerator()
        self.llm_client = LLMClient()

    async def create_monitor_from_nl(
        self,
        user_id: str,
        natural_language: str,
        name: Optional[str] = None,
        user_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a monitor from natural language description
        Uses existing NLP-to-SQL framework

        Args:
            user_id: User identifier
            natural_language: Natural language query (e.g., "Alert me if revenue drops >10%")
            name: Optional monitor name
            user_context: Optional context for query generation

        Returns:
            Dict with generated SQL, preview data, and suggestions
        """
        logger.info(f"Creating monitor from NL: {natural_language}")

        try:
            # Use existing NLP-to-SQL framework (with Weaviate vector search)
            generation_result = self.sql_generator.generate_sql(
                query=natural_language,
                use_vector_search=True,  # Use Weaviate for table context
                max_tables=5,
                auto_optimize=True
            )

            sql_query = generation_result.get('sql', '')
            # Determine data source - BigQuery if query uses backticks
            if '`' in sql_query:
                data_source = 'bigquery'
            else:
                data_source = 'postgresql'

            # Execute query to get preview
            preview_data = await self._execute_query(sql_query, data_source)

            # Analyze results and suggest alert conditions
            suggestions = self._analyze_and_suggest_conditions(
                preview_data,
                natural_language
            )

            # Generate monitor name if not provided
            if not name:
                name = await self._generate_monitor_name(natural_language)

            return {
                'name': name,
                'natural_language_query': natural_language,
                'sql_query': sql_query,
                'data_source': data_source,
                'preview_data': preview_data[:10],  # First 10 rows
                'suggested_conditions': suggestions,
                'suggested_frequency': self._suggest_frequency(natural_language),
                'suggested_severity': self._suggest_severity(natural_language)
            }

        except Exception as e:
            logger.error(f"Error creating monitor from NL: {e}")
            raise

    async def save_monitor(self, monitor_config: Dict[str, Any]) -> str:
        """
        Save a monitor configuration to database

        Returns:
            Monitor ID (UUID)
        """
        monitor_id = str(uuid.uuid4())

        # Calculate next run based on frequency
        next_run = self._calculate_next_run(
            monitor_config.get('frequency', 'daily')
        )

        query = """
        INSERT INTO pulse_monitors (
            id, user_id, name, description,
            natural_language_query, sql_query, data_source,
            alert_condition, severity, frequency,
            enabled, next_run, query_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """

        params = (
            monitor_id,
            monitor_config['user_id'],
            monitor_config['name'],
            monitor_config.get('description', ''),
            monitor_config['natural_language_query'],
            monitor_config['sql_query'],
            monitor_config['data_source'],
            monitor_config.get('alert_condition'),
            monitor_config.get('severity', 'medium'),
            monitor_config.get('frequency', 'daily'),
            monitor_config.get('enabled', True),
            next_run,
            1  # Initial version
        )

        result = self.pg_client.execute_query(query, params)

        if not result:
            raise Exception("Failed to insert monitor into database")

        logger.info(f"Monitor created: {monitor_id}")

        # Save initial query version to history (only if monitor was created successfully)
        try:
            self._save_query_version(
                monitor_id,
                1,
                monitor_config['sql_query'],
                "Initial creation"
            )
        except Exception as e:
            logger.warning(f"Failed to save query history: {e}")
            # Don't fail the whole operation if history fails

        return monitor_id

    async def execute_monitor(self, monitor_id: str) -> Dict[str, Any]:
        """
        Execute a monitor and check alert conditions

        Returns:
            Execution results including any triggered alerts
        """
        # Get monitor configuration
        monitor = self._get_monitor(monitor_id)
        if not monitor:
            raise ValueError(f"Monitor {monitor_id} not found")

        if not monitor['enabled']:
            logger.info(f"Monitor {monitor_id} is disabled, skipping")
            return {'status': 'skipped', 'reason': 'disabled'}

        started_at = datetime.utcnow()
        alert_triggered = False
        alert_id = None

        try:
            # Execute the SQL query
            results = await self._execute_query(
                monitor['sql_query'],
                monitor['data_source']
            )

            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Check alert conditions
            alert_data = self._evaluate_alert_conditions(
                results,
                monitor['alert_condition']
            )

            if alert_data:
                alert_triggered = True
                alert_id = await self._create_alert(monitor, alert_data)
                logger.info(f"Alert triggered for monitor {monitor_id}: {alert_id}")

            # Update monitor's last run and results
            self._update_monitor_execution(
                monitor_id,
                results,
                self._calculate_next_run(monitor['frequency'])
            )

            # Log execution
            self._log_execution(
                monitor_id,
                started_at,
                completed_at,
                duration_ms,
                'success',
                len(results),
                alert_triggered,
                alert_id
            )

            return {
                'status': 'success',
                'row_count': len(results),
                'alert_triggered': alert_triggered,
                'alert_id': alert_id,
                'duration_ms': duration_ms
            }

        except Exception as e:
            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            logger.error(f"Error executing monitor {monitor_id}: {e}")

            # Log failed execution
            self._log_execution(
                monitor_id,
                started_at,
                completed_at,
                duration_ms,
                'error',
                0,
                False,
                None,
                str(e)
            )

            return {
                'status': 'error',
                'error': str(e),
                'duration_ms': duration_ms
            }

    async def refine_query_with_feedback(
        self,
        monitor_id: str,
        feedback: str
    ) -> Dict[str, Any]:
        """
        Refine monitor query based on user feedback
        Uses LLM conversation history to improve the query

        Args:
            monitor_id: Monitor ID
            feedback: User feedback (e.g., "too many false positives", "add region breakdown")

        Returns:
            Updated monitor configuration with new query
        """
        monitor = self._get_monitor(monitor_id)
        if not monitor:
            raise ValueError(f"Monitor {monitor_id} not found")

        # Build conversation history
        conversation = [
            {
                "role": "user",
                "content": monitor['natural_language_query']
            },
            {
                "role": "assistant",
                "content": f"I generated this SQL query:\n\n```sql\n{monitor['sql_query']}\n```"
            },
            {
                "role": "user",
                "content": f"Feedback: {feedback}. Please improve the query."
            }
        ]

        # Use LLM to generate improved query
        improved_result = await self.sql_generator.generate_sql_from_conversation(
            conversation,
            context={'database': monitor['data_source']}
        )

        improved_sql = improved_result.get('sql', '')

        # Preview the improved query
        preview_data = await self._execute_query(
            improved_sql,
            monitor['data_source']
        )

        # Increment version and save to history
        new_version = monitor['query_version'] + 1
        self._save_query_version(
            monitor_id,
            new_version,
            improved_sql,
            f"User feedback: {feedback}"
        )

        # Update monitor with new query
        self._update_monitor_query(monitor_id, improved_sql, new_version)

        return {
            'monitor_id': monitor_id,
            'previous_version': monitor['query_version'],
            'new_version': new_version,
            'improved_sql': improved_sql,
            'preview_data': preview_data[:10],
            'change_reason': feedback
        }

    async def get_user_monitors(
        self,
        user_id: str,
        include_disabled: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all monitors for a user"""
        query = """
        SELECT
            id, name, description, natural_language_query,
            sql_query, data_source, alert_condition,
            severity, frequency, enabled,
            last_run, next_run, query_version,
            false_positives, true_positives, user_rating,
            created_at, updated_at
        FROM pulse_monitors
        WHERE user_id = %s
        """

        if not include_disabled:
            query += " AND enabled = true"

        query += " ORDER BY created_at DESC"

        monitors = self.pg_client.execute_query(query, (user_id,))
        return monitors

    async def get_recent_alerts(
        self,
        user_id: str,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent alerts for user's monitors"""
        query = """
        SELECT
            a.id, a.monitor_id, a.severity, a.title,
            a.message, a.data, a.status,
            a.acknowledged_at, a.resolved_at,
            a.user_feedback, a.triggered_at,
            m.name as monitor_name
        FROM pulse_alerts a
        JOIN pulse_monitors m ON a.monitor_id = m.id
        WHERE m.user_id = %s
        """

        params = [user_id]

        if status:
            query += " AND a.status = %s"
            params.append(status)

        query += " ORDER BY a.triggered_at DESC LIMIT %s"
        params.append(limit)

        alerts = self.pg_client.execute_query(query, tuple(params))
        return alerts

    def _calculate_next_run(self, frequency: str) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.utcnow()

        if frequency == 'real-time':
            return now + timedelta(minutes=1)
        elif frequency == 'hourly':
            return now + timedelta(hours=1)
        elif frequency == 'daily':
            # Run at 8 AM UTC tomorrow
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
        elif frequency == 'weekly':
            # Run next Monday at 8 AM UTC
            days_ahead = 7 - now.weekday()
            next_monday = now + timedelta(days=days_ahead)
            return next_monday.replace(hour=8, minute=0, second=0, microsecond=0)
        elif frequency == 'monthly':
            # Run on 1st of next month at 8 AM UTC
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1)
            else:
                next_month = now.replace(month=now.month + 1, day=1)
            return next_month.replace(hour=8, minute=0, second=0, microsecond=0)
        else:
            return now + timedelta(days=1)

    async def _execute_query(
        self,
        sql: str,
        data_source: str
    ) -> List[Dict[str, Any]]:
        """Execute query against specified data source"""
        if data_source == 'bigquery':
            return self.bq_client.execute_query(sql)
        else:  # postgresql
            return self.pg_client.execute_query(sql)

    def _evaluate_alert_conditions(
        self,
        results: List[Dict[str, Any]],
        alert_condition: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate if alert condition is met

        Returns:
            Alert data if condition is met, None otherwise
        """
        if not alert_condition or not results:
            return None

        # Simple evaluation: check if any row matches condition
        # For more complex conditions, we could use safe eval or parse the condition

        # Example conditions:
        # "status == 'ALERT'"
        # "pct_change < -10"
        # "count > 100"

        for row in results:
            if self._check_condition(row, alert_condition):
                return {
                    'triggered_row': row,
                    'all_results': results,
                    'condition': alert_condition
                }

        return None

    def _check_condition(self, row: Dict[str, Any], condition: str) -> bool:
        """
        Safely check if a row meets the condition
        Simple implementation - can be enhanced
        """
        try:
            # Create a safe context with only the row data
            context = {k: v for k, v in row.items()}

            # Use eval in a restricted context (basic implementation)
            # For production, use a proper expression parser
            return eval(condition, {"__builtins__": {}}, context)
        except:
            return False

    async def _create_alert(
        self,
        monitor: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> str:
        """Create an alert in the database"""
        alert_id = str(uuid.uuid4())

        # Generate alert title and message
        title = f"Alert: {monitor['name']}"
        message = self._generate_alert_message(monitor, alert_data)

        query = """
        INSERT INTO pulse_alerts (
            id, monitor_id, severity, title, message, data, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            alert_id,
            monitor['id'],
            monitor['severity'],
            title,
            message,
            json.dumps(alert_data, default=decimal_serializer),
            'active'
        )

        self.pg_client.execute_query(query, params)
        return alert_id

    def _generate_alert_message(
        self,
        monitor: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> str:
        """Generate human-readable alert message"""
        triggered_row = alert_data.get('triggered_row', {})

        # Simple message generation - can be enhanced with LLM
        parts = []
        for key, value in triggered_row.items():
            if isinstance(value, (int, float)):
                parts.append(f"{key}: {value:,.2f}")
            else:
                parts.append(f"{key}: {value}")

        return f"Condition met: {alert_data['condition']}\n\n" + "\n".join(parts)

    def _analyze_and_suggest_conditions(
        self,
        preview_data: List[Dict[str, Any]],
        natural_language: str
    ) -> Dict[str, Any]:
        """Analyze preview data and suggest alert conditions"""
        if not preview_data:
            return {}

        suggestions = {
            'conditions': [],
            'thresholds': {}
        }

        # Look for common patterns in the query
        nl_lower = natural_language.lower()

        # Check for percentage/numeric columns that might indicate alerts
        first_row = preview_data[0]
        for key, value in first_row.items():
            if isinstance(value, (int, float)):
                if 'pct' in key.lower() or 'percent' in key.lower() or 'change' in key.lower():
                    suggestions['conditions'].append(f"{key} < -10")
                    suggestions['conditions'].append(f"{key} > 10")
                    suggestions['thresholds'][key] = value

        # Check for status columns
        if 'status' in first_row:
            suggestions['conditions'].append("status == 'ALERT'")

        return suggestions

    def _suggest_frequency(self, natural_language: str) -> str:
        """Suggest monitoring frequency based on query"""
        nl_lower = natural_language.lower()

        if any(word in nl_lower for word in ['real-time', 'immediate', 'instantly']):
            return 'real-time'
        elif any(word in nl_lower for word in ['hourly', 'every hour']):
            return 'hourly'
        elif any(word in nl_lower for word in ['weekly', 'every week']):
            return 'weekly'
        elif any(word in nl_lower for word in ['monthly', 'every month']):
            return 'monthly'
        else:
            return 'daily'

    def _suggest_severity(self, natural_language: str) -> str:
        """Suggest alert severity based on query"""
        nl_lower = natural_language.lower()

        if any(word in nl_lower for word in ['critical', 'urgent', 'emergency']):
            return 'high'
        elif any(word in nl_lower for word in ['warning', 'attention', 'watch']):
            return 'medium'
        else:
            return 'medium'

    async def _generate_monitor_name(self, natural_language: str) -> str:
        """Generate a concise monitor name from natural language"""
        # Simple implementation - can use LLM for better names
        words = natural_language.split()[:5]
        return ' '.join(words).capitalize()

    def _get_monitor(self, monitor_id: str) -> Optional[Dict[str, Any]]:
        """Get monitor configuration by ID"""
        query = """
        SELECT * FROM pulse_monitors WHERE id = %s
        """
        result = self.pg_client.execute_query(query, (monitor_id,))
        return result[0] if result else None

    def _save_query_version(
        self,
        monitor_id: str,
        version: int,
        sql_query: str,
        change_reason: str
    ):
        """Save query version to history"""
        query = """
        INSERT INTO pulse_query_history (
            monitor_id, version, sql_query, change_reason
        ) VALUES (%s, %s, %s, %s)
        """
        self.pg_client.execute_query(
            query,
            (monitor_id, version, sql_query, change_reason)
        )

    def _update_monitor_query(
        self,
        monitor_id: str,
        sql_query: str,
        version: int
    ):
        """Update monitor's SQL query and version"""
        query = """
        UPDATE pulse_monitors
        SET sql_query = %s, query_version = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        self.pg_client.execute_query(query, (sql_query, version, monitor_id))

    def _update_monitor_execution(
        self,
        monitor_id: str,
        results: List[Dict[str, Any]],
        next_run: datetime
    ):
        """Update monitor after execution"""
        query = """
        UPDATE pulse_monitors
        SET last_run = CURRENT_TIMESTAMP,
            next_run = %s,
            last_result = %s
        WHERE id = %s
        """
        self.pg_client.execute_query(
            query,
            (next_run, json.dumps(results[:5], default=decimal_serializer), monitor_id)  # Store first 5 results
        )

    def _log_execution(
        self,
        monitor_id: str,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int,
        status: str,
        row_count: int,
        alert_triggered: bool,
        alert_id: Optional[str],
        error_message: Optional[str] = None
    ):
        """Log monitor execution"""
        query = """
        INSERT INTO pulse_execution_log (
            monitor_id, started_at, completed_at, duration_ms,
            status, row_count, alert_triggered, alert_id, error_message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.pg_client.execute_query(
            query,
            (monitor_id, started_at, completed_at, duration_ms,
             status, row_count, alert_triggered, alert_id, error_message)
        )
