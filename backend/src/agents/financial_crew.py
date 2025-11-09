"""
Hierarchical Multi-Agent System for Financial Analysis
Level 1: Master Orchestrator
Level 2: Domain Experts (COPA, GL Account, Financial Accounting, Sales)
Sub-Agents: Specialized analysts under each domain
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import asyncio
import logging
import os
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

logger = logging.getLogger(__name__)


@dataclass
class AgentDefinition:
    """Definition of an agent with role, expertise, and backstory"""
    name: str
    role: str
    goal: str
    backstory: str
    keywords: List[str]  # Keywords to trigger this agent
    level: int  # 1 = orchestrator, 2 = domain expert, 3 = sub-agent


class FinancialAgentHierarchy:
    """
    Hierarchical agent system with intelligent routing
    """
    
    def __init__(self, sql_executor=None):
        self.sql_executor = sql_executor
        self.agents = self._define_agent_hierarchy()
    
    def _define_agent_hierarchy(self) -> Dict[str, AgentDefinition]:
        """Define all agents in the hierarchy"""
        
        agents = {}
        
        # ==================== LEVEL 1: MASTER ORCHESTRATOR ====================
        agents['master_orchestrator'] = AgentDefinition(
            name="Master Financial Orchestrator",
            role="Chief Financial Intelligence Officer",
            goal="Understand user queries, route to appropriate experts, and synthesize comprehensive insights",
            backstory="""You are the Master Financial AI Orchestrator with 20+ years of 
            experience across all financial domains. You understand COPA, GL accounts, 
            financial accounting, and sales operations. Your role is to:
            1. Analyze user questions to identify which domain experts are needed
            2. Coordinate multiple experts when complex cross-functional analysis is required
            3. Synthesize findings from multiple experts into clear, actionable insights
            4. Ensure compliance and accuracy across all financial reporting""",
            keywords=['analyze', 'comprehensive', 'overview', 'summary', 'compare', 'evaluate'],
            level=1
        )
        
        # ==================== LEVEL 2: COPA DOMAIN EXPERT ====================
        agents['copa_expert'] = AgentDefinition(
            name="COPA Expert",
            role="Profitability Analysis Specialist",
            goal="Analyze profitability using SAP COPA (CO-PA) data structures",
            backstory="""You are an expert in SAP CO-PA (Profitability Analysis) with deep 
            knowledge of:
            - CE1* and CE2* tables (COPA segment level data)
            - CE3* and CE4* tables (COPA line item data)
            - Value fields (VV001-VV999) representing revenue, costs, quantities
            - Profitability segments (product, customer, sales org, distribution channel)
            - Contribution margin analysis and variance analysis
            - Operating concern configuration and characteristics
            
            You can analyze profitability by any dimension and provide strategic insights.""",
            keywords=['copa', 'profitability', 'contribution margin', 'segment', 'value field', 
                     'operating concern', 'ce1', 'ce2', 'ce3', 'ce4'],
            level=2
        )
        
        # COPA Sub-Agents (Level 3)
        agents['copa_profitability_analyst'] = AgentDefinition(
            name="Profitability Analyst",
            role="COPA Profitability Specialist",
            goal="Calculate and analyze contribution margins, profit centers, and profitability segments",
            backstory="""You specialize in profitability calculations using COPA data. 
            You excel at:
            - Contribution margin analysis (CM1, CM2, CM3)
            - Profit center performance evaluation
            - Product line profitability
            - Customer profitability analysis
            - Variance analysis between plan and actual""",
            keywords=['margin', 'profit center', 'profitability segment', 'contribution'],
            level=3
        )
        
        agents['copa_product_costing'] = AgentDefinition(
            name="Product Costing Specialist",
            role="COPA Cost Analysis Expert",
            goal="Analyze product costs, COGS, and cost variances in COPA",
            backstory="""You are an expert in product costing within COPA framework.
            You analyze:
            - Cost of goods sold (COGS) by product
            - Standard vs actual cost variances
            - Cost component splits (material, labor, overhead)
            - Cost center allocations to products
            - Manufacturing cost analysis""",
            keywords=['cogs', 'product cost', 'cost variance', 'standard cost', 'manufacturing cost'],
            level=3
        )
        
        agents['copa_segment_analyst'] = AgentDefinition(
            name="Segment Analysis Expert",
            role="COPA Multi-Dimensional Analyst",
            goal="Perform cross-dimensional profitability analysis",
            backstory="""You specialize in multi-dimensional COPA analysis across:
            - Sales organization and distribution channel
            - Customer hierarchy and customer groups
            - Material hierarchy and product groups
            - Geographic regions and divisions
            - Time periods and planning versions""",
            keywords=['dimension', 'segment', 'cross-functional', 'hierarchy', 'multi-dimensional'],
            level=3
        )
        
        # ==================== LEVEL 2: GL ACCOUNT EXPERT ====================
        agents['gl_expert'] = AgentDefinition(
            name="GL Account Expert",
            role="General Ledger Specialist",
            goal="Analyze GL accounts, chart of accounts, and account balances",
            backstory="""You are an expert in General Ledger accounting with deep knowledge of:
            - Chart of accounts structure (SKA1, SKAT tables)
            - GL account master data (account groups, P&L vs balance sheet)
            - Account balances and movements (BSEG, GLT0)
            - Cost elements and cost centers
            - Financial statement mapping
            - Account reconciliation and closing processes
            
            You understand how GL accounts flow into financial statements.""",
            keywords=['gl account', 'general ledger', 'chart of accounts', 'account balance', 
                     'ska1', 'skat', 'bseg', 'financial statement mapping', 'cost element'],
            level=2
        )
        
        # GL Sub-Agents (Level 3)
        agents['gl_chart_specialist'] = AgentDefinition(
            name="Chart of Accounts Specialist",
            role="COA Structure Expert",
            goal="Analyze chart of accounts structure, account groups, and hierarchies",
            backstory="""You specialize in chart of accounts design and structure.
            You analyze:
            - Account number ranges and groupings
            - P&L accounts vs balance sheet accounts
            - Account hierarchies and rollups
            - FSV (Financial Statement Version) assignments
            - Account group classifications""",
            keywords=['chart of accounts', 'account group', 'account hierarchy', 'fsv', 'coa structure'],
            level=3
        )
        
        agents['gl_journal_analyst'] = AgentDefinition(
            name="Journal Entry Analyst",
            role="GL Transaction Expert",
            goal="Analyze journal entries, postings, and GL movements",
            backstory="""You are an expert in GL transactions and postings.
            You analyze:
            - Journal entry details and audit trails
            - Debit/credit balances and movements
            - Posting keys and transaction types
            - Document numbers and fiscal periods
            - Recurring entries and adjustments""",
            keywords=['journal entry', 'posting', 'transaction', 'debit', 'credit', 'document', 'bseg'],
            level=3
        )
        
        agents['gl_reconciliation'] = AgentDefinition(
            name="Account Reconciliation Expert",
            role="GL Reconciliation Specialist",
            goal="Perform account reconciliations and variance analysis",
            backstory="""You specialize in GL account reconciliations.
            You handle:
            - Balance sheet reconciliations
            - Sub-ledger to GL reconciliation
            - Intercompany reconciliations
            - Period-over-period variance analysis
            - Unexplained differences investigation""",
            keywords=['reconciliation', 'variance', 'balance verification', 'sub-ledger'],
            level=3
        )
        
        # ==================== LEVEL 2: FINANCIAL ACCOUNTING EXPERT ====================
        agents['financial_accounting_expert'] = AgentDefinition(
            name="Financial Accounting Expert",
            role="Financial Reporting & Compliance Specialist",
            goal="Ensure accurate financial reporting and GAAP/IFRS compliance",
            backstory="""You are a CPA and financial accounting expert with expertise in:
            - Financial statement preparation (P&L, Balance Sheet, Cash Flow)
            - GAAP and IFRS accounting standards
            - Financial consolidation and intercompany eliminations
            - Deferred revenue and accruals
            - Asset depreciation and amortization
            - Revenue recognition (ASC 606)
            - Lease accounting (ASC 842)
            - Financial ratios and KPIs
            
            You ensure all financial reporting is accurate, compliant, and decision-useful.""",
            keywords=['financial statement', 'gaap', 'ifrs', 'compliance', 'balance sheet', 
                     'p&l', 'income statement', 'cash flow', 'consolidation', 'financial reporting'],
            level=2
        )
        
        # Financial Accounting Sub-Agents (Level 3)
        agents['financial_statement_analyst'] = AgentDefinition(
            name="Financial Statement Analyst",
            role="Financial Statement Expert",
            goal="Analyze and prepare financial statements",
            backstory="""You specialize in financial statement analysis and preparation.
            You excel at:
            - Income statement (P&L) analysis
            - Balance sheet structure and health
            - Cash flow statement analysis
            - Statement of shareholders' equity
            - Financial statement footnotes and disclosures""",
            keywords=['income statement', 'balance sheet', 'cash flow statement', 'financial statements'],
            level=3
        )
        
        agents['gaap_compliance_officer'] = AgentDefinition(
            name="GAAP Compliance Officer",
            role="Accounting Standards Expert",
            goal="Ensure GAAP/IFRS compliance in all financial reporting",
            backstory="""You are an accounting standards expert ensuring compliance.
            You monitor:
            - Revenue recognition (ASC 606)
            - Lease accounting (ASC 842)
            - Financial instruments (ASC 820, 825)
            - Income taxes (ASC 740)
            - Consolidation rules (ASC 810)
            - Recent accounting standard updates""",
            keywords=['gaap', 'ifrs', 'asc 606', 'asc 842', 'accounting standards', 'compliance'],
            level=3
        )
        
        agents['consolidation_specialist'] = AgentDefinition(
            name="Consolidation Specialist",
            role="Financial Consolidation Expert",
            goal="Handle multi-entity consolidations and eliminations",
            backstory="""You specialize in financial consolidations.
            You handle:
            - Multi-entity financial consolidation
            - Intercompany eliminations
            - Currency translation adjustments
            - Non-controlling interests
            - Equity method investments""",
            keywords=['consolidation', 'intercompany', 'elimination', 'multi-entity', 'subsidiary'],
            level=3
        )
        
        # ==================== LEVEL 2: SALES EXPERT ====================
        agents['sales_expert'] = AgentDefinition(
            name="Sales Expert",
            role="Sales Operations & Analytics Specialist",
            goal="Analyze sales data, revenue, and customer metrics",
            backstory="""You are a sales analytics expert with deep knowledge of:
            - Sales orders and order-to-cash process (VBAK, VBAP, VBRK, VBRP)
            - Revenue recognition and deferred revenue
            - Sales organization hierarchy
            - Customer master data and segmentation
            - Sales performance metrics (quotas, attainment, pipeline)
            - Pricing and discount analysis
            - Sales forecasting and pipeline management
            
            You provide insights to drive sales growth and optimize revenue.""",
            keywords=['sales', 'revenue', 'order', 'customer', 'billing', 'invoice', 
                     'vbak', 'vbap', 'vbrk', 'sales order', 'sales performance'],
            level=2
        )
        
        # Sales Sub-Agents (Level 3)
        agents['revenue_recognition_specialist'] = AgentDefinition(
            name="Revenue Recognition Specialist",
            role="Revenue Accounting Expert",
            goal="Ensure proper revenue recognition and deferred revenue accounting",
            backstory="""You specialize in revenue recognition under ASC 606.
            You analyze:
            - Five-step revenue recognition process
            - Performance obligations and contract terms
            - Deferred revenue calculations
            - Revenue allocation and timing
            - Contract modifications and adjustments""",
            keywords=['revenue recognition', 'asc 606', 'deferred revenue', 'performance obligation'],
            level=3
        )
        
        agents['sales_analytics_expert'] = AgentDefinition(
            name="Sales Analytics Expert",
            role="Sales Performance Analyst",
            goal="Analyze sales performance, trends, and KPIs",
            backstory="""You are a sales analytics expert analyzing:
            - Sales trends and seasonality
            - Top customers and customer segments
            - Product mix and cross-sell opportunities
            - Sales rep performance and quotas
            - Win/loss analysis
            - Sales pipeline and conversion rates""",
            keywords=['sales trends', 'sales performance', 'sales kpi', 'pipeline', 'quota', 'attainment'],
            level=3
        )
        
        agents['customer_analysis_specialist'] = AgentDefinition(
            name="Customer Analysis Specialist",
            role="Customer Intelligence Expert",
            goal="Analyze customer behavior, lifetime value, and segmentation",
            backstory="""You specialize in customer analytics including:
            - Customer lifetime value (CLV)
            - Customer segmentation and profiling
            - Churn analysis and retention
            - Customer acquisition cost (CAC)
            - RFM analysis (Recency, Frequency, Monetary)
            - Customer satisfaction and NPS""",
            keywords=['customer', 'lifetime value', 'clv', 'churn', 'retention', 'segmentation', 'cac'],
            level=3
        )
        
        return agents
    
    def route_query(self, query: str) -> Dict[str, List[AgentDefinition]]:
        """
        Intelligently route query to relevant agents based on keywords
        Returns hierarchical structure of agents needed
        """
        query_lower = query.lower()
        
        # Find matching Level 2 agents (domain experts)
        level2_matches = []
        for agent_id, agent in self.agents.items():
            if agent.level == 2:
                if any(keyword in query_lower for keyword in agent.keywords):
                    level2_matches.append((agent_id, agent))
        
        # If no specific domain match, use all domain experts
        if not level2_matches:
            level2_matches = [(aid, a) for aid, a in self.agents.items() if a.level == 2]
        
        # For each Level 2 agent, find relevant Level 3 sub-agents
        routing = {
            'orchestrator': self.agents['master_orchestrator'],
            'domain_experts': []
        }
        
        for domain_id, domain_agent in level2_matches:
            sub_agents = []
            
            # Find Level 3 agents under this domain
            domain_prefix = domain_id.split('_')[0]  # e.g., 'copa', 'gl', 'sales'
            
            for agent_id, agent in self.agents.items():
                if agent.level == 3 and agent_id.startswith(domain_prefix):
                    # Check if sub-agent keywords match
                    if any(keyword in query_lower for keyword in agent.keywords):
                        sub_agents.append(agent)
            
            # If no specific sub-agent match, include all sub-agents for this domain
            if not sub_agents:
                sub_agents = [a for aid, a in self.agents.items() 
                            if a.level == 3 and aid.startswith(domain_prefix)]
            
            routing['domain_experts'].append({
                'expert': domain_agent,
                'sub_agents': sub_agents
            })
        
        return routing
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """Get summary of all agents in the hierarchy"""
        summary = {
            'total_agents': len(self.agents),
            'orchestrator': None,
            'domains': {}
        }
        
        # Get orchestrator
        summary['orchestrator'] = {
            'name': self.agents['master_orchestrator'].name,
            'role': self.agents['master_orchestrator'].role
        }
        
        # Group by domain
        domains = {}
        for agent_id, agent in self.agents.items():
            if agent.level == 2:
                domain_name = agent.name
                domains[domain_name] = {
                    'expert': agent.name,
                    'role': agent.role,
                    'sub_agents': []
                }
                
                # Find sub-agents
                domain_prefix = agent_id.split('_')[0]
                for sub_id, sub_agent in self.agents.items():
                    if sub_agent.level == 3 and sub_id.startswith(domain_prefix):
                        domains[domain_name]['sub_agents'].append({
                            'name': sub_agent.name,
                            'role': sub_agent.role
                        })

        summary['domains'] = domains
        return summary

    def create_crew_agents(self, agent_definitions: List[AgentDefinition]) -> List[Agent]:
        """Convert AgentDefinitions to CrewAI Agent objects"""
        crew_agents = []
        for agent_def in agent_definitions:
            crew_agent = Agent(
                role=agent_def.role,
                goal=agent_def.goal,
                backstory=agent_def.backstory,
                verbose=True,
                allow_delegation=False,  # Disable delegation for faster execution
                llm="gpt-4o"  # Use GPT-4o for CrewAI agents
            )
            crew_agents.append(crew_agent)
        return crew_agents

    def _generate_final_summary(self, original_query: str, sub_tasks: List[str], all_results: List[Dict]) -> str:
        """
        Generate a data-specific final summary based on actual query results.
        """
        summary = []
        summary.append("## Executive Summary")
        summary.append("")

        # Analyze each result set with actual data
        for i, result_data in enumerate(all_results, 1):
            query = result_data.get('query', f'Analysis {i}')
            results = result_data.get('results', [])
            row_count = result_data.get('row_count', 0)

            if row_count > 0 and results:
                summary.append(f"### {i}. {query}")
                summary.append("")

                # Show actual top records with all key data
                if row_count <= 5:
                    summary.append(f"Found {row_count} record(s):")
                    for idx, row in enumerate(results, 1):
                        summary.append(f"**#{idx}:**")
                        for key, value in row.items():
                            if value is not None:
                                # Format numbers nicely
                                if isinstance(value, float):
                                    summary.append(f"  - {key}: ${value:,.2f}" if 'amount' in key.lower() or 'revenue' in key.lower() or 'sales' in key.lower() or 'cost' in key.lower() or 'profit' in key.lower() else f"  - {key}: {value:,.2f}")
                                elif isinstance(value, int):
                                    summary.append(f"  - {key}: {value:,}")
                                else:
                                    summary.append(f"  - {key}: {value}")
                        summary.append("")
                else:
                    summary.append(f"Found {row_count} records. Top 5 shown:")
                    for idx, row in enumerate(results[:5], 1):
                        summary.append(f"**#{idx}:**")
                        for key, value in row.items():
                            if value is not None:
                                if isinstance(value, float):
                                    summary.append(f"  - {key}: ${value:,.2f}" if 'amount' in key.lower() or 'revenue' in key.lower() or 'sales' in key.lower() or 'cost' in key.lower() or 'profit' in key.lower() else f"  - {key}: {value:,.2f}")
                                elif isinstance(value, int):
                                    summary.append(f"  - {key}: {value:,}")
                                else:
                                    summary.append(f"  - {key}: {value}")
                        summary.append("")

                # Calculate and explain aggregates
                numeric_cols = {}
                for col in results[0].keys():
                    try:
                        values = [r[col] for r in results if r.get(col) is not None and isinstance(r[col], (int, float))]
                        if values:
                            numeric_cols[col] = {
                                "total": sum(values),
                                "avg": sum(values) / len(values),
                                "min": min(values),
                                "max": max(values),
                                "count": len(values)
                            }
                    except:
                        pass

                if numeric_cols:
                    summary.append("**Statistical Analysis:**")
                    for col, stats in numeric_cols.items():
                        is_money = any(term in col.lower() for term in ['amount', 'revenue', 'sales', 'cost', 'profit', 'price'])
                        if is_money:
                            summary.append(f"- **{col}**: Total ${stats['total']:,.2f} across {stats['count']} records, averaging ${stats['avg']:,.2f} per record (range: ${stats['min']:,.2f} to ${stats['max']:,.2f})")
                        else:
                            summary.append(f"- **{col}**: Total {stats['total']:,.2f}, averaging {stats['avg']:,.2f} (range: {stats['min']:,.2f} to {stats['max']:,.2f})")
                    summary.append("")

                # Add interpretation
                summary.append("**Key Insight:**")
                if 'customer' in query.lower() or 'client' in query.lower():
                    summary.append(f"The analysis identified the top performing customers/clients. The highest value customer shows significantly stronger performance in key metrics compared to others in the dataset.")
                elif 'product' in query.lower() or 'item' in query.lower():
                    summary.append(f"Product performance analysis reveals variation in sales and profitability. Top performers drive the majority of revenue.")
                elif 'trend' in query.lower() or 'over time' in query.lower():
                    summary.append(f"Time-series analysis shows the evolution of key metrics across the selected period.")
                else:
                    summary.append(f"The data shows measurable differences across the analyzed dimensions, with clear leaders and opportunities for optimization.")
                summary.append("")

        return "\n".join(summary)

    def _generate_query_insights(self, question: str, results: List[Dict], row_count: int) -> str:
        """
        Generate specific insights for a query result.
        This provides immediate analysis of the data returned.
        """
        if not results or row_count == 0:
            return "No data returned for this query."

        insights = []
        insights.append(f"**Query Analysis:** {question}")
        insights.append(f"**Rows Retrieved:** {row_count}")

        # Analyze data structure
        if results:
            columns = list(results[0].keys())
            insights.append(f"**Data Structure:** {len(columns)} columns")

            # Find numeric columns and their ranges
            numeric_cols = []
            for col in columns:
                try:
                    # Check if column has numeric values
                    values = [row[col] for row in results if row.get(col) is not None and isinstance(row[col], (int, float))]
                    if values:
                        numeric_cols.append({
                            "column": col,
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values) if values else 0
                        })
                except:
                    pass

            # Add key metrics
            if numeric_cols:
                insights.append("**Key Metrics:**")
                for nc in numeric_cols[:3]:  # Top 3 numeric columns
                    insights.append(f"- {nc['column']}: Range ${nc['min']:,.2f} - ${nc['max']:,.2f}, Avg ${nc['avg']:,.2f}")

            # Top records preview
            if row_count <= 10:
                insights.append(f"**All {row_count} records are displayed below.**")
            else:
                insights.append(f"**Top records are shown. Total: {row_count} rows.**")

        return "\n".join(insights)

    def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose a complex multi-part query into individual sub-tasks.
        Looks for numbered lists, bullet points, and logical separators.
        """
        sub_tasks = []

        # Check for numbered patterns: "1)", "1.", "1:"
        import re
        numbered_pattern = r'(?:^|\n)\s*(\d+)[\.:\)]\s*([^\n]+(?:\n(?!\s*\d+[\.:\)]).*)*)'
        matches = re.findall(numbered_pattern, query, re.MULTILINE)

        if matches and len(matches) > 1:
            # Found numbered list
            for num, task in matches:
                task_text = task.strip()
                if task_text:
                    sub_tasks.append(task_text)
            return sub_tasks

        # Check for bullet points or dashes
        bullet_pattern = r'(?:^|\n)\s*[-•*]\s*([^\n]+(?:\n(?!\s*[-•*]).*)*)'
        matches = re.findall(bullet_pattern, query, re.MULTILINE)

        if matches and len(matches) > 1:
            # Found bullet list
            for task in matches:
                task_text = task.strip()
                if task_text:
                    sub_tasks.append(task_text)
            return sub_tasks

        # Check for logical separators (and, also, then, additionally)
        separator_pattern = r'(?:,\s*(?:and|also|then|additionally)\s+|;\s*)'
        parts = re.split(separator_pattern, query, flags=re.IGNORECASE)

        if len(parts) > 1:
            for part in parts:
                task_text = part.strip()
                if task_text and len(task_text) > 10:  # Avoid very short fragments
                    sub_tasks.append(task_text)
            return sub_tasks

        # No decomposition needed - return original query
        return [query]

    async def _analyze_simple_mode(self, query: str, routing: Dict, sql_executor) -> Dict[str, Any]:
        """
        Simplified single-agent mode for faster execution.
        Uses only the most relevant domain expert without orchestrator or sub-agents.
        With intelligent task decomposition for multi-part queries.
        """
        try:
            import time
            start_time = time.time()

            # Decompose query into sub-tasks
            sub_tasks = self._decompose_query(query)
            is_complex = len(sub_tasks) > 1

            logger.info(f"Query decomposed into {len(sub_tasks)} sub-tasks")

            # Track execution results for table display (aggregate all results)
            execution_data = {"results": [], "row_count": 0, "all_results": []}

            # Track execution logs for transparency
            execution_logs = []
            execution_logs.append({
                "step": "Query Decomposition",
                "timestamp": time.time(),
                "status": "completed",
                "details": f"Detected {len(sub_tasks)} sub-task(s)",
                "sub_tasks": sub_tasks if is_complex else None
            })

            # Create SQL query tool with execution counter
            query_counter = {"count": 0}

            @tool("Execute SQL Query")
            def execute_sql_query(natural_language_query: str) -> str:
                """Execute a natural language query against the financial database.
                You can and SHOULD call this tool multiple times for different analyses.
                Each call executes a separate SQL query against the database."""
                nonlocal execution_data, execution_logs
                query_counter["count"] += 1
                query_start_time = time.time()

                logger.info(f"SQL Query Tool Called - Execution #{query_counter['count']}: {natural_language_query[:100]}")

                # Log query initiation
                execution_logs.append({
                    "step": f"SQL Query #{query_counter['count']}",
                    "timestamp": query_start_time,
                    "status": "started",
                    "details": f"Executing: {natural_language_query[:100]}..."
                })

                if sql_executor:
                    try:
                        import asyncio
                        import nest_asyncio

                        # Allow nested event loops (needed for CrewAI threads)
                        nest_asyncio.apply()

                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            logger.info(f"Calling sql_executor with query: {natural_language_query[:100]}")
                            results = loop.run_until_complete(sql_executor(natural_language_query))
                            logger.info(f"SQL executor returned: {type(results)}, keys: {results.keys() if isinstance(results, dict) else 'N/A'}")
                        finally:
                            loop.close()

                        if "error" in results:
                            logger.error(f"SQL executor returned error: {results['error']}")
                            return f"Error: {results['error']}"

                        # Store all execution results (for multi-query scenarios)
                        query_results = results.get('results', [])

                        # Generate immediate insights for this specific query result
                        query_insights = self._generate_query_insights(
                            natural_language_query,
                            query_results,
                            results.get('row_count', 0)
                        )

                        execution_data["all_results"].append({
                            "query": natural_language_query,
                            "results": query_results,
                            "row_count": results.get('row_count', 0),
                            "sql": results.get('sql', ''),
                            "insights": query_insights  # Add specific insights for this query
                        })

                        # Keep the last result as primary for table display
                        execution_data["results"] = query_results
                        execution_data["row_count"] = results.get('row_count', 0)
                        execution_data["sql"] = results.get('sql', '')

                        # Log successful query completion
                        execution_logs.append({
                            "step": f"SQL Query #{query_counter['count']}",
                            "timestamp": time.time(),
                            "status": "completed",
                            "details": f"Retrieved {results.get('row_count', 0)} rows",
                            "duration": f"{time.time() - query_start_time:.2f}s",
                            "sql": results.get('sql', '')[:200]
                        })

                        # Return ACTUAL DATA to the agent for analysis
                        output = []
                        output.append(f"✓ Query executed successfully")
                        output.append(f"Rows Retrieved: {results.get('row_count', 0)}")

                        # Include ACTUAL DATA so agent can reference specific values (optimized for speed)
                        if query_results and len(query_results) > 0:
                            columns = list(query_results[0].keys())
                            output.append(f"\nColumns: {', '.join(columns)}")

                            # Include first 10 rows in compact format for context
                            display_limit = min(len(query_results), 10)
                            output.append(f"\n=== DATA SAMPLE ({display_limit} of {len(query_results)} rows) ===")

                            # Compact JSON format for faster processing
                            import json
                            for i, row in enumerate(query_results[:display_limit], 1):
                                output.append(f"{i}. {json.dumps(row)}")

                            if len(query_results) > display_limit:
                                output.append(f"[{len(query_results) - display_limit} more rows with same structure]")

                            output.append(f"\n=== CRITICAL: Use ACTUAL values from data above ===")
                            output.append(f"✓ Reference specific names/IDs and numbers (e.g., 'Product B: $750K revenue, 33.3% margin')")
                            output.append(f"✓ Identify TOP/BOTTOM performers with exact values")
                            output.append(f"✓ Calculate totals, averages, comparisons from the data")
                            output.append(f"✗ NO generic statements like 'some segments' - name them!")
                            if len(query_results) > display_limit:
                                output.append(f"\n⚠️ IMPORTANT: Your analysis is based on {display_limit} sample rows shown above.")
                                output.append(f"   You MUST mention in your response that the full dataset has {len(query_results)} rows")
                                output.append(f"   and that your insights are based on the sample of {display_limit} rows provided.")

                        return "\n".join(output)
                    except Exception as e:
                        logger.error(f"Exception in execute_sql_query tool: {e}", exc_info=True)
                        execution_logs.append({
                            "step": f"SQL Query #{query_counter['count']}",
                            "timestamp": time.time(),
                            "status": "failed",
                            "details": f"Error: {str(e)}",
                            "duration": f"{time.time() - query_start_time:.2f}s"
                        })
                        return f"Error executing query: {str(e)}"
                return "SQL executor not available - cannot query database"

            # Use only the first (most relevant) domain expert
            if routing['domain_experts']:
                expert = routing['domain_experts'][0]['expert']
                agent_def = expert
            else:
                # Fallback to orchestrator
                agent_def = routing['orchestrator']

            # Create single agent
            crew_agents = [self.create_crew_agents([agent_def])[0]]

            # Build task description with sub-tasks if complex query
            if is_complex:
                task_description = f"""You are tasked with completing a MULTI-PART financial analysis. This requires executing MULTIPLE separate SQL queries.

Original Query: {query}

=== SUB-TASKS TO COMPLETE ({len(sub_tasks)} SEPARATE ANALYSES REQUIRED) ===
"""
                for i, sub_task in enumerate(sub_tasks, 1):
                    task_description += f"\nTask {i}: {sub_task}\n"

                task_description += f"""
=== CRITICAL EXECUTION REQUIREMENTS ===
✓ You MUST execute {len(sub_tasks)} SEPARATE SQL queries (one per sub-task above)
✓ Call the "Execute SQL Query" tool {len(sub_tasks)} TIMES - DO NOT try to answer everything in one query
✓ Complete each sub-task in order before moving to the next
✓ After executing all {len(sub_tasks)} queries, synthesize all findings into a comprehensive report

=== EXECUTION WORKFLOW (FOLLOW THIS EXACTLY) ===
Step 1: Use "Execute SQL Query" tool for Task 1 → Analyze results
Step 2: Use "Execute SQL Query" tool for Task 2 → Analyze results
Step 3: Use "Execute SQL Query" tool for Task 3 → Analyze results
Step 4: Use "Execute SQL Query" tool for Task 4 → Analyze results
Step 5: Synthesize all findings into final comprehensive analysis

=== RESPONSE STRUCTURE ===
Use markdown headings to organize your response:

## Task 1: [Task Name]
[Analysis based on SQL query results]

## Task 2: [Task Name]
[Analysis based on SQL query results]

## Task 3: [Task Name]
[Analysis based on SQL query results]

## Task 4: [Task Name]
[Analysis based on SQL query results]

## Comprehensive Summary
[Synthesize all findings and provide strategic recommendations]

REMEMBER: You have access to the SQL tool - use it {len(sub_tasks)} times to complete all tasks!"""
            else:
                task_description = f"""Query: {query}

STEPS:
1. Use "Execute SQL Query" tool to get data
2. Analyze the ACTUAL DATA returned (it will show you the real values)
3. Write analysis using SPECIFIC values from the data

REQUIREMENTS:
✓ Reference ACTUAL names/numbers (e.g., "Product B: $750K, 33.3% margin")
✓ Identify TOP/BOTTOM with exact values (e.g., "Line E leads at $950K")
✓ Calculate totals/averages from data
✗ NO generic terms like "some segments" or "certain products"
⚠️ If data sample is shown (e.g., 10 of 100 rows), YOU MUST state: "Based on sample of X rows from total Y rows"

OUTPUT FORMAT (use markdown):
## Key Findings
- **Finding 1** with specific numbers
- **Finding 2** with actual data points

## Analysis
Brief analysis with **bold** for key metrics

## Recommendations
1. **Action 1** based on specific insight
2. **Action 2** with data justification

Keep it concise, specific, and data-driven."""

            # Create single task
            task = Task(
                description=task_description,
                agent=crew_agents[0],
                expected_output="Comprehensive financial analysis addressing all requirements with data-driven insights",
                tools=[execute_sql_query]
            )

            # Create crew with sequential process (faster than hierarchical)
            crew = Crew(
                agents=crew_agents,
                tasks=[task],
                process=Process.sequential,  # Sequential is faster than hierarchical
                verbose=True
            )

            # Log agent execution start
            execution_logs.append({
                "step": "Agent Execution",
                "timestamp": time.time(),
                "status": "started",
                "details": f"Running {agent_def.name} with CrewAI"
            })

            # Execute with longer timeout for simple mode
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(crew.kickoff)
                try:
                    result = future.result(timeout=240)  # 4 minute timeout for simple mode
                except concurrent.futures.TimeoutError:
                    return {
                        "status": "timeout",
                        "query": query,
                        "agents_used": [agent_def.role],
                        "analysis": "Analysis timed out after 4 minutes. Try simplifying the query.",
                        "routing": {
                            "mode": "simple",
                            "agent": agent_def.name
                        },
                        "error": "Execution timeout",
                        "execution_logs": execution_logs
                    }

            # Log completion
            total_duration = time.time() - start_time
            execution_logs.append({
                "step": "Completion",
                "timestamp": time.time(),
                "status": "completed",
                "details": f"Analysis completed in {total_duration:.2f}s"
            })

            # Build execution plan summary
            execution_plan = {
                "agent": agent_def.name,
                "agent_role": agent_def.role,
                "mode": "simple",
                "is_complex_query": is_complex,
                "total_sub_tasks": len(sub_tasks),
                "sub_tasks": sub_tasks if is_complex else None,
                "expected_queries": len(sub_tasks) if is_complex else 1,
                "actual_queries_executed": len(execution_data.get("all_results", [])),
                "total_duration": f"{total_duration:.2f}s"
            }

            # Include all SQL queries if multiple were executed
            if len(execution_data.get("all_results", [])) > 0:
                execution_data["all_sql_queries"] = execution_data.get("all_results", [])

            # Generate data-specific final summary for complex queries
            final_summary = str(result)
            if is_complex and len(execution_data.get("all_results", [])) > 0:
                final_summary = self._generate_final_summary(query, sub_tasks, execution_data.get("all_results", []))

            return {
                "status": "success",
                "query": query,
                "agents_used": [agent_def.role],
                "analysis": final_summary,
                "execution": execution_data if execution_data.get("results") else None,
                "execution_plan": execution_plan,
                "execution_logs": execution_logs,
                "routing": {
                    "mode": "simple",
                    "agent": agent_def.name,
                    "sub_tasks": sub_tasks if is_complex else None,
                    "task_count": len(sub_tasks),
                    "queries_executed": len(execution_data.get("all_results", []))
                }
            }

        except Exception as e:
            logger.error(f"Error in simple mode analysis: {e}")
            return {
                "status": "error",
                "query": query,
                "agents_used": [],
                "analysis": "",
                "routing": {"mode": "simple"},
                "error": str(e)
            }

    async def analyze_query(self, query: str, sql_executor=None, use_simple_mode=True) -> Dict[str, Any]:
        """
        Execute multi-agent analysis of a financial query

        Args:
            query: User's financial question
            sql_executor: Async function that takes a natural language query and returns:
                         {
                             "sql": "generated SQL query",
                             "results": [...],
                             "row_count": int,
                             "explanation": "query explanation"
                         }
                         This integrates with the existing NLP-to-SQL framework.
            use_simple_mode: If True, use simplified single-agent mode for faster execution (default: True)

        Returns:
            Dict with analysis results including insights from all agents
        """
        try:
            # Route query to appropriate agents
            routing = self.route_query(query)

            # Simple mode: Use only domain experts (no orchestrator, no sub-agents)
            if use_simple_mode:
                return await self._analyze_simple_mode(query, routing, sql_executor)

            # Create SQL query tool for agents to use
            @tool("Execute SQL Query")
            def execute_sql_query(natural_language_query: str) -> str:
                """
                Execute a natural language query against the financial database.

                Args:
                    natural_language_query: A natural language question about financial data

                Returns:
                    String representation of query results including SQL, data, and explanation

                Example:
                    "What is the total revenue for Q1 2024?"
                    "Show me the top 5 customers by sales"
                    "Calculate gross margin by product line"
                """
                if sql_executor:
                    try:
                        # Run the async sql_executor synchronously within the tool
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If already in async context, use run_until_complete
                            results = asyncio.create_task(sql_executor(natural_language_query))
                            results = loop.run_until_complete(results)
                        else:
                            results = asyncio.run(sql_executor(natural_language_query))

                        # Format results for agent consumption
                        if "error" in results:
                            return f"Error: {results['error']}"

                        output = []
                        output.append(f"SQL Query: {results.get('sql', 'N/A')}")
                        output.append(f"Rows Returned: {results.get('row_count', 0)}")
                        output.append(f"Explanation: {results.get('explanation', '')}")

                        # Include sample of results
                        query_results = results.get('results', [])
                        if query_results:
                            output.append(f"\nSample Data (first 5 rows):")
                            for i, row in enumerate(query_results[:5]):
                                output.append(f"  Row {i+1}: {row}")

                        return "\n".join(output)

                    except Exception as e:
                        return f"Error executing query: {str(e)}"
                return "SQL executor not available - cannot query database"

            # Build list of all agents involved
            all_agent_defs = [routing['orchestrator']]
            for domain in routing['domain_experts']:
                all_agent_defs.append(domain['expert'])
                all_agent_defs.extend(domain['sub_agents'])

            # Convert to CrewAI agents
            crew_agents = self.create_crew_agents(all_agent_defs)

            # Create tasks for each agent
            tasks = []

            # Orchestrator task
            orchestrator_task = Task(
                description=f"""Analyze this financial query and coordinate with domain experts: {query}

                Your role is to:
                1. Understand what financial domains are needed (COPA, GL, Financial Accounting, Sales)
                2. Determine what data needs to be retrieved
                3. Coordinate with domain experts to gather comprehensive insights
                4. Synthesize findings into a clear, actionable response
                """,
                agent=crew_agents[0],
                expected_output="Comprehensive analysis plan and coordination strategy"
            )
            tasks.append(orchestrator_task)

            # Domain expert tasks
            agent_idx = 1
            for domain in routing['domain_experts']:
                domain_task = Task(
                    description=f"""As a {domain['expert'].role}, analyze this query: {query}

                    Your expertise areas: {', '.join(domain['expert'].keywords)}

                    Use the SQL query tool to retrieve relevant data and provide expert analysis.
                    Coordinate with your sub-agents for detailed insights.
                    """,
                    agent=crew_agents[agent_idx],
                    expected_output=f"Expert analysis from {domain['expert'].role} perspective",
                    tools=[execute_sql_query]
                )
                tasks.append(domain_task)
                agent_idx += 1

                # Sub-agent tasks
                for sub_agent in domain['sub_agents']:
                    sub_task = Task(
                        description=f"""As a {sub_agent.role}, provide specialized analysis for: {query}

                        Your specialization: {', '.join(sub_agent.keywords)}

                        Use the SQL query tool to retrieve specific data points and provide detailed insights.
                        """,
                        agent=crew_agents[agent_idx],
                        expected_output=f"Specialized insights from {sub_agent.role}",
                        tools=[execute_sql_query]
                    )
                    tasks.append(sub_task)
                    agent_idx += 1

            # Create and execute crew with timeout
            # Use sequential process for better performance (no manager overhead)
            crew = Crew(
                agents=crew_agents,
                tasks=tasks,
                process=Process.sequential,  # Sequential is faster than hierarchical
                verbose=True
            )

            # Execute the crew with timeout (3 minutes for complex mode)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(crew.kickoff)
                try:
                    result = future.result(timeout=180)  # 3 minute timeout
                except concurrent.futures.TimeoutError:
                    return {
                        "status": "timeout",
                        "query": query,
                        "agents_used": [agent.role for agent in all_agent_defs],
                        "analysis": "Analysis timed out after 90 seconds. The query is complex and requires more time than allocated.",
                        "routing": {
                            "orchestrator": routing['orchestrator'].name,
                            "domains": [
                                {
                                    "expert": domain['expert'].name,
                                    "sub_agents": [sa.name for sa in domain['sub_agents']]
                                }
                                for domain in routing['domain_experts']
                            ]
                        },
                        "error": "Crew execution timeout"
                    }

            return {
                "status": "success",
                "query": query,
                "agents_used": [agent.role for agent in all_agent_defs],
                "analysis": str(result),
                "routing": {
                    "orchestrator": routing['orchestrator'].name,
                    "domains": [
                        {
                            "expert": domain['expert'].name,
                            "sub_agents": [sa.name for sa in domain['sub_agents']]
                        }
                        for domain in routing['domain_experts']
                    ]
                }
            }

        except Exception as e:
            logger.error(f"Error in agent analysis: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }


# Singleton instance
_agent_hierarchy = None

def get_agent_hierarchy(sql_executor=None):
    """Get or create agent hierarchy singleton"""
    global _agent_hierarchy
    if _agent_hierarchy is None:
        _agent_hierarchy = FinancialAgentHierarchy(sql_executor)
    return _agent_hierarchy
