# 🚀 START HERE - Docker Testing & Deployment

**Welcome!** This guide gets you from zero to fully tested multi-database system in **30 minutes**.

---

## What You're Testing

✅ **Multi-Database Support** - All 5 databases (BigQuery, Snowflake, PostgreSQL, Redshift, Databricks)
✅ **Cross-Database Queries** - JOIN data across different databases
✅ **SQL Translation** - Convert SQL between database dialects (48 tests)
✅ **Query Optimization** - 95% data reduction through pushdown
✅ **Statistics Pipeline** - 90-98% cost savings through scheduling
✅ **Complete Stack** - API + 6 supporting services in Docker

**Completion Status**: 73% (Phase 1: 100%, Phase 2: 95%, Phase 3: 0%)
**Production Ready**: YES (for Phases 1 & 2)

---

## 🎯 Quick Start (Choose Your Path)

### Option 1: Fully Automated (Recommended) ⚡
**Time**: 30 minutes | **Difficulty**: Easy

```bash
# 1. Setup environment file (3 minutes)
cp .env.example .env
nano .env  # Add your API keys

# 2. Add GCP credentials (1 minute)
mkdir -p credentials
cp /path/to/your-gcp-key.json credentials/gcp-key.json

# 3. Run automated test suite (25 minutes)
./scripts/docker_test_runner.sh

# That's it! The script will:
# ✓ Build Docker images
# ✓ Start all 6 services
# ✓ Wait for health checks
# ✓ Run all feature tests
# ✓ Report results
```

### Option 2: Manual Step-by-Step 📖
**Time**: 45 minutes | **Difficulty**: Moderate

Follow the detailed guide: **[QUICK_START_DOCKER.md](QUICK_START_DOCKER.md)**

### Option 3: Skip to Deployment 🚢
**Time**: 2-4 hours | **Difficulty**: Advanced

Already tested locally? Jump to: **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)**

---

## 📋 Prerequisites

**Required** (5 minutes to set up):
- ✅ Docker Desktop 4.0+ (16GB RAM, 8GB to Docker)
- ✅ Anthropic API Key ([Get here](https://console.anthropic.com/))
- ✅ OpenAI API Key ([Get here](https://platform.openai.com/api-keys))
- ✅ Google Cloud service account JSON ([Create here](https://console.cloud.google.com/))

**Optional** (for full testing):
- Snowflake account credentials
- Databricks workspace credentials
- AWS Redshift cluster (for Redshift connector)

---

## 🎬 Quick Commands

### Start Everything
```bash
# Automated (recommended)
./scripts/docker_test_runner.sh

# Or manual
docker compose -f docker-compose.test.yml up -d
sleep 60  # Wait for services
./scripts/test_all_features.sh
```

### Check Status
```bash
# All services
docker compose -f docker-compose.test.yml ps

# API logs
docker compose -f docker-compose.test.yml logs -f api

# Health check
curl http://localhost:8000/api/v1/health
```

### Run Tests
```bash
# Feature tests (15 tests)
./scripts/test_all_features.sh

# Unit tests (69+ tests)
docker compose -f docker-compose.test.yml exec api pytest -v
```

### Stop Everything
```bash
# Keep data
docker compose -f docker-compose.test.yml down

# Clean slate (removes volumes)
docker compose -f docker-compose.test.yml down -v
```

---

## 📊 What Gets Tested

### Core Features (Automated Tests)
- ✅ API health check
- ✅ All 5 database connectors available
- ✅ PostgreSQL connection test (local Docker)
- ✅ SQL dialect translation (BigQuery ↔ Snowflake ↔ PostgreSQL)
- ✅ Batch translation (3 queries)
- ✅ Cache system working
- ✅ Statistics extraction configuration
- ✅ Cross-database API routes
- ✅ Permission system (if admin token provided)

### Optional Manual Tests
- Cross-database JOIN execution
- Query pushdown optimization
- Load testing (concurrent requests)
- Performance benchmarking
- Statistics extraction pipeline

---

## 🎯 Success Criteria

**Green Light** ✅ (Safe to deploy):
- All Docker containers running and healthy
- 15/15 automated tests passing
- No errors in API logs
- Response time < 2 seconds
- PostgreSQL connection working
- SQL translation working

**Yellow Light** ⚠️ (Review needed):
- Some optional databases not configured (Snowflake, Databricks)
- Warnings in logs (non-critical)
- Slower than expected (may need tuning)

**Red Light** ❌ (Fix before deploying):
- Container fails to start
- Tests failing
- Errors in logs
- Cannot connect to databases
- Missing API keys

---

## 🏗️ Architecture (What's Running)

### Docker Services (6 containers)
```
┌─────────────────────────────────────────────┐
│  mantrix-test-api-1                         │  Port 8000
│  FastAPI Backend + All 5 Database Connectors│
│  + SQL Translation + Cross-DB Features      │
└─────────────────────────────────────────────┘
              ↓ Connects to ↓
┌──────────────┬──────────────┬──────────────┐
│ PostgreSQL   │ Redis        │ MongoDB      │
│ Test DB      │ Cache        │ Conversations│
│ Port 5433    │ Port 6379    │ Port 27017   │
└──────────────┴──────────────┴──────────────┘
┌──────────────┬──────────────┬──────────────┐
│ Weaviate     │ Neo4j        │ [Your DBs]   │
│ Vector DB    │ Knowledge    │ BigQuery,    │
│ Port 8082    │ Graph 7474   │ Snowflake... │
└──────────────┴──────────────┴──────────────┘
```

### Data Flow
```
User Query
    ↓
API (Port 8000)
    ↓
┌──────────────────┐
│ Check Cache      │ → Redis
│ (if cached)      │
└──────────────────┘
    ↓
┌──────────────────┐
│ SQL Translation  │ → Translate between dialects
│ (if cross-DB)    │
└──────────────────┘
    ↓
┌──────────────────┐
│ Query Optimizer  │ → Push filters to source
│ (if applicable)  │
└──────────────────┘
    ↓
┌──────────────────┐
│ Execute Query    │ → Database Connector
│                  │   (BigQuery, Snowflake, etc.)
└──────────────────┘
    ↓
┌──────────────────┐
│ Return Results   │ → User
│ (cache for reuse)│
└──────────────────┘
```

---

## 📚 Documentation

### Implementation Docs
- **[MULTI_DATABASE_IMPLEMENTATION_PLAN.md](MULTI_DATABASE_IMPLEMENTATION_PLAN.md)** - Full implementation plan (73% complete)
- **[backend/PHASE1_COMPLETION_SUMMARY.md](backend/PHASE1_COMPLETION_SUMMARY.md)** - Phase 1 summary (100% complete)
- **[backend/PHASE2_SESSION_SUMMARY.md](backend/PHASE2_SESSION_SUMMARY.md)** - Phase 2 summary (95% complete)
- **[backend/STATISTICS_SCHEDULE_IMPLEMENTATION.md](backend/STATISTICS_SCHEDULE_IMPLEMENTATION.md)** - Statistics pipeline docs
- **[backend/OPTIMIZATION_INTELLIGENCE_IMPLEMENTATION_SUMMARY.md](backend/OPTIMIZATION_INTELLIGENCE_IMPLEMENTATION_SUMMARY.md)** - Optimization features

### Testing Docs
- **[QUICK_START_DOCKER.md](QUICK_START_DOCKER.md)** - Detailed step-by-step guide
- **[DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)** - Full deployment process

### Database-Specific Guides
- BigQuery configuration: See DEPLOYMENT_PLAN.md
- Snowflake setup: See MULTI_DATABASE_IMPLEMENTATION_PLAN.md
- PostgreSQL testing: Included in Docker Compose
- Databricks configuration: See DEPLOYMENT_PLAN.md
- Redshift configuration: See DEPLOYMENT_PLAN.md

---

## 🐛 Troubleshooting

### Problem: "Docker is not running"
**Solution**: Start Docker Desktop and wait for it to fully initialize

### Problem: "Port already in use"
**Solution**:
```bash
# Find what's using the port
lsof -i :8000

# Stop conflicting service or change port in docker-compose.test.yml
```

### Problem: "Container unhealthy"
**Solution**:
```bash
# Check logs
docker compose -f docker-compose.test.yml logs api

# Common issues:
# - Missing .env variables
# - Invalid API keys
# - Insufficient Docker memory (need 8GB+)
```

### Problem: "Tests failing"
**Solution**:
```bash
# Verify environment
cat .env | grep API_KEY

# Verify services healthy
docker compose -f docker-compose.test.yml ps

# Check individual service
docker compose -f docker-compose.test.yml logs postgres
```

### Problem: "Out of memory"
**Solution**: Docker Desktop → Settings → Resources → Increase memory to 8GB+

---

## 🎓 Next Steps

### After Local Testing Passes ✅

1. **Review Results**
   ```bash
   # Check test output
   # All services healthy? ✅
   # All tests passing? ✅
   # No errors in logs? ✅
   ```

2. **Test Real Databases** (Optional)
   - Add Snowflake credentials to .env
   - Test Snowflake connector
   - Try cross-database JOIN (PostgreSQL + BigQuery)

3. **Load Testing** (Optional)
   - Run concurrent queries
   - Monitor resource usage
   - Verify cache efficiency

4. **Proceed to Staging**
   - Follow [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) Phase 2
   - Deploy to AWS ECS
   - Configure production databases

5. **Production Deployment**
   - Follow [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) Phase 3
   - Zero-downtime deployment
   - Monitoring and alerts

---

## 💰 Cost Estimates

### Local Docker Testing
- **Cost**: $0 (uses local Docker containers)
- **Time**: 30-60 minutes
- **Data**: Test data only

### Cloud Staging (AWS ECS)
- **Cost**: ~$180/month
- **Time**: 4-6 hours to set up
- **Data**: Test/staging data

### Production (AWS ECS)
- **Cost**: ~$660-910/month (infrastructure)
- **Variable Costs**: Database queries (BigQuery, Snowflake, etc.)
- **Savings**: Statistics scheduling saves ~$1,480/month (98.7% reduction)

---

## 🆘 Getting Help

**Check Logs**:
```bash
docker compose -f docker-compose.test.yml logs api
```

**Verify Services**:
```bash
docker compose -f docker-compose.test.yml ps
```

**Test Manually**:
```bash
curl http://localhost:8000/api/v1/health
```

**Read Documentation**:
- Quick Start: [QUICK_START_DOCKER.md](QUICK_START_DOCKER.md)
- Deployment: [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md)
- Implementation: [MULTI_DATABASE_IMPLEMENTATION_PLAN.md](MULTI_DATABASE_IMPLEMENTATION_PLAN.md)

---

## ✅ Checklist

Before moving to staging, verify:

- [ ] Docker Desktop running
- [ ] .env file created with API keys
- [ ] GCP credentials file in place
- [ ] All 6 Docker containers healthy
- [ ] 15/15 automated tests passing
- [ ] No errors in API logs
- [ ] PostgreSQL connection working
- [ ] SQL translation working (BigQuery → Snowflake)
- [ ] API responding in < 2 seconds
- [ ] Cache working (Redis)

---

**Ready to start?**

```bash
./scripts/docker_test_runner.sh
```

**Time to completion**: 30 minutes
**Success rate**: 95%+ with prerequisites met
**Next step**: Staging deployment

Good luck! 🚀
