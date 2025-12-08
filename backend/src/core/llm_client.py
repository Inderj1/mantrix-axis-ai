from typing import List, Dict, Any, Optional, Tuple
import anthropic
from anthropic import Anthropic
from openai import OpenAI
import structlog
import json
import time
from pathlib import Path
from src.config import settings
from src.core.error_handler import QueryErrorHandler, ErrorType
from src.core.schema_aware_generator import SchemaAwareGenerator
from src.core.gross_margin_examples import GROSS_MARGIN_EXAMPLES, COPA_GROSS_MARGIN_RULES
from src.core.financial_analysis_queries import FINANCIAL_ANALYSIS_QUERIES

logger = structlog.get_logger()


class LLMClient:
    def __init__(self, use_openai=False):
        """
        Initialize LLM Client with either OpenAI or Anthropic

        Args:
            use_openai: If True, use OpenAI GPT-4o. If False, use Anthropic Claude.
        """
        self.use_openai = use_openai

        if use_openai:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = "gpt-4o"
            logger.info(f"LLMClient initialized with OpenAI model: {self.model}")
        else:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            self.model = settings.anthropic_model
            logger.info(f"LLMClient initialized with Anthropic model: {self.model}")

        self.error_handler = QueryErrorHandler(llm_client=self)
        self.max_retries = 3
        self.retry_delay = 1.0  # Base delay in seconds
        self.schema_aware = SchemaAwareGenerator()
        
        # Few-shot examples for better SQL generation
        self.few_shot_examples = [
            {
                "question": "Show me total sales by month for last year",
                "sql": """SELECT 
  FORMAT_DATE('%Y-%m', order_date) as month,
  SUM(total_amount) as total_sales
FROM `{project}.{dataset}.sales`
WHERE DATE(order_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)
GROUP BY month
ORDER BY month"""
            },
            {
                "question": "What are the top 10 customers by revenue?",
                "sql": """SELECT 
  customer_id,
  customer_name,
  SUM(revenue) as total_revenue
FROM `{project}.{dataset}.customers`
GROUP BY customer_id, customer_name
ORDER BY total_revenue DESC
LIMIT 10"""
            },
            {
                "question": "Show me top 5 GL accounts by total amount",
                "sql": """SELECT 
  GL_Account,
  GL_Account_Description,
  SUM(GL_Amount_in_CC) as total_amount
FROM `{project}.{dataset}.table_name`
WHERE GL_Account IS NOT NULL 
  AND GL_Amount_in_CC IS NOT NULL
GROUP BY GL_Account, GL_Account_Description
ORDER BY total_amount DESC
LIMIT 5"""
            },
            {
                "question": "Show products with low inventory",
                "sql": """SELECT 
  product_id,
  product_name,
  current_inventory,
  reorder_level
FROM `{project}.{dataset}.inventory`
WHERE current_inventory < reorder_level
ORDER BY current_inventory ASC"""
            }
        ]
    
    def generate_sql(
        self,
        user_query: str,
        table_schemas: List[Dict[str, Any]],
        examples: Optional[List[Dict[str, str]]] = None,
        retry_count: int = 0,
        financial_context: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        join_hints: Optional[List[Dict[str, Any]]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        column_mappings: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        database_type: str = 'bigquery',
        database_name: str = 'BigQuery',
        dialect_guide: str = '',
        database_config: Optional[Dict[str, Any]] = None,
        persona_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate SQL query from natural language using table schemas."""
        logger.info(f"=== Starting SQL generation ===")
        logger.info(f"User query: {user_query}")
        logger.info(f"Table schemas type: {type(table_schemas)}")
        logger.info(f"Table schemas count: {len(table_schemas) if table_schemas else 0}")
        if table_schemas:
            logger.info(f"First table schema type: {type(table_schemas[0]) if table_schemas else 'N/A'}")
            if table_schemas and isinstance(table_schemas[0], dict):
                logger.info(f"First table name: {table_schemas[0].get('table_name', 'NO TABLE NAME')}")
        logger.info(f"Financial context type: {type(financial_context)}")
        logger.info(f"Business context type: {type(business_context)}")
        logger.info(f"Conversation context: {bool(conversation_context)}")
        if conversation_context:
            logger.info(f"Follow-up type: {conversation_context.get('follow_up_type', 'unknown')}")

        try:
            logger.info("Building system prompt...")
            system_prompt = self._build_system_prompt(
                financial_context,
                database_config=database_config,
                persona_context=persona_context
            )
            logger.info(f"System prompt built successfully (project={database_config.get('project_id') if database_config else 'default'}, persona={persona_context.get('role_display_name') if persona_context else 'default'})")

            # Use provided examples or default few-shot examples
            logger.info("Getting relevant examples...")
            effective_examples = examples if examples else self._get_relevant_examples(user_query, financial_context)
            logger.info(f"Got {len(effective_examples) if effective_examples else 0} examples")

            logger.info(f"Building user prompt for {database_name} (dialect: {database_type})...")
            user_prompt = self._build_user_prompt(
                user_query,
                table_schemas,
                effective_examples,
                financial_context,
                business_context,
                join_hints,
                conversation_context,
                database_type=database_type,
                database_name=database_name,
                dialect_guide=dialect_guide
            )
            logger.info("User prompt built successfully")
            if join_hints:
                logger.info(f"JOIN hints included in prompt: {len(join_hints)} relationships")
            
            logger.info(f"Generating SQL for query: {user_query[:100]}...", retry_count=retry_count)
            
            # Define the tool for structured output
            sql_generation_tool = {
                "name": "generate_sql_query",
                "description": "Generate a SQL query with metadata and visualization recommendation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The generated BigQuery SQL query"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "A helpful, conversational explanation addressed to the user. Write like a friendly advisor: Start with what you found or analyzed (e.g., 'I analyzed your customer data...', 'Here are your top performers...', 'Based on your question...'). Explain key insights in plain language without mentioning technical details like table names, SQL, or database specifics. Focus on the business meaning and what the user should know."
                        },
                        "tables_used": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of table names referenced in the query"
                        },
                        "estimated_complexity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Estimated query complexity"
                        },
                        "optimization_notes": {
                            "type": "string",
                            "description": "Any performance considerations or optimizations applied"
                        },
                        "recommended_chart_type": {
                            "type": "string",
                            "enum": [
                                "bar", "horizontalBar", "line", "area", "pie", "donut",
                                "scatter", "heatmap", "treemap", "sunburst", "funnel",
                                "gauge", "metric", "radar", "table", "calendar",
                                "sankey", "boxplot", "candlestick"
                            ],
                            "description": """Best chart type for visualizing this query's results. Selection guide:
- metric: Single aggregate value (COUNT, SUM, AVG) - shows one big number
- gauge: Single percentage or rate (0-100 scale)
- line: Time series data with dates/months/years - shows trends over time
- area: Time series with emphasis on cumulative values
- bar: Comparing 7+ categories (vertical bars)
- horizontalBar: Categories with long names or 10+ items
- pie: 2-6 categories showing proportions/distribution (parts of whole)
- donut: 7-12 categories showing proportions (like pie but with center space)
- scatter: Correlation between two numeric measures
- heatmap: Matrix/cross-tab data (two dimensions + one measure)
- treemap: Hierarchical data or many categories with size comparison
- sunburst: Nested hierarchical data (parent-child relationships)
- funnel: Sequential stages with decreasing values (sales pipeline, conversion)
- radar: Comparing multiple metrics across categories
- table: Complex data with many columns, or when exact values matter
- calendar: Daily data over months/years (activity heatmap)
- sankey: Flow/transition data between states
- boxplot: Statistical distribution comparison
- candlestick: Financial OHLC (open, high, low, close) data"""
                        },
                        "chart_config": {
                            "type": "object",
                            "description": "Optional chart configuration hints",
                            "properties": {
                                "x_axis_column": {
                                    "type": "string",
                                    "description": "Column name for x-axis (categories/time)"
                                },
                                "y_axis_column": {
                                    "type": "string",
                                    "description": "Column name for y-axis (values/measures)"
                                },
                                "group_by_column": {
                                    "type": "string",
                                    "description": "Column for grouping/coloring series (optional)"
                                }
                            }
                        }
                    },
                    "required": ["sql", "explanation", "tables_used", "estimated_complexity", "recommended_chart_type"]
                }
            }
            
            if self.use_openai:
                # OpenAI format - use function calling
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    functions=[{
                        "name": "generate_sql_query",
                        "description": "Generate a SQL query based on natural language",
                        "parameters": sql_generation_tool["input_schema"]
                    }],
                    function_call={"name": "generate_sql_query"},
                    temperature=0,
                    max_tokens=2000
                )

                # Extract function call response
                if response.choices[0].message.function_call:
                    raw_result = json.loads(response.choices[0].message.function_call.arguments)
                    logger.info(f"OpenAI function call result: {repr(raw_result)}")
                else:
                    raise ValueError("No function call in OpenAI response")
            else:
                # Anthropic format - use tools
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt + "\n\nPlease use the generate_sql_query tool to provide your response."}
                    ],
                    tools=[sql_generation_tool],
                    tool_choice={"type": "tool", "name": "generate_sql_query"}
                )

                # Debug logging for response structure
                logger.info(f"Response type: {type(response)}")
                logger.info(f"Response content type: {type(response.content)}")
                logger.info(f"Response content length: {len(response.content) if response.content else 'None'}")
                if response.content:
                    for i, content in enumerate(response.content):
                        logger.info(f"Content[{i}] type: {type(content)}, content type: {getattr(content, 'type', 'no type attr')}")
                        if hasattr(content, 'type') and content.type == "tool_use":
                            logger.info(f"Tool use name: {getattr(content, 'name', 'no name')}")
                            logger.info(f"Tool use input type: {type(getattr(content, 'input', 'no input'))}")
                            logger.info(f"Tool use input: {repr(getattr(content, 'input', 'no input'))}")

                # Extract the tool use response
                tool_use = None
                for content in response.content:
                    if content.type == "tool_use" and content.name == "generate_sql_query":
                        tool_use = content
                        break

                if tool_use and hasattr(tool_use, 'input'):
                    raw_result = tool_use.input
                    logger.info(f"Tool use raw result type: {type(raw_result)}")
                    logger.info(f"Tool use raw result content: {repr(raw_result)}")
                else:
                    raise ValueError("No tool use in Anthropic response")

            # Handle different response formats (common for both providers)
            if isinstance(raw_result, dict):
                result = raw_result
                logger.info("Tool returned dict - using directly")

                # Normalize tables_used if it's a string (Claude 3 Opus compatibility)
                if "tables_used" in result and isinstance(result["tables_used"], str):
                    logger.info(f"Normalizing tables_used from string to list: {result['tables_used']}")
                    tables_str = result["tables_used"]
                    # Split by newlines and remove markdown bullet points
                    tables_list = []
                    for line in tables_str.split('\n'):
                        line = line.strip()
                        if line:
                            # Remove markdown bullet points (-, *, etc.)
                            line = line.lstrip('-*• ').strip()
                            if line:
                                tables_list.append(line)
                    result["tables_used"] = tables_list
                    logger.info(f"Normalized tables_used to: {result['tables_used']}")

            elif isinstance(raw_result, str):
                logger.warning("Tool returned string - attempting JSON parse")
                try:
                    result = json.loads(raw_result)
                    logger.info("Successfully parsed JSON from string response")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from tool response: {e}")
                    # Fallback to text parsing
                    result = self._parse_llm_response(raw_result)
            else:
                logger.error(f"Unexpected tool response type: {type(raw_result)}")
                result = {
                    "sql": str(raw_result) if raw_result else "",
                    "explanation": "Generated SQL query",
                    "tables_used": [],
                    "estimated_complexity": "medium",
                    "optimization_notes": ""
                }

            # Final safety check - ensure result is a dict
            if not isinstance(result, dict):
                logger.error(f"Result is still not a dict after processing: {type(result)}")
                result = {
                    "sql": str(result) if result else "",
                    "explanation": "Generated SQL query",
                    "tables_used": [],
                    "estimated_complexity": "medium",
                    "optimization_notes": ""
                }

            logger.info("SQL generation completed successfully")
            # Add confidence score based on complexity
            result["confidence_score"] = self._calculate_confidence(result, table_schemas)
            return result

        except anthropic.RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}")
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (2 ** retry_count))  # Exponential backoff
                return self.generate_sql(user_query, table_schemas, examples, retry_count + 1)
            else:
                error_result = self.error_handler.handle_error(
                    e,
                    {"user_query": user_query, "tables_used": [s["table_name"] for s in table_schemas] if table_schemas and isinstance(table_schemas[0], dict) else []},
                    retry_count
                )
                error_result["sql"] = None
                return error_result
                
        except anthropic.APIError as e:
            logger.error(f"API error: {e}")
            if retry_count < self.max_retries and "timeout" in str(e).lower():
                time.sleep(self.retry_delay)
                return self.generate_sql(user_query, table_schemas, examples, retry_count + 1)
            else:
                error_result = self.error_handler.handle_error(
                    e,
                    {"user_query": user_query, "tables_used": [s["table_name"] for s in table_schemas] if table_schemas and isinstance(table_schemas[0], dict) else []},
                    retry_count
                )
                error_result["sql"] = None
                return error_result
                
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            # Safely extract table names
            table_names = []
            if table_schemas and isinstance(table_schemas, list):
                for s in table_schemas:
                    if isinstance(s, dict) and "table_name" in s:
                        table_names.append(s["table_name"])
            
            error_result = self.error_handler.handle_error(
                e,
                {"user_query": user_query, "tables_used": table_names},
                retry_count
            )
            error_result["sql"] = None
            return error_result

    def generate_cross_connector_sql(
        self,
        user_query: str,
        schemas_by_connector: Dict[str, List[Dict[str, Any]]],
        connector_metadata: Dict[str, Dict[str, Any]],
        financial_context: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate SQL for cross-connector queries (multiple databases/projects).

        When user has multiple connectors enabled (e.g., two BigQuery projects, or
        BigQuery + Snowflake), this method generates separate queries for each
        connector and specifies how to join the results.

        Args:
            user_query: Natural language query from user
            schemas_by_connector: Dict mapping connector_id -> list of table schemas
            connector_metadata: Dict mapping connector_id -> {database_type, project, dataset}
            financial_context: Optional financial context
            business_context: Optional business context
            conversation_context: Optional conversation history

        Returns:
            Dict with:
                - requires_cross_connector: bool
                - connector_queries: Dict[connector_id, {sql, tables_used}]
                - join_specification: {type, left_connector_id, right_connector_id, left_key, right_key}
                - explanation: str
        """
        logger.info(
            "=== Starting cross-connector SQL generation ===",
            user_query=user_query[:100],
            connector_count=len(schemas_by_connector),
            connector_ids=list(schemas_by_connector.keys())
        )

        # Build connector-aware prompt
        connector_schemas_text = self._build_connector_schemas_prompt(
            schemas_by_connector, connector_metadata
        )

        # Determine SQL dialects involved
        dialects = set(m.get('database_type', 'bigquery') for m in connector_metadata.values())
        dialect_note = ""
        if len(dialects) > 1:
            dialect_note = f"""
IMPORTANT - Multiple SQL Dialects:
This query spans multiple database types: {', '.join(dialects)}
Each connector_query MUST use the correct SQL dialect for that connector's database type.
- BigQuery: Uses backticks for identifiers, STRUCT types, DATE functions
- Snowflake: Uses double quotes for identifiers, VARIANT for JSON
- PostgreSQL: Standard SQL, uses double quotes for identifiers
"""

        system_prompt = f"""You are an expert SQL query generator that works with MULTIPLE database connectors.

{dialect_note}

CROSS-CONNECTOR QUERY RULES:
1. If the user's question can be answered from a SINGLE connector, set requires_cross_connector=false
2. If data from MULTIPLE connectors is needed, generate SEPARATE queries for each connector
3. Each connector_query must be valid SQL for that connector's database type
4. Specify join_specification ONLY if results need to be joined (not for simple unions)
5. For JOINs, identify the key columns that link data between connectors

AVAILABLE CONNECTORS AND TABLES:
{connector_schemas_text}
"""

        user_prompt = f"""User Question: {user_query}

Analyze this question and determine:
1. Can it be answered from a single connector? If yes, which one?
2. Does it require data from multiple connectors? If yes, how should they be combined?

Use the generate_cross_connector_query tool to provide your response."""

        # Define the cross-connector tool schema
        cross_connector_tool = {
            "name": "generate_cross_connector_query",
            "description": "Generate queries for cross-connector scenarios (multiple databases/projects)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requires_cross_connector": {
                        "type": "boolean",
                        "description": "True if query requires data from multiple connectors"
                    },
                    "single_connector_id": {
                        "type": "string",
                        "description": "If requires_cross_connector=false, the connector_id to use"
                    },
                    "connector_queries": {
                        "type": "object",
                        "description": "SQL query for each connector_id involved",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "sql": {
                                    "type": "string",
                                    "description": "SQL query for this connector (use correct dialect)"
                                },
                                "tables_used": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Tables referenced in this query"
                                },
                                "database_type": {
                                    "type": "string",
                                    "description": "Database type for this connector"
                                }
                            },
                            "required": ["sql", "tables_used", "database_type"]
                        }
                    },
                    "join_specification": {
                        "type": "object",
                        "description": "How to join results from multiple connectors (only if cross-connector JOIN needed)",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["INNER", "LEFT", "RIGHT", "FULL", "UNION", "UNION_ALL"],
                                "description": "Join type"
                            },
                            "left_connector_id": {
                                "type": "string",
                                "description": "Connector ID for left side of join"
                            },
                            "right_connector_id": {
                                "type": "string",
                                "description": "Connector ID for right side of join"
                            },
                            "left_key": {
                                "type": "string",
                                "description": "Column name from left connector for join key"
                            },
                            "right_key": {
                                "type": "string",
                                "description": "Column name from right connector for join key"
                            }
                        }
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Explanation of the query strategy"
                    }
                },
                "required": ["requires_cross_connector", "explanation"]
            }
        }

        try:
            if self.use_openai:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    functions=[{
                        "name": "generate_cross_connector_query",
                        "description": cross_connector_tool["description"],
                        "parameters": cross_connector_tool["input_schema"]
                    }],
                    function_call={"name": "generate_cross_connector_query"},
                    temperature=0,
                    max_tokens=4000
                )
                if response.choices[0].message.function_call:
                    result = json.loads(response.choices[0].message.function_call.arguments)
                else:
                    raise ValueError("No function call in OpenAI response")
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    temperature=0,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    tools=[cross_connector_tool],
                    tool_choice={"type": "tool", "name": "generate_cross_connector_query"}
                )

                tool_use = None
                for content in response.content:
                    if content.type == "tool_use" and content.name == "generate_cross_connector_query":
                        tool_use = content
                        break

                if tool_use and hasattr(tool_use, 'input'):
                    result = tool_use.input
                else:
                    raise ValueError("No tool use in Anthropic response")

            logger.info(
                "Cross-connector SQL generation completed",
                requires_cross_connector=result.get("requires_cross_connector"),
                connector_queries=list(result.get("connector_queries", {}).keys()) if result.get("connector_queries") else []
            )

            return result

        except Exception as e:
            logger.error(f"Failed to generate cross-connector SQL: {e}")
            return {
                "requires_cross_connector": False,
                "error": str(e),
                "explanation": f"Error generating cross-connector query: {e}"
            }

    def _build_connector_schemas_prompt(
        self,
        schemas_by_connector: Dict[str, List[Dict[str, Any]]],
        connector_metadata: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Build prompt with RDF-enriched schema data grouped by connector.

        Enhanced format includes:
        - Business domains from RDF
        - Row count/size hints
        - Column stats (PK/FK, selectivity, indexes)
        - JOIN relationships
        """
        lines = []

        for connector_id, schemas in schemas_by_connector.items():
            meta = connector_metadata.get(connector_id, {})
            db_type = meta.get('database_type', 'unknown')
            project = meta.get('project', '')
            dataset = meta.get('dataset', meta.get('schema', ''))

            # Connector header
            location = f"{project}.{dataset}" if project and dataset else (project or dataset or '')
            header = f"[CONNECTOR: {connector_id} ({db_type}"
            if location:
                header += f" - {location}"
            header += ")]"
            lines.append(header)
            lines.append("")

            # Format each table with RDF data
            for schema in schemas:
                lines.append(self._format_schema_with_rdf(schema))
                lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, financial_context: Optional[Dict[str, Any]] = None,
                             database_config: Optional[Dict[str, Any]] = None,
                             database_type: str = "bigquery",
                             persona_context: Optional[Dict[str, Any]] = None) -> str:
        # Get database type from config, fallback to parameter, then default to bigquery
        db_type = database_config.get('database_type', database_type) if database_config else database_type

        # Database-specific naming
        db_names = {
            "bigquery": "Google BigQuery",
            "snowflake": "Snowflake",
            "postgresql": "PostgreSQL",
            "redshift": "Amazon Redshift",
            "databricks": "Databricks"
        }
        db_name = db_names.get(db_type, db_type.title())

        # Get persona from context, default to Finance Analyst
        if persona_context:
            persona_name = persona_context.get('role_display_name', 'Financial Analyst')
            persona_additions = persona_context.get('system_prompt_additions', '')
        else:
            persona_name = 'Financial Analyst'
            persona_additions = ''

        # Get project/dataset from database_config, fallback to settings
        project_id = database_config.get('project_id', settings.google_cloud_project) if database_config else settings.google_cloud_project
        dataset_id = database_config.get('dataset_id', settings.bigquery_dataset) if database_config else settings.bigquery_dataset

        # Database-specific table qualification rules
        if db_type == "bigquery":
            table_qual_rule = f"ALWAYS qualify table names with backticks: `{project_id}.{dataset_id}.table_name`"
            table_qual_example = f"`{project_id}.{dataset_id}.table`"
        elif db_type == "snowflake":
            table_qual_rule = f"Use three-part names WITHOUT backticks: {project_id}.{dataset_id}.TABLE_NAME (Snowflake is case-insensitive, uppercase is conventional)"
            table_qual_example = f"{project_id}.{dataset_id}.TABLE"
        elif db_type in ("postgresql", "redshift"):
            table_qual_rule = f"Use schema-qualified names: {dataset_id}.table_name"
            table_qual_example = f"{dataset_id}.table"
        elif db_type == "databricks":
            table_qual_rule = f"Use catalog.schema.table format: {project_id}.{dataset_id}.table_name"
            table_qual_example = f"{project_id}.{dataset_id}.table"
        else:
            table_qual_rule = "Use fully-qualified table names appropriate for this database"
            table_qual_example = "database.schema.table"

        base_prompt = f"""You are an expert SQL query generator for {db_name} with the persona of a seasoned {persona_name}.

PERSONA - {persona_name}:
- You have deep expertise in financial analysis, accounting principles, and business metrics
- You understand financial terminology: EBITDA, COGS, gross margin, contribution margin, variance analysis
- You think in terms of P&L statements, balance sheets, and cash flow
- You recognize the importance of period comparisons (YoY, QoQ, MoM) and trend analysis
- You expect data to be formatted for executive presentations (currency with $, percentages with %)
- You approach every query with the mindset: "What financial insight does this reveal?"

GL ACCOUNTING INTELLIGENCE:
You have deep understanding of General Ledger accounting concepts and practices:

1. **Account Structure & Numbering**:
   - GL accounts follow hierarchical numbering (e.g., 4xxxx = Revenue, 5xxxx = COGS, 6xxxx = Operating Expenses)
   - Account ranges define categories: 400000-499999 (Revenue), 500000-599999 (Cost of Sales), 600000-699999 (OpEx)
   - Understand account formats: 'ACA1/41000000' pattern with company code prefix

2. **Debit/Credit Nature**:
   - Revenue accounts (4xxxxx): Credits increase, debits decrease (negative values in reports)
   - Expense/Cost accounts (5xxxxx, 6xxxxx): Debits increase, credits decrease
   - Asset accounts: Debits increase, credits decrease
   - Liability accounts: Credits increase, debits decrease
   - Understand when amounts should be negated for P&L presentation

3. **Financial Statement Mapping**:
   - Income Statement accounts: 4xxxxx (Revenue), 5xxxxx (COGS), 6xxxxx (Operating Expenses)
   - Balance Sheet accounts: 1xxxxx (Assets), 2xxxxx (Liabilities), 3xxxxx (Equity)
   - Cash Flow relevance: Operating, Investing, Financing activities

4. **Period Concepts**:
   - Fiscal periods vs calendar periods
   - Period closing and adjustments
   - Accruals and deferrals
   - Period-to-date (PTD), Quarter-to-date (QTD), Year-to-date (YTD)

5. **Account Groupings**:
   - Understand natural groupings: All revenue accounts roll up to total revenue
   - COGS components: Material costs, labor costs, manufacturing overhead
   - Operating expenses: SG&A (Sales, General & Administrative)
   - Subtotals: Gross Profit, Operating Income, EBITDA, Net Income

6. **Common GL Queries**:
   - "Show revenue" → Query GL accounts 400000-499999, negate if needed for P&L presentation
   - "Break down expenses" → Group by account ranges within 600000-699999
   - "Cost of goods sold" → Sum accounts 500000-599999
   - "Operating profit" → Revenue - COGS - Operating Expenses

7. **Query Interpretation**:
   - "What did we spend on X?" → Look for expense accounts (6xxxxx) with description matching X
   - "Show sales by region" → Revenue accounts (4xxxxx) grouped by region/division
   - "Material costs" → Subset of COGS accounts (typically 500000-529999)
   - "Freight expenses" → Could be in COGS or OpEx, search descriptions

8. **Variance & Analysis**:
   - Understand budget vs actual comparisons
   - Favorable vs unfavorable variances (revenue up = favorable, expenses up = unfavorable)
   - Period-over-period analysis requires consistent account selection

Your task is to convert natural language questions into optimized {db_name} SQL queries that deliver financial insights.

!!!! ABSOLUTELY CRITICAL - REVENUE CALCULATION RULES !!!!
THIS IS THE MOST IMPORTANT RULE - FOLLOW EXACTLY:

For ANY query about revenue, sales, or income:
1. ALWAYS use the Gross_Revenue column: SUM(COALESCE(Gross_Revenue, 0))
2. NEVER use GL_Amount_in_CC for revenue calculations
3. NEVER use "CASE WHEN GL_Amount_in_CC > 0" pattern for revenue
4. NEVER use "SUM(CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END)"

CORRECT revenue query pattern:
  SELECT EXTRACT(YEAR FROM Posting_Date) as year,
         ROUND(SUM(COALESCE(Gross_Revenue, 0)), 2) as total_revenue
  FROM `project.dataset.table`
  WHERE Posting_Date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 YEAR)
  GROUP BY year

INCORRECT patterns (NEVER USE THESE):
  ❌ SUM(CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END)
  ❌ ROUND(SUM(CASE WHEN GL_Amount_in_CC > 0 THEN GL_Amount_in_CC ELSE 0 END), 2)
  ❌ GL_Amount_in_CC > 0 for revenue

Revenue column mapping:
- "revenue", "total revenue", "sales revenue" → SUM(COALESCE(Gross_Revenue, 0))
- "net sales" → SUM(COALESCE(Net_Sales, 0))  
- "gross sales" → SUM(COALESCE(Gross_Sales, 0))

Rules:
1. Generate valid {db_name} SQL syntax
2. {table_qual_rule}
3. IMPORTANT: Use the table's "Qualified Name" shown in the schema below - it contains the correct database-specific format
4. ⚠️ CRITICAL - AVOID UNNECESSARY JOINS & PREFER SINGLE-TABLE QUERIES:
    - FIRST: Check if ALL required columns exist in a SINGLE table - if yes, use ONLY that table (no joins!)
    - If columns exist in multiple tables, prefer the SMALLEST/MOST SPECIFIC table based on row counts in the schema
    - JOINs on large tables (>1M rows) are EXPENSIVE - avoid unless absolutely necessary
    - Before adding a JOIN, ask yourself: "Do I really need data from the second table, or does the first table have everything?"
    - IMPORTANT: Use ONLY tables provided in the schema context below - do NOT reference any tables not explicitly listed
5. Use CTEs for complex queries to improve readability
6. ⚠️ CRITICAL - HANDLING LARGE TABLES (billions of rows):
    - AGGREGATION QUERIES ARE SAFE: SUM(), COUNT(), AVG(), MIN(), MAX() with GROUP BY are efficient on ANY table size - do NOT add LIMIT
    - LIMIT IS ONLY NEEDED FOR: SELECT * or SELECT columns WITHOUT aggregation - add LIMIT 1000 for row-level queries
    - When user asks for "total", "sum", "count", "average" → Use aggregation, NO LIMIT needed
    - When user asks for "list", "show rows", "details" → Add LIMIT for safety
    - The database optimizer handles aggregations efficiently even on billion-row tables
7. Use proper date/timestamp functions for time-based queries
8. Include WHERE clauses when filtering makes sense for the business question
9. Do not include backticks or triple quotes around the SQL - just provide the raw SQL query
10. For better performance, consider using materialized views when available
11. ⚠️ CRITICAL - COLUMN NAME VALIDATION (NEVER GUESS, INVENT, OR HALLUCINATE):
    - **THE SCHEMA BELOW IS THE SINGLE SOURCE OF TRUTH** - No exceptions!
    - ONLY use column names that EXACTLY match character-for-character in the schema below
    - NEVER invent, guess, or assume column names based on SAP naming patterns you see
    - ❌ COMMON MISTAKE: Seeing "DocumentDate_AUDAT" and inventing "SalesDocumentDate_ERDAT"
    - ✅ CORRECT APPROACH: If you need a date column, search the schema for columns containing "Date" or "ERDAT"
    - If a column name has a suffix like _ERDAT or _VBELN, DO NOT assume other columns follow the same pattern
    - DO NOT combine table names with column names (e.g., NO "SalesDocument" + "Date" = "SalesDocumentDate")
    - CHECK EVERY column name against the schema list below before writing it in your SQL
    - If you cannot find an appropriate column in the schema, return an error with "Column not found: [name]" - DO NOT guess
    - Example scenarios:
      * Schema has "CreationDate_ERDAT" → You must use "CreationDate_ERDAT" (NOT "SalesDocumentDate_ERDAT", NOT "DocumentDate_ERDAT")
      * Schema has "OverallProcessingStatus_GBSTA" → You must use "OverallProcessingStatus_GBSTA" (NOT "OverallSDProcessStatus_GBSTK")
      * Schema has "SalesOrderNetValue" → You must use "SalesOrderNetValue" (NOT "NetValue_NETWR")
    - When in doubt, CTRL+F search the schema below for the column - if it's not there, it doesn't exist
12. CRITICAL: Check column data types before applying CAST:
    - DO NOT use CAST on numeric columns (FLOAT64, INT64, NUMERIC) for SUM/AVG operations
    - DO NOT use NULLIF(column, '') on numeric columns - they cannot contain empty strings
    - Only use CAST when converting between incompatible types (e.g., STRING to FLOAT64)
13. IMPORTANT: Window functions (RANK(), ROW_NUMBER(), etc.) cannot be used in WHERE clauses
    - Use a CTE or subquery to filter on window function results
    - For simple "top N" queries, prefer ORDER BY with LIMIT instead of RANK()
14. COPA Schema Revenue and Margin Rules:
    - Gross Revenue: Use Gross_Revenue column for total gross revenue queries
    - Net Sales: Use Net_Sales column for net sales after deductions
    - Gross Sales: Use Gross_Sales column for gross sales amounts
    - General Revenue: Check for Revenue column or use appropriate revenue column based on context
    - COGS: Use the pre-calculated Total_COGS field, NOT GL account ranges
    - Margin %: Use Sales_Margin_of_Gross_Sales for pre-calculated percentages
    - Gross Profit: Calculate as (Gross_Revenue - Total_COGS)
    - Net Profit: Calculate as (Net_Sales - Total_COS)
    - Fiscal Year: Data is typically for previous year (2024), not current year
    - GL Accounts: 6-digit range (400000-700000), not 4-digit ranges like 4000-4999
15. CRITICAL: When generating queries for revenue, margin, profitability, cost analysis:
    - ALWAYS use the appropriate revenue columns (Gross_Revenue, Net_Sales, Gross_Sales) NOT GL_Amount_in_CC
    - Use Total_COGS for cost of goods sold, not manual calculations
    - Use COALESCE to handle NULL values in revenue and cost columns
    - Follow the column mapping: revenue queries should use revenue columns, not GL account amounts
16. ⭐ CRITICAL - COLUMN SELECTION RULES (Only Select What's Requested) ⭐:
    - ONLY include columns that are EXPLICITLY mentioned or clearly implied in the user's query
    - DO NOT add "helpful" extra columns unless specifically requested
    - Examples:
      * "Show top customers by revenue" → SELECT Customer, Revenue (NOT profit, frequency, margin, etc.)
      * "Show customers with names" → SELECT Customer, Customer_Name (NOT revenue, unless asked)
      * "Show revenue and margin by customer" → SELECT Customer, Revenue, Margin (ONLY these)
    - Exception: Primary key/identifier columns (like Customer ID) can be included if they're needed to identify the entity
    - If user asks for "top customers", include the metric they're sorted by (e.g., revenue for "top by revenue")
    - DO NOT add columns just because they're in the same table or might be interesting
    - ⚠️ SPECIAL CASE - "Add X" queries (e.g., "add customer name to above results"):
      * If user says "add X" or "include X", ONLY add that specific column X
      * DO NOT add profit, margin, COGS, frequency, or any other metrics unless explicitly requested
      * Example: "add customer name" → Add ONLY Customer_Name column (NOT profit, margin, etc.)
      * Example: "add profit and margin" → Add ONLY Profit and Margin columns
      * The word "add" means append ONE column, not rebuild the entire result set
17. For GL account queries:
    - Use the table containing GL_Account column from the schema provided
    - Always include GL_Account in SELECT and GROUP BY
    - Use ROUND(SUM(amount_column), 2) for total amounts
    - Apply appropriate date filters based on available date columns
18. TABLE JOIN RULES:
    - When joining tables, use appropriate key columns from the schema
    - The system will automatically detect and fix format mismatches (e.g., leading zeros) in JOINs

19. CRITICAL - COLUMN FORMATTING RULES (Make Results Readable):
    ⭐ ALWAYS FORMAT MONETARY VALUES, PERCENTAGES, AND COUNTS ⭐

    **Currency Columns** - Round to 2 decimals, frontend will add $ and commas:

    CRITICAL: BigQuery FORMAT() does NOT support comma separators.
    Return numeric values rounded appropriately - frontend handles formatting.

    For currency columns, use: ROUND(column_value, 2)

    Apply to:
    - Revenue, Sales, Gross_Revenue, Net_Sales, Gross_Sales
    - Cost, COGS, Total_COGS, Expenses, OpEx
    - Price, Amount, Value, Total, Sum
    - Profit, Margin (when not %), Income, EBITDA
    - Gross, Net (when monetary), Budget, Spend
    - Payment, Fee, Charge, Invoice, Freight
    - Discount, Rebate, Commission, Wage, Salary
    - Tax (when not rate), Asset, Liability, Equity
    - SAP value fields: VV001, VV002, VV003, etc.

    CORRECT Example:
    ROUND(SUM(COALESCE(Gross_Revenue, 0)), 2) as revenue

    WRONG - DO NOT USE:
    FORMAT('%,d', ...)                          -- WRONG: BigQuery doesn't support comma formatting
    FORMAT('%,.2f', ...)                        -- WRONG: BigQuery doesn't support comma formatting
    FORMAT('%\'d', ...)                         -- WRONG: invalid BigQuery syntax
    CONCAT('$', ...)                            -- WRONG: frontend adds currency symbols

    **Percentage Columns** - Apply `CONCAT(CAST(ROUND(column_name, 2) AS STRING), '%')` to:
    - Margin_Percent, Margin_Pct, Growth_Rate, Change_Percent
    - Any column ending in _percent, _pct, _rate
    - Calculated percentages (growth, variance, ratio)

    Example: `CONCAT(CAST(ROUND(margin_percent, 2) AS STRING), '%') as margin`

    **Numeric Columns** - Return as integers, frontend will add commas:
    - Quantity, Qty, Count, Number, Volume
    - Units, Cases, Items, Orders, Transactions

    Example: `CAST(COUNT(DISTINCT customer_id) AS INT64) as customer_count`

    **IMPORTANT**:
    - Return clean numeric values - BigQuery cannot format with commas
    - Use COALESCE to handle NULLs: SUM(COALESCE(Gross_Revenue, 0))
    - Round currency to 2 decimals, quantities to integers
    - Only add '%' suffix for percentages - all other formatting happens frontend

    **Good Example** - Return clean numeric values:

    WITH CustomerMetrics AS (
      SELECT
        Customer,
        SUM(COALESCE(Gross_Revenue, 0)) as total_revenue,
        SUM(COALESCE(Total_COGS, 0)) as total_cogs,
        COUNT(DISTINCT Sales_Order_KDAUF) as order_count
      FROM dataset_25m_table
      GROUP BY Customer
    )
    SELECT
      Customer,
      ROUND(total_revenue, 2) as revenue,
      ROUND(total_cogs, 2) as cogs,
      CAST(order_count AS INT64) as order_count
    FROM CustomerMetrics

    ⚠️ Frontend will format: 1234567.89 → $1,234,567.89 and 1234 → 1,234

20. CRITICAL - TEMPORAL AGGREGATION PATTERNS (Multi-Period Comparisons):

    **When comparing periods (e.g., "average of previous 3 months"), MUST aggregate by period FIRST, THEN average:**

    ❌ WRONG - Averaging individual rows:
    ```sql
    SELECT MaterialNumber, AVG(quantity) as avg_qty
    FROM sales
    WHERE date >= '2025-02-01' AND date <= '2025-04-30'
    GROUP BY MaterialNumber  -- This averages ALL individual rows
    ```

    ✅ CORRECT - Aggregate by period first, then average:
    ```sql
    WITH MonthlyTotals AS (
      SELECT
        MaterialNumber,
        DATE_TRUNC(date, MONTH) as month,
        SUM(quantity) as monthly_qty
      FROM sales
      WHERE date >= '2025-02-01' AND date <= '2025-04-30'
      GROUP BY MaterialNumber, month  -- Aggregate by month FIRST
    )
    SELECT
      MaterialNumber,
      AVG(monthly_qty) as avg_monthly_qty  -- THEN average the monthly totals
    FROM MonthlyTotals
    GROUP BY MaterialNumber
    ```

    **Key Pattern**: Period comparison queries require TWO levels of aggregation:
    1. First level: Aggregate to period granularity (daily → monthly, monthly → quarterly)
    2. Second level: Calculate average/comparison across periods

    This applies to:
    - "Average of previous N months/quarters"
    - "Compare to same period last year"
    - "Month-over-month growth"
    - Any query comparing aggregated periods

    ⚠️ Failing to use two-level aggregation produces mathematically incorrect results!"""

        # Add financial context if provided
        if financial_context:
            financial_rules = """

Financial Query Rules:
11. For financial metrics, use the provided formulas exactly as specified
12. When calculating margins, ensure proper handling of NULL values with SAFE_DIVIDE
13. For GL account queries, use the gl_account column to filter by account numbers
14. Apply the appropriate hierarchy level (L1, L2, or L3) based on the query intent
15. For time-based financial queries, use fiscal periods when available
16. Group financial data appropriately based on the requested dimensions"""

            # CRITICAL: If a SQL template is provided from the Knowledge Graph, USE IT!
            if financial_context.get("suggested_query"):
                financial_rules += """

⚠️ CRITICAL - SQL TEMPLATE FROM KNOWLEDGE GRAPH ⚠️
A pre-validated SQL template has been retrieved from the Knowledge Graph for this metric.
This template contains the CORRECT formula and calculation logic.

**YOU MUST USE THIS TEMPLATE AS YOUR PRIMARY SOURCE**

Instructions:
1. Use the provided SQL template as the foundation for your query
2. Adapt ONLY the following elements to match the user's request:
   - Table name (if different from template)
   - Column names (map to actual schema)
   - LIMIT clause (e.g., "top 10" → LIMIT 10)
   - ORDER BY clause (if user specifies different sorting)
   - Additional filters (e.g., time period, specific customers)
3. DO NOT CHANGE the metric calculation logic in the template
4. DO NOT CREATE your own formula - the template contains the validated formula
5. The template formulas are from validated financial test suites - they are CORRECT

If you deviate from the template's calculation logic, you WILL generate incorrect results."""

            if financial_context.get("formulas"):
                financial_rules += "\n\nAvailable Financial Formulas:"
                for metric, formula in financial_context["formulas"].items():
                    financial_rules += f"\n- {metric}: {list(formula.values())[0] if formula else 'N/A'}"

            base_prompt += financial_rules

        # Add persona-specific instructions from user profile
        if persona_additions:
            base_prompt += f"""

=== ROLE-SPECIFIC GUIDANCE ===
{persona_additions}"""

        return base_prompt

    # Note: _load_temporal_context removed - temporal context now comes from connector metadata

    def _build_user_prompt(
        self,
        query: str,
        schemas: List[Dict[str, Any]],
        examples: Optional[List[Dict[str, str]]] = None,
        financial_context: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        join_hints: Optional[List[Dict[str, Any]]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
        database_type: str = 'bigquery',
        database_name: str = 'BigQuery',
        dialect_guide: str = ''
    ) -> str:
        prompt_parts = []

        # Add database dialect information FIRST (CRITICAL for multi-database support)
        if dialect_guide:
            prompt_parts.append(f"## 🗄️ TARGET DATABASE: {database_name}\n\n")
            prompt_parts.append(f"**CRITICAL**: You are generating SQL for {database_name}, NOT BigQuery.\n")
            prompt_parts.append(f"You MUST use {database_type.upper()} SQL syntax and follow these guidelines:\n")
            prompt_parts.append(dialect_guide)
            prompt_parts.append("\n" + "=" * 80 + "\n\n")
        else:
            # Default to BigQuery if no dialect guide provided (backward compatibility)
            prompt_parts.append("## 🗄️ TARGET DATABASE: BigQuery\n\n")
            prompt_parts.append("=" * 80 + "\n\n")

        # Note: Temporal context is now derived from connector metadata, not hardcoded JSON
        # Data availability should come from the schema's metadata when available

        # If this is a follow-up query, prepend context-aware prompt
        if conversation_context and conversation_context.get("is_follow_up"):
            from src.core.conversation_context import ConversationContextManager
            context_manager = ConversationContextManager()

            # Build context-aware prompt section
            context_prompt = context_manager.build_context_prompt(
                query,
                conversation_context,
                conversation_context.get("follow_up_type", "other")
            )

            prompt_parts.append(context_prompt)
            prompt_parts.append("\n" + "=" * 80 + "\n")

        # Add table schemas with RDF enrichment (business domains, size, relationships, column stats)
        prompt_parts.append("AVAILABLE TABLES:")
        schema_sections = []
        for schema in schemas:
            schema_sections.append(self._format_schema_with_rdf(schema))
        prompt_parts.append("\n\n".join(schema_sections))

        # Add JOIN hints if multiple tables are involved
        if join_hints and len(join_hints) > 0:
            prompt_parts.append("\n\n⚠️ MULTI-TABLE QUERY DETECTED - JOIN REQUIRED ⚠️")
            prompt_parts.append("\n=== CRITICAL: You MUST use JOINs for this query ===")
            prompt_parts.append("\nTable Relationships and JOIN Instructions:")

            for hint in join_hints:
                source = hint['source']
                target = hint['target']
                keys = hint['keys']
                join_type = hint.get('type', 'left').upper()
                confidence = hint.get('confidence', 0.5)
                confidence_reason = hint.get('confidence_reason', '')
                source_rows = hint.get('source_row_count', 0)
                target_rows = hint.get('target_row_count', 0)

                # Show confidence level
                confidence_level = "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.5 else "LOW"
                prompt_parts.append(f"\n{source} → {target} (Confidence: {confidence_level} {confidence:.0%}):")

                # Show reason for JOIN recommendation
                if confidence_reason:
                    prompt_parts.append(f"  Reason: {confidence_reason}")

                # Show cardinality if available
                if source_rows and target_rows:
                    prompt_parts.append(f"  Cardinality: {source} ({source_rows:,} rows) → {target} ({target_rows:,} rows)")

                for source_col, target_col in keys:
                    # Special handling for Sales_Order JOIN with leading zero issue
                    if source_col == "Sales_Order_KDAUF" and target_col == "SalesDocument_VBELN":
                        prompt_parts.append(f"  ⚠️ CRITICAL: JOIN ON LTRIM({source}.{source_col}, '0') = {target}.{target_col}")
                        prompt_parts.append(f"  (Leading zero transformation required!)")
                    # Special handling for Customer/CustomerNumber JOIN with leading zero issue
                    elif source_col == "Customer" and target_col == "CustomerNumber":
                        prompt_parts.append(f"  ⚠️ CRITICAL: JOIN ON LTRIM({source}.{source_col}, '0') = {target}.{target_col}")
                        prompt_parts.append(f"  (Leading zero transformation required for customer IDs!)")
                    else:
                        prompt_parts.append(f"  JOIN ON {source}.{source_col} = {target}.{target_col}")
                prompt_parts.append(f"  JOIN TYPE: {join_type} JOIN")

            # Add column-to-table mapping
            prompt_parts.append("\n\nColumn Ownership Guide:")
            prompt_parts.append("When using multiple tables, reference columns correctly:")

            # Build column mappings from schemas
            for schema in schemas:
                table_name = schema['table_name']
                table_alias = self._get_table_alias(table_name)

                # Identify key columns to highlight
                key_columns = []
                for col in schema['columns'][:10]:  # Show first 10 important columns
                    key_columns.append(col['name'])

                if key_columns:
                    prompt_parts.append(f"\n  {table_name} (alias: {table_alias}):")
                    for col in key_columns:
                        prompt_parts.append(f"    - {col} → Use {table_alias}.{col}")

            # Add multi-table query reminders
            prompt_parts.append("\n\n⚠️ MULTI-TABLE QUERY RULES:")
            prompt_parts.append("✓ Use table aliases (e.g., t1, t2) to qualify ALL column references")
            prompt_parts.append("✓ Choose the correct table for each column based on the schema above")
            prompt_parts.append("✓ IMPORTANT: Use ONLY tables listed in the schema - do NOT reference any other tables")

        # Add examples if provided
        if examples:
            prompt_parts.append("\n\nExamples:")
            for example in examples:
                prompt_parts.append(f"\nQuestion: {example['question']}")
                prompt_parts.append(f"SQL: {example['sql']}")
        
        # Add financial context if provided
        if financial_context:
            prompt_parts.append("\n\nFinancial Query Context:")
            prompt_parts.append(f"Hierarchy Level: {financial_context.get('hierarchy_level', 'Unknown')}")
            prompt_parts.append(f"Query Intent: {financial_context.get('intent', 'Unknown')}")

            # Add SQL template if provided from Knowledge Graph
            if financial_context.get("suggested_query"):
                logger.info(f"✅ Adding SQL template to user prompt (length: {len(financial_context['suggested_query'])} chars)")
                prompt_parts.append("\n\n🔥 VALIDATED SQL TEMPLATE FROM KNOWLEDGE GRAPH 🔥")
                prompt_parts.append("This template contains the CORRECT formulas and calculation logic.")
                prompt_parts.append("Adapt this template to match the user's request:")
                prompt_parts.append("\n```sql")
                prompt_parts.append(financial_context["suggested_query"])
                prompt_parts.append("```")
                prompt_parts.append("\n⚠️ DO NOT create your own formulas - USE THE TEMPLATE LOGIC!")
                prompt_parts.append("Only adapt: table names, column names, LIMIT, filters, ORDER BY")
            else:
                logger.warning("❌ No SQL template in financial_context")
            
            if financial_context.get("metrics"):
                prompt_parts.append("\nRequested Metrics:")
                for metric in financial_context["metrics"]:
                    # Handle both dict and string formats
                    if isinstance(metric, dict):
                        prompt_parts.append(f"- {metric['name']} ({metric['code']}): {metric.get('formula', 'N/A')}")
                    else:
                        prompt_parts.append(f"- {metric}")
            
            if financial_context.get("buckets"):
                prompt_parts.append("\nRelevant GL Buckets:")
                for bucket in financial_context["buckets"]:
                    # Handle both dict and string formats
                    if isinstance(bucket, dict):
                        prompt_parts.append(f"- {bucket['name']} ({bucket['code']}): GL accounts {bucket['gl_accounts']}")
                    else:
                        prompt_parts.append(f"- {bucket}")
            
            if financial_context.get("gl_accounts"):
                prompt_parts.append("\nSpecific GL Accounts:")
                for account in financial_context["gl_accounts"][:5]:  # Limit to 5
                    # Handle both dict and string formats
                    if isinstance(account, dict):
                        prompt_parts.append(f"- {account['number']}: {account['description']}")
                    else:
                        prompt_parts.append(f"- {account}")
            
            if financial_context.get("time_filter"):
                prompt_parts.append(f"\nTime Filter: {financial_context['time_filter']}")
            
            if financial_context.get("dimensions"):
                prompt_parts.append(f"\nGroup By Dimensions: {', '.join(financial_context['dimensions'])}")
        
        # Add business context if available
        if business_context:
            if business_context.get("gl_accounts"):
                prompt_parts.append("\nBusiness Configuration - GL Accounts:")
                # Group by bucket for clarity
                bucket_groups = {}
                for gl in business_context["gl_accounts"][:20]:  # Limit to prevent prompt overflow
                    bucket = business_context.get("gl_to_bucket", {}).get(gl, "Unknown")
                    if bucket not in bucket_groups:
                        bucket_groups[bucket] = []
                    bucket_groups[bucket].append(gl)
                
                for bucket, accounts in bucket_groups.items():
                    prompt_parts.append(f"- {bucket}: {', '.join(accounts[:5])}...")  # Show first 5
            
            if business_context.get("material_filters"):
                prompt_parts.append("\nMaterial Hierarchy Filters:")
                for level, filter_info in business_context["material_filters"].items():
                    prompt_parts.append(f"- {level}: {filter_info['description']} (code: {filter_info['code']})")
            
            if business_context.get("resolved_terms"):
                prompt_parts.append("\nResolved Business Terms:")
                for term, info in list(business_context["resolved_terms"].items())[:5]:
                    prompt_parts.append(f"- '{term}' maps to: {info}")
        
        # Add the user query
        prompt_parts.append(f"\n\nUser question: {query}")
        prompt_parts.append("\nGenerate the SQL query in the specified JSON format.")
        prompt_parts.append("\nEnsure the SQL is optimized for BigQuery and follows best practices.")
        
        # Store examples used for confidence calculation
        self._last_examples_used = examples
        
        # Enhance prompt with type information
        final_prompt = "\n".join(prompt_parts)
        final_prompt = self.schema_aware.enhance_prompt_with_type_info(final_prompt, schemas)
        
        return final_prompt
    
    def _get_table_alias(self, table_name: str) -> str:
        """Generate a short alias for a table name."""
        # Predefined aliases for known tables
        alias_map = {
            'dataset_25m_table': 'copa',
            'sales_order_cockpit_export': 'cockpit',
            'customer_master': 'cust',
            'product_master': 'prod',
            'inventory': 'inv'
        }

        if table_name in alias_map:
            return alias_map[table_name]

        # Generate alias from table name (first letters of words)
        parts = table_name.replace('_', ' ').split()
        if len(parts) > 1:
            return ''.join(p[0] for p in parts[:3])
        else:
            return table_name[:4]

    def _get_size_hint(self, row_count: int) -> str:
        """Convert row count to human-readable size hint (no optimization advice)."""
        if not row_count:
            return "unknown size"
        elif row_count < 1000:
            return f"~{row_count:,} rows"
        elif row_count < 1000000:
            return f"~{row_count:,} rows"
        else:
            return f"~{row_count/1000000:.1f}M rows"

    def _get_best_filter_columns(self, columns: List[Dict[str, Any]], max_cols: int = 5) -> List[str]:
        """
        Get columns with high selectivity that are good for WHERE clauses.

        High selectivity (close to 1.0) means many unique values, which makes
        filters more effective at reducing result sets.

        Args:
            columns: List of column dicts with stats
            max_cols: Maximum number of columns to return

        Returns:
            List of column names sorted by selectivity (best first)
        """
        filter_cols = []

        for col in columns:
            name = col.get('name', col.get('column_name', ''))
            stats = col.get('stats', {})
            selectivity = stats.get('selectivity', 0)

            # High selectivity (> 0.5) or indexed columns are good for filtering
            is_indexed = col.get('has_index') or stats.get('hasIndex')
            is_pk = col.get('is_primary_key') or stats.get('isPrimaryKey')

            if selectivity and selectivity > 0.5:
                filter_cols.append((name, selectivity, 'selectivity'))
            elif is_indexed or is_pk:
                filter_cols.append((name, 1.0 if is_pk else 0.8, 'indexed'))

        # Sort by selectivity descending
        filter_cols.sort(key=lambda x: x[1], reverse=True)

        return [col[0] for col in filter_cols[:max_cols]]

    def _get_column_aliases(self, columns: List[Dict[str, Any]]) -> str:
        """
        Get a formatted string of column aliases/synonyms.

        Helps the LLM understand alternative names users might use for columns.

        Args:
            columns: List of column dicts that may contain 'synonyms' or 'aliases'

        Returns:
            Formatted string like "revenue=sales_amount, customer=client_id"
        """
        aliases = []

        for col in columns:
            name = col.get('name', col.get('column_name', ''))
            synonyms = col.get('synonyms', col.get('aliases', []))

            if synonyms and isinstance(synonyms, list):
                # Format: alias1/alias2 -> column_name
                alias_str = '/'.join(synonyms[:2])  # Limit to 2 aliases per column
                aliases.append(f"{alias_str}→{name}")

        if not aliases:
            return ""

        # Limit total output to avoid bloating prompts
        return ', '.join(aliases[:8])

    def _format_column_with_stats(self, col: Dict[str, Any]) -> str:
        """Format column with RDF statistics."""
        name = col.get('name', col.get('column_name', ''))
        dtype = col.get('type', col.get('data_type', ''))

        hints = []
        stats = col.get('stats', {})

        # Key indicators
        if col.get('is_primary_key') or stats.get('isPrimaryKey'):
            hints.append("PK")
        if col.get('is_foreign_key') or stats.get('isForeignKey'):
            hints.append("FK")
        if col.get('has_index') or stats.get('hasIndex'):
            hints.append("indexed")

        # Selectivity (good for WHERE)
        selectivity = stats.get('selectivity', 0)
        if selectivity and selectivity < 0.01:
            hints.append("high selectivity")
        elif selectivity and selectivity > 0.9:
            hints.append("low cardinality")

        result = f"{name} ({dtype})"
        if hints:
            result += f" [{', '.join(hints)}]"

        # Add column synonyms/aliases if present
        synonyms = col.get('synonyms', col.get('aliases', []))
        if synonyms:
            result += f" (also: {', '.join(synonyms[:3])})"

        return result

    def _get_table_relationships(self, schema: Dict[str, Any]) -> List[str]:
        """Extract JOIN relationships from schema."""
        rels = []

        # Direct relationships (from RDF)
        for rel in schema.get('relationships', []):
            target = rel.get('target_table', '')
            col = rel.get('join_column', '')
            if target and col:
                rels.append(f"{target}.{col}")

        # Infer from FK columns
        for col in schema.get('columns', []):
            if col.get('is_foreign_key') or col.get('stats', {}).get('isForeignKey'):
                col_name = col.get('name', '')
                if col_name.endswith('_id'):
                    inferred = col_name[:-3].upper() + 'S'
                    if f"{inferred}.{col_name}" not in rels:
                        rels.append(f"{inferred}.{col_name} (inferred)")

        return rels

    def _format_schema_with_rdf(self, schema: Dict[str, Any]) -> str:
        """Format a single schema with all RDF-enriched data."""
        lines = []
        table_name = schema.get('table_name', 'unknown')
        db_type = schema.get('database_type', 'bigquery')

        # Build fully-qualified table name based on database type
        dataset = schema.get('dataset', schema.get('schema', ''))
        project = schema.get('project', schema.get('database', ''))

        if db_type == 'bigquery':
            qualified_name = f"`{project}.{dataset}.{table_name}`" if project and dataset else table_name
        elif db_type == 'snowflake':
            # Snowflake: DATABASE.SCHEMA.TABLE (no backticks, uppercase convention)
            qualified_name = f"{project}.{dataset}.{table_name}" if project and dataset else table_name
        elif db_type in ('postgresql', 'redshift'):
            qualified_name = f"{dataset}.{table_name}" if dataset else table_name
        elif db_type == 'databricks':
            qualified_name = f"{project}.{dataset}.{table_name}" if project and dataset else table_name
        else:
            qualified_name = table_name

        # Table header
        lines.append(f"TABLE: {table_name}")
        lines.append(f"  Qualified Name: {qualified_name}")
        lines.append(f"  Database Type: {db_type}")

        # Business domains
        domains = schema.get('business_domains', [])
        if isinstance(domains, str):
            try:
                domains = json.loads(domains)
            except:
                domains = []
        if domains:
            lines.append(f"  Domain: {', '.join(domains)}")

        # Size hint
        row_count = schema.get('row_count', 0)
        lines.append(f"  Size: {self._get_size_hint(row_count)}")

        # Columns with stats
        lines.append("  Columns:")
        for col in schema.get('columns', [])[:15]:
            col_info = self._format_column_with_stats(col)
            lines.append(f"    - {col_info}")

        if len(schema.get('columns', [])) > 15:
            lines.append(f"    ... and {len(schema['columns']) - 15} more")

        # Best filter columns (high selectivity - good for WHERE clauses)
        best_filter_cols = self._get_best_filter_columns(schema.get('columns', []))
        if best_filter_cols:
            lines.append(f"  Best filter columns: {', '.join(best_filter_cols)}")

        # Column aliases/synonyms (help LLM match user terms to column names)
        column_aliases = self._get_column_aliases(schema.get('columns', []))
        if column_aliases:
            lines.append(f"  Column aliases: {column_aliases}")

        # Relationships
        rels = self._get_table_relationships(schema)
        if rels:
            lines.append("  Joins with:")
            for rel in rels[:5]:
                lines.append(f"    -> {rel}")

        return '\n'.join(lines)

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse the LLM response to extract SQL and metadata."""
        logger.info(f"Parsing LLM response of type: {type(content)}")
        
        # Ensure content is a string
        if not isinstance(content, str):
            logger.error(f"Expected string content, got {type(content)}: {repr(content)}")
            return {
                "sql": str(content) if content is not None else "",
                "explanation": "Generated SQL query",
                "tables_used": [],
                "estimated_complexity": "medium",
                "optimization_notes": "",
                "error": f"Invalid content type: {type(content)}"
            }
        
        try:
            # Try to parse as JSON first
            if content.strip().startswith("{"):
                logger.info("Attempting to parse as direct JSON")
                parsed = json.loads(content)
                
                # Ensure parsed result is a dict
                if not isinstance(parsed, dict):
                    logger.error(f"JSON parsing returned {type(parsed)}, expected dict")
                    raise ValueError(f"JSON parsing returned {type(parsed)}")
                
                # Clean up the SQL if it contains triple quotes
                if "sql" in parsed and isinstance(parsed["sql"], str):
                    sql = parsed["sql"].strip()
                    # Remove triple quotes if present
                    if sql.startswith('"""') and sql.endswith('"""'):
                        sql = sql[3:-3].strip()
                    parsed["sql"] = sql
                
                # Ensure required fields exist
                if "explanation" not in parsed:
                    parsed["explanation"] = "Generated SQL query"
                if "tables_used" not in parsed:
                    parsed["tables_used"] = []
                if "estimated_complexity" not in parsed:
                    parsed["estimated_complexity"] = "medium"
                
                logger.info("Successfully parsed as direct JSON")
                return parsed
            
            # If not JSON, try to extract JSON from the content
            import re
            logger.info("Searching for JSON pattern in content")
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                logger.info("Found JSON pattern, attempting to parse")
                parsed = json.loads(json_match.group())
                
                # Ensure parsed result is a dict
                if not isinstance(parsed, dict):
                    logger.error(f"JSON pattern parsing returned {type(parsed)}, expected dict")
                    raise ValueError(f"JSON pattern parsing returned {type(parsed)}")
                
                # Clean up the SQL if it contains triple quotes
                if "sql" in parsed and isinstance(parsed["sql"], str):
                    sql = parsed["sql"].strip()
                    if sql.startswith('"""') and sql.endswith('"""'):
                        sql = sql[3:-3].strip()
                    parsed["sql"] = sql
                
                # Ensure required fields exist
                if "explanation" not in parsed:
                    parsed["explanation"] = "Generated SQL query"
                if "tables_used" not in parsed:
                    parsed["tables_used"] = []
                if "estimated_complexity" not in parsed:
                    parsed["estimated_complexity"] = "medium"
                
                logger.info("Successfully parsed JSON pattern")
                return parsed
            
            # Fallback: treat entire content as SQL
            logger.warning("No JSON found, treating entire content as SQL")
            return {
                "sql": content.strip(),
                "explanation": "Query generated from natural language",
                "tables_used": [],
                "estimated_complexity": "medium",
                "optimization_notes": ""
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Return a basic structure with the content as SQL
            return {
                "sql": content.strip() if content else "",
                "explanation": "Query generated from natural language",
                "tables_used": [],
                "estimated_complexity": "medium",
                "optimization_notes": "",
                "parse_error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in response parsing: {e}")
            return {
                "sql": content.strip() if isinstance(content, str) and content else "",
                "explanation": "Generated SQL query",
                "tables_used": [],
                "estimated_complexity": "medium",
                "optimization_notes": "",
                "error": str(e)
            }
    
    def optimize_query(self, sql: str, performance_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest query optimizations based on performance statistics."""
        try:
            prompt = f"""Analyze this BigQuery SQL query and suggest optimizations:

SQL Query:
{sql}

Performance Statistics:
- Bytes processed: {performance_stats.get('bytes_processed', 'Unknown')}
- Estimated cost: ${performance_stats.get('estimated_cost', 'Unknown')}
- Execution time: {performance_stats.get('execution_time', 'Unknown')}ms

Suggest optimizations for:
1. Reducing data scanned (partitioning, clustering, filters)
2. Improving query performance (CTEs, materialized views)
3. Cost optimization

Return a JSON object with:
{{
    "optimized_sql": "the optimized query",
    "optimizations_applied": ["list of optimizations"],
    "estimated_improvement": "percentage or description",
    "additional_recommendations": ["other suggestions"]
}}"""

            if self.use_openai:
                # OpenAI format
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=2000
                )
                response_text = response.choices[0].message.content
            else:
                # Anthropic format
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.content[0].text

            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Failed to optimize query: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the embedding service."""
        from src.core.embeddings import EmbeddingService
        embedding_service = EmbeddingService()
        return embedding_service.generate_embedding(text)
    
    def _get_relevant_examples(self, user_query: str, financial_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Get relevant few-shot examples based on the user query."""
        query_lower = user_query.lower()
        relevant_examples = []
        
        # PRIORITY 1: Check for revenue queries FIRST - this is most critical
        if any(term in query_lower for term in ['revenue', 'sales', 'income', 'turnover']):
            # ALWAYS add revenue examples from GROSS_MARGIN_EXAMPLES that use Gross_Revenue correctly
            relevant_examples.extend([ex for ex in GROSS_MARGIN_EXAMPLES if 'revenue' in ex['question'].lower()][:2])
            # Ensure we have at least one revenue example
            if not relevant_examples:
                relevant_examples.append(GROSS_MARGIN_EXAMPLES[0])  # First example is always revenue
        
        # Check for specific financial analysis patterns
        if any(term in query_lower for term in ['variance', 'budget', 'actual vs', 'quarter', 'qoq', 'mom']):
            # Find variance/comparison queries
            relevant_examples.extend([q for q in FINANCIAL_ANALYSIS_QUERIES if 'variance' in q['question'].lower()][:1])
        
        if any(term in query_lower for term in ['cost driver', 'cost breakdown', 'freight', 'material cost']):
            # Find cost analysis queries
            relevant_examples.extend([q for q in FINANCIAL_ANALYSIS_QUERIES if 'cost' in q['question'].lower() and 'COGS' in q['sql']][:1])
        
        if any(term in query_lower for term in ['profitable', 'profitability', 'profit by', 'segment']):
            # Find profitability queries
            relevant_examples.extend([q for q in FINANCIAL_ANALYSIS_QUERIES if 'profitable' in q['question'].lower()][:1])
        
        if any(term in query_lower for term in ['contribution margin', 'fixed', 'variable', 'break-even']):
            # Find contribution margin queries
            relevant_examples.extend([q for q in FINANCIAL_ANALYSIS_QUERIES if 'contribution' in q['question'].lower()][:1])
        
        # ALWAYS check if this is a gross margin/profit query and add those examples too
        if any(term in query_lower for term in ['gross margin', 'gross profit', 'margin', 'profit', 'cogs']):
            # Add gross margin examples
            relevant_examples.extend(GROSS_MARGIN_EXAMPLES[:2])  # Customer and product margin examples
        
        # If we have examples, return them (up to 3)
        if relevant_examples:
            return relevant_examples[:3]
        
        # If financial context is provided, use financial-specific examples
        if financial_context and financial_context.get("hierarchy_level"):
            return self._get_financial_examples(financial_context)
        
        # Default: return a mix of examples
        default_examples = []
        default_examples.extend(GROSS_MARGIN_EXAMPLES[:1])  # One gross margin example
        default_examples.extend(FINANCIAL_ANALYSIS_QUERIES[:1])  # One analysis example
        
        for example in self.few_shot_examples:
            example_lower = example["question"].lower()
            # Check for keyword overlap
            if any(word in query_lower for word in example_lower.split() if len(word) > 3):
                relevant_examples.append(example)
        
        # Return top 2 most relevant examples
        return relevant_examples[:2] if relevant_examples else self.few_shot_examples[:2]
    
    def _get_financial_examples(self, financial_context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get financial-specific few-shot examples based on hierarchy level."""
        logger.info(f"Getting financial examples for context: {type(financial_context)}")
        logger.info(f"Financial context content: {repr(financial_context)}")
        
        # Safety check for financial_context
        if not isinstance(financial_context, dict):
            logger.error(f"Expected dict for financial_context, got {type(financial_context)}")
            return self.few_shot_examples[:2]  # Return default examples
            
        hierarchy_level = financial_context.get("hierarchy_level", 1)
        logger.info(f"Hierarchy level: {hierarchy_level}, type: {type(hierarchy_level)}")
        
        # L1 Metric examples
        if hierarchy_level == 1:
            return [
                {
                    "question": "Show me gross margin by region for last quarter",
                    "sql": """SELECT 
    region,
    SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) as revenue,
    SUM(CASE WHEN gl_account BETWEEN '5000' AND '5999' THEN amount ELSE 0 END) as cogs,
    SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) - 
    SUM(CASE WHEN gl_account BETWEEN '5000' AND '5999' THEN amount ELSE 0 END) as gross_margin,
    SAFE_DIVIDE(
        SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) - 
        SUM(CASE WHEN gl_account BETWEEN '5000' AND '5999' THEN amount ELSE 0 END),
        SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END)
    ) * 100 as gross_margin_pct
FROM `{project}.{dataset}.gl_transactions`
WHERE DATE_TRUNC(date, QUARTER) = DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 QUARTER), QUARTER)
GROUP BY region
ORDER BY gross_margin DESC"""
                },
                {
                    "question": "Calculate EBITDA for current year",
                    "sql": """SELECT 
    SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount 
             WHEN gl_account BETWEEN '5000' AND '6999' THEN -amount 
             ELSE 0 END) as operating_income,
    SUM(CASE WHEN gl_account IN ('6810', '6820', '6830') THEN amount ELSE 0 END) as depreciation,
    SUM(CASE WHEN gl_account IN ('6840', '6850') THEN amount ELSE 0 END) as amortization,
    SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount 
             WHEN gl_account BETWEEN '5000' AND '6999' THEN -amount 
             ELSE 0 END) + 
    SUM(CASE WHEN gl_account IN ('6810', '6820', '6830', '6840', '6850') THEN amount ELSE 0 END) as ebitda
FROM `{project}.{dataset}.gl_transactions`
WHERE EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE())"""
                }
            ]
        
        # L2 Bucket examples
        elif hierarchy_level == 2:
            return [
                {
                    "question": "Break down COGS by component for this month",
                    "sql": """SELECT 
    CASE 
        WHEN gl_account BETWEEN '5000' AND '5299' THEN 'Material Costs'
        WHEN gl_account BETWEEN '5300' AND '5499' THEN 'Direct Labor'
        WHEN gl_account BETWEEN '5500' AND '5799' THEN 'Manufacturing Overhead'
        ELSE 'Other COGS'
    END as cost_component,
    SUM(amount) as total_amount,
    COUNT(DISTINCT gl_account) as account_count
FROM `{project}.{dataset}.gl_transactions`
WHERE gl_account BETWEEN '5000' AND '5999'
    AND DATE_TRUNC(date, MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH)
GROUP BY cost_component
ORDER BY total_amount DESC"""
                },
                {
                    "question": "Show operating expense breakdown by category",
                    "sql": """SELECT 
    CASE 
        WHEN gl_account BETWEEN '6000' AND '6199' THEN 'Sales Expenses'
        WHEN gl_account BETWEEN '6200' AND '6299' THEN 'Marketing Expenses'
        WHEN gl_account BETWEEN '6300' AND '6499' THEN 'Administrative Expenses'
        WHEN gl_account BETWEEN '6500' AND '6599' THEN 'R&D Expenses'
        ELSE 'Other Operating Expenses'
    END as expense_category,
    SUM(amount) as total_expenses,
    COUNT(*) as transaction_count
FROM `{project}.{dataset}.gl_transactions`
WHERE gl_account BETWEEN '6000' AND '6999'
    AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE())
GROUP BY expense_category
ORDER BY total_expenses DESC"""
                }
            ]
        
        # L3 GL Account examples
        else:
            return [
                {
                    "question": "Show all freight charges for Q2",
                    "sql": """SELECT 
    date,
    gl_account,
    gl_description,
    amount,
    reference_number,
    vendor_name
FROM `{project}.{dataset}.gl_transactions`
WHERE LOWER(gl_description) LIKE '%freight%'
    AND EXTRACT(QUARTER FROM date) = 2
    AND EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE())
ORDER BY date DESC"""
                },
                {
                    "question": "List office rent expenses by location",
                    "sql": """SELECT 
    location,
    gl_account,
    gl_description,
    SUM(amount) as total_rent,
    COUNT(*) as payment_count
FROM `{project}.{dataset}.gl_transactions`
WHERE gl_account IN ('6300', '6301', '6302')
    OR LOWER(gl_description) LIKE '%office rent%'
GROUP BY location, gl_account, gl_description
ORDER BY location, total_rent DESC"""
                }
            ]
    
    def _calculate_confidence(self, result: Dict[str, Any], table_schemas: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for generated SQL."""
        # Defensive check: ensure result is a dict
        if not isinstance(result, dict):
            logger.error(f"Expected dict for result, got {type(result)}")
            return 0.5  # Return moderate confidence as fallback
            
        confidence = 1.0
        
        # Reduce confidence for high complexity
        if result.get("estimated_complexity") == "high":
            confidence -= 0.2
        elif result.get("estimated_complexity") == "medium":
            confidence -= 0.1
        
        # Reduce confidence if many tables are involved
        tables_used = result.get("tables_used", [])
        if len(tables_used) > 3:
            confidence -= 0.15
        elif len(tables_used) > 5:
            confidence -= 0.25
        
        # Reduce confidence if no examples were used
        if not hasattr(self, '_last_examples_used') or not self._last_examples_used:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.1, min(1.0, confidence))
    
    def correct_sql_error(self, original_sql: str, error_message: str, table_schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Attempt to correct SQL based on error message."""
        try:
            correction_prompt = f"""The following SQL query has an error:

SQL:
{original_sql}

Error:
{error_message}

Available table schemas:
{self._format_schemas_for_prompt(table_schemas)}

Please correct the SQL query to fix the error. Focus on:
1. Fixing syntax errors
2. Correcting column/table names
3. Adding necessary JOINs or conditions

Return the corrected SQL in the same JSON format."""

            if self.use_openai:
                # OpenAI format
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._build_system_prompt()},
                        {"role": "user", "content": correction_prompt}
                    ],
                    temperature=0,
                    max_tokens=2000
                )
                response_text = response.choices[0].message.content
            else:
                # Anthropic format
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    temperature=0,
                    system=self._build_system_prompt(),
                    messages=[
                        {"role": "user", "content": correction_prompt}
                    ]
                )
                response_text = response.content[0].text

            if response_text:
                result = self._parse_llm_response(response_text)
                result["correction_applied"] = True
                result["original_error"] = error_message
                return result
            else:
                raise ValueError("No valid correction from LLM")
                
        except Exception as e:
            logger.error(f"Failed to correct SQL: {e}")
            return {
                "sql": original_sql,
                "error": f"Failed to correct: {str(e)}",
                "correction_applied": False
            }
    
    def _format_schemas_for_prompt(self, schemas: List[Dict[str, Any]]) -> str:
        """Format schemas concisely for error correction prompt."""
        formatted = []
        for schema in schemas:
            table_info = f"Table: {schema['table_name']}"
            columns = [f"{col['name']} ({col['type']})" for col in schema['columns'][:10]]  # Limit columns
            table_info += "\nColumns: " + ", ".join(columns)
            if len(schema['columns']) > 10:
                table_info += f" ... and {len(schema['columns']) - 10} more"
            formatted.append(table_info)
        return "\n\n".join(formatted)