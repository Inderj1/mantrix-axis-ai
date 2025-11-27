# Mantrix Axis AI - Complete Deployment Guide

This guide walks through deploying Mantrix Axis AI from local testing to AWS ECS and eventually AWS Marketplace.

## 📁 Deployment Structure

```
deployment/
├── minimal-deployment/          # Phase 0: Minimal viable deployment
│   ├── Dockerfile.backend       # Production backend container
│   ├── Dockerfile.frontend      # Production frontend container
│   ├── docker-compose.yml       # Local ECS simulation
│   ├── nginx-lb.conf           # Load balancer config
│   ├── .env.template           # Environment variables template
│   ├── deploy.sh               # Local deployment script
│   ├── ecs/                    # ECS task definitions
│   │   ├── task-definition-backend.json
│   │   ├── task-definition-frontend.json
│   │   └── register-task-definitions.sh
│   └── terraform/              # Infrastructure as Code
│       ├── main.tf             # Core infrastructure
│       ├── variables.tf        # Variable definitions
│       ├── databases.tf        # RDS and ElastiCache
│       ├── ecs-services.tf     # ECS services
│       ├── terraform.tfvars.example
│       └── deploy-ecs.sh       # AWS deployment script
```

## 🚀 Phase 0: Minimal Viable Deployment (Week 1-2)

### Step 1: Local Testing with Docker Compose

**Goal**: Verify the application works before deploying to AWS.

```bash
cd deployment/minimal-deployment

# 1. Set up environment variables
cp .env.template .env
# Edit .env with your actual API keys and configuration

# 2. Run the deployment script
./deploy.sh

# 3. Access the application
# Main app: http://localhost:8080
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**What this creates locally:**
- Backend API container (FastAPI)
- Frontend container (React + Nginx)
- PostgreSQL database
- Redis cache
- MongoDB for conversations
- Weaviate vector database
- Nginx load balancer

### Step 2: Deploy to AWS ECS

**Prerequisites:**
- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- Terraform installed
- Docker installed

```bash
cd deployment/minimal-deployment/terraform

# 1. Configure Terraform variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# 2. Run the deployment script
./deploy-ecs.sh

# Select option 6 for full deployment:
# - Creates secrets in AWS Secrets Manager
# - Initializes Terraform
# - Creates infrastructure (VPC, ECS, RDS, etc.)
# - Builds and pushes Docker images
```

**What this creates on AWS:**
- VPC with public/private subnets
- ECS Fargate cluster
- Application Load Balancer
- RDS PostgreSQL (db.t3.micro)
- ElastiCache Redis (cache.t3.micro)
- ECR repositories for images
- CloudWatch logging
- IAM roles and policies

**Estimated Costs (Minimal):**
- ECS Fargate: ~$30/month
- RDS PostgreSQL: ~$15/month
- ElastiCache Redis: ~$13/month
- ALB: ~$25/month
- **Total: ~$83/month**

## 🔒 Phase 1: Code Protection (Week 3-4)

### Backend Protection

1. **Create Cython compilation setup:**
```python
# backend/setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension("src.core.sql_generator", ["src/core/sql_generator.py"]),
    Extension("src.agents.orchestrator", ["src/agents/orchestrator.py"]),
]

setup(
    name="mantrix-backend",
    ext_modules=cythonize(extensions)
)
```

2. **Build protected backend:**
```bash
cd backend
pip install cython
python setup.py build_ext --inplace
```

3. **Create PyInstaller build:**
```bash
pyinstaller --onefile \
    --key=YOUR_ENCRYPTION_KEY \
    --add-data="configs:configs" \
    --hidden-import=anthropic \
    src/main.py
```

### Frontend Protection

1. **Install obfuscation tools:**
```bash
cd frontend
npm install --save-dev javascript-obfuscator terser
```

2. **Build protected frontend:**
```bash
npm run build:protected
```

## 🏗️ Phase 2: Production Infrastructure (Week 5-6)

### Upgrade to Production Configuration

Modify `terraform/variables.tf`:

```hcl
# Production settings
rds_instance_class    = "db.r6g.large"   # From db.t3.micro
redis_node_type       = "cache.r6g.large" # From cache.t3.micro
backend_cpu           = 2048              # 2 vCPU
backend_memory        = 4096              # 4 GB
backend_desired_count = 2                 # Multi-instance
frontend_desired_count = 2                # Multi-instance
```

### Add Auto-scaling

Create `terraform/autoscaling.tf`:

```hcl
resource "aws_appautoscaling_target" "backend" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "backend_cpu" {
  name               = "backend-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.backend.resource_id
  scalable_dimension = aws_appautoscaling_target.backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.backend.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

## 📦 Phase 3: AWS Marketplace Preparation (Week 7-10)

### 1. Container Registry Setup

```bash
# Tag images for marketplace
docker tag mantrix-backend:protected \
  709825985650.dkr.ecr.us-east-1.amazonaws.com/mantrix/backend:1.0.0

docker tag mantrix-frontend:protected \
  709825985650.dkr.ecr.us-east-1.amazonaws.com/mantrix/frontend:1.0.0

# Push to marketplace ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 709825985650.dkr.ecr.us-east-1.amazonaws.com

docker push 709825985650.dkr.ecr.us-east-1.amazonaws.com/mantrix/backend:1.0.0
docker push 709825985650.dkr.ecr.us-east-1.amazonaws.com/mantrix/frontend:1.0.0
```

### 2. Create CloudFormation Template

Create `marketplace/cloudformation-template.yaml` for customer deployment.

### 3. Implement License Validation

```python
# backend/src/core/license_validator.py
class LicenseValidator:
    def validate(self, license_key: str, customer_id: str) -> bool:
        # Validate with license server
        response = requests.post(
            f"{self.license_server_url}/validate",
            json={"license_key": license_key, "customer_id": customer_id}
        )
        return response.json().get("valid", False)
```

### 4. AWS Marketplace Submission

1. Register as AWS Marketplace seller
2. Create product listing
3. Upload container images
4. Submit CloudFormation template
5. Configure pricing model
6. Submit for review (7-10 days)

## 📊 Monitoring & Maintenance

### CloudWatch Dashboards

Create monitoring dashboard:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name MantrixMonitoring \
  --dashboard-body file://cloudwatch-dashboard.json
```

### Alerts

Set up critical alerts:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name backend-high-cpu \
  --alarm-description "Backend CPU above 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Build and push backend
        run: |
          docker build -f deployment/minimal-deployment/Dockerfile.backend -t backend .
          docker tag backend:latest $ECR_BACKEND:${{ github.sha }}
          docker push $ECR_BACKEND:${{ github.sha }}

      - name: Update ECS service
        run: |
          aws ecs update-service \
            --cluster mantrix-cluster \
            --service mantrix-backend \
            --force-new-deployment
```

## 🎯 Success Metrics

### Minimal Deployment (Phase 0)
✅ Application runs locally with Docker Compose
✅ All services healthy
✅ Can execute NLP queries
✅ Authentication works

### AWS ECS Deployment (Phase 1)
✅ Application accessible via ALB
✅ Auto-scaling works
✅ Costs < $200/month
✅ Response time < 2 seconds

### Production Ready (Phase 2)
✅ Code protection implemented
✅ 99.9% uptime
✅ Handles 100+ concurrent users
✅ Automated deployments

### Marketplace Ready (Phase 3)
✅ License validation working
✅ Customer can self-deploy
✅ Source code protected
✅ Marketplace listing approved

## 🛟 Troubleshooting

### Common Issues

**1. ECS Tasks Not Starting**
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster mantrix-cluster \
  --tasks $(aws ecs list-tasks --cluster mantrix-cluster --query 'taskArns[0]' --output text)

# Check CloudWatch logs
aws logs tail /ecs/mantrix-backend --follow
```

**2. Database Connection Failed**
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Test connection from ECS task
aws ecs execute-command \
  --cluster mantrix-cluster \
  --task task-id \
  --container backend \
  --interactive \
  --command "/bin/bash"
```

**3. High Costs**
```bash
# Review cost breakdown
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE
```

## 📚 Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Terraform AWS Modules](https://registry.terraform.io/namespaces/terraform-aws-modules)
- [AWS Marketplace Seller Guide](https://docs.aws.amazon.com/marketplace/latest/userguide/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

## 🤝 Support

For deployment issues:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Contact AWS Support (for infrastructure issues)
4. Open a GitHub issue (for application issues)

---

**Next Steps:**
1. Complete local testing with Docker Compose
2. Deploy minimal version to AWS ECS
3. Validate all features work
4. Proceed with code protection
5. Upgrade to production configuration
6. Submit to AWS Marketplace

This phased approach ensures each component works before moving to the next phase, reducing risk and allowing for iterative improvements.