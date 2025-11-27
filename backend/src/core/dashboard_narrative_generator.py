"""
Dashboard Narrative Generator - AI-powered insights and summaries for dashboards.

Generates:
- Executive summaries for entire dashboards
- Widget-level insights
- Trend analysis narratives
- Anomaly explanations
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from anthropic import Anthropic
import structlog

from src.config import settings
from src.core.narrative_prompts import (
    EXECUTIVE_SUMMARY_PROMPT,
    WIDGET_INSIGHT_PROMPT,
    TREND_ANALYSIS_PROMPT,
    ANOMALY_NARRATIVE_PROMPT,
    COMPARATIVE_ANALYSIS_PROMPT,
    format_widget_data_for_prompt,
    get_time_period_description
)

logger = structlog.get_logger()


class DashboardNarrativeGenerator:
    """
    Generates AI-powered narratives for dashboards and widgets.

    Usage:
        generator = DashboardNarrativeGenerator()
        summary = await generator.generate_executive_summary(dashboard_data)
        insight = await generator.generate_widget_insight(widget_data)
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = 2048

    async def generate_executive_summary(
        self,
        dashboard_name: str,
        dashboard_description: str,
        widgets: List[Dict[str, Any]],
        time_period: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate an executive summary for a dashboard.

        Args:
            dashboard_name: Name of the dashboard
            dashboard_description: Description of what the dashboard shows
            widgets: List of widget data including type, title, and data
            time_period: Optional dict with 'start' and 'end' dates

        Returns:
            Dict with summary, key_metrics, highlights, concerns, recommendations
        """
        try:
            # Format widget data for the prompt
            widget_data_str = format_widget_data_for_prompt(widgets)

            # Get time period description
            period_desc = "current period"
            if time_period:
                period_desc = get_time_period_description(
                    time_period.get('start', ''),
                    time_period.get('end', '')
                )

            # Build the prompt
            prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                dashboard_name=dashboard_name,
                dashboard_description=dashboard_description or "Business analytics dashboard",
                time_period=period_desc,
                widget_data=widget_data_str
            )

            # Call LLM
            response = await self._generate_text(prompt)

            # Parse JSON response
            result = self._parse_json_response(response)

            # Add metadata
            result['generated_at'] = datetime.now(timezone.utc).isoformat()
            result['dashboard_name'] = dashboard_name

            logger.info(
                "executive_summary_generated",
                dashboard=dashboard_name,
                widget_count=len(widgets)
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return self._get_fallback_summary(dashboard_name)

    async def generate_widget_insight(
        self,
        widget_type: str,
        widget_title: str,
        metric_name: str,
        current_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an insight for a specific widget.

        Args:
            widget_type: Type of widget (bar, line, pie, kpi, etc.)
            widget_title: Title of the widget
            metric_name: Name of the primary metric
            current_data: Current data displayed in the widget
            historical_data: Optional historical data for comparison

        Returns:
            Dict with insight, trend, confidence, comparison
        """
        try:
            prompt = WIDGET_INSIGHT_PROMPT.format(
                widget_type=widget_type,
                widget_title=widget_title,
                metric_name=metric_name,
                current_data=json.dumps(current_data, indent=2, default=str),
                historical_data=json.dumps(historical_data, indent=2, default=str) if historical_data else "Not available"
            )

            response = await self._generate_text(prompt)
            result = self._parse_json_response(response)

            # Add metadata
            result['widget_title'] = widget_title
            result['generated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(
                "widget_insight_generated",
                widget=widget_title,
                metric=metric_name
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate widget insight: {e}")
            return {
                "insight": f"Data shows {metric_name} performance.",
                "trend": "stable",
                "confidence": "low",
                "comparison": None,
                "widget_title": widget_title
            }

    async def generate_trend_analysis(
        self,
        metric_name: str,
        data_points: List[Dict[str, Any]],
        time_period: str
    ) -> Dict[str, Any]:
        """
        Generate trend analysis for time series data.

        Args:
            metric_name: Name of the metric being analyzed
            data_points: List of {timestamp, value} data points
            time_period: Description of the time period

        Returns:
            Dict with trend analysis including direction, strength, narrative
        """
        try:
            prompt = TREND_ANALYSIS_PROMPT.format(
                metric_name=metric_name,
                time_period=time_period,
                data_points=json.dumps(data_points, indent=2, default=str)
            )

            response = await self._generate_text(prompt)
            result = self._parse_json_response(response)

            result['metric_name'] = metric_name
            result['generated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info("trend_analysis_generated", metric=metric_name)

            return result

        except Exception as e:
            logger.error(f"Failed to generate trend analysis: {e}")
            return {
                "overall_trend": "stable",
                "trend_strength": "weak",
                "key_changes": [],
                "seasonality": "none detected",
                "forecast_direction": "uncertain",
                "narrative": f"Unable to analyze trend for {metric_name}.",
                "metric_name": metric_name
            }

    async def generate_anomaly_narrative(
        self,
        widget_title: str,
        metric_name: str,
        expected_value: Any,
        actual_value: Any,
        deviation_percentage: float,
        timestamp: str,
        historical_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a narrative explanation for a detected anomaly.

        Args:
            widget_title: Title of the widget with the anomaly
            metric_name: Name of the affected metric
            expected_value: What was expected based on historical data
            actual_value: What was actually observed
            deviation_percentage: How far off the value is
            timestamp: When the anomaly occurred
            historical_context: Additional context about historical patterns

        Returns:
            Dict with severity, headline, explanation, impact, suggested_action
        """
        try:
            prompt = ANOMALY_NARRATIVE_PROMPT.format(
                widget_title=widget_title,
                metric_name=metric_name,
                expected_value=expected_value,
                actual_value=actual_value,
                deviation_percentage=deviation_percentage,
                timestamp=timestamp,
                historical_context=historical_context or "No historical context available"
            )

            response = await self._generate_text(prompt)
            result = self._parse_json_response(response)

            result['widget_title'] = widget_title
            result['metric_name'] = metric_name
            result['generated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(
                "anomaly_narrative_generated",
                widget=widget_title,
                deviation=deviation_percentage
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate anomaly narrative: {e}")
            severity = "critical" if abs(deviation_percentage) > 50 else "warning"
            return {
                "severity": severity,
                "headline": f"Unusual {metric_name} detected",
                "explanation": f"The value deviated {deviation_percentage:.1f}% from expected.",
                "impact": "Requires investigation",
                "suggested_action": "Review recent changes and data sources",
                "widget_title": widget_title
            }

    async def generate_comparative_analysis(
        self,
        comparison_type: str,
        categories: List[str],
        comparison_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comparative analysis between categories/segments.

        Args:
            comparison_type: Type of comparison (e.g., "period", "segment", "region")
            categories: List of category names being compared
            comparison_data: Data for each category

        Returns:
            Dict with winner, laggard, gap_analysis, insights, narrative
        """
        try:
            prompt = COMPARATIVE_ANALYSIS_PROMPT.format(
                comparison_type=comparison_type,
                categories=", ".join(categories),
                comparison_data=json.dumps(comparison_data, indent=2, default=str)
            )

            response = await self._generate_text(prompt)
            result = self._parse_json_response(response)

            result['comparison_type'] = comparison_type
            result['generated_at'] = datetime.now(timezone.utc).isoformat()

            logger.info(
                "comparative_analysis_generated",
                comparison_type=comparison_type,
                category_count=len(categories)
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate comparative analysis: {e}")
            return {
                "winner": categories[0] if categories else "Unknown",
                "laggard": categories[-1] if categories else "Unknown",
                "gap_analysis": "Unable to analyze",
                "insights": [],
                "narrative": "Comparative analysis unavailable.",
                "comparison_type": comparison_type
            }

    async def generate_full_dashboard_narrative(
        self,
        dashboard_id: str,
        dashboard_name: str,
        dashboard_description: str,
        widgets: List[Dict[str, Any]],
        time_period: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete narrative for a dashboard including summary and widget insights.

        Args:
            dashboard_id: ID of the dashboard
            dashboard_name: Name of the dashboard
            dashboard_description: Description of the dashboard
            widgets: List of widgets with their data
            time_period: Optional time period filter

        Returns:
            Complete narrative with executive summary and widget-level insights
        """
        try:
            # Generate executive summary
            summary = await self.generate_executive_summary(
                dashboard_name=dashboard_name,
                dashboard_description=dashboard_description,
                widgets=widgets,
                time_period=time_period
            )

            # Generate insights for each widget (limit to avoid too many API calls)
            widget_insights = []
            for widget in widgets[:10]:  # Limit to 10 widgets
                if widget.get('data'):
                    insight = await self.generate_widget_insight(
                        widget_type=widget.get('type', 'unknown'),
                        widget_title=widget.get('title', 'Untitled'),
                        metric_name=widget.get('metric', widget.get('title', 'metric')),
                        current_data=widget.get('data', {}),
                        historical_data=widget.get('historical_data')
                    )
                    widget_insights.append(insight)

            return {
                "dashboard_id": dashboard_id,
                "dashboard_name": dashboard_name,
                "executive_summary": summary,
                "widget_insights": widget_insights,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "widget_count": len(widgets),
                "insights_generated": len(widget_insights)
            }

        except Exception as e:
            logger.error(f"Failed to generate full dashboard narrative: {e}")
            return {
                "dashboard_id": dashboard_id,
                "dashboard_name": dashboard_name,
                "executive_summary": self._get_fallback_summary(dashboard_name),
                "widget_insights": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    async def _generate_text(self, prompt: str) -> str:
        """
        Call the LLM to generate text.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated text response
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract text from response
            if message.content and len(message.content) > 0:
                return message.content[0].text

            return "{}"

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling potential formatting issues.

        Args:
            response: Raw text response from LLM

        Returns:
            Parsed JSON as dict
        """
        try:
            # Try direct parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find JSON object in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            logger.warning("Could not parse JSON from LLM response")
            return {"raw_response": response}

    def _get_fallback_summary(self, dashboard_name: str) -> Dict[str, Any]:
        """Generate a fallback summary when AI generation fails."""
        return {
            "summary": f"Dashboard overview for {dashboard_name}",
            "key_metrics": [],
            "highlights": ["Data is loading or unavailable"],
            "concerns": [],
            "recommendations": ["Refresh the dashboard to see latest data"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dashboard_name": dashboard_name,
            "is_fallback": True
        }


# Singleton instance
_generator_instance: Optional[DashboardNarrativeGenerator] = None


def get_narrative_generator() -> DashboardNarrativeGenerator:
    """Get or create the singleton narrative generator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = DashboardNarrativeGenerator()
    return _generator_instance
