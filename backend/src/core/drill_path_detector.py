"""
Drill Path Detector - Auto-detect drill-down hierarchies from schema.

Analyzes table schemas to find common hierarchical relationships:
- Time: year → quarter → month → week → day
- Geography: country → region → state → city
- Product: category → subcategory → product
- Organization: department → team → employee

This enables Superset-like drill-down without manual configuration.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import structlog

logger = structlog.get_logger()


class DrillPathDetector:
    """
    Detects drill-down hierarchies from table schema metadata.

    Uses column naming patterns and semantic analysis to identify
    natural drill-down paths in the data.
    """

    # Common hierarchy patterns (ordered from high to low granularity)
    HIERARCHY_PATTERNS = {
        "time": {
            "columns": ["year", "quarter", "month", "week", "day", "date", "hour"],
            "patterns": [
                r"^(fiscal_)?year$",
                r"^(fiscal_)?quarter$",
                r"^month(_name|_num)?$",
                r"^week(_num|_of_year)?$",
                r"^day(_of_week|_of_month|_name)?$",
                r"^date$",
                r"^hour$"
            ],
            "order": ["year", "quarter", "month", "week", "day", "date", "hour"]
        },
        "geography": {
            "columns": ["continent", "country", "region", "state", "province", "city", "zip", "postal"],
            "patterns": [
                r"^continent$",
                r"^country(_code|_name)?$",
                r"^region(_name)?$",
                r"^(state|province)(_code|_name)?$",
                r"^city(_name)?$",
                r"^(zip|postal)(_code)?$"
            ],
            "order": ["continent", "country", "region", "state", "province", "city", "zip", "postal"]
        },
        "product": {
            "columns": ["category", "subcategory", "product", "sku", "item", "variant"],
            "patterns": [
                r"^(product_)?category(_name)?$",
                r"^(product_)?subcategory(_name)?$",
                r"^product(_name|_id)?$",
                r"^(sku|item)(_id)?$",
                r"^variant(_id)?$"
            ],
            "order": ["category", "subcategory", "product", "sku", "item", "variant"]
        },
        "organization": {
            "columns": ["company", "division", "department", "team", "manager", "employee"],
            "patterns": [
                r"^company(_name)?$",
                r"^division(_name)?$",
                r"^department(_name)?$",
                r"^team(_name)?$",
                r"^manager(_name|_id)?$",
                r"^employee(_name|_id)?$"
            ],
            "order": ["company", "division", "department", "team", "manager", "employee"]
        },
        "customer": {
            "columns": ["segment", "tier", "type", "customer", "account"],
            "patterns": [
                r"^customer_segment$",
                r"^(customer_)?tier$",
                r"^customer_type$",
                r"^customer(_name|_id)?$",
                r"^account(_name|_id)?$"
            ],
            "order": ["segment", "tier", "type", "customer", "account"]
        },
        "sales_channel": {
            "columns": ["channel", "store", "location", "outlet"],
            "patterns": [
                r"^(sales_)?channel$",
                r"^store(_name|_id)?$",
                r"^location(_name)?$",
                r"^outlet(_name|_id)?$"
            ],
            "order": ["channel", "store", "location", "outlet"]
        }
    }

    # Date column patterns for time hierarchy extraction
    DATE_COLUMN_PATTERNS = [
        r".*_date$",
        r".*_at$",
        r"^date$",
        r"^created$",
        r"^updated$",
        r"^timestamp$"
    ]

    def __init__(self):
        """Initialize the detector."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self._compiled_patterns = {}
        for hierarchy_type, config in self.HIERARCHY_PATTERNS.items():
            self._compiled_patterns[hierarchy_type] = [
                re.compile(p, re.IGNORECASE) for p in config["patterns"]
            ]

        self._date_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DATE_COLUMN_PATTERNS
        ]

    def detect_hierarchies(
        self,
        columns: List[Dict[str, Any]],
        table_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect possible drill-down paths from column metadata.

        Args:
            columns: List of column metadata dicts with 'name' and optionally 'type'
            table_name: Optional table name for context

        Returns:
            List of detected hierarchy dicts:
            [
                {
                    "type": "time",
                    "path": ["year", "quarter", "month"],
                    "columns": ["fiscal_year", "fiscal_quarter", "month_name"],
                    "confidence": 0.9
                },
                ...
            ]
        """
        if not columns:
            return []

        column_names = [c["name"].lower() if isinstance(c, dict) else c.lower() for c in columns]
        detected = []

        # Check each hierarchy type
        for hierarchy_type, config in self.HIERARCHY_PATTERNS.items():
            matches = self._find_hierarchy_matches(column_names, hierarchy_type, config)

            if len(matches) >= 2:
                # Sort by hierarchy order
                order = config["order"]
                sorted_matches = sorted(
                    matches,
                    key=lambda x: order.index(x["level"]) if x["level"] in order else 999
                )

                path = [m["level"] for m in sorted_matches]
                columns_matched = [m["column"] for m in sorted_matches]

                # Calculate confidence based on number of matches and pattern strength
                confidence = min(0.95, 0.5 + (len(matches) * 0.15))

                detected.append({
                    "type": hierarchy_type,
                    "path": path,
                    "columns": columns_matched,
                    "confidence": round(confidence, 2)
                })

        # Check for date columns that could support time drill-down
        date_columns = self._find_date_columns(column_names)
        if date_columns and not any(h["type"] == "time" for h in detected):
            # Add synthetic time hierarchy for date columns
            detected.append({
                "type": "time",
                "path": ["year", "quarter", "month", "day"],
                "columns": date_columns,
                "confidence": 0.7,
                "synthetic": True,  # Indicates drill expressions need to be generated
                "source_column": date_columns[0]
            })

        # Sort by confidence
        detected.sort(key=lambda x: x["confidence"], reverse=True)

        logger.info(
            "Hierarchies detected",
            table=table_name,
            count=len(detected),
            types=[h["type"] for h in detected]
        )

        return detected

    def _find_hierarchy_matches(
        self,
        column_names: List[str],
        hierarchy_type: str,
        config: Dict
    ) -> List[Dict]:
        """Find columns matching a hierarchy type."""
        matches = []
        patterns = self._compiled_patterns[hierarchy_type]

        for col in column_names:
            for i, pattern in enumerate(patterns):
                if pattern.match(col):
                    # Determine the hierarchy level from the pattern
                    level = config["order"][min(i, len(config["order"]) - 1)]
                    matches.append({
                        "column": col,
                        "level": level,
                        "pattern_index": i
                    })
                    break

        return matches

    def _find_date_columns(self, column_names: List[str]) -> List[str]:
        """Find columns that appear to be date/timestamp columns."""
        date_cols = []
        for col in column_names:
            for pattern in self._date_patterns:
                if pattern.match(col):
                    date_cols.append(col)
                    break
        return date_cols

    def get_next_drill_level(
        self,
        hierarchy: Dict[str, Any],
        current_level: str
    ) -> Optional[str]:
        """
        Get the next drill-down level in a hierarchy.

        Args:
            hierarchy: Hierarchy dict from detect_hierarchies
            current_level: Current dimension being viewed

        Returns:
            Next dimension to drill into, or None if at lowest level
        """
        path = hierarchy.get("path", [])
        columns = hierarchy.get("columns", [])

        # Find current position
        try:
            # Try to find by level name
            if current_level in path:
                idx = path.index(current_level)
            else:
                # Try to find by column name
                idx = columns.index(current_level)

            # Return next level if available
            if idx < len(path) - 1:
                return path[idx + 1]
            if idx < len(columns) - 1:
                return columns[idx + 1]

        except ValueError:
            pass

        return None

    def get_drill_column(
        self,
        hierarchy: Dict[str, Any],
        level: str
    ) -> Optional[str]:
        """
        Get the actual column name for a hierarchy level.

        Args:
            hierarchy: Hierarchy dict
            level: Level name (e.g., "month")

        Returns:
            Actual column name in the table
        """
        path = hierarchy.get("path", [])
        columns = hierarchy.get("columns", [])

        try:
            idx = path.index(level)
            if idx < len(columns):
                return columns[idx]
        except ValueError:
            # Level might already be a column name
            if level in columns:
                return level

        return None

    def build_drill_sql_expression(
        self,
        hierarchy: Dict[str, Any],
        level: str,
        db_type: str = "bigquery"
    ) -> Optional[str]:
        """
        Build SQL expression for synthetic time hierarchy drill-down.

        For date columns, generates EXTRACT or DATE_TRUNC expressions.

        Args:
            hierarchy: Hierarchy dict (must have synthetic=True)
            level: Target level (year, quarter, month, day)
            db_type: Database type for SQL dialect

        Returns:
            SQL expression string
        """
        if not hierarchy.get("synthetic"):
            return None

        source_col = hierarchy.get("source_column")
        if not source_col:
            return None

        # SQL expressions by database type
        expressions = {
            "bigquery": {
                "year": f"EXTRACT(YEAR FROM {source_col})",
                "quarter": f"EXTRACT(QUARTER FROM {source_col})",
                "month": f"EXTRACT(MONTH FROM {source_col})",
                "week": f"EXTRACT(WEEK FROM {source_col})",
                "day": f"EXTRACT(DAY FROM {source_col})"
            },
            "snowflake": {
                "year": f"YEAR({source_col})",
                "quarter": f"QUARTER({source_col})",
                "month": f"MONTH({source_col})",
                "week": f"WEEKOFYEAR({source_col})",
                "day": f"DAY({source_col})"
            },
            "postgres": {
                "year": f"EXTRACT(YEAR FROM {source_col})",
                "quarter": f"EXTRACT(QUARTER FROM {source_col})",
                "month": f"EXTRACT(MONTH FROM {source_col})",
                "week": f"EXTRACT(WEEK FROM {source_col})",
                "day": f"EXTRACT(DAY FROM {source_col})"
            },
            "postgresql": {
                "year": f"EXTRACT(YEAR FROM {source_col})",
                "quarter": f"EXTRACT(QUARTER FROM {source_col})",
                "month": f"EXTRACT(MONTH FROM {source_col})",
                "week": f"EXTRACT(WEEK FROM {source_col})",
                "day": f"EXTRACT(DAY FROM {source_col})"
            }
        }

        db_expressions = expressions.get(db_type, expressions["postgres"])
        return db_expressions.get(level)

    def suggest_drill_paths(
        self,
        columns: List[Dict[str, Any]],
        measures: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Suggest drill paths optimized for specific measures.

        Args:
            columns: Column metadata
            measures: List of measure column names

        Returns:
            List of suggested drill configurations
        """
        hierarchies = self.detect_hierarchies(columns)
        suggestions = []

        for hierarchy in hierarchies:
            # Create suggestion for each hierarchy
            suggestion = {
                "hierarchy": hierarchy,
                "recommended_measures": [],
                "description": ""
            }

            h_type = hierarchy["type"]

            if h_type == "time":
                suggestion["recommended_measures"] = [
                    m for m in measures
                    if any(kw in m.lower() for kw in ["revenue", "sales", "count", "amount", "total"])
                ]
                suggestion["description"] = "Drill from year to day to analyze trends over time"

            elif h_type == "geography":
                suggestion["recommended_measures"] = [
                    m for m in measures
                    if any(kw in m.lower() for kw in ["revenue", "customers", "orders", "stores"])
                ]
                suggestion["description"] = "Drill from country to city to analyze regional performance"

            elif h_type == "product":
                suggestion["recommended_measures"] = [
                    m for m in measures
                    if any(kw in m.lower() for kw in ["revenue", "quantity", "margin", "units"])
                ]
                suggestion["description"] = "Drill from category to product to analyze product performance"

            elif h_type == "customer":
                suggestion["recommended_measures"] = [
                    m for m in measures
                    if any(kw in m.lower() for kw in ["revenue", "orders", "ltv", "count"])
                ]
                suggestion["description"] = "Drill from segment to customer for customer analysis"

            suggestions.append(suggestion)

        return suggestions


# Singleton instance
_drill_path_detector: Optional[DrillPathDetector] = None


def get_drill_path_detector() -> DrillPathDetector:
    """Get the singleton DrillPathDetector instance."""
    global _drill_path_detector
    if _drill_path_detector is None:
        _drill_path_detector = DrillPathDetector()
    return _drill_path_detector
