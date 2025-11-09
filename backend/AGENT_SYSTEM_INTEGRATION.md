# Multi-Agent Financial Analysis System - Integration Guide

## Overview

The multi-agent system is now **fully integrated** with the existing NLP-to-SQL framework. Agents can analyze natural language questions about financial data, execute SQL queries, and provide comprehensive insights.

## Architecture

### 3-Level Hierarchical Agent System

```
Level 1: Master Orchestrator
    ├── Coordinates all analysis
    └── Synthesizes findings from domain experts

Level 2: Domain Experts (4 experts)
    ├── COPA Expert (Profitability Analysis)
    ├── GL Account Expert (General Ledger)
    ├── Financial Accounting Expert (Financial Reporting)
    └── Sales Expert (Sales Operations & Analytics)

Level 3: Sub-Agents (12 specialists - 3 per domain)
    ├── COPA Sub-agents:
    │   ├── Profitability Analyst
    │   ├── Product Costing Specialist
    │   └── Segment Analysis Expert
    │
    ├── GL Sub-agents:
    │   ├── Chart of Accounts Specialist
    │   ├── Journal Entry Analyst
    │   └── Account Reconciliation Expert
    │
    ├── Financial Accounting Sub-agents:
    │   ├── Financial Statement Analyst
    │   ├── GAAP Compliance Officer
    │   └── Consolidation Specialist
    │
    └── Sales Sub-agents:
        ├── Revenue Recognition Specialist
        ├── Sales Analytics Expert
        └── Customer Analysis Specialist
```

## NLP-to-SQL Integration

### How It Works

1. **User Query** → Agent Mode interface receives natural language question
2. **Agent Routing** → System selects relevant domain experts based on keywords
3. **SQL Tool Access** → Agents have access to "Execute SQL Query" tool that:
   - Takes natural language input (e.g., "What is total revenue for Q1 2024?")
   - Calls existing `SQLGenerator.generate_sql()` to convert NL → SQL
   - Executes SQL via `BigQueryClient.execute_query()`
   - Returns formatted results to agents
4. **Multi-Agent Collaboration** → Agents work together using CrewAI's hierarchical process
5. **Synthesized Response** → Results are combined and returned to user

### Code Flow

```python
# In agent_routes.py
async def sql_executor(natural_language_query: str):
    # Generate SQL from natural language
    sql_result = await sql_gen.generate_sql(natural_language_query)

    # Execute SQL
    execution_result = bq.execute_query(sql_result["sql"])

    return {
        "sql": sql_query,
        "results": execution_result["results"],
        "row_count": execution_result["row_count"]
    }

# Agents can use this tool
@tool("Execute SQL Query")
def execute_sql_query(nl_query: str) -> str:
    """Agents call this to query financial data"""
    results = await sql_executor(nl_query)
    return formatted_results
```

## API Endpoints

### 1. Analyze Financial Query
```bash
POST /api/v1/agents/analyze
{
    "query": "What are the top 5 customers by profitability?",
    "context": {}
}
```

**Response:**
```json
{
    "status": "success",
    "query": "What are the top 5 customers by profitability?",
    "agents_used": [
        "Chief Financial Intelligence Officer",
        "Profitability Analysis Specialist",
        "Profitability Analyst",
        "Sales Operations & Analytics Specialist",
        "Customer Analysis Specialist"
    ],
    "analysis": "...",
    "routing": {
        "orchestrator": "Master Financial Orchestrator",
        "domains": [
            {
                "expert": "COPA Expert",
                "sub_agents": ["Profitability Analyst"]
            }
        ]
    }
}
```

### 2. Get Agent Hierarchy
```bash
GET /api/v1/agents/hierarchy
```

### 3. Preview Agent Routing
```bash
POST /api/v1/agents/route?query=Show me gross margin trends
```

## Agent Capabilities

Each agent has:
- **Role**: Specific financial expertise area
- **Goal**: What the agent aims to accomplish
- **Backstory**: Domain knowledge and experience
- **Keywords**: Triggers for query routing
- **Tools**: Access to NLP-to-SQL query executor

### Example Agent Definitions

**COPA Expert** (Level 2):
- Keywords: `copa`, `profitability`, `contribution margin`, `segment`
- Can analyze: CE1/CE2/CE3/CE4 tables, value fields, profitability segments
- Sub-agents: Profitability Analyst, Product Costing Specialist, Segment Analysis Expert

**Sales Expert** (Level 2):
- Keywords: `sales`, `revenue`, `order`, `customer`, `billing`
- Can analyze: VBAK, VBAP, VBRK tables, sales performance, customer metrics
- Sub-agents: Revenue Recognition Specialist, Sales Analytics Expert, Customer Analysis Specialist

## Usage Example

```javascript
// Frontend - Agent Mode Interface
const response = await fetch('/api/v1/agents/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        query: "Analyze contribution margin by product line for Q4 2024"
    })
});

const data = await response.json();
// Display: agents used, analysis, routing details
```

## Benefits

1. **Intelligent Routing**: Automatically selects relevant financial experts
2. **Deep Expertise**: Each sub-agent has specialized knowledge
3. **SQL Integration**: Agents can query actual financial data
4. **Collaborative Analysis**: Multiple agents work together on complex tasks
5. **Comprehensive Insights**: Synthesized findings from all experts

## Files Modified

- `backend/src/agents/financial_crew.py` - Agent hierarchy definitions
- `backend/src/agents/__init__.py` - Agent exports
- `backend/src/api/agent_routes.py` - API endpoints with NLP-to-SQL integration
- `backend/src/main.py` - Route registration
- `frontend/src/components/AgentModeInterface.jsx` - UI for agent collaboration
- `frontend/src/components/EnhancedSidebar.jsx` - Agent Mode tab

## Next Steps

To test the integration:

1. Start the backend server
2. Navigate to Agent Mode in the UI
3. Ask a financial question like:
   - "What is our total revenue by sales organization?"
   - "Show me top 10 products by contribution margin"
   - "Analyze customer profitability segments"
4. Watch agents collaborate and execute SQL queries
5. Review the comprehensive analysis with routing details

## Technical Notes

- Uses GPT-4o for agent intelligence (via OpenAI API)
- CrewAI hierarchical process for coordination
- Async SQL execution integrated with event loop
- Keyword-based routing with fallback to all agents
- Results formatted for agent consumption and user display
- 90-second timeout on crew execution
- Note: Multi-agent hierarchical process can be slow due to sequential LLM calls and agent delegation
