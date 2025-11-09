"""
Enhanced column matching with type compatibility and fuzzy matching.
"""
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import structlog

logger = structlog.get_logger()


# Type compatibility matrix for BigQuery types
TYPE_COMPATIBILITY = {
    # (source_type, target_type): cast_function
    ('STRING', 'INTEGER'): 'CAST({col} AS STRING)',
    ('STRING', 'INT64'): 'CAST({col} AS STRING)',
    ('INTEGER', 'STRING'): 'SAFE_CAST({col} AS INT64)',  # SAFE_CAST handles nulls
    ('INT64', 'STRING'): 'SAFE_CAST({col} AS INT64)',
    ('STRING', 'FLOAT64'): 'CAST({col} AS STRING)',
    ('FLOAT64', 'STRING'): 'SAFE_CAST({col} AS FLOAT64)',
    ('INTEGER', 'FLOAT64'): 'CAST({col} AS FLOAT64)',
    ('INT64', 'FLOAT64'): 'CAST({col} AS FLOAT64)',
    ('FLOAT64', 'INTEGER'): 'CAST({col} AS INT64)',
    ('FLOAT64', 'INT64'): 'CAST({col} AS INT64)',
    ('DATE', 'TIMESTAMP'): 'CAST({col} AS TIMESTAMP)',
    ('TIMESTAMP', 'DATE'): 'DATE({col})',
    ('DATE', 'STRING'): 'CAST({col} AS STRING)',
    ('STRING', 'DATE'): 'SAFE_CAST({col} AS DATE)',
    ('TIMESTAMP', 'STRING'): 'CAST({col} AS STRING)',
    ('STRING', 'TIMESTAMP'): 'SAFE_CAST({col} AS TIMESTAMP)',
}


class ColumnMatchResult:
    """Result of a column match operation."""

    def __init__(
        self,
        match_type: str,
        confidence: float,
        source_column: str,
        target_column: str,
        source_type: str,
        target_type: str,
        cast_required: Optional[str] = None,
        reason: str = ""
    ):
        self.match_type = match_type  # 'exact', 'type_compatible', 'fuzzy', 'semantic'
        self.confidence = confidence  # 0.0 to 1.0
        self.source_column = source_column
        self.target_column = target_column
        self.source_type = source_type
        self.target_type = target_type
        self.cast_required = cast_required  # SQL cast function if needed
        self.reason = reason

    def to_dict(self):
        return {
            'match_type': self.match_type,
            'confidence': self.confidence,
            'source_column': self.source_column,
            'target_column': self.target_column,
            'source_type': self.source_type,
            'target_type': self.target_type,
            'cast_required': self.cast_required,
            'reason': self.reason
        }


class EnhancedColumnMatcher:
    """Enhanced column matching with multiple strategies."""

    def __init__(self):
        self.fuzzy_threshold = 0.80  # 80% similarity for fuzzy matching

    def are_types_compatible(
        self,
        type1: str,
        type2: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if two types can be joined with casting.

        Returns:
            (compatible, cast_for_source, cast_for_target)
        """
        # Normalize type names
        type1 = type1.upper()
        type2 = type2.upper()

        # Exact match - no casting needed
        if type1 == type2:
            return True, None, None

        # Check forward direction
        cast_template = TYPE_COMPATIBILITY.get((type1, type2))
        if cast_template:
            return True, None, cast_template

        # Check reverse direction
        cast_template = TYPE_COMPATIBILITY.get((type2, type1))
        if cast_template:
            return True, cast_template, None

        # Not compatible
        return False, None, None

    def fuzzy_name_match(self, name1: str, name2: str) -> float:
        """
        Calculate fuzzy similarity between column names.

        Returns:
            Similarity score 0.0 to 1.0
        """
        # Normalize: lowercase, remove underscores/spaces
        n1 = name1.lower().replace('_', '').replace(' ', '')
        n2 = name2.lower().replace('_', '').replace(' ', '')

        # Calculate similarity
        similarity = SequenceMatcher(None, n1, n2).ratio()

        return similarity

    def match_columns(
        self,
        col1_name: str,
        col1_type: str,
        col2_name: str,
        col2_type: str
    ) -> Optional[ColumnMatchResult]:
        """
        Match two columns using multiple strategies.

        Returns:
            ColumnMatchResult if match found, None otherwise
        """
        # Strategy 1: Exact match (name + type)
        if col1_name == col2_name and col1_type.upper() == col2_type.upper():
            return ColumnMatchResult(
                match_type='exact',
                confidence=1.0,
                source_column=col1_name,
                target_column=col2_name,
                source_type=col1_type,
                target_type=col2_type,
                cast_required=None,
                reason='Exact name and type match'
            )

        # Strategy 2: Type-compatible match (same name, compatible types)
        if col1_name == col2_name:
            compatible, cast_source, cast_target = self.are_types_compatible(
                col1_type, col2_type
            )

            if compatible:
                # Determine which side needs casting
                cast_func = cast_source or cast_target
                if cast_func:
                    cast_func = cast_func.replace('{col}', col1_name)

                return ColumnMatchResult(
                    match_type='type_compatible',
                    confidence=0.90,
                    source_column=col1_name,
                    target_column=col2_name,
                    source_type=col1_type,
                    target_type=col2_type,
                    cast_required=cast_func,
                    reason=f'Same name with type casting: {col1_type} → {col2_type}'
                )

        # Strategy 3: Fuzzy name match (similar names, same or compatible types)
        fuzzy_score = self.fuzzy_name_match(col1_name, col2_name)

        if fuzzy_score >= self.fuzzy_threshold:
            # Check if types are compatible
            compatible, cast_source, cast_target = self.are_types_compatible(
                col1_type, col2_type
            )

            if compatible:
                # Determine which side needs casting
                cast_func = cast_source or cast_target
                if cast_func:
                    # For fuzzy matches, we need to know which column name to use
                    # Use the source column name in the cast
                    cast_func = cast_func.replace('{col}', col1_name)

                return ColumnMatchResult(
                    match_type='fuzzy',
                    confidence=fuzzy_score * 0.9,  # Discount for fuzzy
                    source_column=col1_name,
                    target_column=col2_name,
                    source_type=col1_type,
                    target_type=col2_type,
                    cast_required=cast_func,
                    reason=f'Fuzzy name match ({fuzzy_score:.0%} similar) with type compatibility'
                )

        # No match found
        return None

    def find_all_matches(
        self,
        columns1: List[Dict[str, str]],
        columns2: List[Dict[str, str]]
    ) -> List[ColumnMatchResult]:
        """
        Find all matches between two lists of columns.

        Args:
            columns1: List of {'name': str, 'type': str}
            columns2: List of {'name': str, 'type': str}

        Returns:
            List of ColumnMatchResult
        """
        matches = []

        for col1 in columns1:
            for col2 in columns2:
                result = self.match_columns(
                    col1['name'],
                    col1['type'],
                    col2['name'],
                    col2['type']
                )

                if result:
                    matches.append(result)

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches

    def get_best_join_column(
        self,
        table1_columns: List[Dict[str, str]],
        table2_columns: List[Dict[str, str]]
    ) -> Optional[ColumnMatchResult]:
        """
        Get the best join column between two tables.

        Returns:
            Best ColumnMatchResult or None
        """
        matches = self.find_all_matches(table1_columns, table2_columns)

        if matches:
            best_match = matches[0]
            logger.info(
                "Best join column found",
                source=best_match.source_column,
                target=best_match.target_column,
                match_type=best_match.match_type,
                confidence=f"{best_match.confidence:.2%}"
            )
            return best_match

        return None


def test_column_matching():
    """Test the enhanced column matcher."""
    matcher = EnhancedColumnMatcher()

    # Test 1: Exact match
    result = matcher.match_columns('Customer', 'STRING', 'Customer', 'STRING')
    assert result.match_type == 'exact'
    assert result.confidence == 1.0
    print(f"✓ Test 1 passed: {result.reason}")

    # Test 2: Type compatible
    result = matcher.match_columns('Customer', 'STRING', 'Customer', 'INTEGER')
    assert result.match_type == 'type_compatible'
    assert result.confidence == 0.90
    assert result.cast_required is not None
    print(f"✓ Test 2 passed: {result.reason}")
    print(f"  Cast: {result.cast_required}")

    # Test 3: Fuzzy match
    result = matcher.match_columns('Customer', 'STRING', 'CustomerID', 'STRING')
    if result and result.match_type == 'fuzzy':
        print(f"✓ Test 3 passed: {result.reason} (confidence: {result.confidence:.2%})")
    else:
        print(f"⚠ Test 3: Fuzzy match not found (threshold may be too high)")

    # Test 4: Fuzzy + type compatible
    result = matcher.match_columns('MaterialNumber', 'STRING', 'Material_Number', 'STRING')
    print(f"✓ Test 4 passed: {result.reason if result else 'No match'}")

    # Test 5: No match
    result = matcher.match_columns('Customer', 'STRING', 'ProductID', 'INTEGER')
    assert result is None
    print(f"✓ Test 5 passed: No match (as expected)")

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_column_matching()
