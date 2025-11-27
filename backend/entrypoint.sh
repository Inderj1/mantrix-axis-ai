#!/bin/bash
set -e

# =============================================================================
# Mantrix Axis AI - Backend Entrypoint Script
# =============================================================================

echo "Starting Mantrix Axis AI Backend..."

# -----------------------------------------------------------------------------
# GCP Credentials Setup
# -----------------------------------------------------------------------------
# If GCP_CREDENTIALS_JSON is provided (from AWS Secrets Manager),
# write it to a file and set GOOGLE_APPLICATION_CREDENTIALS
if [ -n "$GCP_CREDENTIALS_JSON" ]; then
    echo "Setting up GCP credentials..."
    echo "$GCP_CREDENTIALS_JSON" > /app/credentials/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-key.json
    echo "GCP credentials configured at: $GOOGLE_APPLICATION_CREDENTIALS"
fi

# -----------------------------------------------------------------------------
# Environment Information
# -----------------------------------------------------------------------------
echo "Environment: ${API_ENV:-production}"
echo "Host: ${API_HOST:-0.0.0.0}"
echo "Port: ${API_PORT:-8000}"
echo "Log Level: ${LOG_LEVEL:-INFO}"

# -----------------------------------------------------------------------------
# Database Connection Check (optional)
# -----------------------------------------------------------------------------
if [ -n "$POSTGRES_HOST" ]; then
    echo "PostgreSQL Host: $POSTGRES_HOST"
fi

if [ -n "$REDIS_HOST" ]; then
    echo "Redis Host: $REDIS_HOST"
fi

if [ -n "$MONGODB_URL" ]; then
    echo "MongoDB configured"
fi

if [ -n "$WEAVIATE_URL" ]; then
    echo "Weaviate URL: $WEAVIATE_URL"
fi

# -----------------------------------------------------------------------------
# Start Uvicorn Server
# -----------------------------------------------------------------------------
echo "Starting Uvicorn server..."

# Number of workers based on environment
# - Development: 1 worker with reload
# - Production: 2 workers (or based on CPU)
if [ "$API_ENV" = "development" ]; then
    exec uvicorn src.main:app \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8000}" \
        --reload
else
    exec uvicorn src.main:app \
        --host "${API_HOST:-0.0.0.0}" \
        --port "${API_PORT:-8000}" \
        --workers 2 \
        --timeout-keep-alive 65 \
        --access-log
fi
