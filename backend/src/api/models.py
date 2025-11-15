from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    dataset: Optional[str] = Field(None, description="Override default dataset")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    conversationId: Optional[str] = Field(None, description="Conversation ID for context")
    page_size: Optional[int] = Field(10000, description="Number of rows per page (default: 10000, max: 100000)")
    page_token: Optional[str] = Field(None, description="Token for fetching next page of results")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Show me total sales by region last quarter",
                "options": {
                    "use_vector_search": True,
                    "max_tables": 5
                },
                "page_size": 10000,
                "page_token": None
            }
        }


class SQLGenerateRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    use_vector_search: bool = Field(True, description="Use vector search for table selection")
    max_tables: int = Field(5, description="Maximum number of tables to consider")


class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., description="SQL query to execute")


class OptimizeRequest(BaseModel):
    sql: str = Field(..., description="SQL query to optimize")


class QueryResponse(BaseModel):
    sql: Optional[str] = None
    explanation: Optional[str] = None
    tables_used: List[str] = Field(default_factory=list)
    estimated_complexity: Optional[str] = None
    optimization_notes: Optional[str] = None
    validation: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None  # Enhanced error information
    confidence_score: Optional[float] = None
    suggestions: Optional[List[Dict[str, Any]]] = None
    follow_up_suggestions: Optional[List[str]] = None  # Copilot follow-up suggestions
    from_cache: bool = False


# Document Intelligence Models
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    size_bytes: int
    upload_timestamp: str
    message: str


class DocumentAnalysisRequest(BaseModel):
    document_id: str
    analysis_type: str = Field("comprehensive", description="Type of analysis: comprehensive, summary, quality")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DocumentAnalysisResponse(BaseModel):
    summary: str
    key_points: List[str]
    data_quality: Dict[str, float]
    suggestions: List[str]
    response: str


class DocumentQuestionRequest(BaseModel):
    document_ids: List[str]
    question: str


class DocumentQuestionResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[str]
    follow_up_questions: List[str]


class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total_count: int


class ExecutionResponse(BaseModel):
    results: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    total_rows: Optional[int] = None
    truncated: Optional[bool] = None
    has_more: Optional[bool] = None
    next_page_token: Optional[str] = None
    page_info: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    performance_stats: Optional[Dict[str, Any]] = None


class OptimizationResponse(BaseModel):
    optimized_sql: Optional[str] = None
    optimizations_applied: List[str] = Field(default_factory=list)
    estimated_improvement: Optional[str] = None
    additional_recommendations: List[str] = Field(default_factory=list)
    validation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SchemaResponse(BaseModel):
    tables: List[Dict[str, Any]]
    total_count: int


class HealthResponse(BaseModel):
    status: str
    bigquery: str
    weaviate: str
    redis: Optional[str] = None
    cache_stats: Optional[Dict[str, Any]] = None
    version: str = "0.1.0"


# Materialized View Models

class MaterializedViewCreateRequest(BaseModel):
    name: str = Field(..., description="Name for the materialized view")
    query: str = Field(..., description="SQL query for the materialized view")
    partition_by: Optional[str] = Field(None, description="Column to partition by")
    cluster_by: Optional[List[str]] = Field(None, description="Columns to cluster by")
    auto_refresh: bool = Field(True, description="Enable automatic refresh")
    refresh_interval_hours: int = Field(24, description="Refresh interval in hours")
    description: Optional[str] = Field(None, description="Description of the MV")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "copa_monthly_summary",
                "query": "SELECT GJAHR, PERIO, SUM(VV001) as revenue FROM CE11000 GROUP BY 1,2",
                "partition_by": "GJAHR",
                "cluster_by": ["BUKRS", "VKORG"],
                "auto_refresh": True,
                "refresh_interval_hours": 24,
                "description": "Monthly COPA summary for performance"
            }
        }


class MaterializedViewResponse(BaseModel):
    status: str
    view_name: str
    full_name: Optional[str] = None
    estimated_monthly_cost: Optional[float] = None
    error: Optional[str] = None


class MaterializedViewStatsResponse(BaseModel):
    view_name: str
    created_at: str
    last_refreshed: str
    size_mb: float
    row_count: int
    staleness_hours: float
    query_count: int
    avg_query_time_saved_ms: float
    estimated_monthly_cost: float


class MaterializedViewListResponse(BaseModel):
    views: List[Dict[str, Any]]
    total_count: int


class OptimizationRecommendation(BaseModel):
    query_pattern: str
    frequency: int
    avg_bytes_processed: int
    avg_execution_time_ms: float
    potential_savings: Dict[str, float]
    suggested_mv: Dict[str, Any]


class OptimizationReportResponse(BaseModel):
    summary: Dict[str, Any]
    existing_mvs: List[Dict[str, Any]]
    underutilized_mvs: List[Dict[str, Any]]
    recommendations: List[OptimizationRecommendation]
    potential_monthly_savings: float
    report_generated_at: str


# Query Suggestion Models

class QuerySuggestionRequest(BaseModel):
    query: str = Field(..., description="User's natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_suggestions: int = Field(5, description="Maximum number of suggestions")


class QuerySuggestion(BaseModel):
    suggestion_type: str = Field(..., description="Type: similar, template, correction, refinement")
    text: str = Field(..., description="Suggested query text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    explanation: Optional[str] = Field(None, description="Why this suggestion")
    example_sql: Optional[str] = Field(None, description="Example SQL if applicable")


class QuerySuggestionsResponse(BaseModel):
    suggestions: List[QuerySuggestion]
    clarifying_questions: Optional[List[str]] = None
    

class QueryExplanationRequest(BaseModel):
    sql: str = Field(..., description="SQL query to explain")
    user_query: str = Field(..., description="Original natural language query")


class QueryExplanationResponse(BaseModel):
    summary: str = Field(..., description="Natural language explanation")
    original_question: str
    query_type: str = Field(..., description="Type of query: aggregation, ranking, etc")
    complexity: str = Field(..., description="Query complexity: simple, moderate, complex")
    performance_tips: Optional[List[str]] = None


class ErrorCorrectionRequest(BaseModel):
    sql: str = Field(..., description="SQL query with error")
    error_message: str = Field(..., description="Error message from execution")
    table_schemas: List[Dict[str, Any]] = Field(..., description="Available table schemas")


class ErrorCorrectionResponse(BaseModel):
    corrected_sql: Optional[str] = None
    correction_applied: bool
    original_error: str
    suggestions: List[str]
    confidence: float


class ResultAnalysisRequest(BaseModel):
    question: str = Field(..., description="Original user question")
    sql: str = Field(..., description="Executed SQL query")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Query metadata (cost, bytes processed, etc)")


class ResultAnalysisResponse(BaseModel):
    summary: str = Field(..., description="Executive summary of results")
    key_insights: List[str] = Field(..., description="Key insights from the data")
    trends: Optional[List[str]] = Field(default=None, description="Identified trends or patterns")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    follow_up_questions: List[str] = Field(..., description="Suggested follow-up questions", max_items=3)
    data_quality_notes: Optional[List[str]] = Field(default=None, description="Notes about data quality or completeness")


class AnalyzeDocumentRequest(BaseModel):
    document_id: str = Field(..., description="Document ID to analyze")
    analysis_type: str = Field("comprehensive", description="Type of analysis to perform")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional analysis options")


class AskDocumentQuestionRequest(BaseModel):
    document_ids: List[str] = Field(..., description="List of document IDs to query")
    question: str = Field(..., description="Question to ask about the documents")


# Research Models

class CreateResearchPlanRequest(BaseModel):
    query: str = Field(..., description="Natural language query for research")
    depth: str = Field("standard", description="Research depth: quick, standard, or deep")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Analyze our customer retention over the past year",
                "depth": "standard",
                "focus_areas": ["revenue", "segments", "trends"]
            }
        }


class ResearchStepResponse(BaseModel):
    id: str
    name: str
    description: str
    query_template: str
    step_type: str
    estimated_duration: int
    dependencies: List[str]
    priority: int


class ResearchPlanResponse(BaseModel):
    plan_id: str
    title: str
    objective: str
    steps: List[ResearchStepResponse]
    total_steps: int
    estimated_duration: int
    complexity_score: float


class ExecuteResearchRequest(BaseModel):
    parallel: bool = Field(True, description="Execute steps in parallel where possible")


class ResearchProgressResponse(BaseModel):
    execution_id: str
    plan_id: str
    status: str
    progress_percentage: float
    current_step: Optional[str] = None
    steps_completed: int
    total_steps: int
    elapsed_seconds: Optional[float] = None
    steps: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Step execution details")


class ResearchInsightResponse(BaseModel):
    id: str
    title: str
    description: str
    importance: str
    category: str
    confidence: float
    supporting_data: Optional[Dict[str, Any]] = None


class ResearchRecommendationResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    expected_impact: str
    related_insights: List[str]


class ResearchReportResponse(BaseModel):
    report_id: str
    plan_id: str
    execution_id: str
    title: str
    executive_summary: str
    key_findings: List[str]
    insights: List[ResearchInsightResponse]
    recommendations: List[ResearchRecommendationResponse]
    methodology: str
    data_summary: Dict[str, Any]
    generated_at: str