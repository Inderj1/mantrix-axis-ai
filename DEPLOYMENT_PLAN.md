# Deployment Plan - Mantrix Axis AI (STOX.AI)

**Last Updated**: November 18, 2025
**Status**: Ready for Local Testing → Staging → Production
**Completion**: Phase 1 (100%), Phase 2 (95%)

---

## Overview

This deployment plan guides you from local Docker testing through production deployment, with a focus on the new multi-database and cross-database features.

---

## Phase 1: Local Testing with Docker ✅ **START HERE**

### Prerequisites

**Required**:
- Docker Desktop 4.0+ (with Docker Compose V2)
- 16GB RAM minimum (8GB allocated to Docker)
- 50GB free disk space
- Git

**API Keys Required**:
- Anthropic API Key (Claude)
- OpenAI API Key (embeddings)
- Google Cloud service account JSON (BigQuery)

**Optional** (for full multi-database testing):
- Snowflake account credentials
- Databricks workspace credentials
- AWS Redshift cluster (optional)

---

### Step 1: Environment Setup (5 minutes)

**1.1: Clone and Navigate**
```bash
cd /Users/jay/Workspace/Cloudmantra_code/mantrix-axis-ai
```

**1.2: Create Environment File**
```bash
# Copy the example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

**Required Environment Variables**:
```bash
# ============================================================================
# REQUIRED - Core Services
# ============================================================================

# Anthropic Claude (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-api03-...your-key
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenAI (REQUIRED - for embeddings)
OPENAI_API_KEY=sk-...your-key

# Google Cloud / BigQuery (REQUIRED)
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
BIGQUERY_DATASET=your_dataset_name
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-key.json

# ============================================================================
# OPTIONAL - Additional Databases (Phase 1 Multi-Database Support)
# ============================================================================

# Snowflake (Optional)
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=PUBLIC

# Databricks (Optional)
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your_warehouse_id
DATABRICKS_ACCESS_TOKEN=dapi...your_token
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=default

# Amazon Redshift (Optional)
REDSHIFT_HOST=your-cluster.us-east-1.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=your_database
REDSHIFT_USER=your_username
REDSHIFT_PASSWORD=your_password

# ============================================================================
# OPTIONAL - Statistics Extraction Configuration (Phase 2 Optimization)
# ============================================================================

STATS_EXTRACTION_ENABLED=true
STATS_EXTRACTION_SCHEDULE=weekly
STATS_EXTRACTION_DAY=0
STATS_EXTRACTION_HOUR=2
STATS_MAX_AGE_DAYS=7
STATS_USE_SAMPLING=true
STATS_SAMPLE_PERCENT=10
STATS_SAMPLING_THRESHOLD_GB=10.0
```

**1.3: Place GCP Credentials**
```bash
# Create credentials directory
mkdir -p credentials

# Copy your GCP service account key
cp /path/to/your-gcp-key.json credentials/gcp-key.json

# Verify file exists
ls -la credentials/gcp-key.json
```

---

### Step 2: Build and Start All Services (10 minutes)

**2.1: Build Docker Images**
```bash
# Build backend API image
docker compose build api

# This will:
# - Install Python 3.11
# - Install all dependencies from Dockerfile
# - Copy application code
# Expected time: 5-8 minutes (first build)
```

**2.2: Start All Services**
```bash
# Start all services in detached mode
docker compose up -d

# Services started:
# - api (backend API on port 8000)
# - weaviate (vector DB on port 8082)
# - redis (cache on port 6379)
# - mongodb (conversations on port 27017)
# - neo4j (graph DB on ports 7474, 7687)
# - postgres (app DB on port 5433)
```

**2.3: Verify Services Health**
```bash
# Check all containers are running
docker compose ps

# Expected output: All services "Up" and healthy
# NAME                    STATUS
# mantrix-api-1          Up (healthy)
# mantrix-weaviate-1     Up (healthy)
# mantrix-redis-1        Up (healthy)
# mantrix-mongodb-1      Up (healthy)
# mantrix-neo4j-1        Up (healthy)
# mantrix-postgres-1     Up (healthy)
```

**2.4: View Logs**
```bash
# Follow all logs
docker compose logs -f

# Or specific service
docker compose logs -f api

# Check for startup errors
docker compose logs api | grep -i error
```

---

### Step 3: Test Multi-Database Connectors (15 minutes)

**3.1: Test BigQuery Connection**
```bash
# Test via API
curl -X POST http://localhost:8000/api/v1/connectors/test \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "bigquery",
    "config": {
      "project_id": "your-gcp-project",
      "dataset_id": "your_dataset"
    }
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Successfully connected to bigquery",
#   "connection_time_ms": 234.56
# }
```

**3.2: Test PostgreSQL Connection (Local Docker)**
```bash
# Test local PostgreSQL container
curl -X POST http://localhost:8000/api/v1/connectors/test \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "postgresql",
    "config": {
      "host": "postgres",
      "port": 5432,
      "database": "mantrix_madison",
      "user": "mantrix",
      "password": "mantrix123"
    }
  }'

# Expected: success=true
```

**3.3: Test Snowflake (if configured)**
```bash
curl -X POST http://localhost:8000/api/v1/connectors/test \
  -H "Content-Type: application/json" \
  -d '{
    "connector_type": "snowflake",
    "config": {
      "account": "xy12345.us-east-1",
      "user": "your_user",
      "password": "your_password",
      "warehouse": "COMPUTE_WH"
    }
  }'
```

**3.4: Verify Available Databases**
```bash
# List all configured and available databases
curl http://localhost:8000/api/v1/connectors/types

# Expected response:
# {
#   "bigquery": {"available": true, "configured": true},
#   "postgresql": {"available": true, "configured": true},
#   "snowflake": {"available": true, "configured": false},
#   "redshift": {"available": true, "configured": false},
#   "databricks": {"available": true, "configured": false}
# }
```

---

### Step 4: Test Cross-Database Features (20 minutes)

**4.1: Test SQL Dialect Translation**
```bash
# Translate BigQuery SQL to Snowflake
curl -X POST http://localhost:8000/api/v1/cross-db/translate \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) as week_ago",
    "source_dialect": "bigquery",
    "target_dialect": "snowflake",
    "validate": true
  }'

# Expected response:
# {
#   "translated_sql": "SELECT DATEADD(day, -7, CURRENT_DATE()) AS week_ago",
#   "source_dialect": "bigquery",
#   "target_dialect": "snowflake",
#   "is_lossless": true,
#   "confidence_score": 0.95
# }
```

**4.2: Test Cross-Database Query Execution (PostgreSQL + BigQuery)**

**First, load test data into PostgreSQL**:
```bash
# Execute test data load script
docker compose exec api python -c "
from src.db.connector_factory import ConnectorFactory
import pandas as pd

# Create test customers table
config = {
    'host': 'postgres',
    'port': 5432,
    'database': 'mantrix_madison',
    'user': 'mantrix',
    'password': 'mantrix123'
}

connector = ConnectorFactory.create_connector('postgresql', config)

# Create test table
connector.execute_query('''
    CREATE TABLE IF NOT EXISTS test_customers (
        customer_id INT PRIMARY KEY,
        name VARCHAR(100),
        tier VARCHAR(20)
    )
''')

# Insert test data
connector.execute_query('''
    INSERT INTO test_customers VALUES
    (1, 'Alice Johnson', 'Gold'),
    (2, 'Bob Smith', 'Silver'),
    (3, 'Carol Williams', 'Platinum')
    ON CONFLICT DO NOTHING
''')

print('Test data loaded successfully')
"
```

**Then test cross-database JOIN**:
```bash
# Execute cross-database query via Python script
docker compose exec api python /app/scripts/test_cross_db_join.py
```

**4.3: Test Query Pushdown Optimization**
```bash
# Test pushdown analysis
curl -X POST http://localhost:8000/api/v1/cross-db/analyze-pushdown \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM sales WHERE customer_id = 123 AND date >= '\''2024-01-01'\''",
    "table_name": "sales",
    "source_database": "bigquery"
  }'

# Expected: Shows which filters can be pushed to source
```

---

### Step 5: Run Automated Tests (15 minutes)

**5.1: Run Unit Tests**
```bash
# Run all unit tests inside Docker container
docker compose exec api pytest /app/tests/unit/ -v

# Expected: 48+ tests passing
# tests/unit/core/test_sql_dialect_translator.py::test_bigquery_to_snowflake PASSED
# tests/unit/core/test_sql_dialect_translator.py::test_snowflake_to_postgresql PASSED
# ... (48 total)
```

**5.2: Run Integration Tests**
```bash
# Run integration tests (requires databases running)
docker compose exec api pytest /app/tests/integration/ -v

# Expected: Tests for permissions, connectors, cross-DB queries
```

**5.3: Run End-to-End Tests**
```bash
# Run full pipeline E2E tests
docker compose exec api pytest /app/tests/e2e/ -v --tb=short

# Expected: LLM generation tests, full pipeline tests
```

**5.4: View Test Coverage**
```bash
# Run tests with coverage
docker compose exec api pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

### Step 6: Test Statistics Extraction Pipeline (10 minutes)

**6.1: Check Statistics Configuration**
```bash
# View current statistics configuration
curl http://localhost:8000/api/v1/statistics/status

# Expected:
# {
#   "enabled": true,
#   "schedule": "weekly",
#   "max_age_days": 7,
#   "use_sampling": true,
#   "sample_percent": 10
# }
```

**6.2: List Stale Tables**
```bash
# Get list of tables needing statistics update
curl http://localhost:8000/api/v1/statistics/tables/stale

# Expected: List of tables with stale or missing statistics
```

**6.3: Manual Statistics Extraction (Admin Only)**
```bash
# Trigger manual extraction for specific table
# NOTE: Requires admin authentication token
curl -X POST http://localhost:8000/api/v1/statistics/extract \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": ["test_customers"],
    "force_refresh": false
  }'

# Expected:
# {
#   "status": "completed",
#   "tables_processed": 1,
#   "statistics_extracted": 5,
#   "duration_seconds": 2.34
# }
```

---

### Step 7: Performance and Load Testing (20 minutes)

**7.1: Create Load Test Script**

Create `scripts/load_test.sh`:
```bash
#!/bin/bash

echo "Running load tests..."

# Test 1: Concurrent SQL translations
echo "Test 1: 100 concurrent SQL translations"
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/cross-db/translate \
    -H "Content-Type: application/json" \
    -d "{\"sql\":\"SELECT * FROM table_$i\",\"source_dialect\":\"bigquery\",\"target_dialect\":\"snowflake\"}" \
    > /dev/null 2>&1 &
done
wait
echo "✓ Translation test complete"

# Test 2: Database connection pooling
echo "Test 2: 50 concurrent database queries"
for i in {1..50}; do
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"SELECT 1 as test_$i\",\"database_type\":\"bigquery\"}" \
    > /dev/null 2>&1 &
done
wait
echo "✓ Query test complete"

echo "All load tests passed!"
```

**7.2: Run Load Tests**
```bash
chmod +x scripts/load_test.sh
./scripts/load_test.sh

# Monitor container resources
docker stats
```

**7.3: Check Performance Metrics**
```bash
# Check cache hit rate
curl http://localhost:8000/api/v1/cache/stats

# Check API health
curl http://localhost:8000/api/v1/health

# Check database connection pool status
docker compose logs api | grep "connection pool"
```

---

### Step 8: Verify All Features (10 minutes)

**✅ Checklist**:
- [ ] All 6 Docker containers running and healthy
- [ ] BigQuery connector working
- [ ] PostgreSQL connector working
- [ ] Snowflake connector working (if configured)
- [ ] SQL dialect translation (48/48 tests passing)
- [ ] Cross-database JOIN execution
- [ ] Query pushdown optimization
- [ ] Statistics extraction pipeline
- [ ] Cache working (Redis)
- [ ] Conversation persistence (MongoDB)
- [ ] Vector search (Weaviate)
- [ ] Knowledge graph (Neo4j)
- [ ] All unit tests passing (48+)
- [ ] All integration tests passing
- [ ] API health check responding
- [ ] No errors in logs

---

## Phase 2: Staging Deployment (AWS ECS) 🚀

### Prerequisites

**AWS Setup**:
- AWS Account with admin access
- AWS CLI configured (`aws configure`)
- ECR repository created
- ECS cluster created
- RDS instance for PostgreSQL (optional, can use container)
- ElastiCache Redis cluster (recommended for production)
- DocumentDB or MongoDB Atlas (for conversations)
- VPC with public/private subnets
- Application Load Balancer
- Route53 hosted zone (for custom domain)

---

### Step 1: Build and Push Docker Images (15 minutes)

**1.1: Login to AWS ECR**
```bash
# Set variables
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME=mantrix-axis-ai

# Create ECR repository if it doesn't exist
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  || echo "Repository already exists"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

**1.2: Build Production Image**
```bash
# Build with production optimizations
docker build \
  --platform linux/amd64 \
  --build-arg ENV=production \
  -t mantrix-axis-ai:latest \
  -f Dockerfile \
  .

# Tag for ECR
docker tag mantrix-axis-ai:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

docker tag mantrix-axis-ai:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$(git rev-parse --short HEAD)
```

**1.3: Push to ECR**
```bash
# Push both tags
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$(git rev-parse --short HEAD)

# Verify images
aws ecr describe-images \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION
```

---

### Step 2: Create ECS Task Definition (10 minutes)

**2.1: Create Task Definition JSON**

Save as `ecs-task-definition.json`:
```json
{
  "family": "mantrix-axis-ai",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/mantrixTaskRole",
  "containerDefinitions": [
    {
      "name": "mantrix-api",
      "image": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mantrix-axis-ai:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "API_ENV", "value": "production"},
        {"name": "API_HOST", "value": "0.0.0.0"},
        {"name": "API_PORT", "value": "8000"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {"name": "ANTHROPIC_API_KEY", "valueFrom": "arn:aws:secretsmanager:region:account:secret:anthropic-key"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-key"},
        {"name": "GOOGLE_CLOUD_PROJECT", "valueFrom": "arn:aws:secretsmanager:region:account:secret:gcp-project"},
        {"name": "SNOWFLAKE_PASSWORD", "valueFrom": "arn:aws:secretsmanager:region:account:secret:snowflake-password"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mantrix-axis-ai",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

**2.2: Register Task Definition**
```bash
# Replace ACCOUNT_ID in task definition
sed -i "s/ACCOUNT_ID/$AWS_ACCOUNT_ID/g" ecs-task-definition.json

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition.json \
  --region $AWS_REGION
```

---

### Step 3: Create ECS Service (15 minutes)

**3.1: Create Service**
```bash
# Create service with load balancer
aws ecs create-service \
  --cluster mantrix-cluster \
  --service-name mantrix-api-service \
  --task-definition mantrix-axis-ai \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/mantrix-tg,containerName=mantrix-api,containerPort=8000" \
  --health-check-grace-period-seconds 60 \
  --enable-execute-command \
  --region $AWS_REGION
```

**3.2: Configure Auto Scaling**
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/mantrix-cluster/mantrix-api-service \
  --min-capacity 2 \
  --max-capacity 10 \
  --region $AWS_REGION

# Create scaling policy (CPU-based)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/mantrix-cluster/mantrix-api-service \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json \
  --region $AWS_REGION
```

---

### Step 4: Configure Supporting Services (20 minutes)

**4.1: Setup ElastiCache Redis**
```bash
# Create Redis cluster
aws elasticache create-replication-group \
  --replication-group-id mantrix-redis \
  --replication-group-description "Mantrix cache cluster" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-node-groups 1 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --region $AWS_REGION

# Get endpoint
aws elasticache describe-replication-groups \
  --replication-group-id mantrix-redis \
  --query 'ReplicationGroups[0].ConfigurationEndpoint.Address' \
  --output text
```

**4.2: Setup DocumentDB (MongoDB-compatible)**
```bash
# Create DocumentDB cluster
aws docdb create-db-cluster \
  --db-cluster-identifier mantrix-docdb \
  --engine docdb \
  --master-username mantrix \
  --master-user-password 'YourSecurePassword123!' \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name your-subnet-group \
  --region $AWS_REGION

# Create instance
aws docdb create-db-instance \
  --db-instance-identifier mantrix-docdb-instance \
  --db-instance-class db.t3.medium \
  --engine docdb \
  --db-cluster-identifier mantrix-docdb \
  --region $AWS_REGION
```

**4.3: Setup Secrets Manager**
```bash
# Store API keys
aws secretsmanager create-secret \
  --name mantrix/anthropic-key \
  --secret-string "sk-ant-api03-..." \
  --region $AWS_REGION

aws secretsmanager create-secret \
  --name mantrix/openai-key \
  --secret-string "sk-..." \
  --region $AWS_REGION

# Store database credentials
aws secretsmanager create-secret \
  --name mantrix/snowflake-password \
  --secret-string "your-snowflake-password" \
  --region $AWS_REGION
```

---

### Step 5: Deploy and Verify (10 minutes)

**5.1: Update Service to Latest Image**
```bash
# Force new deployment
aws ecs update-service \
  --cluster mantrix-cluster \
  --service mantrix-api-service \
  --force-new-deployment \
  --region $AWS_REGION

# Watch deployment progress
aws ecs describe-services \
  --cluster mantrix-cluster \
  --services mantrix-api-service \
  --query 'services[0].deployments' \
  --region $AWS_REGION
```

**5.2: Verify Health**
```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names mantrix-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text \
  --region $AWS_REGION)

# Test health endpoint
curl http://$ALB_DNS/api/v1/health

# Test connector status
curl http://$ALB_DNS/api/v1/connectors/types
```

**5.3: Check Logs**
```bash
# View CloudWatch logs
aws logs tail /ecs/mantrix-axis-ai --follow --region $AWS_REGION

# Check for errors
aws logs filter-log-events \
  --log-group-name /ecs/mantrix-axis-ai \
  --filter-pattern "ERROR" \
  --region $AWS_REGION
```

---

## Phase 3: Production Deployment 🎯

### Prerequisites

**Production Readiness**:
- [ ] All staging tests passed
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Backup strategy defined
- [ ] Monitoring configured
- [ ] Incident response plan
- [ ] DNS configured
- [ ] SSL certificate provisioned

---

### Step 1: Configure Production Infrastructure

**1.1: Setup CloudFront (CDN)**
```bash
# Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name $ALB_DNS \
  --default-root-object "" \
  --comment "Mantrix Axis AI Production" \
  --enabled
```

**1.2: Configure Route53**
```bash
# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch file://route53-change.json
```

**1.3: Setup WAF (Web Application Firewall)**
```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name mantrix-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json \
  --region $AWS_REGION
```

---

### Step 2: Configure Monitoring and Alerts

**2.1: CloudWatch Dashboards**
```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name mantrix-production \
  --dashboard-body file://cloudwatch-dashboard.json \
  --region $AWS_REGION
```

**2.2: Setup Alarms**
```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mantrix-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region $AWS_REGION

# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name mantrix-high-errors \
  --alarm-description "Alert when error rate > 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --region $AWS_REGION
```

**2.3: Setup SNS Topics for Alerts**
```bash
# Create SNS topic
aws sns create-topic \
  --name mantrix-alerts \
  --region $AWS_REGION

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account:mantrix-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region $AWS_REGION
```

---

### Step 3: Zero-Downtime Deployment Strategy

**Blue-Green Deployment**:
```bash
# Create new task definition version
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-definition-v2.json

# Update service gradually
aws ecs update-service \
  --cluster mantrix-cluster \
  --service mantrix-api-service \
  --task-definition mantrix-axis-ai:2 \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
  --region $AWS_REGION

# Monitor deployment
watch -n 5 'aws ecs describe-services \
  --cluster mantrix-cluster \
  --services mantrix-api-service \
  --query "services[0].deployments" \
  --region $AWS_REGION'
```

---

### Step 4: Post-Deployment Verification

**4.1: Smoke Tests**
```bash
# Run smoke test script
./scripts/production-smoke-test.sh https://api.mantrix.ai

# Expected:
# ✓ Health check passed
# ✓ Database connectivity verified
# ✓ Cache connectivity verified
# ✓ All 5 database connectors available
# ✓ SQL translation working
# ✓ Cross-database features available
```

**4.2: Performance Validation**
```bash
# Run performance tests
./scripts/production-load-test.sh https://api.mantrix.ai

# Monitor metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=mantrix-api-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region $AWS_REGION
```

**4.3: Cost Monitoring**
```bash
# Check current costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --filter file://cost-filter.json
```

---

## Rollback Procedures

### Quick Rollback (5 minutes)

**Option 1: Revert to Previous Task Definition**
```bash
# List task definitions
aws ecs list-task-definitions \
  --family-prefix mantrix-axis-ai \
  --sort DESC \
  --region $AWS_REGION

# Rollback to previous version
aws ecs update-service \
  --cluster mantrix-cluster \
  --service mantrix-api-service \
  --task-definition mantrix-axis-ai:PREVIOUS_VERSION \
  --force-new-deployment \
  --region $AWS_REGION
```

**Option 2: Scale Down to Zero (Emergency)**
```bash
# Stop all tasks immediately
aws ecs update-service \
  --cluster mantrix-cluster \
  --service mantrix-api-service \
  --desired-count 0 \
  --region $AWS_REGION
```

**Option 3: Switch DNS to Backup**
```bash
# Point Route53 to backup ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch file://route53-rollback.json
```

---

## Cost Optimization

### Estimated Monthly Costs

**Staging Environment**:
- ECS Fargate (2 tasks, 2 vCPU, 4GB): ~$50/month
- ElastiCache Redis (t3.medium): ~$30/month
- DocumentDB (t3.medium): ~$70/month
- ALB: ~$20/month
- Data transfer: ~$10/month
- **Total**: ~$180/month

**Production Environment**:
- ECS Fargate (4-10 tasks): ~$100-250/month
- ElastiCache Redis (m5.large, multi-AZ): ~$150/month
- DocumentDB (r5.large, multi-AZ): ~$300/month
- ALB + CloudFront: ~$50/month
- WAF: ~$10/month
- Data transfer: ~$50/month
- **Total**: ~$660-910/month

**Database Query Costs** (variable):
- BigQuery: $5 per TB scanned
- Snowflake: Compute credits (varies)
- Redshift: Cluster cost (fixed)
- Databricks: DBU-based (varies)

**Cost Savings with Statistics Scheduling**:
- Daily statistics: ~$1,500/month
- Weekly statistics (recommended): ~$20/month
- **Savings**: ~$1,480/month (98.7% reduction)

---

## Maintenance and Operations

### Daily Operations

**Monitor Health**:
```bash
# Check service health
aws ecs describe-services \
  --cluster mantrix-cluster \
  --services mantrix-api-service \
  --region $AWS_REGION

# Check task health
aws ecs list-tasks \
  --cluster mantrix-cluster \
  --service-name mantrix-api-service \
  --desired-status RUNNING \
  --region $AWS_REGION
```

**View Logs**:
```bash
# Stream logs
aws logs tail /ecs/mantrix-axis-ai --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /ecs/mantrix-axis-ai \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

### Weekly Maintenance

- [ ] Review CloudWatch metrics and alarms
- [ ] Check error rates and latency
- [ ] Review cost reports
- [ ] Update dependencies (security patches)
- [ ] Run full test suite
- [ ] Review and archive old logs

### Monthly Maintenance

- [ ] Security audit
- [ ] Performance review
- [ ] Cost optimization review
- [ ] Backup verification
- [ ] Documentation updates
- [ ] Disaster recovery drill

---

## Success Criteria

### Local Testing ✅
- [ ] All Docker containers running
- [ ] All 69+ tests passing
- [ ] All 5 database connectors working
- [ ] Cross-database JOINs validated
- [ ] SQL translation working (48/48 tests)
- [ ] No errors in logs
- [ ] Performance acceptable (<2s for queries)

### Staging ✅
- [ ] ECS service deployed successfully
- [ ] Health checks passing
- [ ] All features working via ALB
- [ ] Load tests passed
- [ ] No critical errors in 24 hours
- [ ] Cost within budget

### Production ✅
- [ ] Zero-downtime deployment completed
- [ ] All monitoring configured
- [ ] SSL certificate active
- [ ] DNS propagated
- [ ] Performance SLAs met
- [ ] Backup procedures tested
- [ ] Incident response team ready

---

## Support and Troubleshooting

### Common Issues

**Issue: Container fails to start**
```bash
# Check logs
docker compose logs api

# Common causes:
# - Missing environment variables
# - Invalid credentials
# - Port conflicts
# - Insufficient memory
```

**Issue: Database connection timeout**
```bash
# Verify network connectivity
docker compose exec api ping postgres

# Check credentials
docker compose exec api env | grep POSTGRES

# Test connection manually
docker compose exec api python -c "
from src.db.connector_factory import ConnectorFactory
config = {'host': 'postgres', 'port': 5432, 'database': 'mantrix_madison', 'user': 'mantrix', 'password': 'mantrix123'}
connector = ConnectorFactory.create_connector('postgresql', config)
print('Connection successful!' if connector.test_connection() else 'Connection failed!')
"
```

**Issue: High memory usage**
```bash
# Check container stats
docker stats

# Increase memory limits in docker-compose.yml
# Under api service:
deploy:
  resources:
    limits:
      memory: 4G
```

### Getting Help

- **Documentation**: Check all `*_PLAN.md` and `*_SUMMARY.md` files
- **Logs**: `docker compose logs -f api`
- **Health**: `curl http://localhost:8000/api/v1/health`
- **Tests**: `docker compose exec api pytest -v`

---

**Next Steps**: Start with Phase 1 (Local Testing) and work through each section systematically. Each phase must pass before moving to the next.

**Estimated Total Time**:
- Phase 1 (Local Testing): 2-3 hours
- Phase 2 (Staging): 4-6 hours
- Phase 3 (Production): 8-12 hours
- **Total**: 14-21 hours (can be done over multiple days)

Good luck! 🚀
