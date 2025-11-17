from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from contextlib import asynccontextmanager
from src.config import settings
from src.api.routes import router
from src.api.margen_routes import router as margen_router
from src.api.conversation_routes import router as conversation_router
from src.api.project_routes import router as project_router
from src.api.vision_routes import router as vision_router
from src.api.pulse_routes import router as pulse_router
from src.api.process_mining_routes import router as process_mining_router
from src.api.control_center_routes import router as control_center_router
from src.api.user_profile_routes import router as user_profile_router
from src.api.document_routes import router as document_router
from src.api.markets_routes import router as markets_router
from src.api.stox_routes import router as stox_router
from src.api.comms_routes import router as comms_router
from src.api.comms_config_routes import router as comms_config_router
from src.api.agent_routes import router as agent_router
from src.api.pipeline_routes import router as pipeline_router
from src.api.connector_routes import router as connector_router
from src.api.permissions_routes import router as permissions_router
from src.api.cross_database_routes import router as cross_database_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting NLP to SQL BigQuery service...")

    # Connect to MongoDB
    from src.db.mongodb_client import mongodb_client
    await mongodb_client.connect()
    logger.info("MongoDB connected")

    # Start Enterprise Pulse scheduler in background
    from src.core.pulse_scheduler import get_scheduler
    from src.core.market_signal_scheduler import get_market_signal_scheduler
    from src.core.pipeline_scheduler import get_pipeline_scheduler
    from datetime import time
    import asyncio

    pulse_scheduler = get_scheduler(check_interval=60)  # Check every minute
    pulse_task = asyncio.create_task(pulse_scheduler.start())
    logger.info("Enterprise Pulse Scheduler started")

    # Start Markets.AI signal scheduler
    markets_scheduler = get_market_signal_scheduler(check_interval=1800)  # Check every 30 minutes
    markets_task = asyncio.create_task(markets_scheduler.start())
    logger.info("Markets.AI Signal Scheduler started")

    # Start Pipeline scheduler (daily at 2:00 AM)
    pipeline_scheduler = get_pipeline_scheduler(
        execution_time=time(2, 0),  # 2:00 AM
        check_interval=300  # Check every 5 minutes
    )
    pipeline_task = asyncio.create_task(pipeline_scheduler.start())
    logger.info("Pipeline Scheduler started (daily at 2:00 AM)")

    yield

    # Shutdown
    logger.info("Shutting down NLP to SQL BigQuery service...")

    # Stop pulse scheduler
    await pulse_scheduler.stop()
    pulse_task.cancel()
    try:
        await pulse_task
    except asyncio.CancelledError:
        pass
    logger.info("Enterprise Pulse Scheduler stopped")

    # Stop markets scheduler
    await markets_scheduler.stop()
    markets_task.cancel()
    try:
        await markets_task
    except asyncio.CancelledError:
        pass
    logger.info("Markets.AI Signal Scheduler stopped")

    # Stop pipeline scheduler
    await pipeline_scheduler.stop()
    pipeline_task.cancel()
    try:
        await pipeline_task
    except asyncio.CancelledError:
        pass
    logger.info("Pipeline Scheduler stopped")


app = FastAPI(
    title="NLP to SQL BigQuery API",
    description="Convert natural language queries to optimized BigQuery SQL",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS with Clerk domains
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:8000",
    "https://accounts.dev.clerk",
    "https://*.clerk.accounts.dev",
    "https://clerk.com",
    "https://*.clerk.com",
]

# Add production domains if configured
if hasattr(settings, "PRODUCTION_DOMAIN"):
    allowed_origins.extend([
        f"https://{settings.PRODUCTION_DOMAIN}",
        f"https://www.{settings.PRODUCTION_DOMAIN}",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")
app.include_router(margen_router)
app.include_router(conversation_router)
app.include_router(project_router)
app.include_router(vision_router)
app.include_router(pulse_router)
app.include_router(process_mining_router)
app.include_router(control_center_router)
app.include_router(user_profile_router)
app.include_router(document_router, prefix="/api/v1/documents")
app.include_router(markets_router, prefix="/api/v1")
app.include_router(stox_router)
app.include_router(comms_router)
app.include_router(comms_config_router)
app.include_router(agent_router)
app.include_router(pipeline_router)
app.include_router(connector_router)
app.include_router(permissions_router)
app.include_router(cross_database_router)


@app.get("/")
async def root():
    return {
        "service": "NLP to SQL BigQuery",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_env == "development",
        log_level=settings.log_level.lower()
    )