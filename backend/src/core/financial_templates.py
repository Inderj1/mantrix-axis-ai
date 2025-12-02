"""Financial query templates for the three-tiered GL hierarchy system."""

from typing import Dict, List, Optional, Any
from src.core.industry_configs import QueryTemplate

# Financial Query Templates organized by hierarchy level

FINANCIAL_QUERY_TEMPLATES = {
    # Level 1: Financial Metrics Templates
    "l1_gross_margin": QueryTemplate(
        name="gross_margin_analysis",
        description="Calculate gross margin with revenue and COGS",
        pattern=r"(gross\s+margin|gross\s+profit)(?!.*breakdown)(?!.*component)",
        sql_template="""
        WITH financial_metrics AS (
            SELECT 
                {dimensions},
                SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN gl_account BETWEEN '5000' AND '5999' THEN amount ELSE 0 END) as cogs
            FROM `{project}.{dataset}.gl_transactions`
            WHERE {time_filter}
                {additional_filters}
            GROUP BY {group_by}
        )
        SELECT 
            *,
            revenue - cogs as gross_margin,
            SAFE_DIVIDE(revenue - cogs, revenue) * 100 as gross_margin_pct
        FROM financial_metrics
        ORDER BY gross_margin DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["dimensions", "time_filter", "additional_filters", "group_by"]
    ),
    
    "l1_operating_income": QueryTemplate(
        name="operating_income_analysis",
        description="Calculate operating income (gross margin minus operating expenses)",
        pattern=r"operating\s+(income|profit|earnings)",
        sql_template="""
        WITH financial_data AS (
            SELECT 
                {dimensions},
                SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN gl_account BETWEEN '5000' AND '5999' THEN amount ELSE 0 END) as cogs,
                SUM(CASE WHEN gl_account BETWEEN '6000' AND '6999' THEN amount ELSE 0 END) as operating_expenses
            FROM `{project}.{dataset}.gl_transactions`
            WHERE {time_filter}
                {additional_filters}
            GROUP BY {group_by}
        )
        SELECT 
            *,
            revenue - cogs as gross_margin,
            revenue - cogs - operating_expenses as operating_income,
            SAFE_DIVIDE(revenue - cogs - operating_expenses, revenue) * 100 as operating_margin_pct
        FROM financial_data
        ORDER BY operating_income DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["dimensions", "time_filter", "additional_filters", "group_by"]
    ),
    
    "l1_ebitda": QueryTemplate(
        name="ebitda_calculation",
        description="Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)",
        pattern=r"ebitda|earnings\s+before",
        sql_template="""
        WITH ebitda_calc AS (
            SELECT 
                {dimensions},
                -- Operating Income
                SUM(CASE 
                    WHEN gl_account BETWEEN '4000' AND '4999' THEN amount 
                    WHEN gl_account BETWEEN '5000' AND '6999' THEN -amount 
                    ELSE 0 
                END) as operating_income,
                -- Add back D&A
                SUM(CASE 
                    WHEN gl_account IN ('6810', '6820', '6830') THEN amount 
                    ELSE 0 
                END) as depreciation,
                SUM(CASE 
                    WHEN gl_account IN ('6840', '6850') THEN amount 
                    ELSE 0 
                END) as amortization
            FROM `{project}.{dataset}.gl_transactions`
            WHERE {time_filter}
                {additional_filters}
            GROUP BY {group_by}
        )
        SELECT 
            *,
            operating_income + depreciation + amortization as ebitda,
            SAFE_DIVIDE(operating_income + depreciation + amortization, 
                       ABS(operating_income + depreciation + amortization)) * 
                       (operating_income + depreciation + amortization) as ebitda_normalized
        FROM ebitda_calc
        ORDER BY ebitda DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["dimensions", "time_filter", "additional_filters", "group_by"]
    ),
    
    "l1_net_income": QueryTemplate(
        name="net_income_analysis",
        description="Calculate net income (bottom line profit)",
        pattern=r"net\s+(income|profit|earnings)|bottom\s+line",
        sql_template="""
        SELECT 
            {dimensions},
            SUM(CASE 
                WHEN gl_account BETWEEN '4000' AND '4999' THEN amount  -- Revenue
                WHEN gl_account BETWEEN '5000' AND '8999' THEN -amount -- All expenses
                ELSE 0 
            END) as net_income,
            SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END) as total_revenue,
            SUM(CASE WHEN gl_account BETWEEN '5000' AND '8999' THEN amount ELSE 0 END) as total_expenses,
            SAFE_DIVIDE(
                SUM(CASE 
                    WHEN gl_account BETWEEN '4000' AND '4999' THEN amount 
                    WHEN gl_account BETWEEN '5000' AND '8999' THEN -amount 
                    ELSE 0 
                END),
                SUM(CASE WHEN gl_account BETWEEN '4000' AND '4999' THEN amount ELSE 0 END)
            ) * 100 as net_margin_pct
        FROM `{project}.{dataset}.gl_transactions`
        WHERE {time_filter}
            {additional_filters}
        GROUP BY {group_by}
        ORDER BY net_income DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["dimensions", "time_filter", "additional_filters", "group_by"]
    ),
    
    # Level 2: Sub-Bucket Breakdown Templates
    "l2_revenue_breakdown": QueryTemplate(
        name="revenue_breakdown",
        description="Break down revenue by sub-categories",
        pattern=r"(revenue|sales).*(breakdown|break\s+down|components|composition)",
        sql_template="""
        SELECT 
            CASE 
                WHEN gl_account BETWEEN '4000' AND '4299' THEN 'Product Sales'
                WHEN gl_account BETWEEN '4300' AND '4499' THEN 'Service Revenue'
                WHEN gl_account BETWEEN '4500' AND '4799' THEN 'Other Revenue'
                ELSE 'Unclassified Revenue'
            END as revenue_category,
            SUM(amount) as total_amount,
            COUNT(DISTINCT gl_account) as account_count,
            ARRAY_AGG(DISTINCT gl_account ORDER BY gl_account LIMIT 10) as sample_accounts
        FROM `{project}.{dataset}.gl_transactions`
        WHERE gl_account BETWEEN '4000' AND '4999'
            AND {time_filter}
            {additional_filters}
        GROUP BY revenue_category
        ORDER BY total_amount DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["time_filter", "additional_filters"]
    ),
    
    "l2_cogs_breakdown": QueryTemplate(
        name="cogs_breakdown",
        description="Break down Cost of Goods Sold by components",
        pattern=r"(cogs|cost\s+of\s+goods).*(breakdown|break\s+down|components|composition)",
        sql_template="""
        SELECT 
            CASE 
                WHEN gl_account BETWEEN '5000' AND '5299' THEN 'Material Costs'
                WHEN gl_account BETWEEN '5300' AND '5499' THEN 'Direct Labor'
                WHEN gl_account BETWEEN '5500' AND '5799' THEN 'Manufacturing Overhead'
                WHEN gl_account BETWEEN '5800' AND '5999' THEN 'Other COGS'
                ELSE 'Unclassified COGS'
            END as cost_component,
            SUM(amount) as total_amount,
            SAFE_DIVIDE(SUM(amount), 
                       SUM(SUM(amount)) OVER ()) * 100 as percentage_of_total,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_transaction_amount
        FROM `{project}.{dataset}.gl_transactions`
        WHERE gl_account BETWEEN '5000' AND '5999'
            AND {time_filter}
            {additional_filters}
        GROUP BY cost_component
        ORDER BY total_amount DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["time_filter", "additional_filters"]
    ),
    
    "l2_opex_breakdown": QueryTemplate(
        name="operating_expense_breakdown",
        description="Break down operating expenses by category",
        pattern=r"(operating\s+expense|opex).*(breakdown|break\s+down|components|by\s+category)",
        sql_template="""
        WITH opex_categories AS (
            SELECT 
                CASE 
                    WHEN gl_account BETWEEN '6000' AND '6199' THEN 'Sales & Distribution'
                    WHEN gl_account BETWEEN '6200' AND '6299' THEN 'Marketing & Advertising'
                    WHEN gl_account BETWEEN '6300' AND '6499' THEN 'General & Administrative'
                    WHEN gl_account BETWEEN '6500' AND '6599' THEN 'Research & Development'
                    WHEN gl_account BETWEEN '6600' AND '6799' THEN 'Other Operating'
                    WHEN gl_account IN ('6810', '6820', '6830') THEN 'Depreciation'
                    WHEN gl_account IN ('6840', '6850') THEN 'Amortization'
                    ELSE 'Unclassified OpEx'
                END as expense_category,
                gl_account,
                gl_description,
                amount
            FROM `{project}.{dataset}.gl_transactions`
            WHERE gl_account BETWEEN '6000' AND '6999'
                AND {time_filter}
                {additional_filters}
        )
        SELECT 
            expense_category,
            SUM(amount) as total_expenses,
            SAFE_DIVIDE(SUM(amount), 
                       SUM(SUM(amount)) OVER ()) * 100 as percentage_of_opex,
            COUNT(DISTINCT gl_account) as unique_accounts,
            COUNT(*) as transaction_count,
            MIN(amount) as min_transaction,
            MAX(amount) as max_transaction,
            AVG(amount) as avg_transaction
        FROM opex_categories
        GROUP BY expense_category
        ORDER BY total_expenses DESC
        """,
        required_tables=["gl_transactions"],
        parameters=["time_filter", "additional_filters"]
    ),
    
    # Level 3: GL Account Detail Templates
    # Note: Table names should come from Weaviate schema search, not hardcoded
    "l3_gl_total_amount": QueryTemplate(
        name="gl_account_total_amount",
        description="Calculate total amount by GL account",
        pattern=r"total\s+amount\s+by\s+gl\s+account|sum.*by\s+gl\s+account|gl\s+account.*total",
        sql_template="""
        SELECT
            GL_Account,
            GL_Account_Description,
            ROUND(SUM(GL_Amount_in_CC), 2) AS total_amount
        FROM `{project}.{dataset}.{primary_table}`
        WHERE GL_Account IS NOT NULL
            {additional_filters}
        GROUP BY GL_Account, GL_Account_Description
        ORDER BY GL_Account
        """,
        required_tables=[],  # Tables come from Weaviate search
        parameters=["primary_table", "additional_filters"]
    ),
    
    "l3_specific_account": QueryTemplate(
        name="specific_gl_account_detail",
        description="Show detailed transactions for specific GL accounts",
        pattern=r"gl\s+account\s+\d{4,6}|account\s+number\s+\d{4,6}",
        sql_template="""
        SELECT 
            date,
            gl_account,
            gl_description,
            amount,
            CASE 
                WHEN amount > 0 THEN 'Debit'
                ELSE 'Credit'
            END as entry_type,
            reference_number,
            vendor_name,
            {additional_fields}
        FROM `{project}.{dataset}.gl_transactions`
        WHERE gl_account = '{gl_account_number}'
            AND {time_filter}
            {additional_filters}
        ORDER BY date DESC, ABS(amount) DESC
        LIMIT 1000
        """,
        required_tables=["gl_transactions"],
        parameters=["gl_account_number", "time_filter", "additional_filters", "additional_fields"]
    ),
    
    "l3_description_search": QueryTemplate(
        name="gl_description_search",
        description="Search GL transactions by description keywords",
        pattern=r"(transactions|entries|charges|expenses)\s+(for|containing|with).*",
        sql_template="""
        SELECT 
            date,
            gl_account,
            gl_description,
            amount,
            {dimensions},
            reference_number,
            vendor_name
        FROM `{project}.{dataset}.gl_transactions`
        WHERE LOWER(gl_description) LIKE LOWER('%{search_term}%')
            AND {time_filter}
            {additional_filters}
        ORDER BY date DESC, ABS(amount) DESC
        LIMIT 500
        """,
        required_tables=["gl_transactions"],
        parameters=["search_term", "dimensions", "time_filter", "additional_filters"]
    ),
    
    "l3_vendor_expenses": QueryTemplate(
        name="vendor_expense_detail",
        description="Show expenses by vendor with GL account detail",
        pattern=r"vendor\s+expenses|expenses\s+by\s+vendor|supplier\s+payments",
        sql_template="""
        SELECT 
            vendor_name,
            gl_account,
            gl_description,
            SUM(amount) as total_amount,
            COUNT(*) as transaction_count,
            MIN(date) as first_transaction,
            MAX(date) as last_transaction,
            ARRAY_AGG(DISTINCT gl_account ORDER BY gl_account) as gl_accounts_used
        FROM `{project}.{dataset}.gl_transactions`
        WHERE vendor_name IS NOT NULL
            AND amount > 0  -- Expenses are positive in GL
            AND {time_filter}
            {additional_filters}
        GROUP BY vendor_name, gl_account, gl_description
        HAVING SUM(amount) > 0
        ORDER BY total_amount DESC
        LIMIT 1000
        """,
        required_tables=["gl_transactions"],
        parameters=["time_filter", "additional_filters"]
    ),
    
    # Comparison Templates (work across all levels)
    "comparison_period_over_period": QueryTemplate(
        name="period_over_period_comparison",
        description="Compare metrics between two time periods",
        pattern=r"compare|vs\s+last|year\s+over\s+year|month\s+over\s+month",
        sql_template="""
        WITH current_period AS (
            SELECT 
                {dimensions},
                {metric_calculation} as metric_value
            FROM `{project}.{dataset}.gl_transactions`
            WHERE {current_period_filter}
            GROUP BY {group_by}
        ),
        previous_period AS (
            SELECT 
                {dimensions},
                {metric_calculation} as metric_value
            FROM `{project}.{dataset}.gl_transactions`
            WHERE {previous_period_filter}
            GROUP BY {group_by}
        )
        SELECT 
            COALESCE(c.{primary_dimension}, p.{primary_dimension}) as {primary_dimension},
            c.metric_value as current_value,
            p.metric_value as previous_value,
            c.metric_value - p.metric_value as absolute_change,
            SAFE_DIVIDE(c.metric_value - p.metric_value, p.metric_value) * 100 as percent_change
        FROM current_period c
        FULL OUTER JOIN previous_period p 
            ON c.{primary_dimension} = p.{primary_dimension}
        ORDER BY current_value DESC NULLS LAST
        """,
        required_tables=["gl_transactions"],
        parameters=["dimensions", "metric_calculation", "current_period_filter", 
                   "previous_period_filter", "group_by", "primary_dimension"]
    ),
    
    # Trend Analysis Template
    "trend_analysis": QueryTemplate(
        name="financial_trend_analysis",
        description="Show financial metrics trend over time",
        pattern=r"trend|over\s+time|by\s+(month|quarter|year)|historical",
        sql_template="""
        SELECT 
            {time_dimension} as period,
            {metric_calculation} as metric_value,
            LAG({metric_calculation}) OVER (ORDER BY {time_dimension}) as previous_period,
            {metric_calculation} - LAG({metric_calculation}) OVER (ORDER BY {time_dimension}) as period_change,
            SAFE_DIVIDE(
                {metric_calculation} - LAG({metric_calculation}) OVER (ORDER BY {time_dimension}),
                LAG({metric_calculation}) OVER (ORDER BY {time_dimension})
            ) * 100 as percent_change
        FROM `{project}.{dataset}.gl_transactions`
        WHERE {time_filter}
            {additional_filters}
        GROUP BY {time_dimension}
        ORDER BY {time_dimension}
        """,
        required_tables=["gl_transactions"],
        parameters=["time_dimension", "metric_calculation", "time_filter", "additional_filters"]
    )
}


def get_financial_template(query: str, hierarchy_level: int) -> Optional[QueryTemplate]:
    """Get the most appropriate financial template for a query."""
    import re
    
    # Filter templates by hierarchy level
    level_prefixes = {
        1: "l1_",
        2: "l2_", 
        3: "l3_"
    }
    
    # First try to find level-specific templates
    for template_name, template in FINANCIAL_QUERY_TEMPLATES.items():
        if template_name.startswith(level_prefixes.get(hierarchy_level, "")):
            if re.search(template.pattern, query, re.IGNORECASE):
                return template
    
    # Then check comparison and trend templates (work across all levels)
    for template_name in ["comparison_period_over_period", "trend_analysis"]:
        template = FINANCIAL_QUERY_TEMPLATES.get(template_name)
        if template and re.search(template.pattern, query, re.IGNORECASE):
            return template
    
    return None


def apply_financial_template(
    template: QueryTemplate,
    context: Dict[str, Any],
    project: str,
    dataset: str
) -> str:
    """Apply a financial template with the given context."""
    # Default parameter values
    params = {
        "project": project,
        "dataset": dataset,
        "dimensions": "1",  # Default to no dimensions
        "group_by": "1",
        "time_filter": context.get("time_filter", "1=1"),
        "additional_filters": "",
        "additional_fields": ""
    }
    
    # Add dimensions if specified
    if context.get("dimensions"):
        dims = context["dimensions"]
        params["dimensions"] = ", ".join(dims)
        params["group_by"] = ", ".join(dims)
        params["primary_dimension"] = dims[0] if dims else "1"
    
    # Add filters
    if context.get("filters"):
        filter_conditions = []
        for field, value in context["filters"].items():
            filter_conditions.append(f"AND {field} = '{value}'")
        params["additional_filters"] = " ".join(filter_conditions)
    
    # Add metric calculation for flexible templates
    if context.get("metric_calculation"):
        params["metric_calculation"] = context["metric_calculation"]
    
    # Add time dimensions for trend analysis
    if "trend" in template.name:
        time_dim_map = {
            "month": "DATE_TRUNC(date, MONTH)",
            "quarter": "DATE_TRUNC(date, QUARTER)",
            "year": "EXTRACT(YEAR FROM date)"
        }
        # Default to month if not specified
        params["time_dimension"] = time_dim_map.get("month")
    
    # Handle period comparisons
    if "comparison" in template.name:
        # This would be enhanced based on the specific comparison type
        params["current_period_filter"] = context.get("time_filter", "1=1")
        params["previous_period_filter"] = "1=1"  # Would be calculated based on comparison type
    
    # Format the SQL template
    sql = template.sql_template
    for param, value in params.items():
        sql = sql.replace(f"{{{param}}}", str(value))
    
    return sql