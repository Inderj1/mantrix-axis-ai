"""
Narrative Prompts - System prompts for AI-generated dashboard narratives.

Contains prompts for:
- Executive summaries
- Widget-level insights
- Trend analysis
- Anomaly detection narratives
"""

# Executive Summary Prompt
EXECUTIVE_SUMMARY_PROMPT = """You are an expert business analyst generating an executive summary for a dashboard.

Given the dashboard data below, generate a concise executive summary that:
1. Highlights the most important metrics and their current values
2. Identifies key trends (up/down/stable)
3. Calls out any anomalies or areas requiring attention
4. Provides actionable insights

Dashboard Name: {dashboard_name}
Dashboard Description: {dashboard_description}
Time Period: {time_period}

Widget Data:
{widget_data}

Guidelines:
- Be concise and actionable (3-5 bullet points max)
- Use specific numbers and percentages
- Highlight both positive trends and areas of concern
- Write for C-level executives who need quick insights
- Avoid technical jargon

Generate the executive summary in the following JSON format:
{{
    "summary": "One sentence overview",
    "key_metrics": [
        {{"metric": "name", "value": "formatted value", "trend": "up/down/stable", "insight": "brief insight"}}
    ],
    "highlights": ["bullet point 1", "bullet point 2"],
    "concerns": ["area of concern 1"],
    "recommendations": ["action item 1"]
}}
"""

# Widget Insight Prompt
WIDGET_INSIGHT_PROMPT = """You are a data analyst generating insights for a specific dashboard widget.

Widget Type: {widget_type}
Widget Title: {widget_title}
Metric: {metric_name}

Current Data:
{current_data}

Historical Data (if available):
{historical_data}

Generate a brief insight (1-2 sentences) that:
1. Explains what the data shows
2. Highlights any notable trends or anomalies
3. Provides context for the numbers

Return the insight as JSON:
{{
    "insight": "Your insight text here",
    "trend": "up/down/stable/anomaly",
    "confidence": "high/medium/low",
    "comparison": "vs previous period if applicable"
}}
"""

# Trend Analysis Prompt
TREND_ANALYSIS_PROMPT = """Analyze the following time series data and identify trends.

Metric: {metric_name}
Time Period: {time_period}
Data Points:
{data_points}

Provide analysis in JSON format:
{{
    "overall_trend": "increasing/decreasing/stable/volatile",
    "trend_strength": "strong/moderate/weak",
    "key_changes": [
        {{"period": "date or period", "change": "description of change", "magnitude": "percentage or value"}}
    ],
    "seasonality": "detected pattern or 'none detected'",
    "forecast_direction": "likely direction for next period",
    "narrative": "2-3 sentence narrative explaining the trend"
}}
"""

# Anomaly Detection Prompt
ANOMALY_NARRATIVE_PROMPT = """You detected an anomaly in the dashboard data. Generate an explanation.

Widget: {widget_title}
Metric: {metric_name}
Expected Value: {expected_value}
Actual Value: {actual_value}
Deviation: {deviation_percentage}%
Time: {timestamp}

Historical Context:
{historical_context}

Generate an anomaly explanation in JSON format:
{{
    "severity": "critical/warning/info",
    "headline": "Brief attention-grabbing headline",
    "explanation": "What might have caused this anomaly",
    "impact": "Potential business impact",
    "suggested_action": "Recommended next step"
}}
"""

# Comparative Analysis Prompt
COMPARATIVE_ANALYSIS_PROMPT = """Compare the following data sets and generate insights.

Comparison Type: {comparison_type}
Categories/Segments: {categories}

Data:
{comparison_data}

Generate comparative analysis in JSON format:
{{
    "winner": "Best performing category/segment",
    "laggard": "Worst performing category/segment",
    "gap_analysis": "Key differences between top and bottom",
    "insights": ["Insight about the comparison"],
    "narrative": "2-3 sentence narrative comparing the data"
}}
"""

# Dashboard Narrative Template
FULL_NARRATIVE_TEMPLATE = """
## Executive Summary
{executive_summary}

## Key Metrics at a Glance
{key_metrics_section}

## Trend Analysis
{trend_section}

## Areas Requiring Attention
{attention_section}

## Recommendations
{recommendations_section}

---
*Generated on {generated_at} | Data as of {data_timestamp}*
"""

# Formatting helpers
def format_metric_for_prompt(metric_data: dict) -> str:
    """Format a single metric for inclusion in prompts."""
    return f"- {metric_data.get('name', 'Unknown')}: {metric_data.get('value', 'N/A')} ({metric_data.get('change', 'no change')})"


def format_widget_data_for_prompt(widgets: list) -> str:
    """Format multiple widgets' data for the executive summary prompt."""
    formatted = []
    for widget in widgets:
        widget_str = f"""
Widget: {widget.get('title', 'Untitled')}
Type: {widget.get('type', 'unknown')}
Data: {widget.get('data', {})}
"""
        formatted.append(widget_str)
    return "\n".join(formatted)


def get_time_period_description(start_date: str, end_date: str) -> str:
    """Generate a human-readable time period description."""
    if start_date and end_date:
        return f"from {start_date} to {end_date}"
    elif end_date:
        return f"as of {end_date}"
    else:
        return "current period"
