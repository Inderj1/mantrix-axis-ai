# Quick Start Guide - Docker Testing

**Estimated Time**: 30 minutes
**Difficulty**: Easy
**Requirements**: Docker Desktop, API keys

---

## Prerequisites (5 minutes)

### 1. Install Docker Desktop
- Download from https://www.docker.com/products/docker-desktop
- Minimum 16GB RAM, 8GB allocated to Docker
- 50GB free disk space

### 2. Get API Keys
- **Anthropic Claude**: https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Google Cloud**: https://console.cloud.google.com/ (create service account)

### 3. Verify Docker Installation
```bash
docker --version
# Expected: Docker version 24.0.0 or higher

docker compose version
# Expected: Docker Compose version v2.20.0 or higher
```

---

## Step-by-Step Setup (10 minutes)

### Step 1: Clone Repository (1 minute)
```bash
cd /Users/jay/Workspace/Cloudmantra_code/mantrix-axis-ai
```

### Step 2: Create Environment File (3 minutes)
```bash
# Create .env file
cat > .env << 'EOF'
# ============================================================================
# REQUIRED - Core Services
# ============================================================================

# Anthropic Claude (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenAI (REQUIRED for embeddings)
OPENAI_API_KEY=sk-YOUR_KEY_HERE

# Google Cloud / BigQuery (REQUIRED)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
BIGQUERY_DATASET=your_dataset_name
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-key.json

# ============================================================================
# OPTIONAL - Additional Databases
# ============================================================================

# Snowflake (Optional)
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# Leave empty if not using
DATABRICKS_SERVER_HOSTNAME=
REDSHIFT_HOST=

# ============================================================================
# Development Settings
# ============================================================================
API_ENV=development
LOG_LEVEL=INFO
EOF
```

**Now edit the .env file**:
```bash
nano .env  # or use your preferred editor

# Replace:
# - YOUR_KEY_HERE with your actual Anthropic API key
# - YOUR_KEY_HERE with your actual OpenAI API key
# - your-gcp-project-id with your Google Cloud project ID
# - your_dataset_name with your BigQuery dataset name
```

### Step 3: Add Google Cloud Credentials (2 minutes)
```bash
# Create credentials directory
mkdir -p credentials

# Copy your GCP service account JSON key
cp /path/to/your-gcp-service-account-key.json credentials/gcp-key.json

# Verify file exists
ls -la credentials/gcp-key.json
```

### Step 4: Start Docker Services (4 minutes)
```bash
# Start all services with test configuration
docker compose -f docker-compose.test.yml up -d

# This will start:
# ✓ Backend API (FastAPI)
# ✓ PostgreSQL (test database with sample data)
# ✓ Redis (cache)
# ✓ MongoDB (conversations)
# ✓ Weaviate (vector search)
# ✓ Neo4j (knowledge graph)

# Wait for all services to be healthy (60 seconds)
echo "Waiting for services to start..."
sleep 60
```

### Step 5: Verify Services are Running
```bash
# Check status of all containers
docker compose -f docker-compose.test.yml ps

# Expected: All services showing "Up (healthy)"
# NAME                          STATUS
# mantrix-test-api-1           Up (healthy)
# mantrix-test-postgres-1      Up (healthy)
# mantrix-test-redis-1         Up (healthy)
# mantrix-test-mongodb-1       Up (healthy)
# mantrix-test-weaviate-1      Up (healthy)
# mantrix-test-neo4j-1         Up (healthy)
```

---

## Run Tests (10 minutes)

### Quick Test - API Health
```bash
# Test API is responding
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status":"healthy","version":"0.1.0",...}
```

### Comprehensive Test Suite
```bash
# Make test script executable
chmod +x scripts/test_all_features.sh

# Run all feature tests
./scripts/test_all_features.sh

# Expected output:
# ✓ PASS: API health check
# ✓ PASS: BigQuery connector available
# ✓ PASS: PostgreSQL connector available
# ✓ PASS: SQL translation: BigQuery → Snowflake
# ...
# ✓ ALL TESTS PASSED!
```

### Individual Feature Tests

**Test 1: Database Connectors**
```bash
# List all available connectors
curl http://localhost:8000/api/v1/connectors/types | jq

# Expected: All 5 databases listed
```

**Test 2: PostgreSQL Connection**
```bash
# Test local PostgreSQL container
curl -X POST http://localhost:8000/api/v1/connectors/test \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "postgresql",
    "config": {
      "host": "postgres",
      "port": 5432,
      "database": "mantrix_test_db",
      "user": "mantrix_test",
      "password": "mantrix_test_123"
    }
  }' | jq

# Expected: "success": true
```

**Test 3: SQL Dialect Translation**
```bash
# Translate BigQuery SQL to Snowflake
curl -X POST http://localhost:8000/api/v1/cross-db/translate \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) as week_ago",
    "source_dialect": "bigquery",
    "target_dialect": "snowflake"
  }' | jq

# Expected: Translated SQL in response
```

**Test 4: Statistics Configuration**
```bash
# Check statistics extraction settings
curl http://localhost:8000/api/v1/statistics/status | jq

# Expected: Current configuration
```

---

## Optional: Start with Database UI Tools (5 minutes)

Docker Compose includes optional database management tools. Start them with:

```bash
# Start with UI tools
docker compose -f docker-compose.test.yml --profile tools up -d

# Now you can access:
# - Adminer (PostgreSQL UI): http://localhost:8080
# - Redis Commander: http://localhost:8081
# - Mongo Express: http://localhost:8083
# - Neo4j Browser: http://localhost:7474
```

### Using Adminer (PostgreSQL UI)
1. Open http://localhost:8080
2. Login:
   - System: PostgreSQL
   - Server: postgres
   - Username: mantrix_test
   - Password: mantrix_test_123
   - Database: mantrix_test_db
3. Browse tables: `test_customers`, `test_sales`, etc.

---

## Viewing Logs

### All Services
```bash
# Follow all logs
docker compose -f docker-compose.test.yml logs -f

# Or specific service
docker compose -f docker-compose.test.yml logs -f api
```

### Check for Errors
```bash
# Search for errors in API logs
docker compose -f docker-compose.test.yml logs api | grep -i error

# Last 100 lines
docker compose -f docker-compose.test.yml logs --tail=100 api
```

---

## Running Unit Tests

### All Tests
```bash
# Run all tests inside container
docker compose -f docker-compose.test.yml exec api pytest /app/tests/ -v

# Expected: 69+ tests passing
```

### Specific Test Categories
```bash
# Unit tests only
docker compose -f docker-compose.test.yml exec api pytest /app/tests/unit/ -v

# Integration tests
docker compose -f docker-compose.test.yml exec api pytest /app/tests/integration/ -v

# E2E tests
docker compose -f docker-compose.test.yml exec api pytest /app/tests/e2e/ -v
```

### Test Coverage
```bash
# Run with coverage report
docker compose -f docker-compose.test.yml exec api pytest \
  --cov=src \
  --cov-report=html \
  --cov-report=term

# View HTML report (from host)
open htmlcov/index.html
```

---

## Stopping Services

### Stop All Services
```bash
# Stop but keep data
docker compose -f docker-compose.test.yml stop

# Stop and remove containers (keeps volumes)
docker compose -f docker-compose.test.yml down

# Stop, remove containers AND volumes (clean slate)
docker compose -f docker-compose.test.yml down -v
```

### Restart Services
```bash
# Restart all services
docker compose -f docker-compose.test.yml restart

# Restart specific service
docker compose -f docker-compose.test.yml restart api
```

---

## Troubleshooting

### Problem: Container fails to start

**Solution 1: Check logs**
```bash
docker compose -f docker-compose.test.yml logs api | tail -50
```

**Solution 2: Check environment variables**
```bash
# Verify .env file exists and has values
cat .env | grep API_KEY

# Check environment inside container
docker compose -f docker-compose.test.yml exec api env | grep ANTHROPIC
```

**Solution 3: Rebuild image**
```bash
# Stop everything
docker compose -f docker-compose.test.yml down

# Rebuild API image
docker compose -f docker-compose.test.yml build api --no-cache

# Start again
docker compose -f docker-compose.test.yml up -d
```

### Problem: Port already in use

**Solution: Change ports in docker-compose.test.yml**
```bash
# Edit file and change ports, e.g.:
# ports:
#   - "8001:8000"  # Changed from 8000:8000
```

### Problem: Out of memory

**Solution: Increase Docker memory**
1. Open Docker Desktop
2. Settings → Resources → Advanced
3. Increase Memory to at least 8GB
4. Click Apply & Restart

### Problem: Database connection timeout

**Solution: Wait for services to be fully ready**
```bash
# Check health status
docker compose -f docker-compose.test.yml ps

# Wait until all show "healthy"
# PostgreSQL typically takes 30-60 seconds
```

---

## Next Steps

Once all tests pass locally:

1. ✅ **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Local Docker testing successful"
   ```

2. ✅ **Review Deployment Plan**
   ```bash
   cat DEPLOYMENT_PLAN.md
   # Follow Phase 2 for staging deployment
   ```

3. ✅ **Configure Production Databases**
   - Add Snowflake credentials to test Snowflake connector
   - Add Databricks credentials to test Databricks connector
   - Test cross-database JOINs with real data

4. ✅ **Performance Testing**
   - Load test with concurrent requests
   - Monitor resource usage
   - Verify cache efficiency

---

## Quick Reference

### Useful Commands
```bash
# Start services
docker compose -f docker-compose.test.yml up -d

# Stop services
docker compose -f docker-compose.test.yml down

# View logs
docker compose -f docker-compose.test.yml logs -f api

# Run tests
./scripts/test_all_features.sh

# Check service status
docker compose -f docker-compose.test.yml ps

# Rebuild API
docker compose -f docker-compose.test.yml build api

# Shell into API container
docker compose -f docker-compose.test.yml exec api bash

# Run Python script in container
docker compose -f docker-compose.test.yml exec api python -c "print('hello')"
```

### Service URLs
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6379
- **MongoDB**: localhost:27017
- **Weaviate**: http://localhost:8082
- **Neo4j Browser**: http://localhost:7474
- **Adminer (DB UI)**: http://localhost:8080

### Health Checks
- API: http://localhost:8000/api/v1/health
- Weaviate: http://localhost:8082/v1/.well-known/ready
- Neo4j: http://localhost:7474

---

## Support

**Documentation**:
- Full deployment plan: `DEPLOYMENT_PLAN.md`
- Multi-database implementation: `MULTI_DATABASE_IMPLEMENTATION_PLAN.md`
- Phase summaries: `backend/PHASE*_SUMMARY.md`

**Logs Location**:
- API logs: `./logs/backend.log`
- Query logs: `./query_logs/`

**Need Help?**
1. Check logs: `docker compose -f docker-compose.test.yml logs api`
2. Verify environment: `cat .env`
3. Check service health: `docker compose -f docker-compose.test.yml ps`

---

**Total Time**: ~30 minutes
**Success Criteria**: All tests passing, all services healthy
**Next**: Proceed to staging deployment (DEPLOYMENT_PLAN.md Phase 2)
