"""
Dashboard Intent Detector - Detects conversational dashboard creation requests.

When users type messages like:
- "Create a sales dashboard with revenue by region"
- "Build me a dashboard showing customer trends"
- "Make a new dashboard for inventory analysis"

This module detects the intent and extracts widget descriptions.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class DashboardIntentType(Enum):
    """Types of dashboard-related intents."""
    CREATE = "create"           # Create a new dashboard
    ADD_WIDGET = "add_widget"   # Add widget to existing dashboard
    MODIFY = "modify"           # Modify dashboard configuration
    NONE = "none"               # Not a dashboard intent


@dataclass
class WidgetDescription:
    """Parsed widget description from user query."""
    query: str                          # The NLP query for this widget
    suggested_title: Optional[str] = None
    suggested_chart_type: Optional[str] = None
    position: int = 0                   # Order in layout


@dataclass
class DashboardIntent:
    """Parsed dashboard creation intent from user query."""
    intent_type: DashboardIntentType
    dashboard_name: Optional[str] = None
    dashboard_description: Optional[str] = None
    widget_descriptions: List[WidgetDescription] = field(default_factory=list)
    global_filters: Dict[str, str] = field(default_factory=dict)
    raw_query: str = ""
    confidence: float = 0.0


class DashboardIntentDetector:
    """
    Detects dashboard creation intents from natural language queries.

    Uses pattern matching to identify:
    1. Dashboard creation commands
    2. Widget specifications within the query
    3. Chart type preferences
    4. Filter requirements
    """

    # Primary dashboard creation patterns (high confidence)
    DASHBOARD_CREATE_PATTERNS = [
        r"create\s+(a\s+)?(new\s+)?dashboard",
        r"build\s+(a\s+)?(new\s+)?dashboard",
        r"make\s+(a\s+)?(new\s+)?dashboard",
        r"set\s+up\s+(a\s+)?(new\s+)?dashboard",
        r"generate\s+(a\s+)?(new\s+)?dashboard",
        r"new\s+dashboard\s+(for|with|showing)",
        r"^dashboard\s+(for|with|showing|of)",
        r"i\s+(want|need)\s+(a\s+)?dashboard",
        r"can\s+you\s+(create|build|make)\s+.*dashboard",
    ]

    # Widget addition patterns
    ADD_WIDGET_PATTERNS = [
        r"add\s+(a\s+)?(chart|widget|graph|table)\s+",
        r"include\s+(a\s+)?(chart|widget|graph|table)\s+",
        r"put\s+(a\s+)?(chart|widget|graph|table)\s+",
    ]

    # Chart type extraction patterns
    CHART_TYPE_PATTERNS = {
        "bar": [r"\bbar\s+chart", r"\bbar\s+graph", r"\bcolumn\s+chart"],
        "line": [r"\bline\s+chart", r"\bline\s+graph", r"\btrend\s+chart", r"\btime\s+series"],
        "pie": [r"\bpie\s+chart", r"\bdonut\s+chart", r"\bdistribution"],
        "area": [r"\barea\s+chart", r"\bstacked\s+area"],
        "scatter": [r"\bscatter\s+plot", r"\bscatter\s+chart", r"\bcorrelation"],
        "table": [r"\btable\b", r"\bdata\s+table", r"\bgrid"],
        "metric": [r"\bkpi\b", r"\bmetric\s+card", r"\bsingle\s+number", r"\bsummary\s+metric"],
    }

    # Name extraction patterns
    NAME_PATTERNS = [
        r"(?:called|named|titled)\s+['\"]?([^'\"]+)['\"]?",
        r"['\"]([^'\"]+)['\"]?\s+dashboard",
        r"dashboard\s+['\"]?([^'\"]+)['\"]?",
    ]

    # Widget separator patterns (for multi-widget queries)
    WIDGET_SEPARATORS = [
        r"\s+and\s+(?:also\s+)?(?:a\s+)?(?:chart|widget|graph|table)?\s*(?:showing|for|of|with)",
        r"\s+,\s+(?:and\s+)?(?:a\s+)?(?:another\s+)?(?:chart|widget|graph)?\s*(?:showing|for|of|with)?",
        r"\s+plus\s+(?:a\s+)?",
        r"\s+also\s+(?:show|include|add)\s+",
        r"\s+along\s+with\s+",
    ]

    # Metric keywords that suggest widget content
    METRIC_KEYWORDS = {
        "revenue": ["revenue", "sales", "income", "earnings"],
        "cost": ["cost", "expense", "spending"],
        "profit": ["profit", "margin", "earnings"],
        "count": ["count", "number of", "total", "quantity"],
        "trend": ["trend", "over time", "monthly", "weekly", "daily"],
        "comparison": ["vs", "compared to", "versus", "comparison"],
        "distribution": ["by", "breakdown", "split", "per"],
    }

    # Time filter patterns
    TIME_FILTER_PATTERNS = {
        "last_7_days": [r"last\s+7\s+days", r"past\s+week"],
        "last_30_days": [r"last\s+30\s+days", r"past\s+month", r"last\s+month"],
        "last_90_days": [r"last\s+90\s+days", r"past\s+quarter", r"last\s+quarter"],
        "last_year": [r"last\s+year", r"past\s+year", r"last\s+12\s+months"],
        "ytd": [r"year\s+to\s+date", r"ytd", r"this\s+year"],
    }

    def __init__(self):
        # Compile patterns for efficiency
        self._create_patterns = [re.compile(p, re.IGNORECASE) for p in self.DASHBOARD_CREATE_PATTERNS]
        self._add_widget_patterns = [re.compile(p, re.IGNORECASE) for p in self.ADD_WIDGET_PATTERNS]
        self._name_patterns = [re.compile(p, re.IGNORECASE) for p in self.NAME_PATTERNS]
        self._separator_patterns = [re.compile(p, re.IGNORECASE) for p in self.WIDGET_SEPARATORS]

        self._chart_type_patterns = {
            chart_type: [re.compile(p, re.IGNORECASE) for p in patterns]
            for chart_type, patterns in self.CHART_TYPE_PATTERNS.items()
        }

        self._time_filter_patterns = {
            time_filter: [re.compile(p, re.IGNORECASE) for p in patterns]
            for time_filter, patterns in self.TIME_FILTER_PATTERNS.items()
        }

    def detect(self, query: str) -> DashboardIntent:
        """
        Detect dashboard intent from a natural language query.

        Args:
            query: The user's natural language input

        Returns:
            DashboardIntent with parsed information
        """
        query = query.strip()
        query_lower = query.lower()

        # Check for dashboard creation intent
        intent_type = self._detect_intent_type(query_lower)

        if intent_type == DashboardIntentType.NONE:
            return DashboardIntent(
                intent_type=DashboardIntentType.NONE,
                raw_query=query,
                confidence=0.0
            )

        # Extract dashboard name
        dashboard_name = self._extract_dashboard_name(query)

        # Extract widget descriptions
        widget_descriptions = self._extract_widget_descriptions(query)

        # Extract global filters
        global_filters = self._extract_global_filters(query_lower)

        # Calculate confidence based on matched patterns
        confidence = self._calculate_confidence(query_lower, widget_descriptions)

        # Generate description
        description = self._generate_description(widget_descriptions)

        logger.info(
            "dashboard_intent_detected",
            intent_type=intent_type.value,
            dashboard_name=dashboard_name,
            widget_count=len(widget_descriptions),
            confidence=confidence
        )

        return DashboardIntent(
            intent_type=intent_type,
            dashboard_name=dashboard_name,
            dashboard_description=description,
            widget_descriptions=widget_descriptions,
            global_filters=global_filters,
            raw_query=query,
            confidence=confidence
        )

    def _detect_intent_type(self, query_lower: str) -> DashboardIntentType:
        """Detect the type of dashboard intent."""
        # Check for create patterns
        for pattern in self._create_patterns:
            if pattern.search(query_lower):
                return DashboardIntentType.CREATE

        # Check for add widget patterns
        for pattern in self._add_widget_patterns:
            if pattern.search(query_lower):
                return DashboardIntentType.ADD_WIDGET

        return DashboardIntentType.NONE

    def _extract_dashboard_name(self, query: str) -> Optional[str]:
        """Extract dashboard name from query."""
        for pattern in self._name_patterns:
            match = pattern.search(query)
            if match:
                name = match.group(1).strip()
                # Clean up common words
                name = re.sub(r"\b(dashboard|for|with|showing)\b", "", name, flags=re.IGNORECASE)
                name = name.strip()
                if name:
                    return name.title()

        # Generate name from metrics mentioned
        return self._generate_name_from_metrics(query)

    def _generate_name_from_metrics(self, query: str) -> str:
        """Generate a dashboard name from metrics mentioned in query."""
        query_lower = query.lower()
        found_metrics = []

        for metric, keywords in self.METRIC_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                found_metrics.append(metric.title())

        if found_metrics:
            return f"{' & '.join(found_metrics[:2])} Dashboard"

        return "New Dashboard"

    def _extract_widget_descriptions(self, query: str) -> List[WidgetDescription]:
        """Extract individual widget descriptions from query."""
        widgets = []
        query_lower = query.lower()

        # Remove dashboard creation prefix
        content = re.sub(
            r"^(create|build|make|set up|generate)\s+(a\s+)?(new\s+)?dashboard\s+(for|with|showing|of|called|named)?\s*",
            "",
            query,
            flags=re.IGNORECASE
        ).strip()

        if not content:
            content = query

        # Try to split into multiple widgets
        widget_texts = self._split_into_widgets(content)

        for i, text in enumerate(widget_texts):
            text = text.strip()
            if not text:
                continue

            # Extract chart type preference
            chart_type = self._detect_chart_type(text)

            # Generate title
            title = self._generate_widget_title(text)

            # Clean up the query text
            widget_query = self._clean_widget_query(text)

            widgets.append(WidgetDescription(
                query=widget_query,
                suggested_title=title,
                suggested_chart_type=chart_type,
                position=i
            ))

        # If no widgets extracted, create one from the full query
        if not widgets:
            chart_type = self._detect_chart_type(query)
            widgets.append(WidgetDescription(
                query=self._clean_widget_query(query),
                suggested_title=self._generate_widget_title(query),
                suggested_chart_type=chart_type,
                position=0
            ))

        return widgets

    def _split_into_widgets(self, content: str) -> List[str]:
        """Split content into separate widget descriptions."""
        # First try explicit separators
        for pattern in self._separator_patterns:
            parts = pattern.split(content)
            if len(parts) > 1:
                return [p.strip() for p in parts if p.strip()]

        # Try simple comma/and splitting for list-like content
        if " and " in content.lower() and len(content.split(" and ")) <= 4:
            parts = re.split(r"\s+and\s+", content, flags=re.IGNORECASE)
            # Only split if parts look like separate widget descriptions
            if all(len(p.split()) >= 2 for p in parts):
                return parts

        # Return as single widget
        return [content]

    def _detect_chart_type(self, text: str) -> Optional[str]:
        """Detect chart type from text."""
        text_lower = text.lower()

        for chart_type, patterns in self._chart_type_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    return chart_type

        # Infer from content
        if any(kw in text_lower for kw in ["trend", "over time", "monthly", "weekly"]):
            return "line"
        if any(kw in text_lower for kw in ["distribution", "breakdown", "split"]):
            return "pie"
        if any(kw in text_lower for kw in ["comparison", "vs", "compare"]):
            return "bar"

        return None  # Let backend choose

    def _generate_widget_title(self, text: str) -> str:
        """Generate a widget title from text."""
        # Remove common words
        title = re.sub(
            r"\b(show|display|chart|graph|table|widget|me|the|a|an|please|with|for)\b",
            "",
            text,
            flags=re.IGNORECASE
        )

        # Clean up
        title = " ".join(title.split())[:50]  # Limit length

        if title:
            return title.title()

        return "Chart"

    def _clean_widget_query(self, text: str) -> str:
        """Clean widget query for execution."""
        # Remove chart type specifications
        for patterns in self.CHART_TYPE_PATTERNS.values():
            for p in patterns:
                text = re.sub(p, "", text, flags=re.IGNORECASE)

        # Remove dashboard-specific words
        text = re.sub(
            r"\b(dashboard|widget|chart|graph)\b",
            "",
            text,
            flags=re.IGNORECASE
        )

        # Clean up
        text = " ".join(text.split())

        # Ensure it starts with "Show" or similar for the NLP engine
        if not re.match(r"^(show|get|find|list|calculate|what)", text, re.IGNORECASE):
            text = f"Show {text}"

        return text.strip()

    def _extract_global_filters(self, query_lower: str) -> Dict[str, str]:
        """Extract global filters from query."""
        filters = {}

        # Extract time filters
        for time_filter, patterns in self._time_filter_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    filters["time_range"] = time_filter
                    break
            if "time_range" in filters:
                break

        return filters

    def _calculate_confidence(self, query_lower: str, widgets: List[WidgetDescription]) -> float:
        """Calculate confidence score for the intent detection."""
        score = 0.0

        # Pattern matches
        for pattern in self._create_patterns:
            if pattern.search(query_lower):
                score += 0.4
                break

        # Widget extraction success
        if widgets:
            score += 0.2
            if len(widgets) > 1:
                score += 0.1

        # Clear metric mentions
        for keywords in self.METRIC_KEYWORDS.values():
            if any(kw in query_lower for kw in keywords):
                score += 0.1
                break

        # Chart type specification
        for patterns in self._chart_type_patterns.values():
            for pattern in patterns:
                if pattern.search(query_lower):
                    score += 0.1
                    break

        return min(score, 1.0)

    def _generate_description(self, widgets: List[WidgetDescription]) -> str:
        """Generate dashboard description from widgets."""
        if not widgets:
            return "A new dashboard"

        widget_summaries = []
        for w in widgets:
            if w.suggested_title:
                widget_summaries.append(w.suggested_title)

        if widget_summaries:
            return f"Dashboard with: {', '.join(widget_summaries[:3])}"

        return f"Dashboard with {len(widgets)} widget(s)"


# Singleton instance
_detector_instance: Optional[DashboardIntentDetector] = None


def get_dashboard_intent_detector() -> DashboardIntentDetector:
    """Get or create the singleton dashboard intent detector."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = DashboardIntentDetector()
    return _detector_instance


def detect_dashboard_intent(query: str) -> DashboardIntent:
    """Convenience function to detect dashboard intent."""
    return get_dashboard_intent_detector().detect(query)
