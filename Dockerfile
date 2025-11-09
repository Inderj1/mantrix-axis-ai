# Backend API Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    structlog \
    pydantic-settings \
    anthropic \
    openai \
    google-cloud-bigquery \
    weaviate-client \
    pymongo \
    redis \
    psycopg2-binary \
    neo4j \
    sqlparse \
    pandas \
    numpy \
    openpyxl \
    xlrd \
    sqlalchemy \
    aioredis \
    motor \
    aiohttp \
    google-cloud-storage \
    psutil \
    pytesseract \
    pillow \
    scikit-learn \
    matplotlib \
    seaborn \
    plotly \
    pypdf \
    rdflib \
    python-docx \
    python-multipart \
    crewai \
    nest-asyncio

# Copy application code
COPY backend/src/ ./src/
COPY backend/configs/ ./configs/

# Create necessary directories
RUN mkdir -p query_logs logs files

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]