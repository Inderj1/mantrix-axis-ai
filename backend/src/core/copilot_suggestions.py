"""Copilot suggestion engine - Pattern-based, performance-optimized."""
from typing import List, Dict, Any, Optional
import re
import structlog
from datetime import datetime, timedelta
from functools import lru_cache

logger = structlog.get_logger()


class CopilotSuggestionEngine:
    """
    Pattern-based suggestion engine for follow-up queries.

    Performance characteristics:
    - <5ms for pattern matching
    - >90% cache hit rate for common patterns
    - Zero blocking on main query execution
    """

    # Pattern-based suggestion templates
    SUGGESTION_PATTERNS = {
        # Revenue queries
        'revenue': {
            'keywords': ['revenue', 'sales', 'income', 'top line'],
            'suggestions': [
                "Show revenue breakdown by product category",
                "Compare revenue vs. last year",
                "Show top 10 revenue-generating products",
                "Analyze revenue trends by month",
                "Show revenue by customer segment"
            ]
        },

        # Expense/Cost queries
        'expenses': {
            'keywords': ['expense', 'cost', 'cogs', 'spending', 'opex'],
            'suggestions': [
                "Show expense breakdown by category",
                "Compare expenses vs. budget",
                "Identify top expense drivers",
                "Analyze expense trends over time",
                "Show cost variance analysis"
            ]
        },

        # Margin/Profitability queries
        'profitability': {
            'keywords': ['margin', 'profit', 'ebitda', 'contribution', 'gross profit'],
            'suggestions': [
                "Show margin trends by product",
                "Compare margins across categories",
                "Identify low-margin products",
                "Show profitability by customer",
                "Analyze margin compression drivers"
            ]
        },

        # Comparison queries
        'comparison': {
            'keywords': ['vs', 'versus', 'compare', 'comparison'],
            'suggestions': [
                "Add year-over-year comparison",
                "Compare to budget",
                "Show quarter-over-quarter change",
                "Add benchmark comparison",
                "Show variance analysis"
            ]
        },

        # Time period queries
        'time_period': {
            'keywords': ['month', 'quarter', 'year', 'ytd', 'qtd', 'period'],
            'suggestions': [
                "Show same period last year",
                "Break down by month",
                "Show quarterly trends",
                "Analyze seasonality patterns",
                "Compare to prior period"
            ]
        },

        # Top N queries
        'top_n': {
            'keywords': ['top', 'bottom', 'highest', 'lowest', 'best', 'worst'],
            'suggestions': [
                "Show bottom performers",
                "Expand to top 20",
                "Show performance distribution",
                "Identify outliers",
                "Show median vs. top performers"
            ]
        },

        # Trend queries
        'trends': {
            'keywords': ['trend', 'growth', 'decline', 'change', 'movement'],
            'suggestions': [
                "Show trend drivers",
                "Compare growth rates",
                "Identify inflection points",
                "Forecast next period",
                "Show growth acceleration"
            ]
        },

        # Product queries
        'product': {
            'keywords': ['product', 'sku', 'item', 'category'],
            'suggestions': [
                "Show product mix analysis",
                "Compare product performance",
                "Show product lifecycle stage",
                "Analyze cannibalization",
                "Show new vs. existing products"
            ]
        },

        # Customer queries
        'customer': {
            'keywords': ['customer', 'client', 'account', 'segment'],
            'suggestions': [
                "Show customer concentration",
                "Analyze customer retention",
                "Show customer lifetime value",
                "Compare customer segments",
                "Show new vs. repeat customers"
            ]
        },

        # Variance/Analysis queries
        'variance': {
            'keywords': ['variance', 'difference', 'gap', 'delta'],
            'suggestions': [
                "Show variance drivers",
                "Analyze favorable vs. unfavorable",
                "Break down by component",
                "Show variance waterfall",
                "Identify key contributors"
            ]
        }
    }

    # Context-based suggestions (depend on result data)
    CONTEXT_PATTERNS = {
        'negative_trend': {
            'condition': lambda results: any(
                'growth' in str(k).lower() and v < 0
                for row in results for k, v in row.items() if isinstance(v, (int, float))
            ),
            'suggestions': [
                "Identify root causes of decline",
                "Show which segments are declining",
                "Compare to market trends"
            ]
        },

        'high_variance': {
            'condition': lambda results: any(
                'variance' in str(k).lower() and abs(v) > 0.1
                for row in results for k, v in row.items() if isinstance(v, (int, float))
            ),
            'suggestions': [
                "Break down variance by driver",
                "Show variance waterfall",
                "Identify controllable vs. uncontrollable factors"
            ]
        },

        'few_results': {
            'condition': lambda results: len(results) < 5,
            'suggestions': [
                "Expand time range",
                "Remove filters to see full picture",
                "Show related data"
            ]
        },

        'many_results': {
            'condition': lambda results: len(results) > 50,
            'suggestions': [
                "Show top 10 only",
                "Group by category",
                "Show summary statistics"
            ]
        }
    }

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=1)

    @lru_cache(maxsize=1000)
    def _detect_patterns(self, query: str) -> List[str]:
        """
        Detect patterns in query text.

        Performance: <2ms for pattern matching
        """
        query_lower = query.lower()
        detected_patterns = []

        for pattern_name, pattern_config in self.SUGGESTION_PATTERNS.items():
            keywords = pattern_config['keywords']
            if any(keyword in query_lower for keyword in keywords):
                detected_patterns.append(pattern_name)

        return detected_patterns

    def _get_context_suggestions(
        self,
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Get suggestions based on result data.

        Performance: <3ms for simple condition checks
        """
        suggestions = []

        for pattern_name, pattern_config in self.CONTEXT_PATTERNS.items():
            try:
                if pattern_config['condition'](results):
                    suggestions.extend(pattern_config['suggestions'][:2])
            except Exception as e:
                logger.warning(
                    "Context pattern check failed",
                    pattern=pattern_name,
                    error=str(e)
                )

        return suggestions

    def generate_suggestions(
        self,
        query: str,
        sql: str,
        results: List[Dict[str, Any]],
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Generate follow-up suggestions based on query patterns and results.

        Performance target: <10ms total

        Args:
            query: Natural language query
            sql: Generated SQL
            results: Query results
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of follow-up suggestion strings
        """
        start_time = datetime.utcnow()

        # Check cache first
        cache_key = f"{query}:{len(results)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.utcnow() - cached['timestamp'] < self.cache_ttl:
                logger.debug(
                    "Cache hit for suggestions",
                    query_preview=query[:50],
                    suggestions=len(cached['suggestions'])
                )
                return cached['suggestions']

        suggestions = []

        # 1. Pattern-based suggestions (fast, cached)
        detected_patterns = self._detect_patterns(query)
        for pattern in detected_patterns[:2]:  # Limit to 2 patterns
            pattern_suggestions = self.SUGGESTION_PATTERNS[pattern]['suggestions']
            suggestions.extend(pattern_suggestions[:2])  # Take 2 from each

        # 2. Context-based suggestions (conditional on results)
        if results:
            context_suggestions = self._get_context_suggestions(results)
            suggestions.extend(context_suggestions)

        # 3. Generic intelligent suggestions
        if len(suggestions) < max_suggestions:
            generic = self._get_generic_suggestions(query, sql)
            suggestions.extend(generic)

        # Deduplicate and limit
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion not in seen:
                unique_suggestions.append(suggestion)
                seen.add(suggestion)
                if len(unique_suggestions) >= max_suggestions:
                    break

        # Cache the results
        self.cache[cache_key] = {
            'suggestions': unique_suggestions,
            'timestamp': datetime.utcnow()
        }

        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(
            "Generated suggestions",
            query_preview=query[:50],
            num_suggestions=len(unique_suggestions),
            elapsed_ms=round(elapsed_ms, 2),
            patterns_detected=detected_patterns
        )

        return unique_suggestions

    def _get_generic_suggestions(self, query: str, sql: str) -> List[str]:
        """
        Get generic intelligent suggestions based on query structure.
        """
        suggestions = []

        # If no GROUP BY, suggest aggregation
        if 'GROUP BY' not in sql.upper():
            suggestions.append("Group results by category")

        # If no time dimension, suggest temporal analysis
        if not any(time_word in query.lower() for time_word in ['month', 'quarter', 'year', 'date']):
            suggestions.append("Show trends over time")

        # If no ORDER BY, suggest sorting
        if 'ORDER BY' not in sql.upper():
            suggestions.append("Sort by value")

        # Generic drill-down
        suggestions.append("Drill down into details")

        return suggestions

    def clear_cache(self):
        """Clear the suggestion cache."""
        self.cache.clear()
        logger.info("Suggestion cache cleared")


# Singleton instance
_suggestion_engine: Optional[CopilotSuggestionEngine] = None


def get_suggestion_engine() -> CopilotSuggestionEngine:
    """Get or create the singleton suggestion engine."""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = CopilotSuggestionEngine()
    return _suggestion_engine
