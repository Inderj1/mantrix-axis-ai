"""
Results Formatter Agent

This agent specializes in formatting query results into various presentation formats
for better visualization and understanding.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import json
from .base import MantraxAgent


class ResultsFormatterAgent(MantraxAgent):
    """Agent that formats query results into various presentation formats."""

    def __init__(self):
        super().__init__(
            name="ResultsFormatter",
            description="Formats query results into various presentation formats with insights",
            model="gpt-4-turbo-preview"
        )
        # Store the current system prompt (can be updated with persona context)
        self._current_system_prompt = None
        # Backend chart intelligence (set by format_results)
        self._current_backend_chart_recommendation = None
        self._chart_recommendations = []
        self._dimensions = []
        self._measures = []
        self._time_columns = []
    
    def get_system_prompt(self, user_context: str = "") -> str:
        # If a current prompt was set (with persona context), return that
        if self._current_system_prompt:
            return self._current_system_prompt

        base_prompt = """You are a DATA ANALYST. Your ONLY job is to extract insights from the ACTUAL DATA provided to you.

🎯 YOUR PROCESS (FOLLOW EXACTLY):

STEP 1: ANALYZE THE DATA
━━━━━━━━━━━━━━━━━━━━━━━━━
- Read every row of the actual results provided
- Calculate totals, averages, mins, maxs from the DATA
- Identify the top performers BY NAME with EXACT VALUES
- Identify the bottom performers BY NAME with EXACT VALUES
- Find outliers and anomalies IN THE ACTUAL DATA
- Compare values within the dataset (not external assumptions)

STEP 2: EXTRACT PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━
What does THIS DATA actually show?
- Which items/customers/products have highest values?
- Which have lowest values?
- What's the spread (min to max)?
- Are there any surprising numbers?
- What relationships exist in the data?

STEP 3: PROJECT FINDINGS (PERSONA-FILTERED)
━━━━━━━━━━━━━━━━━━━━━━━━━
Based ONLY on what the data shows:
- State what you observed (with exact numbers)
- Explain what it means through the persona lens
- Suggest actions based on data patterns (not generic advice)

🚫 FORBIDDEN:
- Making up recommendations not supported by the data
- Generic advice like "optimize pricing" without citing specific prices
- Suggesting actions without data-based impact estimates
- Using phrases like "consider" or "monitor" without specifics

✅ REQUIRED FORMAT FOR EVERY INSIGHT:

**[Actual Item Name from Data]: [Exact Value] at [Key Metric]**

Data: [Quote exact values from the dataset - use the actual names you see in the rows]
Pattern: [What this specific data shows - compare actual items in the dataset]
Impact: [Calculate using the actual numbers - show your arithmetic]
Action: [Based on the actual data patterns - cite specific items by their real names]

⚠️ CRITICAL: Use ONLY the actual item names, customer names, product names from the data rows.
DO NOT use placeholder names. DO NOT make up examples. CITE THE ACTUAL DATA.

📊 CHART SELECTION (DO NOT default to bar - analyze the data first!):
REQUIRED: Before choosing a chart type, analyze these data characteristics:
1. Row count: 1 row = metric/gauge, 2-6 rows = pie/donut, 7+ rows = bar/line
2. Column types: Has date/time column? → USE line or area (NOT bar)
3. Value range: Single aggregated value? → USE metric (NOT bar)
4. Categories: ≤6 distinct values? → USE pie or donut (NOT bar)
5. Hierarchy: Parent-child relationship? → USE treemap or sunburst

CHART PRIORITY (check in this order):
- 1 row, 1 numeric value → metric (NEVER bar for single values!)
- Has date/month/year/quarter column → line or area (time series)
- 2-6 categories with values → pie or donut (proportions)
- Parent-child/nested data → treemap or sunburst
- Two numeric columns → scatter (correlation)
- Row × column matrix → heatmap
- Stage/funnel data → funnel
- Long category names (>15 chars) → horizontalBar
- ONLY use bar for 7+ categorical comparisons with no time dimension"""

        if user_context:
            return base_prompt + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n" + user_context
        return base_prompt
    
    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_summary_card",
                    "description": "Create a summary card with key metrics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "metrics": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "value": {"type": "string"},
                                        "change": {"type": "string"},
                                        "trend": {"type": "string", "enum": ["up", "down", "stable"]}
                                    }
                                }
                            },
                            "insight": {"type": "string"}
                        },
                        "required": ["title", "metrics"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_data_table",
                    "description": "Create a formatted data table with sorting and grouping",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "key": {"type": "string"},
                                        "label": {"type": "string"},
                                        "type": {"type": "string", "enum": ["text", "number", "currency", "percentage", "date"]},
                                        "align": {"type": "string", "enum": ["left", "center", "right"]}
                                    }
                                }
                            },
                            "data": {"type": "string", "description": "JSON string of the data array"},
                            "groupBy": {"type": "string"},
                            "sortBy": {"type": "string"},
                            "highlights": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "condition": {"type": "string"},
                                        "style": {"type": "string"}
                                    }
                                }
                            }
                        },
                        "required": ["title", "columns", "data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_chart_config",
                    "description": "Create configuration for charts and visualizations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "bar", "horizontalBar", "pictorialBar",
                                    "line", "area", "themeRiver", "calendar",
                                    "pie", "donut", "treemap", "sunburst",
                                    "scatter", "heatmap", "boxplot",
                                    "funnel", "sankey", "graph",
                                    "gauge", "metric",
                                    "radar", "parallel",
                                    "candlestick"
                                ],
                                "description": "Chart type - bar/horizontalBar for comparisons, line/area for time series, pie/donut/treemap/sunburst for part-to-whole, scatter/heatmap/boxplot for distributions, funnel/sankey/graph for flows, gauge/metric for KPIs, radar/parallel for multi-dimensional, candlestick for financial"
                            },
                            "title": {"type": "string"},
                            "data": {"type": "string", "description": "JSON string of the data array"},
                            "xAxis": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "label": {"type": "string"}
                                }
                            },
                            "yAxis": {
                                "type": "object",
                                "properties": {
                                    "key": {"type": "string"},
                                    "label": {"type": "string"}
                                }
                            },
                            "series": {"type": "string", "description": "JSON string of the series array"},
                            "colors": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["type", "title", "data"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_insight_cards",
                    "description": "Create insight cards with findings and recommendations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "insights": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["finding", "trend", "anomaly", "recommendation"]},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "impact": {"type": "string", "enum": ["high", "medium", "low"]},
                                        "actions": {"type": "array", "items": {"type": "string"}}
                                    }
                                }
                            }
                        },
                        "required": ["insights"]
                    }
                }
            }
        ]
    
    def format_results(self,
                      query: str,
                      sql: str,
                      results: List[Dict[str, Any]],
                      metadata: Optional[Dict[str, Any]] = None,
                      user_id: Optional[str] = None,
                      recommended_chart_type: Optional[str] = None,
                      chart_config: Optional[Dict[str, Any]] = None,
                      chart_recommendations: Optional[List[str]] = None,
                      dimensions: Optional[List[str]] = None,
                      measures: Optional[List[str]] = None,
                      time_columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Format query results into a structured presentation.

        Args:
            query: Original user query
            sql: Executed SQL query
            results: Raw query results
            metadata: Optional metadata about the query
            user_id: Optional user ID for personalized insights
            recommended_chart_type: LLM's primary chart type recommendation (highest priority)
            chart_config: LLM's chart axis configuration hints
            chart_recommendations: Backend's deterministic chart type recommendations (fallback)
            dimensions: Identified dimension columns (categorical)
            measures: Identified measure columns (numeric)
            time_columns: Identified time/date columns

        Returns:
            Formatted presentation structure
        """
        # LLM recommendation takes priority over column-based analysis
        # Priority: recommended_chart_type (LLM) > chart_recommendations[0] (column analysis)
        if recommended_chart_type:
            self._current_backend_chart_recommendation = recommended_chart_type
            logger.info(f"Using LLM recommended chart type: {recommended_chart_type}")
        else:
            self._current_backend_chart_recommendation = chart_recommendations[0] if chart_recommendations else None

        # Store chart config for axis hints
        self._chart_config = chart_config or {}
        self._chart_recommendations = chart_recommendations or []
        self._dimensions = dimensions or []
        self._measures = measures or []
        self._time_columns = time_columns or []
        # Get user personalization context if user_id provided
        user_context = ""
        user_role_name = ""
        if user_id:
            from ...core.user_profile_manager import user_profile_manager
            context = user_profile_manager.get_personalization_context(user_id)
            if context and 'system_prompt_additions' in context:
                user_context = context['system_prompt_additions']
                user_role_name = context.get('role_display_name', '')
                logger.info(f"Using persona context for user {user_id}: role={user_role_name}")

        # Update system prompt with user context and store it
        if user_context:
            self._current_system_prompt = self.get_system_prompt(user_context)
            logger.info(f"System prompt updated with {user_role_name} persona context")
        else:
            # Reset to base prompt if no persona
            self._current_system_prompt = None

        # If OpenAI is not available, provide basic formatting
        if not self.client:
            return self._basic_format_results(query, sql, results, metadata)
        
        input_data = {
            "query": query,
            "sql": sql,
            "results": results,
            "row_count": len(results),
            "columns": list(results[0].keys()) if results else [],
            "metadata": metadata or {}
        }
        
        # Add data statistics
        if results:
            df = pd.DataFrame(results)
            
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            
            # Calculate statistics for numeric columns
            stats = {}
            for col in numeric_cols:
                stats[col] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": float(df[col].mean()),
                    "median": float(df[col].median()),
                    "std": float(df[col].std())
                }
            
            input_data["statistics"] = stats
            
            # Detect data types
            data_types = {}
            for col in df.columns:
                dtype = str(df[col].dtype)
                if 'int' in dtype or 'float' in dtype:
                    data_types[col] = 'numeric'
                elif 'datetime' in dtype:
                    data_types[col] = 'datetime'
                else:
                    data_types[col] = 'text'
            
            input_data["data_types"] = data_types
        
        # Execute the agent
        try:
            result = self.execute(input_data)

            # Process the response to ensure it's properly formatted
            if result.get("status") == "success":
                formatted_result = self._process_formatting_response(result)
                return formatted_result
            else:
                # If execution failed, fall back to basic formatting
                return self._basic_format_results(query, sql, results, metadata)
        except Exception as e:
            # On any error, fall back to basic formatting
            return self._basic_format_results(query, sql, results, metadata)
    
    def _process_formatting_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the agent response into a standardized format."""
        content = response.get("content", "") or "Results formatted successfully."
        tool_calls = response.get("tool_calls", [])

        # Build the formatted result
        formatted = {
            "summary": content,
            "components": []
        }

        # Process tool calls
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool")
            arguments = tool_call.get("arguments", {})

            component = {
                "type": tool_name.replace("create_", "").replace("_", "-"),
                "data": arguments
            }

            # For chart-config components, add backend recommendation for frontend to use
            if component["type"] == "chart-config":
                if self._current_backend_chart_recommendation:
                    component["data"]["backend_recommended_type"] = self._current_backend_chart_recommendation
                component["data"]["all_recommendations"] = self._chart_recommendations
                # Add LLM axis hints if available
                if hasattr(self, '_chart_config') and self._chart_config:
                    if self._chart_config.get("x_axis_column"):
                        component["data"]["llm_x_axis"] = self._chart_config["x_axis_column"]
                    if self._chart_config.get("y_axis_column"):
                        component["data"]["llm_y_axis"] = self._chart_config["y_axis_column"]
                    if self._chart_config.get("group_by_column"):
                        component["data"]["llm_group_by"] = self._chart_config["group_by_column"]

            formatted["components"].append(component)

        return formatted
    
    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format input data for the agent."""
        # Limit the number of results shown to the agent to avoid token limits
        data_copy = input_data.copy()
        if "results" in data_copy and len(data_copy["results"]) > 10:
            data_copy["results"] = data_copy["results"][:10]
            data_copy["results_truncated"] = True
            data_copy["total_results"] = input_data["row_count"]

        # Build a more detailed analysis prompt
        stats = input_data.get('statistics', {})
        results = data_copy.get('results', [])

        # Extract key insights from the data to guide the LLM
        analysis_guide = self._build_data_analysis_guide(results, stats, input_data.get('columns', []))

        return f"""USER QUESTION: {input_data.get('query', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 THE COMPLETE DATASET ({input_data.get('row_count', 0)} rows)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(results, indent=2, default=str)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 STATISTICAL SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(stats, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR ANALYSIS GUIDE (Use this to build insights)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{analysis_guide}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NOW CREATE YOUR PRESENTATION:

1. SUMMARY CARDS (3-5 cards):
   - Total/aggregate metrics
   - Top performer with exact name/value
   - Bottom performer with exact name/value
   - Key spread/range/variance metric
   - Most surprising finding from the data

2. DATA TABLE:
   - Show ALL rows (or top 10 if >10 rows)
   - Highlight top 3 and bottom 3 performers

3. CHART:
   - Backend analysis recommends: {self._current_backend_chart_recommendation or 'auto (analyze data to determine)'}
   - Use the backend recommendation unless it cannot render this data shape
   - Show distribution or comparison of key metric

4. INSIGHTS (3-7 insights):
   MANDATORY FORMAT FOR EACH:

   **[Specific Item Name]: [Exact Value] at [Key Metric]**

   📊 Data Points:
   • [Item/Customer/Product Name]: [Exact dollar/number] ([% of total])
   • Compared to [comparison item]: [exact delta] ([percentage difference])
   • Range: [min] to [max], [standard deviation or spread]

   🔍 What This Means:
   [Explain the pattern - why is this significant? What stands out?]

   💰 Impact Calculation:
   [Show the math - if we do X, impact = Y]
   [Use actual numbers from the data to calculate potential impact]

   ✅ Specific Action:
   [Exactly what to do - with numbers, names, timelines]
   [Expected outcome with calculated impact]

QUALITY CHECKLIST - Every insight MUST have:
✓ Specific name of item/customer/product from the ACTUAL DATA ROWS above
✓ Exact dollar amount or number FROM THE DATA (not rounded generically)
✓ Percentage or comparison to total/average CALCULATED FROM THE DATA
✓ At least 2 data points cited FROM THE ACTUAL ROWS
✓ Calculated impact using THE NUMBERS ABOVE (show your math)
✓ Specific action with quantified expected outcome BASED ON THE DATA

🚨 ABSOLUTE RULE: Every single name, number, and insight MUST come from the dataset above.
If you reference an item/customer/product, it MUST exist in the actual rows.
If you cite a number, it MUST be in the data or calculated from the data.

DO NOT:
❌ Use example names like "Product A" or "Customer X"
❌ Make up product categories not in the data
❌ Invent numbers not present in the dataset
❌ Reference items that don't exist in the actual rows

Use the tools now to build this presentation using ONLY the actual data."""
    
    def _build_data_analysis_guide(self, results: List[Dict[str, Any]], stats: Dict[str, Any], columns: List[str]) -> str:
        """Pre-analyze the ACTUAL data and provide specific guidance to the LLM."""
        if not results:
            return "No data to analyze."

        guide_parts = []

        # Identify numeric columns with stats
        numeric_cols = list(stats.keys()) if stats else []

        # Auto-detect identifier column (first text column that's not a numeric stat)
        identifier_col = None
        if results:
            for col_name in results[0].keys():
                if col_name not in numeric_cols:
                    identifier_col = col_name
                    break

        guide_parts.append(f"Analyzing {len(results)} rows of data")
        if identifier_col:
            guide_parts.append(f"Items identified by: {identifier_col}")

        # Build guide for each numeric column
        for col in numeric_cols:
            col_stats = stats[col]
            guide_parts.append(f"\n📊 Analysis of {col}:")

            # Calculate total
            total = sum(float(r.get(col, 0) or 0) for r in results)
            guide_parts.append(f"   • Total: ${total:,.2f}")
            guide_parts.append(f"   • Range: ${col_stats['min']:,.2f} to ${col_stats['max']:,.2f}")
            guide_parts.append(f"   • Average: ${col_stats['mean']:,.2f}")

            spread_pct = ((col_stats['max'] - col_stats['min']) / col_stats['mean'] * 100) if col_stats['mean'] > 0 else 0
            guide_parts.append(f"   • Spread: ${col_stats['max'] - col_stats['min']:,.2f} ({spread_pct:.1f}% of avg)")

            # Find top and bottom performers for this column
            sorted_results = sorted(results, key=lambda x: float(x.get(col, 0) or 0), reverse=True)

            if len(sorted_results) >= 3:
                guide_parts.append(f"\n   TOP 3 {col}:")
                for i, row in enumerate(sorted_results[:3], 1):
                    # Get the actual identifier value from the data
                    if identifier_col and identifier_col in row:
                        identifier = str(row[identifier_col])
                    else:
                        # Show all non-numeric values from the row
                        identifier = ", ".join([f"{k}={v}" for k, v in row.items() if k not in numeric_cols][:2])

                    value = float(row.get(col, 0) or 0)
                    pct_of_total = (value / total * 100) if total > 0 else 0
                    guide_parts.append(f"      {i}. {identifier}: ${value:,.2f} ({pct_of_total:.1f}% of total)")

                guide_parts.append(f"\n   BOTTOM 3 {col}:")
                for i, row in enumerate(sorted_results[-3:][::-1], 1):
                    if identifier_col and identifier_col in row:
                        identifier = str(row[identifier_col])
                    else:
                        identifier = ", ".join([f"{k}={v}" for k, v in row.items() if k not in numeric_cols][:2])

                    value = float(row.get(col, 0) or 0)
                    pct_of_total = (value / total * 100) if total > 0 else 0
                    guide_parts.append(f"      {i}. {identifier}: ${value:,.2f} ({pct_of_total:.1f}% of total)")

        # Add concentration analysis using actual data
        if numeric_cols and results and len(results) >= 3:
            main_col = numeric_cols[0]  # Use first numeric column
            sorted_results = sorted(results, key=lambda x: float(x.get(main_col, 0) or 0), reverse=True)
            total = sum(float(r.get(main_col, 0) or 0) for r in results)

            if total > 0:
                top3_sum = sum(float(r.get(main_col, 0) or 0) for r in sorted_results[:3])
                top3_pct = (top3_sum / total) * 100

                guide_parts.append(f"\n🎯 KEY FINDINGS:")
                guide_parts.append(f"   • Top 3 items = {top3_pct:.1f}% of total {main_col}")

                if len(sorted_results) > 0:
                    top_item_name = ""
                    if identifier_col and identifier_col in sorted_results[0]:
                        top_item_name = str(sorted_results[0][identifier_col])
                    else:
                        top_item_name = "Item 1"

                    bottom_item_name = ""
                    if identifier_col and identifier_col in sorted_results[-1]:
                        bottom_item_name = str(sorted_results[-1][identifier_col])
                    else:
                        bottom_item_name = "Last item"

                    top_val = float(sorted_results[0].get(main_col, 0) or 0)
                    bottom_val = float(sorted_results[-1].get(main_col, 0) or 0)

                    if bottom_val > 0:
                        gap_multiple = top_val / bottom_val
                        guide_parts.append(f"   • Gap: {top_item_name} (${top_val:,.2f}) is {gap_multiple:.1f}x higher than {bottom_item_name} (${bottom_val:,.2f})")

        guide_parts.append("\n💡 USE THESE ACTUAL VALUES IN YOUR INSIGHTS - Don't make up numbers!")

        return "\n".join(guide_parts)

    def _basic_format_results(self, query: str, sql: str, results: List[Dict[str, Any]],
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Provide basic formatting when OpenAI is not available."""
        if not results:
            return {
                "summary": "Query executed successfully but returned no results.",
                "components": []
            }
        
        # Create basic summary
        summary = f"Query returned {len(results)} rows with {len(results[0].keys())} columns."
        
        # Create basic table component
        columns = []
        for key in results[0].keys():
            col_type = "text"
            if isinstance(results[0].get(key), (int, float)):
                col_type = "number"
            columns.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "type": col_type,
                "align": "right" if col_type == "number" else "left"
            })
        
        components = [{
            "type": "data-table",
            "data": {
                "title": "Query Results",
                "columns": columns,
                "data": results[:100]  # Limit to first 100 rows
            }
        }]
        
        # Add basic metrics for numeric columns
        numeric_cols = [col["key"] for col in columns if col["type"] == "number"]
        if numeric_cols:
            metrics = []
            for col in numeric_cols[:4]:  # Show up to 4 metrics
                values = [float(row[col]) for row in results if row.get(col) is not None]
                if values:
                    metrics.append({
                        "label": col.replace("_", " ").title(),
                        "value": f"{sum(values):,.2f}",
                        "change": f"Avg: {sum(values)/len(values):,.2f}",
                        "trend": "stable"
                    })
            
            if metrics:
                components.insert(0, {
                    "type": "summary-card",
                    "data": {
                        "title": "Key Metrics",
                        "metrics": metrics,
                        "insight": "Basic statistical summary of numeric columns."
                    }
                })
        
        return {
            "summary": summary,
            "components": components
        }