"""
Cross-Database API Routes

Provides endpoints for SQL dialect translation and cross-database query execution.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import structlog

from src.core.sql_dialect_translator import SQLDialectTranslator, TranslationError
from src.api.middleware.cognito_auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/cross-db", tags=["cross-database"])


# ==========================================
# Request/Response Models
# ==========================================

class TranslateSQLRequest(BaseModel):
    """Request model for SQL translation."""
    sql: str = Field(..., description="SQL query to translate")
    source_dialect: str = Field(..., description="Source database dialect (bigquery, snowflake, postgresql, redshift, databricks)")
    target_dialect: str = Field(..., description="Target database dialect")
    validate: bool = Field(True, description="Validate translated SQL syntax")

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)",
                "source_dialect": "bigquery",
                "target_dialect": "snowflake",
                "validate": True
            }
        }


class TranslateSQLResponse(BaseModel):
    """Response model for SQL translation."""
    translated_sql: str = Field(..., description="Translated SQL query")
    source_dialect: str
    target_dialect: str
    changes: List[str] = Field(default_factory=list, description="List of changes made during translation")
    warnings: List[str] = Field(default_factory=list, description="List of warnings about translation")
    is_lossless: bool = Field(..., description="Whether translation is lossless")
    confidence_score: float = Field(..., description="Confidence score (0-1)")


class BatchTranslateSQLRequest(BaseModel):
    """Request model for batch SQL translation."""
    queries: List[str] = Field(..., description="List of SQL queries to translate")
    source_dialect: str
    target_dialect: str

    class Config:
        json_schema_extra = {
            "example": {
                "queries": [
                    "SELECT * FROM users",
                    "SELECT COUNT(*) FROM products",
                    "SELECT id, name FROM orders WHERE status = 'active'"
                ],
                "source_dialect": "bigquery",
                "target_dialect": "snowflake"
            }
        }


class BatchTranslateSQLResponse(BaseModel):
    """Response model for batch SQL translation."""
    results: List[TranslateSQLResponse]
    total_queries: int
    successful: int
    failed: int


class TranslationCostRequest(BaseModel):
    """Request model for translation cost estimation."""
    sql: str
    source_dialect: str
    target_dialect: str

    class Config:
        json_schema_extra = {
            "example": {
                "sql": "SELECT DATE_TRUNC('month', date_column), ARRAY_AGG(DISTINCT value) FROM table",
                "source_dialect": "snowflake",
                "target_dialect": "redshift"
            }
        }


class TranslationCostResponse(BaseModel):
    """Response model for translation cost."""
    cost: float = Field(..., description="Translation cost (0-1, where 0=trivial, 1=complex)")
    source_dialect: str
    target_dialect: str
    explanation: str = Field(..., description="Explanation of cost factors")


# ==========================================
# API Endpoints
# ==========================================

@router.post("/translate", response_model=TranslateSQLResponse)
async def translate_sql_dialect(
    request: TranslateSQLRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Translate SQL from one dialect to another.

    This endpoint uses sqlglot for AST-based SQL translation between different
    database dialects. It supports:
    - BigQuery
    - Snowflake
    - PostgreSQL
    - Redshift
    - Databricks

    The translation attempts to preserve semantic meaning while adapting syntax
    to the target dialect.
    """
    try:
        logger.info(
            "SQL translation request",
            user_id=user.get('id'),
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect,
            sql_length=len(request.sql)
        )

        translator = SQLDialectTranslator()
        result = translator.translate(
            sql=request.sql,
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect,
            validate=request.validate
        )

        logger.info(
            "SQL translation successful",
            user_id=user.get('id'),
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect,
            is_lossless=result.is_lossless,
            confidence_score=result.confidence_score
        )

        return TranslateSQLResponse(
            translated_sql=result.translated_sql,
            source_dialect=result.source_dialect,
            target_dialect=result.target_dialect,
            changes=result.changes,
            warnings=result.warnings,
            is_lossless=result.is_lossless,
            confidence_score=result.confidence_score
        )

    except ValueError as e:
        logger.error("Invalid translation request", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=400, detail=str(e))

    except TranslationError as e:
        logger.error("Translation failed", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=422, detail=f"Translation failed: {str(e)}")

    except Exception as e:
        logger.error("Unexpected error during translation", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=500, detail="Internal server error during translation")


@router.post("/translate/batch", response_model=BatchTranslateSQLResponse)
async def batch_translate_sql(
    request: BatchTranslateSQLRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Translate multiple SQL queries in batch.

    This endpoint translates multiple queries efficiently, continuing even if
    some translations fail. Failed translations will have confidence_score = 0
    and warnings describing the error.
    """
    try:
        logger.info(
            "Batch SQL translation request",
            user_id=user.get('id'),
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect,
            query_count=len(request.queries)
        )

        translator = SQLDialectTranslator()
        results = translator.batch_translate(
            queries=request.queries,
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect
        )

        # Convert to response models
        response_results = [
            TranslateSQLResponse(
                translated_sql=r.translated_sql,
                source_dialect=r.source_dialect,
                target_dialect=r.target_dialect,
                changes=r.changes,
                warnings=r.warnings,
                is_lossless=r.is_lossless,
                confidence_score=r.confidence_score
            )
            for r in results
        ]

        successful = sum(1 for r in results if r.confidence_score > 0)
        failed = len(results) - successful

        logger.info(
            "Batch SQL translation complete",
            user_id=user.get('id'),
            total=len(results),
            successful=successful,
            failed=failed
        )

        return BatchTranslateSQLResponse(
            results=response_results,
            total_queries=len(results),
            successful=successful,
            failed=failed
        )

    except ValueError as e:
        logger.error("Invalid batch translation request", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during batch translation", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=500, detail="Internal server error during batch translation")


@router.post("/translate/cost", response_model=TranslationCostResponse)
async def get_translation_cost(
    request: TranslationCostRequest,
    user: Dict = Depends(get_current_user)
):
    """
    Estimate the complexity/cost of translating a query.

    Returns a cost score from 0 to 1:
    - 0.0 = Trivial (identical syntax or same dialect)
    - 0.1-0.3 = Low cost (minor syntax changes)
    - 0.3-0.6 = Moderate cost (function changes, some data type differences)
    - 0.6-1.0 = High cost (complex features, potential functionality loss)

    This endpoint is useful for:
    - Determining if translation is feasible
    - Identifying queries that may need manual review
    - Planning migration efforts
    """
    try:
        logger.info(
            "Translation cost request",
            user_id=user.get('id'),
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect
        )

        translator = SQLDialectTranslator()
        cost = translator.get_translation_cost(
            sql=request.sql,
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect
        )

        # Generate explanation
        if cost == 0.0:
            explanation = "Identical dialects - no translation needed"
        elif cost < 0.2:
            explanation = "Low cost - dialects are very similar, minimal changes required"
        elif cost < 0.5:
            explanation = "Moderate cost - some function and syntax changes required"
        elif cost < 0.8:
            explanation = "High cost - significant differences, may require manual review"
        else:
            explanation = "Very high cost - complex features may not translate perfectly"

        logger.info(
            "Translation cost calculated",
            user_id=user.get('id'),
            cost=cost,
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect
        )

        return TranslationCostResponse(
            cost=cost,
            source_dialect=request.source_dialect,
            target_dialect=request.target_dialect,
            explanation=explanation
        )

    except ValueError as e:
        logger.error("Invalid cost request", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error("Unexpected error during cost calculation", error=str(e), user_id=user.get('id'))
        raise HTTPException(status_code=500, detail="Internal server error during cost calculation")


@router.get("/dialects")
async def get_supported_dialects(user: Dict = Depends(get_current_user)):
    """
    Get list of supported SQL dialects.

    Returns information about all supported database dialects and their
    capabilities.
    """
    return {
        "dialects": [
            {
                "name": "bigquery",
                "display_name": "Google BigQuery",
                "description": "Google's serverless data warehouse"
            },
            {
                "name": "snowflake",
                "display_name": "Snowflake",
                "description": "Cloud data warehouse platform"
            },
            {
                "name": "postgresql",
                "display_name": "PostgreSQL",
                "description": "Open-source relational database"
            },
            {
                "name": "redshift",
                "display_name": "Amazon Redshift",
                "description": "AWS data warehouse service"
            },
            {
                "name": "databricks",
                "display_name": "Databricks",
                "description": "Unified analytics platform (Spark SQL)"
            }
        ],
        "total": 5
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint for cross-database services.

    Does not require authentication.
    """
    try:
        # Quick test that translator can be initialized
        translator = SQLDialectTranslator()
        return {
            "status": "healthy",
            "service": "cross-database-translation",
            "dialects_supported": 5
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")
