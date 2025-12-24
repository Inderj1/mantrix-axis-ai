"""
Financial Agent API Routes

API endpoints for the multi-agent financial analysis system.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional, AsyncGenerator
import structlog
from pydantic import BaseModel
import json
import asyncio
from datetime import date, datetime
from decimal import Decimal

# Lazy import for CrewAI to avoid startup failures when ChromaDB can't initialize
# from src.agents.financial_crew import get_agent_hierarchy
from src.core.sql_generator import SQLGenerator
from src.core.sql_generator_singleton import get_sql_generator
from src.db.bigquery import BigQueryClient
from src.api.middleware.cognito_auth import get_current_user

logger = structlog.get_logger()
router = APIRouter(tags=["agents"], prefix="/api/v1/agents")

# Lazy initialization for agent hierarchy (CrewAI)
_agent_hierarchy = None


def get_agent_hierarchy_lazy():
    """Lazy initialization of agent hierarchy to avoid CrewAI import at startup."""
    global _agent_hierarchy
    if _agent_hierarchy is None:
        try:
            from src.agents.financial_crew import get_agent_hierarchy
            _agent_hierarchy = get_agent_hierarchy()
        except Exception as e:
            logger.error("Failed to initialize agent hierarchy", error=str(e))
            raise HTTPException(
                status_code=503,
                detail=f"Agent service unavailable - CrewAI initialization failed: {str(e)}"
            )
    return _agent_hierarchy

# Custom JSON encoder for BigQuery date/datetime/decimal types
def json_serializer(obj):
    """Convert non-JSON-serializable objects to JSON-compatible format."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Initialize SQL components
# Note: sql_generator is now managed by sql_generator_singleton module
# get_sql_generator is imported from sql_generator_singleton
bq_client = None

def get_bq_client() -> BigQueryClient:
    global bq_client
    if bq_client is None:
        bq_client = BigQueryClient()
    return bq_client


class AgentAnalysisRequest(BaseModel):
    """Request model for agent analysis."""
    query: str
    context: Optional[Dict[str, Any]] = None


class AgentAnalysisResponse(BaseModel):
    """Response model for agent analysis."""
    status: str
    query: str
    agents_used: List[str]
    analysis: str
    routing: Dict[str, Any]
    execution: Optional[Dict[str, Any]] = None  # Table data for chat interface
    execution_plan: Optional[Dict[str, Any]] = None  # Execution plan details
    execution_logs: Optional[List[Dict[str, Any]]] = None  # Step-by-step logs
    error: Optional[str] = None


@router.post("/analyze", response_model=AgentAnalysisResponse)
async def analyze_financial_query(
    request: AgentAnalysisRequest,
    user: Optional[Dict] = Depends(get_current_user)
) -> AgentAnalysisResponse:
    """
    Analyze a financial query using the multi-agent system.

    The system will:
    1. Route the query to appropriate domain experts (COPA, GL, Financial Accounting, Sales)
    2. Each expert coordinates with specialized sub-agents
    3. Agents collaborate to gather data using NLP-to-SQL
    4. Results are synthesized into comprehensive insights
    """
    try:
        logger.info("Starting agent analysis", query=request.query)

        # Get components with organization context
        org_id = user.get('organization_id') if user else None
        agent_hierarchy = get_agent_hierarchy_lazy()
        sql_gen = get_sql_generator(organization_id=org_id)
        bq = get_bq_client()

        # Create SQL executor function that agents can use
        async def sql_executor(natural_language_query: str) -> Dict[str, Any]:
            """
            Execute a natural language query using the NLP-to-SQL framework.
            This function is provided to agents as a tool.
            """
            try:
                # Generate SQL from natural language
                logger.info("Generating SQL from NL query", nl_query=natural_language_query)
                sql_result = sql_gen.generate_sql(natural_language_query)

                # Handle result - could be dict or other types
                if isinstance(sql_result, list):
                    # If it's a list, wrap it
                    sql_result = {"results": sql_result, "sql": None}
                elif not isinstance(sql_result, dict):
                    return {"error": f"Unexpected result type: {type(sql_result)}", "results": []}

                if not sql_result or "error" in sql_result:
                    error_msg = sql_result.get("error", "Failed to generate SQL") if isinstance(sql_result, dict) else "Failed to generate SQL"
                    return {
                        "error": error_msg,
                        "results": []
                    }

                sql_query = sql_result.get("sql")
                if not sql_query:
                    return {"error": "No SQL generated", "results": []}

                # Execute the SQL query
                logger.info("Executing SQL query", sql=sql_query[:200])
                execution_result = bq.execute_query(sql_query)

                # Extract results from the new Dict format
                results = execution_result.get('rows', [])
                row_count = execution_result.get('fetched_rows', len(results))
                total_rows = execution_result.get('total_rows', row_count)
                truncated = execution_result.get('truncated', False)

                return {
                    "sql": sql_query,
                    "results": results,
                    "row_count": row_count,
                    "total_rows": total_rows,
                    "truncated": truncated,
                    "explanation": sql_result.get("explanation", "")
                }

            except Exception as e:
                logger.error(f"SQL execution error: {e}")
                return {"error": str(e), "results": []}

        # Execute agent analysis with SQL capability
        result = await agent_hierarchy.analyze_query(
            query=request.query,
            sql_executor=sql_executor
        )

        return AgentAnalysisResponse(**result)

    except Exception as e:
        logger.error(f"Failed to analyze query: {e}")
        return AgentAnalysisResponse(
            status="error",
            query=request.query,
            agents_used=[],
            analysis="",
            routing={},
            error=str(e)
        )


@router.get("/hierarchy")
async def get_agent_hierarchy_info() -> Dict[str, Any]:
    """Get information about the agent hierarchy."""
    agent_hierarchy = get_agent_hierarchy_lazy()
    return agent_hierarchy.get_agent_summary()


@router.post("/route")
async def route_query(query: str) -> Dict[str, Any]:
    """
    Preview which agents would be selected for a query.
    Useful for debugging and understanding agent routing.
    """
    agent_hierarchy = get_agent_hierarchy_lazy()
    routing = agent_hierarchy.route_query(query)

    return {
        "query": query,
        "orchestrator": {
            "name": routing['orchestrator'].name,
            "role": routing['orchestrator'].role
        },
        "domain_experts": [
            {
                "expert": {
                    "name": domain['expert'].name,
                    "role": domain['expert'].role,
                    "keywords": domain['expert'].keywords
                },
                "sub_agents": [
                    {
                        "name": sa.name,
                        "role": sa.role,
                        "keywords": sa.keywords
                    }
                    for sa in domain['sub_agents']
                ]
            }
            for domain in routing['domain_experts']
        ]
    }


@router.post("/analyze-stream")
async def analyze_financial_query_stream(
    request: AgentAnalysisRequest,
    user: Optional[Dict] = Depends(get_current_user)
):
    """
    Analyze a financial query using the multi-agent system with streaming updates.

    Returns Server-Sent Events (SSE) stream with progressive updates:
    - Agent routing information
    - Execution plan
    - Query execution progress
    - Results as they become available
    - Final summary
    """
    # Get organization context for SQL generator
    org_id = user.get('organization_id') if user else None

    # Use a queue to collect events from nested callbacks
    event_queue = asyncio.Queue()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Send initial status
            await event_queue.put({'type': 'status', 'message': 'Understanding your financial question...'})
            yield f"data: {json.dumps({'type': 'status', 'message': 'Understanding your financial question...'}, default=json_serializer)}\n\n"

            # Get components with organization context
            agent_hierarchy = get_agent_hierarchy_lazy()
            sql_gen = get_sql_generator(organization_id=org_id)
            bq = get_bq_client()

            # Send routing information
            await event_queue.put({'type': 'status', 'message': 'Selecting specialized financial experts...'})
            yield f"data: {json.dumps({'type': 'status', 'message': 'Selecting specialized financial experts...'}, default=json_serializer)}\n\n"

            routing = agent_hierarchy.route_query(request.query)

            # Create more descriptive expert names
            expert_names = [d['expert'].role for d in routing['domain_experts']]
            expert_summary = ', '.join(expert_names) if len(expert_names) <= 2 else f"{expert_names[0]}, {expert_names[1]}, and {len(expert_names)-2} more"

            routing_data = {
                'type': 'routing',
                'data': {
                    'orchestrator': routing['orchestrator'].name,
                    'experts': [d['expert'].name for d in routing['domain_experts']]
                }
            }
            await event_queue.put(routing_data)
            yield f"data: {json.dumps(routing_data, default=json_serializer)}\n\n"

            # Send expert assignment message
            await event_queue.put({'type': 'status', 'message': f'Assigned: {expert_summary}'})
            yield f"data: {json.dumps({'type': 'status', 'message': f'Assigned: {expert_summary}'}, default=json_serializer)}\n\n"

            # Create SQL executor that sends events to queue
            async def sql_executor(natural_language_query: str) -> Dict[str, Any]:
                try:
                    # Notify SQL generation started with more context
                    await event_queue.put({'type': 'sql_generation', 'data': {'query': natural_language_query}})
                    await event_queue.put({'type': 'status', 'message': 'Generating SQL query...'})

                    sql_result = sql_gen.generate_sql(natural_language_query)

                    if isinstance(sql_result, list):
                        sql_result = {"results": sql_result, "sql": None}
                    elif not isinstance(sql_result, dict):
                        return {"error": f"Unexpected result type: {type(sql_result)}", "results": []}

                    if not sql_result or "error" in sql_result:
                        error_msg = sql_result.get("error", "Failed to generate SQL") if isinstance(sql_result, dict) else "Failed to generate SQL"
                        return {"error": error_msg, "results": []}

                    sql_query = sql_result.get("sql")
                    if not sql_query:
                        return {"error": "No SQL generated", "results": []}

                    # Notify SQL execution started
                    await event_queue.put({'type': 'sql_execution', 'data': {'sql': sql_query[:200]}})
                    await event_queue.put({'type': 'status', 'message': 'Executing query on SAP data...'})

                    # Use SQLGenerator.execute_query for proper pagination support
                    # Get target database type from sql_result if available
                    target_db_type = sql_result.get("target_database_type")
                    execution_result = sql_gen.execute_query(sql_query, target_db_type)

                    # Extract results from the new Dict format
                    results = execution_result.get('results', execution_result.get('rows', []))
                    row_count = execution_result.get('row_count', len(results))
                    total_rows = execution_result.get('total_rows', row_count)
                    truncated = execution_result.get('truncated', False)

                    result_data = {
                        "sql": sql_query,
                        "results": results,
                        "row_count": row_count,
                        "total_rows": total_rows,
                        "truncated": truncated,
                        "explanation": sql_result.get("explanation", ""),
                        # Include database_type and connector_id for "Load More" requests
                        "database_type": sql_result.get("target_database_type") or sql_gen.database_type,
                        "connector_id": sql_result.get("connector_id"),
                    }

                    # Include pagination info if available (for large non-aggregation queries)
                    if execution_result.get("pagination"):
                        result_data["pagination"] = execution_result["pagination"]

                    # Send query results with success message
                    truncation_note = f" (showing {row_count:,} of {total_rows:,})" if truncated else ""
                    await event_queue.put({'type': 'status', 'message': f'Retrieved {row_count:,} rows of financial data{truncation_note}'})
                    await event_queue.put({'type': 'query_results', 'data': result_data})

                    return result_data

                except Exception as e:
                    logger.error(f"SQL execution error: {e}")
                    return {"error": str(e), "results": []}

            # Execute agent analysis with streaming
            await event_queue.put({'type': 'status', 'message': 'Financial experts analyzing your data...'})
            yield f"data: {json.dumps({'type': 'status', 'message': 'Financial experts analyzing your data...'}, default=json_serializer)}\n\n"

            # Run analysis in background task
            async def run_analysis():
                result = await agent_hierarchy.analyze_query(
                    query=request.query,
                    sql_executor=sql_executor
                )
                await event_queue.put({'type': 'analysis_complete', 'data': result})

            analysis_task = asyncio.create_task(run_analysis())

            # Stream events as they arrive
            while not analysis_task.done():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                    yield f"data: {json.dumps(event, default=json_serializer)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
                    continue

            # Get final result
            await analysis_task

            # Drain remaining events
            while not event_queue.empty():
                event = await event_queue.get()
                if event.get('type') == 'analysis_complete':
                    result = event['data']

                    # Send execution plan
                    if result.get('execution_plan'):
                        yield f"data: {json.dumps({'type': 'execution_plan', 'data': result['execution_plan']}, default=json_serializer)}\n\n"

                    # Send execution logs progressively with delays
                    if result.get('execution_logs'):
                        for i, log in enumerate(result['execution_logs']):
                            yield f"data: {json.dumps({'type': 'execution_log', 'data': log}, default=json_serializer)}\n\n"
                            # Don't delay after the last log
                            if i < len(result['execution_logs']) - 1:
                                await asyncio.sleep(1.0)
                                # Send heartbeat to prevent buffering
                                yield f": heartbeat\n\n"

                    # Send analysis results
                    if result.get('analysis'):
                        yield f"data: {json.dumps({'type': 'analysis', 'data': result['analysis']}, default=json_serializer)}\n\n"

                    # Send final completion
                    yield f"data: {json.dumps({'type': 'complete', 'data': result}, default=json_serializer)}\n\n"
                else:
                    yield f"data: {json.dumps(event, default=json_serializer)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, default=json_serializer)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
