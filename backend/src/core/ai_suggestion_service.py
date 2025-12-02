"""
AI-Powered Suggestion Service

Generates contextual follow-up suggestions using LLM based on:
- User's persona/role (CFO, COO, analyst, etc.)
- The query they just asked
- The results they received
"""

from typing import List, Dict, Any, Optional
import json
import structlog
from datetime import datetime
from anthropic import Anthropic

from src.config import settings
from src.models.user_profile import UserRole, ROLE_TEMPLATES

logger = structlog.get_logger()


class AISuggestionService:
    """
    AI-powered suggestion engine that generates persona-aware follow-up queries.

    Uses a fast LLM model (configurable via ANTHROPIC_FAST_MODEL env var).
    Default: claude-haiku-4-5-20251001
    Target: <2s response time
    """

    # Suggestion prompt template for queries with results
    SUGGESTION_PROMPT = """You are a data analytics assistant generating follow-up query suggestions.

USER CONTEXT:
- Role: {role_name}
- Role Focus: {role_description}
- Key Metrics: {key_metrics}

CURRENT QUERY:
Question: {query}

QUERY RESULTS SUMMARY:
- Columns: {columns}
- Row Count: {row_count}
- Sample Data: {sample_data}

Generate exactly {num_suggestions} follow-up questions this {role_name} would likely ask next.

REQUIREMENTS:
1. Each suggestion must be relevant to the user's role and the current query results
2. Suggestions should build on or drill down into the data they're looking at
3. Use natural language questions (not SQL)
4. Keep suggestions concise (under 15 words each)
5. Make suggestions actionable and specific to the data shown

Return ONLY a JSON array of strings, no other text:
["suggestion 1", "suggestion 2", ...]"""

    # Prompt for queries with no results - diagnostic version with SQL context
    EMPTY_RESULTS_PROMPT = """You are a data analytics assistant. A query returned NO RESULTS.

USER CONTEXT:
- Role: {role_name}
- Role Focus: {role_description}

QUERY: {query}

SQL CONTEXT:
- Generated SQL: {sql}
- Tables Used: {tables_used}
- Explanation: {explanation}

AVAILABLE TABLES IN DATABASE:
{available_tables}

ANALYZE why the query returned no results and generate {num_suggestions} helpful suggestions.

Your suggestions should:
1. Diagnose likely reasons for no results (date range too narrow, table doesn't have this data, filter too restrictive)
2. Suggest specific modifications based on what data IS available
3. Recommend alternative tables from the available data that might have relevant information
4. Be actionable and specific to this query
5. Use natural language questions (not SQL)

Return ONLY a JSON array of strings, no other text:
["suggestion 1", "suggestion 2", ...]"""

    # Fallback prompt when no SQL context is available
    EMPTY_RESULTS_PROMPT_SIMPLE = """You are a data analytics assistant. A query returned NO RESULTS.

USER CONTEXT:
- Role: {role_name}
- Role Focus: {role_description}

QUERY: {query}

Generate exactly {num_suggestions} helpful follow-up suggestions for this {role_name}.

REQUIREMENTS:
1. Suggest alternative queries or different angles to explore the topic
2. Consider broadening date ranges, removing filters, or trying related data
3. Suggest checking what data IS available on this topic
4. Use natural language questions (not SQL)
5. Keep suggestions concise (under 15 words each)

Return ONLY a JSON array of strings, no other text:
["suggestion 1", "suggestion 2", ...]"""

    # Default suggestions when AI fails or for generic users
    DEFAULT_SUGGESTIONS = [
        "Show trends over time",
        "Break down by category",
        "Compare to prior period",
        "Show top performers",
        "Drill down into details"
    ]

    # Default suggestions for empty results
    EMPTY_RESULTS_SUGGESTIONS = [
        "Try a broader date range",
        "Show all available data for this topic",
        "What data do we have?",
        "Remove filters and show all results",
        "Try a related query"
    ]

    def __init__(self):
        self._client = None
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds = 300  # 5 minutes

    @property
    def client(self):
        """Lazy load Anthropic client."""
        if self._client is None:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def _get_role_context(self, role: Optional[UserRole]) -> Dict[str, str]:
        """Get role-specific context for the prompt."""
        if role and role in ROLE_TEMPLATES:
            template = ROLE_TEMPLATES[role]
            return {
                "role_name": template.display_name,
                "role_description": template.description,
                "key_metrics": ", ".join(template.key_metrics[:5])  # Top 5 metrics
            }

        # Default context for unknown roles
        return {
            "role_name": "Business Analyst",
            "role_description": "General business analysis and data exploration",
            "key_metrics": "revenue, costs, trends, comparisons, breakdowns"
        }

    def _build_results_summary(
        self,
        results: List[Dict[str, Any]],
        max_sample_rows: int = 3
    ) -> Dict[str, str]:
        """Build a summary of query results for the prompt."""
        if not results:
            return {
                "columns": "No data",
                "row_count": "0",
                "sample_data": "No results"
            }

        columns = list(results[0].keys())
        sample_rows = results[:max_sample_rows]

        # Format sample data concisely
        sample_str = json.dumps(sample_rows, default=str)
        if len(sample_str) > 500:
            sample_str = sample_str[:500] + "..."

        return {
            "columns": ", ".join(columns),
            "row_count": str(len(results)),
            "sample_data": sample_str
        }

    def _get_cache_key(
        self,
        query: str,
        role: Optional[UserRole],
        result_columns: List[str]
    ) -> str:
        """Generate cache key for suggestions."""
        role_str = role.value if role else "default"
        cols_str = ",".join(sorted(result_columns)) if result_columns else ""
        return f"{query}:{role_str}:{cols_str}"

    def _check_cache(self, cache_key: str) -> Optional[List[str]]:
        """Check if suggestions are cached and still valid."""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = (datetime.utcnow() - cached['timestamp']).total_seconds()
            if age < self.cache_ttl_seconds:
                logger.debug("Cache hit for AI suggestions", cache_key=cache_key[:50])
                return cached['suggestions']
        return None

    async def generate_suggestions(
        self,
        query: str,
        results: List[Dict[str, Any]],
        role: Optional[UserRole] = None,
        num_suggestions: int = 5,
        timeout_seconds: Optional[float] = None,
        sql_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate AI-powered follow-up suggestions.

        Args:
            query: The natural language query that was asked
            results: The query results
            role: User's role (from UserProfile)
            num_suggestions: Number of suggestions to generate
            timeout_seconds: Timeout for LLM call (defaults to settings.ai_suggestion_timeout_seconds)
            sql_context: Optional SQL context for diagnostic suggestions (sql, tables_used, explanation, available_tables)

        Returns:
            List of follow-up suggestion strings
        """
        if timeout_seconds is None:
            timeout_seconds = settings.ai_suggestion_timeout_seconds
        start_time = datetime.utcnow()

        # Check cache first
        result_columns = list(results[0].keys()) if results else []
        cache_key = self._get_cache_key(query, role, result_columns)
        cached = self._check_cache(cache_key)
        if cached:
            return cached

        try:
            # Build prompt based on whether we have results
            role_context = self._get_role_context(role)

            if results:
                # Normal case: we have results to analyze
                results_summary = self._build_results_summary(results)
                prompt = self.SUGGESTION_PROMPT.format(
                    role_name=role_context["role_name"],
                    role_description=role_context["role_description"],
                    key_metrics=role_context["key_metrics"],
                    query=query,
                    columns=results_summary["columns"],
                    row_count=results_summary["row_count"],
                    sample_data=results_summary["sample_data"],
                    num_suggestions=num_suggestions
                )
            else:
                # Empty results: use diagnostic prompt if sql_context available
                if sql_context:
                    # Format available tables as a readable list
                    available_tables = sql_context.get("available_tables", [])
                    if available_tables:
                        tables_str = "\n".join(f"- {t}" for t in available_tables[:15])
                        if len(available_tables) > 15:
                            tables_str += f"\n... and {len(available_tables) - 15} more tables"
                    else:
                        tables_str = "No table information available"

                    prompt = self.EMPTY_RESULTS_PROMPT.format(
                        role_name=role_context["role_name"],
                        role_description=role_context["role_description"],
                        query=query,
                        sql=sql_context.get("sql", "N/A")[:1000],  # Limit SQL length
                        tables_used=", ".join(sql_context.get("tables_used", [])) or "N/A",
                        explanation=sql_context.get("explanation", "N/A")[:500],
                        available_tables=tables_str,
                        num_suggestions=num_suggestions
                    )
                    logger.info("Using diagnostic empty results prompt with SQL context")
                else:
                    # Fallback to simple prompt
                    prompt = self.EMPTY_RESULTS_PROMPT_SIMPLE.format(
                        role_name=role_context["role_name"],
                        role_description=role_context["role_description"],
                        query=query,
                        num_suggestions=num_suggestions
                    )
                    logger.info("Using simple empty results prompt (no SQL context)")

            # Call LLM with fast model
            response = await self._call_llm(prompt, timeout_seconds)

            # Parse suggestions
            suggestions = self._parse_suggestions(response, num_suggestions)

            # Cache the results
            self.cache[cache_key] = {
                'suggestions': suggestions,
                'timestamp': datetime.utcnow()
            }

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                "Generated AI suggestions",
                role=role.value if role else "default",
                num_suggestions=len(suggestions),
                elapsed_ms=round(elapsed_ms, 2)
            )

            return suggestions

        except Exception as e:
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.warning(
                "AI suggestion generation failed, using defaults",
                error=str(e),
                elapsed_ms=round(elapsed_ms, 2)
            )
            return self._get_fallback_suggestions(role, num_suggestions, has_results=bool(results))

    async def _call_llm(self, prompt: str, timeout_seconds: float) -> str:
        """Call LLM with fast model for suggestions."""
        import asyncio

        # Use synchronous call wrapped in executor for compatibility
        def sync_call():
            response = self.client.messages.create(
                model=settings.anthropic_fast_model,
                max_tokens=300,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # Extract text from response
            return response.content[0].text if response.content else ""

        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, sync_call),
            timeout=timeout_seconds
        )
        return response

    def _parse_suggestions(
        self,
        response: str,
        num_suggestions: int
    ) -> List[str]:
        """Parse LLM response into list of suggestions."""
        try:
            # Try to parse as JSON array
            response = response.strip()

            # Handle potential markdown code blocks
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()

            suggestions = json.loads(response)

            if isinstance(suggestions, list):
                # Clean and validate suggestions
                clean_suggestions = []
                for s in suggestions[:num_suggestions]:
                    if isinstance(s, str) and len(s.strip()) > 5:
                        clean_suggestions.append(s.strip())

                if clean_suggestions:
                    return clean_suggestions

        except json.JSONDecodeError:
            logger.warning("Failed to parse AI suggestions as JSON", response=response[:100])

        return self.DEFAULT_SUGGESTIONS[:num_suggestions]

    def _get_fallback_suggestions(
        self,
        role: Optional[UserRole],
        num_suggestions: int,
        has_results: bool = True
    ) -> List[str]:
        """Get role-specific fallback suggestions."""
        # If no results, return empty results suggestions
        if not has_results:
            return self.EMPTY_RESULTS_SUGGESTIONS[:num_suggestions]

        # Role-specific fallbacks
        role_fallbacks = {
            UserRole.CFO: [
                "Show margin analysis",
                "Compare to budget",
                "Show cash flow impact",
                "Break down by cost center",
                "Show year-over-year trend"
            ],
            UserRole.COO: [
                "Show operational efficiency",
                "Break down by region",
                "Show process bottlenecks",
                "Compare to targets",
                "Show resource utilization"
            ],
            UserRole.CEO: [
                "Show strategic impact",
                "Compare to market",
                "Show growth drivers",
                "Break down by business unit",
                "Show competitive position"
            ],
            UserRole.SALES_DIRECTOR: [
                "Show top customers",
                "Break down by sales rep",
                "Show pipeline analysis",
                "Compare to quota",
                "Show win/loss trends"
            ],
            UserRole.FINANCE_ANALYST: [
                "Show variance analysis",
                "Break down by account",
                "Show trend analysis",
                "Compare to prior period",
                "Show detailed breakdown"
            ]
        }

        if role and role in role_fallbacks:
            return role_fallbacks[role][:num_suggestions]

        return self.DEFAULT_SUGGESTIONS[:num_suggestions]

    def clear_cache(self):
        """Clear the suggestion cache."""
        self.cache.clear()
        logger.info("AI suggestion cache cleared")


# Singleton instance
_ai_suggestion_service: Optional[AISuggestionService] = None


def get_ai_suggestion_service() -> AISuggestionService:
    """Get or create the singleton AI suggestion service."""
    global _ai_suggestion_service
    if _ai_suggestion_service is None:
        _ai_suggestion_service = AISuggestionService()
    return _ai_suggestion_service
