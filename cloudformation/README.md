# Mantrix Axis AI - CloudFormation Deployment

## Overview

This CloudFormation template deploys Mantrix Axis AI to your AWS account with a single click. It provisions all required infrastructure including:

- **Compute**: ECS Fargate cluster with backend and frontend services
- **Database**: RDS PostgreSQL for application data
- **Cache**: ElastiCache Redis for caching
- **Networking**: VPC, subnets, security groups, NAT Gateway
- **Load Balancer**: Application Load Balancer with optional HTTPS

## Quick Start

### Prerequisites

Before deploying, you'll need:

1. **Anthropic API Key** - For Claude AI (NLP-to-SQL)
2. **OpenAI API Key** - For embeddings
3. **GCP Service Account JSON** - For BigQuery access (if using BigQuery)

### Deploy via AWS Console

1. Click the "Launch Stack" button below (or use the Quick Create URL)
2. Fill in the required parameters
3. Review and create the stack
4. Wait ~15-20 minutes for deployment

### Deploy via CLI

```bash
aws cloudformation create-stack \
  --stack-name mantrix-prod \
  --template-body file://mantrix-main.yaml \
  --parameters \
    ParameterKey=AnthropicApiKey,ParameterValue=YOUR_KEY \
    ParameterKey=OpenAIApiKey,ParameterValue=YOUR_KEY \
    ParameterKey=GCPCredentialsJson,ParameterValue='{"type":"service_account",...}' \
    ParameterKey=DeploymentSize,ParameterValue=Small \
  --capabilities CAPABILITY_IAM
```

## Deployment Sizes

| Size | Backend | Frontend | RDS | Redis | Est. Monthly Cost |
|------|---------|----------|-----|-------|-------------------|
| **Small** | 0.5 vCPU, 1GB | 0.25 vCPU, 0.5GB | db.t4g.micro | cache.t4g.micro | ~$150 |
| **Medium** | 1 vCPU, 2GB | 0.5 vCPU, 1GB | db.t4g.small | cache.t4g.small | ~$300 |
| **Large** | 2 vCPU, 4GB | 1 vCPU, 2GB | db.t4g.medium | cache.t4g.medium | ~$500 |

## Parameters

### Required

| Parameter | Description |
|-----------|-------------|
| `AnthropicApiKey` | Your Anthropic Claude API key |
| `OpenAIApiKey` | Your OpenAI API key for embeddings |
| `GCPCredentialsJson` | GCP service account JSON (for BigQuery) |

### Optional

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DeploymentSize` | Small | Infrastructure size (Small/Medium/Large) |
| `EnvironmentName` | prod | Environment name (affects resource naming) |
| `CreateNewVpc` | true | Create new VPC or use existing |
| `VpcId` | - | Existing VPC ID (if CreateNewVpc=false) |
| `SubnetIds` | - | Existing subnet IDs (if CreateNewVpc=false) |
| `DomainName` | - | Custom domain for HTTPS |
| `HostedZoneId` | - | Route 53 hosted zone ID |

## Post-Deployment Steps

After the CloudFormation stack completes:

### 1. Push Container Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
docker build -t mantrix-backend -f backend/Dockerfile.aws backend/
docker tag mantrix-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mantrix-prod/backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mantrix-prod/backend:latest

# Build and push frontend
docker build -t mantrix-frontend -f frontend/Dockerfile.aws frontend/ \
  --build-arg VITE_API_URL=http://YOUR_ALB_DNS \
  --build-arg VITE_AWS_COGNITO_USER_POOL_ID=YOUR_POOL_ID \
  --build-arg VITE_AWS_COGNITO_APP_CLIENT_ID=YOUR_CLIENT_ID
docker tag mantrix-frontend:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mantrix-prod/frontend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/mantrix-prod/frontend:latest
```

### 2. Create First Admin User

1. Go to AWS Cognito Console
2. Select the Mantrix user pool
3. Create a new user with admin email
4. Add user to "Admins" group

### 3. Configure BigQuery (Optional)

If using BigQuery as your data warehouse:

1. Create a GCP project
2. Enable BigQuery API
3. Create a service account with BigQuery access
4. Download the JSON key
5. Use the JSON key as `GCPCredentialsJson` parameter

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                         VPC                              │   │
│  │  ┌──────────────┐  ┌──────────────┐                     │   │
│  │  │ Public       │  │ Public       │                     │   │
│  │  │ Subnet 1     │  │ Subnet 2     │                     │   │
│  │  │    ┌────┐    │  │              │                     │   │
│  │  │    │ ALB│    │  │              │                     │   │
│  │  └────┴────┴────┘  └──────────────┘                     │   │
│  │         │                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐                     │   │
│  │  │ Private      │  │ Private      │                     │   │
│  │  │ Subnet 1     │  │ Subnet 2     │                     │   │
│  │  │  ┌────────┐  │  │  ┌────────┐  │                     │   │
│  │  │  │Backend │  │  │  │Frontend│  │                     │   │
│  │  │  │(ECS)   │  │  │  │(ECS)   │  │                     │   │
│  │  │  └────────┘  │  │  └────────┘  │                     │   │
│  │  │  ┌────────┐  │  │  ┌────────┐  │                     │   │
│  │  │  │ RDS    │  │  │  │ Redis  │  │                     │   │
│  │  │  │ Postgres│ │  │  │        │  │                     │   │
│  │  │  └────────┘  │  │  └────────┘  │                     │   │
│  │  └──────────────┘  └──────────────┘                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Stack Creation Failed

1. Check CloudFormation Events tab for error details
2. Common issues:
   - Invalid API keys
   - Insufficient IAM permissions
   - VPC/Subnet conflicts

### Services Not Healthy

1. Check ECS Service events
2. Check CloudWatch logs: `/ecs/mantrix-*/backend`
3. Verify secrets are populated correctly

### Database Connection Issues

1. Verify security group rules
2. Check RDS instance status
3. Verify credentials in Secrets Manager

## Support

For issues and feature requests, please contact support or visit our documentation.

## License

This software is provided under [Your License Terms].
