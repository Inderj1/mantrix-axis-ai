"""Column Metadata Service for backend-driven chart intelligence.

This service analyzes column types and suggests chart configurations,
aggregations, drill-down paths, and semantic types.
"""
import re
from typing import List, Dict, Any, Optional, Set
import structlog

logger = structlog.get_logger()


class ColumnMetadataService:
    """
    Analyzes column types and suggests chart configurations.
    This is the "brain" that makes charts intelligent.
    """

    # Type classification for different databases
    DIMENSION_TYPES: Set[str] = {
        'STRING', 'VARCHAR', 'TEXT', 'CATEGORY', 'CHAR', 'NVARCHAR',
        'CHARACTER', 'CHARACTER VARYING', 'BPCHAR'
    }

    MEASURE_TYPES: Set[str] = {
        'INTEGER', 'INT', 'INT64', 'INT32', 'INT16', 'INT8',
        'FLOAT', 'FLOAT64', 'FLOAT32', 'DOUBLE', 'DOUBLE PRECISION',
        'DECIMAL', 'NUMERIC', 'NUMBER', 'MONEY', 'SMALLMONEY',
        'BIGINT', 'SMALLINT', 'TINYINT', 'REAL'
    }

    TIME_TYPES: Set[str] = {
        'DATE', 'DATETIME', 'TIMESTAMP', 'TIMESTAMPTZ', 'TIMESTAMP_TZ',
        'TIMESTAMP_NTZ', 'TIMESTAMP_LTZ', 'TIME', 'TIMETZ',
        'DATETIME2', 'SMALLDATETIME', 'DATETIMEOFFSET'
    }

    BOOLEAN_TYPES: Set[str] = {
        'BOOLEAN', 'BOOL', 'BIT'
    }

    # Semantic type detection via column name patterns
    SEMANTIC_PATTERNS: Dict[str, str] = {
        'currency': r'(price|cost|revenue|amount|total|value|salary|wage|fee|charge|balance|payment|budget|margin|profit|loss|income|expense)s?$',
        'percentage': r'(rate|percent|pct|ratio|proportion|share|fraction|discount)s?$',
        'count': r'(count|cnt|qty|quantity|num|number|total|sum)s?$',
        'identifier': r'(_id|_key|_code|_no|_num|_number)$',
        'name': r'(name|title|label|description|desc)s?$',
        'email': r'(email|e_mail|mail)s?$',
        'phone': r'(phone|tel|telephone|mobile|cell|fax)s?$',
        'address': r'(address|addr|street|city|state|country|zip|postal|region)s?$',
        'date': r'(date|dt|day|month|year|quarter|week|period|time)s?$',
        'status': r'(status|state|flag|type|category|class|level|tier|grade|rank)s?$',
    }

    # Known geographical hierarchies
    GEO_HIERARCHY = ['continent', 'country', 'region', 'state', 'province', 'city', 'district', 'zip', 'postal']

    # Known time hierarchies
    TIME_HIERARCHY = ['year', 'quarter', 'month', 'week', 'day', 'hour', 'minute']

    # Known product hierarchies
    PRODUCT_HIERARCHY = ['division', 'category', 'subcategory', 'product', 'sku', 'item', 'variant']

    # Known organization hierarchies
    ORG_HIERARCHY = ['company', 'division', 'department', 'team', 'group', 'employee', 'user']

    def __init__(self):
        pass

    def analyze_columns(self, columns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze column metadata and return chart recommendations.

        Args:
            columns: List of column metadata dicts with 'name' and 'type' keys

        Returns:
            {
                "dimensions": ["country", "product_category"],
                "measures": ["revenue", "quantity"],
                "time_columns": ["order_date"],
                "boolean_columns": ["is_active"],
                "recommended_charts": ["bar", "line", "pie"],
                "default_aggregations": {"revenue": "SUM", "quantity": "SUM"},
                "drill_paths": [["country", "region", "city"]],
                "semantic_types": {"revenue": "currency", "margin_rate": "percentage"},
                "filter_suggestions": {
                    "dimensions": ["country", "product_category"],
                    "time_ranges": ["order_date"],
                    "boolean_toggles": ["is_active"]
                }
            }
        """
        dimensions: List[str] = []
        measures: List[str] = []
        time_cols: List[str] = []
        boolean_cols: List[str] = []
        semantic_types: Dict[str, str] = {}

        for col in columns:
            col_name = col.get('name', '')
            col_type = col.get('type', 'STRING').upper()

            # Normalize type name (remove precision, etc.)
            col_type = self._normalize_type(col_type)

            # Classify by type
            if col_type in self.TIME_TYPES:
                time_cols.append(col_name)
            elif col_type in self.BOOLEAN_TYPES:
                boolean_cols.append(col_name)
            elif col_type in self.DIMENSION_TYPES:
                dimensions.append(col_name)
            elif col_type in self.MEASURE_TYPES:
                measures.append(col_name)
            else:
                # Default to dimension for unknown types
                dimensions.append(col_name)

            # Detect semantic type from column name
            semantic_type = self._detect_semantic_type(col_name)
            if semantic_type:
                semantic_types[col_name] = semantic_type

                # Reclassify based on semantic type
                if semantic_type == 'identifier' and col_name in measures:
                    measures.remove(col_name)
                    dimensions.append(col_name)

        # Generate recommendations
        recommended_charts = self._suggest_charts(dimensions, measures, time_cols, boolean_cols)
        default_aggregations = self._suggest_aggregations(measures, semantic_types)
        drill_paths = self._suggest_drill_paths(dimensions + time_cols)
        filter_suggestions = self._suggest_filters(dimensions, time_cols, boolean_cols)

        result = {
            "dimensions": dimensions,
            "measures": measures,
            "time_columns": time_cols,
            "boolean_columns": boolean_cols,
            "recommended_charts": recommended_charts,
            "default_aggregations": default_aggregations,
            "drill_paths": drill_paths,
            "semantic_types": semantic_types,
            "filter_suggestions": filter_suggestions,
            "visualization_config": self._generate_visualization_config(
                dimensions, measures, time_cols, semantic_types
            )
        }

        logger.debug("Column analysis complete",
                    dimensions=len(dimensions),
                    measures=len(measures),
                    time_cols=len(time_cols),
                    recommended_charts=recommended_charts)

        return result

    def _normalize_type(self, col_type: str) -> str:
        """Normalize SQL type to base type (remove precision, length, etc.)"""
        # Remove precision/scale: DECIMAL(10,2) -> DECIMAL
        col_type = re.sub(r'\([^)]*\)', '', col_type)
        # Remove array notation: INTEGER[] -> INTEGER
        col_type = col_type.replace('[]', '')
        # Remove extra whitespace
        col_type = col_type.strip().upper()
        return col_type

    def _detect_semantic_type(self, col_name: str) -> Optional[str]:
        """Detect semantic type from column name patterns."""
        col_lower = col_name.lower()

        for sem_type, pattern in self.SEMANTIC_PATTERNS.items():
            if re.search(pattern, col_lower):
                return sem_type

        return None

    def _suggest_charts(
        self,
        dims: List[str],
        measures: List[str],
        time_cols: List[str],
        boolean_cols: List[str]
    ) -> List[str]:
        """Suggest chart types based on column composition."""
        charts: List[str] = []

        # Time series data -> line chart
        if time_cols and measures:
            charts.append("line")
            charts.append("area")

        # Categorical with measures -> bar chart
        if dims and measures:
            charts.append("bar")
            # Pie chart only for single dimension and measure
            if len(dims) == 1 and len(measures) == 1:
                charts.append("pie")
                charts.append("donut")

        # Multiple measures -> scatter/correlation
        if len(measures) >= 2:
            charts.append("scatter")

        # Stacked charts for 2 dimensions
        if len(dims) >= 2 and measures:
            charts.append("stacked_bar")

        # Heatmap for 2 dimensions and 1 measure
        if len(dims) >= 2 and len(measures) == 1:
            charts.append("heatmap")

        # Single measure -> metric card
        if len(measures) == 1 and not dims:
            charts.append("metric")
            charts.append("gauge")

        # Table is always an option
        charts.append("table")

        # Remove duplicates while preserving order
        return list(dict.fromkeys(charts))

    def _suggest_aggregations(
        self,
        measures: List[str],
        semantic_types: Dict[str, str]
    ) -> Dict[str, str]:
        """Suggest default aggregations for measures."""
        aggregations: Dict[str, str] = {}

        for measure in measures:
            sem_type = semantic_types.get(measure)
            measure_lower = measure.lower()

            if sem_type == 'count' or 'count' in measure_lower:
                aggregations[measure] = 'SUM'
            elif sem_type == 'percentage' or 'avg' in measure_lower or 'average' in measure_lower:
                aggregations[measure] = 'AVG'
            elif 'min' in measure_lower:
                aggregations[measure] = 'MIN'
            elif 'max' in measure_lower:
                aggregations[measure] = 'MAX'
            elif sem_type == 'currency' or 'total' in measure_lower or 'sum' in measure_lower:
                aggregations[measure] = 'SUM'
            else:
                # Default to SUM for most measures
                aggregations[measure] = 'SUM'

        return aggregations

    def _suggest_drill_paths(self, columns: List[str]) -> List[List[str]]:
        """Suggest hierarchical drill paths from columns."""
        paths: List[List[str]] = []
        column_lower_map = {col.lower(): col for col in columns}
        column_set = set(col.lower() for col in columns)

        # Check for geographical hierarchy
        geo_match = [column_lower_map[col] for col in self.GEO_HIERARCHY
                    if col in column_set or any(col in c for c in column_set)]
        if len(geo_match) >= 2:
            paths.append(geo_match)

        # Check for time hierarchy
        time_match = []
        for time_level in self.TIME_HIERARCHY:
            matching = [col for col in columns if time_level in col.lower()]
            if matching:
                time_match.extend(matching)
        if len(time_match) >= 2:
            paths.append(list(dict.fromkeys(time_match)))  # Remove duplicates

        # Check for product hierarchy
        prod_match = [column_lower_map.get(col) or column_lower_map.get(next(
            (c for c in column_set if col in c), None))
            for col in self.PRODUCT_HIERARCHY
            if col in column_set or any(col in c for c in column_set)]
        prod_match = [p for p in prod_match if p]  # Remove None
        if len(prod_match) >= 2:
            paths.append(prod_match)

        # Check for organization hierarchy
        org_match = [column_lower_map.get(col) or column_lower_map.get(next(
            (c for c in column_set if col in c), None))
            for col in self.ORG_HIERARCHY
            if col in column_set or any(col in c for c in column_set)]
        org_match = [o for o in org_match if o]  # Remove None
        if len(org_match) >= 2:
            paths.append(org_match)

        return paths

    def _suggest_filters(
        self,
        dimensions: List[str],
        time_cols: List[str],
        boolean_cols: List[str]
    ) -> Dict[str, List[str]]:
        """Suggest filter types for each column."""
        return {
            "dimensions": dimensions[:5],  # Limit to top 5 for UI
            "time_ranges": time_cols,
            "boolean_toggles": boolean_cols
        }

    def _generate_visualization_config(
        self,
        dimensions: List[str],
        measures: List[str],
        time_cols: List[str],
        semantic_types: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate default visualization configuration."""
        config: Dict[str, Any] = {}

        # Suggest X-axis
        if time_cols:
            config["suggested_x_axis"] = time_cols[0]
        elif dimensions:
            config["suggested_x_axis"] = dimensions[0]

        # Suggest Y-axis
        if measures:
            config["suggested_y_axis"] = measures[0]
            config["suggested_metrics"] = measures[:3]  # Top 3 measures

        # Suggest grouping
        if len(dimensions) > 1:
            config["suggested_group_by"] = dimensions[1]

        # Format hints for semantic types
        format_hints = {}
        for col, sem_type in semantic_types.items():
            if sem_type == 'currency':
                format_hints[col] = {"format": "currency", "prefix": "$"}
            elif sem_type == 'percentage':
                format_hints[col] = {"format": "percentage", "suffix": "%"}
            elif sem_type == 'count':
                format_hints[col] = {"format": "number", "decimals": 0}

        if format_hints:
            config["format_hints"] = format_hints

        return config

    def analyze_query_result(
        self,
        data: List[Dict[str, Any]],
        sql: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze actual query results to infer column types.
        Useful when column metadata is not available.

        Args:
            data: List of result row dictionaries
            sql: Optional SQL query for additional context

        Returns:
            Same format as analyze_columns()
        """
        if not data:
            return self.analyze_columns([])

        # Infer column types from first few rows
        sample_rows = data[:100]
        inferred_columns = []

        first_row = sample_rows[0]
        for col_name in first_row.keys():
            values = [row.get(col_name) for row in sample_rows if row.get(col_name) is not None]

            if not values:
                inferred_type = 'STRING'
            elif all(isinstance(v, bool) for v in values):
                inferred_type = 'BOOLEAN'
            elif all(isinstance(v, int) for v in values):
                inferred_type = 'INTEGER'
            elif all(isinstance(v, (int, float)) for v in values):
                inferred_type = 'FLOAT'
            else:
                inferred_type = 'STRING'

            inferred_columns.append({
                'name': col_name,
                'type': inferred_type
            })

        return self.analyze_columns(inferred_columns)


# Singleton instance
_column_metadata_service: Optional[ColumnMetadataService] = None


def get_column_metadata_service() -> ColumnMetadataService:
    """Get or create the singleton ColumnMetadataService instance."""
    global _column_metadata_service
    if _column_metadata_service is None:
        _column_metadata_service = ColumnMetadataService()
    return _column_metadata_service
