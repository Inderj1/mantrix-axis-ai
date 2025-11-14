# ROIC (Return on Invested Capital) Calculation Guide

## Formula Structure

```
ROIC = NOPAT Margin × Capital Turnover
     = (NOPAT / Revenue) × (Revenue / Invested Capital)
     = NOPAT / Invested Capital
```

## Components

### 1. NOPAT (Net Operating Profit After Tax)
**Formula:** `Revenue - Operating Costs - Taxes`

For customer-level analysis:
- **Revenue**: Total sales/revenue from the customer
- **Operating Costs**: Total costs associated with serving the customer
- **Taxes**: Tax burden (can be estimated as a percentage of operating profit)

**Simplified:** `NOPAT = (Revenue - Costs) × (1 - Tax Rate)`

### 2. Invested Capital
**Formula:** `Working Capital + Fixed Assets`

Components:
- **Working Capital**: Current assets - Current liabilities (typically 2.6% of revenue as per example)
- **Fixed Assets**: Long-term assets like equipment, facilities (typically 33.7% of revenue as per example)

**For customer-level:** `Invested Capital = Revenue × (Working Capital % + Fixed Assets %)`
- Default: `Invested Capital = Revenue × (2.6% + 33.7%) = Revenue × 36.3%`

### 3. ROIC Calculation
**Final Formula:** `ROIC = NOPAT / Invested Capital × 100%`

## SQL Query Pattern for Top 10 Customers by ROIC

```sql
WITH customer_metrics AS (
  SELECT
    customer_name,
    customer_segment,
    SUM(revenue) AS total_revenue,
    SUM(cost) AS total_cost,

    -- Calculate NOPAT (assuming 25% tax rate)
    (SUM(revenue) - SUM(cost)) * 0.75 AS nopat,

    -- Calculate Invested Capital (36.3% of revenue)
    SUM(revenue) * 0.363 AS invested_capital

  FROM drinkaz-big-query.dataset.profitability_table
  GROUP BY customer_name, customer_segment
),
roic_analysis AS (
  SELECT
    customer_name,
    customer_segment,
    total_revenue,
    total_cost,
    nopat,
    invested_capital,

    -- Calculate ROIC
    CASE
      WHEN invested_capital > 0
      THEN (nopat / invested_capital) * 100
      ELSE 0
    END AS roic_percentage,

    -- Calculate NOPAT Margin
    CASE
      WHEN total_revenue > 0
      THEN (nopat / total_revenue) * 100
      ELSE 0
    END AS nopat_margin,

    -- Calculate Capital Turnover
    CASE
      WHEN invested_capital > 0
      THEN total_revenue / invested_capital
      ELSE 0
    END AS capital_turnover

  FROM customer_metrics
)
SELECT
  customer_name,
  customer_segment,
  ROUND(total_revenue, 2) AS revenue,
  ROUND(total_cost, 2) AS cost,
  ROUND(nopat, 2) AS nopat,
  ROUND(invested_capital, 2) AS invested_capital,
  ROUND(roic_percentage, 2) AS roic_percent,
  ROUND(nopat_margin, 2) AS nopat_margin_percent,
  ROUND(capital_turnover, 2) AS capital_turnover_ratio
FROM roic_analysis
WHERE invested_capital > 0
ORDER BY roic_percentage DESC
LIMIT 10;
```

## Key Insights from ROIC Analysis

1. **High ROIC (>20%)**: Indicates efficient use of capital - these customers generate strong returns
2. **Medium ROIC (10-20%)**: Acceptable returns, room for improvement
3. **Low ROIC (<10%)**: Poor capital efficiency - may need strategy adjustment
4. **Negative ROIC**: Losing money - immediate attention required

## ROIC Drivers

### NOPAT Margin Improvement:
- Increase prices
- Reduce costs
- Improve operational efficiency

### Capital Turnover Improvement:
- Increase sales velocity
- Reduce inventory levels
- Optimize working capital
- Improve asset utilization

## Example Interpretation

If a customer has:
- Revenue: $1,000,000
- Cost: $600,000
- Tax Rate: 25%

Calculations:
1. NOPAT = ($1,000,000 - $600,000) × 0.75 = $300,000
2. Invested Capital = $1,000,000 × 0.363 = $363,000
3. ROIC = $300,000 / $363,000 = 82.6%
4. NOPAT Margin = $300,000 / $1,000,000 = 30%
5. Capital Turnover = $1,000,000 / $363,000 = 2.75x

This customer generates an 82.6% return on invested capital, which is excellent.

## Notes

- Adjust Working Capital % and Fixed Assets % based on actual business data if available
- Tax rate can be adjusted based on applicable tax jurisdiction (default 25%)
- Consider customer-specific costs like CAC (Customer Acquisition Cost) if available
- Factor in customer lifetime value for long-term ROIC analysis
