"""
SQL Dialect Translator

Translates SQL queries between different database dialects using sqlglot.
Supports: BigQuery, Snowflake, PostgreSQL, Redshift, Databricks.
"""
import sqlglot
from sqlglot import parse_one, transpile, ParseError
from typing import Dict, List, Optional, Any
import structlog
from dataclasses import dataclass, field
import hashlib

logger = structlog.get_logger()


@dataclass
class TranslationResult:
    """Result of SQL dialect translation."""
    translated_sql: str
    source_dialect: str
    target_dialect: str
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_lossless: bool = True
    confidence_score: float = 1.0  # 0-1, 1 = perfect translation


class TranslationError(Exception):
    """Raised when SQL translation fails."""
    pass


class SQLDialectTranslator:
    """
    Translate SQL between database dialects.

    Uses sqlglot for AST-based translation to ensure semantic correctness.
    """

    # Map our database types to sqlglot dialect names
    DIALECT_MAP = {
        'bigquery': 'bigquery',
        'snowflake': 'snowflake',
        'postgresql': 'postgres',
        'redshift': 'redshift',
        'databricks': 'databricks'
    }

    # Known lossy transformations that reduce confidence
    LOSSY_PATTERNS = {
        'window_functions': ['ROW_NUMBER', 'RANK', 'DENSE_RANK'],
        'date_functions': ['DATE_TRUNC', 'DATE_PART', 'EXTRACT'],
        'array_functions': ['ARRAY_AGG', 'UNNEST', 'ARRAY_CONCAT'],
        'json_functions': ['JSON_EXTRACT', 'JSON_VALUE', 'JSON_QUERY'],
    }

    def __init__(self):
        """Initialize the translator."""
        self._translation_cache = {}
        logger.info("SQLDialectTranslator initialized")

    def translate(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str,
        validate: bool = True
    ) -> TranslationResult:
        """
        Translate SQL from source dialect to target dialect.

        Args:
            sql: SQL query to translate
            source_dialect: Source database type (bigquery, snowflake, etc.)
            target_dialect: Target database type
            validate: Validate syntax after translation

        Returns:
            TranslationResult with translated SQL and metadata

        Raises:
            ValueError: If dialects are invalid or SQL is malformed
            TranslationError: If translation fails
        """
        # Validate dialects
        if source_dialect not in self.DIALECT_MAP:
            raise ValueError(f"Invalid source dialect: {source_dialect}. Supported: {list(self.DIALECT_MAP.keys())}")
        if target_dialect not in self.DIALECT_MAP:
            raise ValueError(f"Invalid target dialect: {target_dialect}. Supported: {list(self.DIALECT_MAP.keys())}")

        # Check cache
        cache_key = self._get_cache_key(sql, source_dialect, target_dialect)
        if cache_key in self._translation_cache:
            logger.debug("Translation cache hit", cache_key=cache_key)
            return self._translation_cache[cache_key]

        logger.info(
            "Translating SQL",
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            sql_length=len(sql)
        )

        try:
            # Parse SQL with source dialect
            source_sqlglot = self.DIALECT_MAP[source_dialect]
            target_sqlglot = self.DIALECT_MAP[target_dialect]

            # Parse the SQL
            try:
                parsed = parse_one(sql, read=source_sqlglot)
            except ParseError as e:
                raise ValueError(f"Failed to parse SQL: {str(e)}")

            # Transpile to target dialect
            try:
                translated_sql = parsed.sql(dialect=target_sqlglot, pretty=True)
            except Exception as e:
                raise TranslationError(f"Failed to translate SQL: {str(e)}")

            # Detect changes between original and translated
            changes = self._detect_changes(sql, translated_sql, source_dialect, target_dialect)

            # Validate translated SQL if requested
            is_valid = True
            if validate:
                is_valid = self._validate_translation(translated_sql, target_dialect)
                if not is_valid:
                    logger.warning(
                        "Translated SQL failed validation",
                        target_dialect=target_dialect,
                        translated_sql=translated_sql
                    )

            # Calculate confidence score
            confidence_score = self._calculate_confidence(sql, translated_sql, changes)

            # Detect warnings
            warnings = self._detect_warnings(sql, source_dialect, target_dialect)

            # Determine if translation is lossless
            is_lossless = len(warnings) == 0 and confidence_score >= 0.95

            result = TranslationResult(
                translated_sql=translated_sql,
                source_dialect=source_dialect,
                target_dialect=target_dialect,
                changes=changes,
                warnings=warnings,
                is_lossless=is_lossless,
                confidence_score=confidence_score
            )

            # Cache the result
            self._translation_cache[cache_key] = result

            logger.info(
                "Translation successful",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
                changes_count=len(changes),
                warnings_count=len(warnings),
                is_lossless=is_lossless,
                confidence_score=confidence_score
            )

            return result

        except Exception as e:
            logger.error(
                "Translation failed",
                error=str(e),
                source_dialect=source_dialect,
                target_dialect=target_dialect
            )
            raise TranslationError(f"Translation failed: {str(e)}") from e

    def get_translation_cost(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> float:
        """
        Estimate complexity/cost of translating query.

        Returns:
            Float 0-1 where:
            - 0 = trivial (identical syntax)
            - 0.5 = moderate (some function changes)
            - 1 = complex (may lose functionality)
        """
        # Same dialect = zero cost
        if source_dialect == target_dialect:
            return 0.0

        # PostgreSQL and Redshift are very similar
        if {source_dialect, target_dialect} == {'postgresql', 'redshift'}:
            return 0.1

        try:
            # Try translation to see what changes
            result = self.translate(sql, source_dialect, target_dialect, validate=False)

            # Calculate cost based on changes and warnings
            cost = 0.0

            # Each change adds to cost
            cost += len(result.changes) * 0.05

            # Each warning adds more cost
            cost += len(result.warnings) * 0.15

            # Low confidence increases cost
            cost += (1.0 - result.confidence_score) * 0.3

            # Cap at 1.0
            return min(cost, 1.0)

        except Exception as e:
            logger.warning("Failed to estimate translation cost", error=str(e))
            # If we can't translate, assume high cost
            return 0.8

    def batch_translate(
        self,
        queries: List[str],
        source_dialect: str,
        target_dialect: str
    ) -> List[TranslationResult]:
        """
        Translate multiple queries in batch.

        Args:
            queries: List of SQL queries to translate
            source_dialect: Source database type
            target_dialect: Target database type

        Returns:
            List of TranslationResult objects
        """
        results = []
        for i, query in enumerate(queries):
            try:
                result = self.translate(query, source_dialect, target_dialect)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Batch translation failed for query",
                    query_index=i,
                    error=str(e)
                )
                # Create error result
                results.append(TranslationResult(
                    translated_sql="",
                    source_dialect=source_dialect,
                    target_dialect=target_dialect,
                    changes=[],
                    warnings=[f"Translation failed: {str(e)}"],
                    is_lossless=False,
                    confidence_score=0.0
                ))

        logger.info(
            "Batch translation complete",
            total_queries=len(queries),
            successful=sum(1 for r in results if r.confidence_score > 0),
            failed=sum(1 for r in results if r.confidence_score == 0)
        )

        return results

    def _detect_changes(
        self,
        original_sql: str,
        translated_sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> List[str]:
        """
        Detect what changed during translation.

        Returns:
            List of human-readable change descriptions
        """
        changes = []

        # Normalize for comparison
        original_upper = original_sql.upper()
        translated_upper = translated_sql.upper()

        # Detect function changes
        function_mappings = {
            ('bigquery', 'snowflake'): [
                ('DATE_SUB', 'DATEADD'),
                ('DATE_ADD', 'DATEADD'),
                ('TIMESTAMP_SUB', 'TIMESTAMPADD'),
                ('STRING_AGG', 'LISTAGG'),
            ],
            ('snowflake', 'postgresql'): [
                ('DATEADD', 'INTERVAL'),
                ('DATEDIFF', 'DATE subtraction'),
                ('LISTAGG', 'STRING_AGG'),
            ],
            ('postgresql', 'bigquery'): [
                ('INTERVAL', 'DATE_SUB/DATE_ADD'),
                ('NOW()', 'CURRENT_TIMESTAMP()'),
                ('AGE', 'DATE_DIFF'),
            ],
        }

        key = (source_dialect, target_dialect)
        if key in function_mappings:
            for old_func, new_func in function_mappings[key]:
                if old_func in original_upper and old_func not in translated_upper:
                    changes.append(f"{old_func} → {new_func}")

        # Detect quote style changes
        if '`' in original_sql and '`' not in translated_sql:
            changes.append("Backticks removed")
        elif '`' not in original_sql and '`' in translated_sql:
            changes.append("Backticks added")

        # Detect LIMIT/TOP changes
        if 'LIMIT' in original_upper and 'TOP' in translated_upper:
            changes.append("LIMIT → TOP")
        elif 'TOP' in original_upper and 'LIMIT' in translated_upper:
            changes.append("TOP → LIMIT")

        return changes

    def _validate_translation(
        self,
        sql: str,
        dialect: str
    ) -> bool:
        """
        Validate that translated SQL is syntactically correct.

        Returns:
            True if valid, False otherwise
        """
        try:
            sqlglot_dialect = self.DIALECT_MAP.get(dialect)
            if not sqlglot_dialect:
                return False

            # Try to parse the translated SQL
            parse_one(sql, read=sqlglot_dialect)
            return True

        except Exception as e:
            logger.warning(
                "SQL validation failed",
                dialect=dialect,
                error=str(e)
            )
            return False

    def _calculate_confidence(
        self,
        original_sql: str,
        translated_sql: str,
        changes: List[str]
    ) -> float:
        """
        Calculate confidence score for translation.

        Returns:
            Float 0-1 where 1 is perfect confidence
        """
        confidence = 1.0

        # Each change reduces confidence slightly
        confidence -= len(changes) * 0.05

        # Check for lossy patterns
        sql_upper = original_sql.upper()
        for pattern_type, patterns in self.LOSSY_PATTERNS.items():
            for pattern in patterns:
                if pattern in sql_upper:
                    confidence -= 0.1
                    break

        # Cap at 0-1 range
        return max(0.0, min(1.0, confidence))

    def _detect_warnings(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> List[str]:
        """
        Detect potential issues with translation.

        Returns:
            List of warning messages
        """
        warnings = []
        sql_upper = sql.upper()

        # Warn about array functions (may not translate perfectly)
        if any(func in sql_upper for func in ['ARRAY_AGG', 'UNNEST', 'ARRAY[']):
            if target_dialect in ['redshift', 'postgresql']:
                warnings.append("Array functions may have different behavior in target dialect")

        # Warn about JSON functions
        if any(func in sql_upper for func in ['JSON_EXTRACT', 'JSON_VALUE', 'JSON_QUERY']):
            warnings.append("JSON functions may have different syntax in target dialect")

        # Warn about window functions
        if 'OVER (' in sql_upper:
            if target_dialect == 'redshift':
                warnings.append("Window functions may have limited support in Redshift")

        # Warn about CTEs
        if 'WITH ' in sql_upper and target_dialect == 'databricks':
            warnings.append("CTE support may vary in Databricks")

        return warnings

    def _get_cache_key(
        self,
        sql: str,
        source_dialect: str,
        target_dialect: str
    ) -> str:
        """Generate cache key for translation."""
        content = f"{source_dialect}:{target_dialect}:{sql}"
        return hashlib.sha256(content.encode()).hexdigest()
