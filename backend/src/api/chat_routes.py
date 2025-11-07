"""API routes for Ask AXIS chat functionality."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog
import anthropic
from src.config import Settings

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
settings = Settings()


class ChatContext(BaseModel):
    """Context information for the chat."""
    moduleName: Optional[str] = None
    tabName: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    dateRange: Optional[Dict[str, str]] = None
    visibleData: Optional[Any] = None
    chartData: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    question: str
    context: ChatContext
    sessionId: str
    userId: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    success: bool
    answer: str
    error: Optional[str] = None


def build_context_prompt(context: ChatContext) -> str:
    """Build a context description for the AI."""
    context_parts = []

    if context.moduleName:
        context_parts.append(f"Current module: {context.moduleName}")

    if context.tabName:
        context_parts.append(f"Current tab: {context.tabName}")

    if context.filters:
        context_parts.append(f"Active filters: {context.filters}")

    if context.dateRange:
        context_parts.append(
            f"Date range: {context.dateRange.get('from')} to {context.dateRange.get('to')}"
        )

    if context.visibleData:
        context_parts.append(f"Visible data: {str(context.visibleData)[:500]}")  # Limit size

    if context.chartData:
        context_parts.append(f"Chart data available: {type(context.chartData)}")

    if context.metadata:
        context_parts.append(f"Metadata: {context.metadata}")

    if not context_parts:
        return "No specific context available."

    return "\n".join(context_parts)


@router.post("/ask", response_model=ChatResponse)
async def ask_axis(request: ChatRequest):
    """
    Ask AXIS - Context-aware AI assistant endpoint.

    Receives a question along with page context and returns an AI-generated response.
    """
    try:
        logger.info(
            "Chat request received",
            user_id=request.userId,
            session_id=request.sessionId,
            module=request.context.moduleName,
            tab=request.context.tabName
        )

        # Get Anthropic API key from settings
        api_key = settings.anthropic_api_key
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not configured, using mock response")
            # Return a mock response for development
            return ChatResponse(
                success=True,
                answer=f"I understand you're asking about '{request.question}' in the context of {request.context.moduleName or 'the application'}. "
                       f"This is a development mock response. Please configure ANTHROPIC_API_KEY to enable AI responses."
            )

        # Build context description
        context_description = build_context_prompt(request.context)

        # Create Anthropic client
        client = anthropic.Anthropic(api_key=api_key)

        # Build the system prompt
        system_prompt = f"""You are AXIS, an AI assistant for the MANTRA-X Decision Intelligence Platform.

PERSONA - Financial Analyst:
You are a seasoned financial analyst with deep expertise in business intelligence and data analysis. You:
- Understand financial metrics: revenue, COGS, gross margin, EBITDA, contribution margin, variance analysis
- Think in terms of P&L statements, balance sheets, cash flow, and business performance
- Recognize the importance of period comparisons (YoY, QoQ, MoM) and trend analysis
- Communicate insights in terms executives understand
- Focus on actionable insights: "What does this mean for the business?"
- Expect properly formatted financial data ($ for currency, % for percentages, commas for thousands)

GL ACCOUNTING KNOWLEDGE:
You understand General Ledger concepts:
- Account structure: 4xxxxx = Revenue, 5xxxxx = COGS, 6xxxxx = Operating Expenses
- Debit/Credit nature: Revenue accounts typically show as negative in reports, expenses as positive
- Financial statements: Income Statement (P&L), Balance Sheet, Cash Flow
- Period concepts: YTD (Year-to-Date), QTD (Quarter-to-Date), fiscal vs calendar periods
- Account groupings: Revenue accounts roll up to total revenue, expenses group into COGS and OpEx
- Variance interpretation: Revenue increase = favorable, expense increase = unfavorable

When users ask about:
- "Revenue" or "sales" → You know this comes from GL accounts 400000-499999
- "Expenses" or "costs" → You distinguish between COGS (5xxxxx) and OpEx (6xxxxx)
- "Profit" or "margin" → You understand the calculation: Revenue - COGS = Gross Profit
- "What was spent on X" → You know to look at expense accounts and their descriptions
- Period comparisons → You provide variance analysis with favorable/unfavorable context

Current Context:
{context_description}

Provide helpful, accurate, and concise responses with a financial analyst's perspective.
When discussing numbers, always provide context and business implications.
Interpret financial data through the lens of GL accounting principles.
If the context doesn't contain enough information to answer fully, acknowledge that and provide what you can."""

        # Call Claude API
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": request.question
                }
            ]
        )

        # Extract the response
        answer = message.content[0].text if message.content else "I'm sorry, I couldn't generate a response."

        logger.info(
            "Chat response generated",
            user_id=request.userId,
            response_length=len(answer)
        )

        return ChatResponse(
            success=True,
            answer=answer
        )

    except anthropic.APIError as e:
        logger.error("Anthropic API error", error=str(e))
        return ChatResponse(
            success=False,
            answer="I'm experiencing technical difficulties. Please try again later.",
            error=str(e)
        )
    except Exception as e:
        logger.error("Chat request failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat request failed: {str(e)}")


@router.get("/health")
async def chat_health():
    """Health check for chat service."""
    return {
        "status": "healthy",
        "anthropic_configured": bool(settings.anthropic_api_key)
    }
