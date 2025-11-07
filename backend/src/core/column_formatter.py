"""
Column Formatter - Intelligent formatting rules for different data types
Automatically adds $ signs, commas, percentages, and other formatting to appropriate columns
"""

from typing import Dict, List, Set
import re


class ColumnFormatter:
    """Intelligent column formatting based on column names and data types."""

    # Column patterns that should be formatted as currency (with $ and commas)
    CURRENCY_PATTERNS = [
        r'.*revenue.*',
        r'.*sales.*',
        r'.*cost.*',
        r'.*cogs.*',
        r'.*price.*',
        r'.*amount.*',
        r'.*value.*',
        r'.*total.*',
        r'.*sum.*',
        r'.*expense.*',
        r'.*profit.*',
        r'.*income.*',
        r'.*margin(?!.*percent).*',  # margin but not margin_percent
        r'.*ebitda.*',
        r'.*gross.*',
        r'.*net.*',
        r'.*budget.*',
        r'.*spend.*',
        r'.*payment.*',
        r'.*fee.*',
        r'.*charge.*',
        r'.*invoice.*',
        r'.*liability.*',
        r'.*asset.*',
        r'.*equity.*',
        r'.*balance.*',
        r'.*freight.*',
        r'.*discount.*',
        r'.*rebate.*',
        r'.*commission.*',
        r'.*wage.*',
        r'.*salary.*',
        r'.*tax(?!.*rate).*',  # tax but not tax_rate
    ]

    # Column patterns that should be formatted as percentages
    PERCENTAGE_PATTERNS = [
        r'.*percent.*',
        r'.*pct.*',
        r'.*rate.*',
        r'.*margin.*percent.*',
        r'.*margin.*pct.*',
        r'.*growth.*',
        r'.*change.*',
        r'.*variance.*',
        r'.*ratio.*',
        r'.*_%.*',
    ]

    # Column patterns that should be formatted with commas only (no $)
    NUMERIC_PATTERNS = [
        r'.*quantity.*',
        r'.*qty.*',
        r'.*count.*',
        r'.*number.*',
        r'.*volume.*',
        r'.*units.*',
        r'.*cases.*',
        r'.*items.*',
        r'.*orders.*',
        r'.*transactions.*',
    ]

    # SAP COPA specific value fields (VV codes)
    SAP_VALUE_FIELDS = [
        'VV001', 'VV002', 'VV003', 'VV004', 'VV005',
        'VV010', 'VV020', 'VV030', 'VV040', 'VV050',
        'VV100', 'VV110', 'VV120', 'VV130', 'VV140',
        'VV200', 'VV210', 'VV220', 'VV230', 'VV240',
    ]

    def __init__(self):
        self.currency_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.CURRENCY_PATTERNS]
        self.percentage_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.PERCENTAGE_PATTERNS]
        self.numeric_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.NUMERIC_PATTERNS]

    def is_currency_column(self, column_name: str) -> bool:
        """Check if column should be formatted as currency."""
        column_name_clean = column_name.strip().lower()

        # Check SAP value fields
        if any(vv in column_name.upper() for vv in self.SAP_VALUE_FIELDS):
            return True

        # Check currency patterns
        return any(regex.match(column_name_clean) for regex in self.currency_regex)

    def is_percentage_column(self, column_name: str) -> bool:
        """Check if column should be formatted as percentage."""
        column_name_clean = column_name.strip().lower()
        return any(regex.match(column_name_clean) for regex in self.percentage_regex)

    def is_numeric_column(self, column_name: str) -> bool:
        """Check if column should be formatted with commas (no $)."""
        column_name_clean = column_name.strip().lower()
        return any(regex.match(column_name_clean) for regex in self.numeric_regex)

    def get_format_expression(self, column_name: str, table_alias: str = None) -> str:
        """
        Get the SQL formatting expression for a column.

        Args:
            column_name: Name of the column
            table_alias: Optional table alias (e.g., 'copa', 't1')

        Returns:
            Formatted SQL expression
        """
        column_ref = f"{table_alias}.{column_name}" if table_alias else column_name

        # Check for percentage first (most specific)
        if self.is_percentage_column(column_name):
            return f"CONCAT(CAST(ROUND({column_ref}, 2) AS STRING), '%')"

        # Check for currency
        elif self.is_currency_column(column_name):
            return f"CONCAT('$', FORMAT('%,.2f', {column_ref}))"

        # Check for numeric (commas only)
        elif self.is_numeric_column(column_name):
            return f"FORMAT('%,d', CAST({column_ref} AS INT64))"

        # No formatting needed
        else:
            return column_ref

    def should_format_column(self, column_name: str) -> bool:
        """Check if column needs any formatting."""
        return (self.is_currency_column(column_name) or
                self.is_percentage_column(column_name) or
                self.is_numeric_column(column_name))

    def get_formatting_rules_for_prompt(self) -> str:
        """Get formatting rules to include in LLM prompt."""
        return """
## COLUMN FORMATTING RULES - CRITICAL FOR READABILITY

**ALWAYS apply these formatting rules to make results readable:**

### 1. Currency Columns (Add $ and commas):
Apply `CONCAT('$', FORMAT('%,.2f', column_name))` to:
- Revenue, Sales, Gross_Revenue, Net_Sales
- Cost, COGS, Total_COGS, Expenses
- Price, Amount, Value, Total
- Profit, Margin (when not %), Income
- EBITDA, Gross, Net (when monetary)
- Budget, Spend, Payment, Fee, Charge
- Invoice, Freight, Discount, Rebate
- Commission, Wage, Salary, Tax (when not rate)
- SAP value fields: VV001, VV002, VV003, etc.

**CRITICAL**: The FORMAT function syntax MUST be exactly:
- `FORMAT('%,.2f', value)` for currency with 2 decimals
- `FORMAT('%,d', value)` for whole numbers
- DO NOT use `FORMAT('%\'d', ...)` - this is INVALID
- DO NOT use complex FLOOR/ROUND combinations - use FORMAT directly

**Example**:
```sql
-- ✅ CORRECT:
CONCAT('$', FORMAT('%,.2f', Gross_Revenue)) as revenue,
CONCAT('$', FORMAT('%,.2f', Total_COGS)) as cost

-- ❌ WRONG (DO NOT USE):
CONCAT('$', FORMAT('%\'d', CAST(FLOOR(Gross_Revenue) AS INT64))) -- INVALID SYNTAX
```

### 2. Percentage Columns (Add %):
Apply `CONCAT(CAST(ROUND(column_name, 2) AS STRING), '%')` to:
- Margin_Percent, Margin_Pct
- Growth_Rate, Change_Percent
- Any column ending in _percent, _pct, _rate
- Calculated percentages (growth, variance, ratio)

**Example**:
```sql
CONCAT(CAST(ROUND(margin_percent, 2) AS STRING), '%') as margin,
CONCAT(CAST(ROUND(yoy_growth, 2) AS STRING), '%') as growth
```

### 3. Numeric Columns (Add commas, no $):
Apply `FORMAT('%,d', CAST(column_name AS INT64))` to:
- Quantity, Qty, Count, Number
- Volume, Units, Cases, Items
- Order_Count, Transaction_Count

**Example**:
```sql
FORMAT('%,d', CAST(quantity AS INT64)) as qty,
FORMAT('%,d', CAST(order_count AS INT64)) as orders
```

### 4. Calculated Fields - Format Results:
When calculating new fields, apply formatting to the result:

```sql
-- Revenue calculation
CONCAT('$', FORMAT('%,.2f', SUM(Gross_Revenue))) as total_revenue

-- Margin calculation
CONCAT(CAST(ROUND(SAFE_DIVIDE(profit, revenue) * 100, 2) AS STRING), '%') as margin_pct

-- Count aggregation
FORMAT('%,d', CAST(COUNT(DISTINCT customer_id) AS INT64)) as customer_count
```

### 5. Multi-Column Queries:
**Format EVERY applicable column** in the SELECT clause:

```sql
SELECT
  Customer,
  Sold_to_Name,
  CONCAT('$', FORMAT('%,.2f', SUM(Gross_Revenue))) as revenue,
  CONCAT('$', FORMAT('%,.2f', SUM(Total_COGS))) as cogs,
  CONCAT('$', FORMAT('%,.2f', SUM(Gross_Revenue) - SUM(Total_COGS))) as gross_profit,
  CONCAT(CAST(ROUND(SAFE_DIVIDE(SUM(Gross_Revenue) - SUM(Total_COGS), SUM(Gross_Revenue)) * 100, 2) AS STRING), '%') as margin_pct,
  FORMAT('%,d', CAST(COUNT(DISTINCT Sales_Order_KDAUF) AS INT64)) as order_count
FROM ...
```

### 6. Important Notes:
- ✅ ALWAYS format monetary values with $ and commas
- ✅ ALWAYS format percentages with %
- ✅ ALWAYS format counts/quantities with commas
- ✅ Apply formatting to BOTH raw columns AND calculated fields
- ✅ Use SAFE_DIVIDE to prevent division by zero
- ✅ Use COALESCE(column, 0) before formatting to handle NULLs
- ✅ Alias formatted columns with readable names

### 7. Before/After Example:

**❌ BAD (No Formatting):**
```sql
SELECT
  Customer,
  SUM(Gross_Revenue) as revenue,
  SUM(Total_COGS) as cogs,
  (SUM(Gross_Revenue) - SUM(Total_COGS)) / SUM(Gross_Revenue) * 100 as margin
FROM dataset_25m_table
```

**✅ GOOD (Proper Formatting):**
```sql
SELECT
  Customer,
  CONCAT('$', FORMAT('%,.2f', SUM(COALESCE(Gross_Revenue, 0)))) as revenue,
  CONCAT('$', FORMAT('%,.2f', SUM(COALESCE(Total_COGS, 0)))) as cogs,
  CONCAT('$', FORMAT('%,.2f', SUM(COALESCE(Gross_Revenue, 0)) - SUM(COALESCE(Total_COGS, 0)))) as gross_profit,
  CONCAT(CAST(ROUND(SAFE_DIVIDE(SUM(Gross_Revenue) - SUM(Total_COGS), SUM(Gross_Revenue)) * 100, 2) AS STRING), '%') as margin_pct
FROM dataset_25m_table
```

**USER EXPECTATION**: When users see revenue, cost, or any monetary value, they expect:
- $1,234,567.89 (NOT 1234567.89)
- 25.5% (NOT 0.255 or 25.5)
- 1,234 orders (NOT 1234)

**CRITICAL**: Format ALL applicable columns - this makes results presentation-ready!
"""

    def format_example_query(self, query: str) -> str:
        """Add formatting to an example query (for demonstration)."""
        # This is a helper to show before/after
        # In practice, the LLM will generate formatted queries directly
        return query


# Singleton instance
column_formatter = ColumnFormatter()
