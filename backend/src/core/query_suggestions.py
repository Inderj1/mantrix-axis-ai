"""Query suggestion and recommendation service."""

from typing import List, Dict, Any, Optional, Tuple
import structlog
from dataclasses import dataclass
import re
from collections import Counter
import difflib

logger = structlog.get_logger()


@dataclass
class QuerySuggestion:
    """Represents a query suggestion."""
    suggestion_type: str  # 'similar', 'template', 'correction', 'refinement'
    text: str
    confidence: float
    explanation: Optional[str] = None
    example_sql: Optional[str] = None


class QuerySuggestionService:
    """Provides intelligent query suggestions and recommendations."""
    
    def __init__(self, cache_manager=None, llm_client=None):
        self.cache_manager = cache_manager
        self.llm_client = llm_client
        
        # Common query templates by category
        self.query_templates = {
            "aggregation": [
                {
                    "pattern": "total {metric} by {dimension}",
                    "example": "Show me total sales by region",
                    "sql_template": "SELECT {dimension}, SUM({metric}) as total_{metric} FROM {table} GROUP BY {dimension}"
                },
                {
                    "pattern": "average {metric} for {filter}",
                    "example": "What's the average order value for last month",
                    "sql_template": "SELECT AVG({metric}) as avg_{metric} FROM {table} WHERE {filter}"
                }
            ],
            "ranking": [
                {
                    "pattern": "top {n} {entity} by {metric}",
                    "example": "Show me top 10 customers by revenue",
                    "sql_template": "SELECT {entity}, {metric} FROM {table} ORDER BY {metric} DESC LIMIT {n}"
                },
                {
                    "pattern": "bottom {n} {entity} by {metric}",
                    "example": "Find bottom 5 products by sales",
                    "sql_template": "SELECT {entity}, {metric} FROM {table} ORDER BY {metric} ASC LIMIT {n}"
                }
            ],
            "time_series": [
                {
                    "pattern": "{metric} over time",
                    "example": "Show revenue over time",
                    "sql_template": "SELECT DATE_TRUNC('month', date_column) as period, SUM({metric}) FROM {table} GROUP BY period ORDER BY period"
                },
                {
                    "pattern": "{metric} trend for {period}",
                    "example": "Sales trend for last quarter",
                    "sql_template": "SELECT date_column, {metric} FROM {table} WHERE {period_filter} ORDER BY date_column"
                }
            ],
            "comparison": [
                {
                    "pattern": "compare {metric} between {entity1} and {entity2}",
                    "example": "Compare sales between region A and region B",
                    "sql_template": "SELECT entity, {metric} FROM {table} WHERE entity IN ('{entity1}', '{entity2}')"
                },
                {
                    "pattern": "{metric} this {period} vs last {period}",
                    "example": "Revenue this month vs last month",
                    "sql_template": "WITH current AS (...), previous AS (...) SELECT * FROM current UNION ALL SELECT * FROM previous"
                }
            ]
        }
        
        # Common metric and dimension keywords
        self.common_metrics = [
            "sales", "revenue", "profit", "cost", "count", "amount", 
            "quantity", "price", "margin", "total", "average", "sum"
        ]
        
        self.common_dimensions = [
            "customer", "product", "region", "country", "category",
            "department", "branch", "store", "employee", "supplier"
        ]
        
        self.time_keywords = [
            "today", "yesterday", "week", "month", "quarter", "year",
            "daily", "weekly", "monthly", "quarterly", "yearly"
        ]
    
    def get_suggestions(
        self, 
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        max_suggestions: int = 5
    ) -> List[QuerySuggestion]:
        """Get query suggestions based on user input and context."""
        suggestions = []
        
        # Check if query is incomplete
        if self._is_incomplete_query(user_query):
            suggestions.extend(self._get_autocomplete_suggestions(user_query))
        
        # Get template-based suggestions
        template_suggestions = self._get_template_suggestions(user_query)
        suggestions.extend(template_suggestions)
        
        # Get similar queries from history (if cache available)
        if self.cache_manager:
            similar_queries = self._get_similar_historical_queries(user_query)
            suggestions.extend(similar_queries)
        
        # Get refinement suggestions
        refinements = self._get_refinement_suggestions(user_query, context)
        suggestions.extend(refinements)
        
        # Sort by confidence and deduplicate
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions[:max_suggestions]
    
    def get_clarifying_questions(
        self,
        user_query: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Generate clarifying questions for ambiguous queries."""
        questions = []
        query_lower = user_query.lower()
        
        # Check for missing time context
        if not any(time_word in query_lower for time_word in self.time_keywords):
            if any(metric in query_lower for metric in ["sales", "revenue", "orders"]):
                questions.append("What time period are you interested in? (e.g., last month, this year)")
        
        # Check for missing aggregation level
        if "by" not in query_lower and any(word in query_lower for word in ["show", "get", "find"]):
            questions.append("Would you like to see this data grouped by any dimension? (e.g., by customer, by product)")
        
        # Check for missing filters
        if not any(word in query_lower for word in ["where", "filter", "only", "just"]):
            questions.append("Do you want to filter the data in any way? (e.g., only active customers, specific regions)")
        
        # Check for ambiguous metrics
        if "best" in query_lower or "top" in query_lower:
            if not any(metric in query_lower for metric in self.common_metrics):
                questions.append("What metric should we use to determine 'best' or 'top'? (e.g., by revenue, by quantity)")
        
        # Context-specific questions based on errors
        if error_context and error_context.get("error_type") == "ambiguous_request":
            questions.append("Could you be more specific about what data you want to see?")
        
        return questions[:3]  # Limit to 3 questions
    
    def suggest_query_improvements(
        self,
        original_query: str,
        generated_sql: str,
        performance_stats: Optional[Dict[str, Any]] = None,
        execution_error: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Suggest improvements to the query based on SQL analysis.

        Note: Error-specific analysis is now handled by ErrorCorrectionAgent
        which provides detailed error_analysis in the response. This method
        focuses on performance and query optimization suggestions.
        """
        improvements = []

        # Skip suggestions if there was an execution error
        # (error analysis is handled by ErrorCorrectionAgent)
        if execution_error:
            return improvements

        # Analyze the generated SQL
        sql_upper = generated_sql.upper()
        query_lower = original_query.lower()

        # Check for SELECT *
        if "SELECT *" in sql_upper:
            improvements.append({
                "type": "performance",
                "suggestion": "Specify only the columns you need instead of SELECT *",
                "impact": "Reduces data transfer and improves query speed",
                "example": "Instead of 'show all customer data', try 'show customer name and total purchases'"
            })

        # Check for missing LIMIT - but be smarter about implicit limits
        has_explicit_limit = "LIMIT" in sql_upper or "TOP " in sql_upper
        has_implicit_limit = any(word in query_lower for word in [
            "top ", "first ", "single", " one ", "latest", "most recent",
            "highest", "lowest", "best", "worst"
        ])
        # Check for specific ID lookups (e.g., "show order 12345")
        has_specific_id = any(word in query_lower for word in ["id ", "number ", "code "])

        # Only suggest limit if: no limit, no implicit limit, and query is for listing data
        list_query_words = ["show", "list", "display", "all", "every"]
        is_list_query = any(word in query_lower for word in list_query_words)

        if (not has_explicit_limit
            and not has_implicit_limit
            and not has_specific_id
            and is_list_query):
            improvements.append({
                "type": "performance",
                "suggestion": "Add a limit to your query",
                "impact": "Prevents retrieving too much data",
                "example": f"{original_query} (limit to 100 results)"
            })

        # Check for expensive operations without filters
        if "JOIN" in sql_upper and "WHERE" not in sql_upper:
            improvements.append({
                "type": "performance",
                "suggestion": "Add filters to reduce the amount of data joined",
                "impact": "Significantly reduces query execution time",
                "example": "Add a date range or specific conditions"
            })

        # Suggest using materialized views if available
        if performance_stats and performance_stats.get("bytes_processed", 0) > 1_000_000_000:  # 1GB
            improvements.append({
                "type": "optimization",
                "suggestion": "This query processes a lot of data - consider using a materialized view",
                "impact": "Could reduce query time by 90% or more",
                "example": "Ask your admin about creating a pre-aggregated view for this data"
            })

        return improvements

    def _is_incomplete_query(self, query: str) -> bool:
        """Check if the query appears to be incomplete."""
        # Very short queries
        if len(query.split()) < 3:
            return True
        
        # Ends with common incomplete patterns
        incomplete_endings = ["by", "for", "with", "show me", "get me", "find"]
        return any(query.lower().strip().endswith(ending) for ending in incomplete_endings)
    
    def _get_autocomplete_suggestions(self, partial_query: str) -> List[QuerySuggestion]:
        """Get autocomplete suggestions for incomplete queries."""
        suggestions = []
        query_lower = partial_query.lower().strip()
        
        # Common completions based on starting words
        if query_lower.endswith("show me"):
            completions = [
                "total sales by month",
                "top customers by revenue",
                "all products in category",
                "revenue trend over time"
            ]
            for completion in completions:
                suggestions.append(QuerySuggestion(
                    suggestion_type="template",
                    text=f"{partial_query} {completion}",
                    confidence=0.8,
                    explanation="Common query pattern"
                ))
        
        elif query_lower.endswith("by"):
            # Suggest common dimensions
            for dimension in self.common_dimensions[:3]:
                suggestions.append(QuerySuggestion(
                    suggestion_type="refinement",
                    text=f"{partial_query} {dimension}",
                    confidence=0.7,
                    explanation=f"Group results by {dimension}"
                ))
        
        return suggestions
    
    def _get_template_suggestions(self, user_query: str) -> List[QuerySuggestion]:
        """Match query against templates and suggest variations."""
        suggestions = []
        query_lower = user_query.lower()
        
        # Extract key components
        metrics = [m for m in self.common_metrics if m in query_lower]
        dimensions = [d for d in self.common_dimensions if d in query_lower]
        
        # Find matching templates
        for category, templates in self.query_templates.items():
            for template in templates:
                # Simple pattern matching (in production, use more sophisticated NLP)
                pattern_words = set(re.findall(r'\w+', template["pattern"].lower()))
                query_words = set(re.findall(r'\w+', query_lower))
                
                overlap = len(pattern_words.intersection(query_words))
                if overlap > 0:
                    confidence = overlap / len(pattern_words)
                    suggestions.append(QuerySuggestion(
                        suggestion_type="template",
                        text=template["example"],
                        confidence=confidence,
                        explanation=f"Similar to: {template['pattern']}",
                        example_sql=template.get("sql_template")
                    ))
        
        return suggestions
    
    def _get_similar_historical_queries(self, user_query: str) -> List[QuerySuggestion]:
        """Find similar queries from cache history."""
        suggestions = []
        
        if not self.cache_manager:
            return suggestions
        
        # Get popular queries from cache
        popular_queries = self.cache_manager.get_popular_queries(limit=20)
        
        # Calculate similarity
        for cached_query in popular_queries:
            similarity = self._calculate_similarity(user_query, cached_query["query"])
            if similarity > 0.6:  # Threshold for similarity
                suggestions.append(QuerySuggestion(
                    suggestion_type="similar",
                    text=cached_query["query"],
                    confidence=similarity,
                    explanation=f"Similar query (used {cached_query['hit_count']} times)",
                    example_sql=cached_query.get("sql")
                ))
        
        return suggestions
    
    def _get_refinement_suggestions(
        self, 
        user_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[QuerySuggestion]:
        """Suggest query refinements based on context."""
        suggestions = []
        query_lower = user_query.lower()
        
        # Add time refinements if missing
        if not any(time in query_lower for time in self.time_keywords):
            time_refinements = [
                f"{user_query} for last month",
                f"{user_query} for this year",
                f"{user_query} for last 30 days"
            ]
            for refinement in time_refinements[:2]:
                suggestions.append(QuerySuggestion(
                    suggestion_type="refinement",
                    text=refinement,
                    confidence=0.6,
                    explanation="Add time context for more specific results"
                ))
        
        # Add limit if showing lists
        if any(word in query_lower for word in ["all", "list", "show"]) and "limit" not in query_lower:
            suggestions.append(QuerySuggestion(
                suggestion_type="refinement",
                text=f"{user_query} (limit 100)",
                confidence=0.7,
                explanation="Limit results for better performance"
            ))
        
        return suggestions
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        # Simple word-based similarity
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Jaccard similarity
        jaccard = len(intersection) / len(union)
        
        # Also consider sequence similarity
        sequence_similarity = difflib.SequenceMatcher(None, query1.lower(), query2.lower()).ratio()
        
        # Weighted average
        return 0.7 * jaccard + 0.3 * sequence_similarity
    
    def _deduplicate_suggestions(self, suggestions: List[QuerySuggestion]) -> List[QuerySuggestion]:
        """Remove duplicate or very similar suggestions."""
        unique_suggestions = []
        seen_texts = set()
        
        for suggestion in suggestions:
            # Check if we've seen a very similar suggestion
            is_duplicate = False
            for seen in seen_texts:
                if self._calculate_similarity(suggestion.text, seen) > 0.9:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_suggestions.append(suggestion)
                seen_texts.add(suggestion.text)
        
        return unique_suggestions
    
    def explain_query(self, sql: str, user_query: str) -> Dict[str, Any]:
        """Generate a natural language explanation of the generated SQL."""
        explanation_parts = []
        
        sql_upper = sql.upper()
        
        # Explain what the query does
        if "SELECT" in sql_upper:
            # Extract selected columns
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_upper, re.DOTALL)
            if select_match:
                columns = select_match.group(1)
                if "*" in columns:
                    explanation_parts.append("This query retrieves all columns")
                else:
                    explanation_parts.append(f"This query retrieves: {columns.lower()}")
        
        # Explain data source
        from_match = re.search(r'FROM\s+([^\s]+)', sql_upper)
        if from_match:
            table = from_match.group(1)
            explanation_parts.append(f"from the {table.lower()} table")
        
        # Explain filters
        if "WHERE" in sql_upper:
            explanation_parts.append("with specific filters applied")
        
        # Explain grouping
        if "GROUP BY" in sql_upper:
            explanation_parts.append("grouped by certain dimensions")
        
        # Explain ordering
        if "ORDER BY" in sql_upper:
            desc_match = re.search(r'ORDER BY.*DESC', sql_upper)
            if desc_match:
                explanation_parts.append("sorted in descending order")
            else:
                explanation_parts.append("sorted in ascending order")
        
        # Explain limits
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            limit = limit_match.group(1)
            explanation_parts.append(f"limited to {limit} results")
        
        return {
            "summary": " ".join(explanation_parts),
            "original_question": user_query,
            "query_type": self._identify_query_type(sql),
            "complexity": self._assess_complexity(sql)
        }
    
    def _identify_query_type(self, sql: str) -> str:
        """Identify the type of query."""
        sql_upper = sql.upper()
        
        if "GROUP BY" in sql_upper and any(agg in sql_upper for agg in ["SUM", "COUNT", "AVG", "MAX", "MIN"]):
            return "aggregation"
        elif "ORDER BY" in sql_upper and "LIMIT" in sql_upper:
            return "ranking"
        elif "JOIN" in sql_upper:
            return "join"
        elif "WHERE" in sql_upper:
            return "filtered_selection"
        else:
            return "simple_selection"
    
    def _assess_complexity(self, sql: str) -> str:
        """Assess query complexity."""
        sql_upper = sql.upper()
        complexity_score = 0
        
        # Check for various SQL features
        if "JOIN" in sql_upper:
            complexity_score += 2
        if "GROUP BY" in sql_upper:
            complexity_score += 1
        if "HAVING" in sql_upper:
            complexity_score += 2
        if "UNION" in sql_upper:
            complexity_score += 3
        if sql_upper.count("SELECT") > 1:  # Subqueries
            complexity_score += 2
        
        if complexity_score == 0:
            return "simple"
        elif complexity_score <= 2:
            return "moderate"
        else:
            return "complex"