#!/bin/bash

# Mantrix Axis AI - ECS Deployment Script
# This script helps deploy the minimal infrastructure to AWS ECS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create secret in AWS Secrets Manager
create_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3

    if aws secretsmanager describe-secret --secret-id "$secret_name" >/dev/null 2>&1; then
        print_info "Secret $secret_name already exists"
    else
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --description "$description" \
            --secret-string "$secret_value" \
            --output table
        print_success "Created secret: $secret_name"
    fi
}

# Header
echo "================================================"
echo "  Mantrix Axis AI - ECS Deployment"
echo "================================================"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

if ! command_exists terraform; then
    print_error "Terraform is not installed. Please install Terraform first."
    echo "Visit: https://www.terraform.io/downloads"
    exit 1
fi
print_success "Terraform is installed ($(terraform version -json | jq -r '.terraform_version'))"

if ! command_exists aws; then
    print_error "AWS CLI is not installed. Please install AWS CLI first."
    echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi
print_success "AWS CLI is installed"

if ! command_exists jq; then
    print_warning "jq is not installed. Some features may not work properly."
    echo "Install with: brew install jq (Mac) or apt-get install jq (Linux)"
fi

# Check AWS credentials
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    print_error "AWS credentials not configured. Please run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

print_success "AWS Account: $ACCOUNT_ID"
print_success "AWS Region: $REGION"
echo ""

# Check for terraform.tfvars
if [ ! -f terraform.tfvars ]; then
    if [ -f terraform.tfvars.example ]; then
        print_warning "terraform.tfvars not found. Creating from example..."
        cp terraform.tfvars.example terraform.tfvars
        print_info "Please edit terraform.tfvars with your values"
        exit 1
    else
        print_error "terraform.tfvars not found"
        exit 1
    fi
fi

# Menu for deployment options
echo "Select deployment action:"
echo "1) Create secrets in AWS Secrets Manager"
echo "2) Build and push Docker images"
echo "3) Initialize Terraform"
echo "4) Plan infrastructure changes"
echo "5) Apply infrastructure (create resources)"
echo "6) Full deployment (all of the above)"
echo "7) Destroy infrastructure"
echo "8) Exit"
echo ""
read -p "Enter your choice (1-8): " choice

case $choice in
    1)
        # Create secrets
        print_info "Creating secrets in AWS Secrets Manager..."
        echo ""

        # Read secrets from environment or prompt
        if [ -f ../.env ]; then
            source ../.env
        fi

        if [ -z "$ANTHROPIC_API_KEY" ]; then
            read -p "Enter Anthropic API Key: " ANTHROPIC_API_KEY
        fi
        create_secret "mantrix/anthropic-key" "$ANTHROPIC_API_KEY" "Anthropic Claude API Key"

        if [ -z "$OPENAI_API_KEY" ]; then
            read -p "Enter OpenAI API Key: " OPENAI_API_KEY
        fi
        create_secret "mantrix/openai-key" "$OPENAI_API_KEY" "OpenAI API Key"

        if [ -z "$AWS_COGNITO_USER_POOL_ID" ]; then
            read -p "Enter Cognito User Pool ID: " AWS_COGNITO_USER_POOL_ID
        fi
        create_secret "mantrix/cognito-pool-id" "$AWS_COGNITO_USER_POOL_ID" "AWS Cognito User Pool ID"

        if [ -z "$AWS_COGNITO_CLIENT_ID" ]; then
            read -p "Enter Cognito Client ID: " AWS_COGNITO_CLIENT_ID
        fi
        create_secret "mantrix/cognito-client-id" "$AWS_COGNITO_CLIENT_ID" "AWS Cognito Client ID"

        if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
            read -p "Enter Google Cloud Project ID: " GOOGLE_CLOUD_PROJECT
        fi
        create_secret "mantrix/gcp-project" "$GOOGLE_CLOUD_PROJECT" "Google Cloud Project ID"

        if [ -z "$BIGQUERY_DATASET" ]; then
            read -p "Enter BigQuery Dataset: " BIGQUERY_DATASET
        fi
        create_secret "mantrix/bigquery-dataset" "$BIGQUERY_DATASET" "BigQuery Dataset Name"

        print_success "All secrets created successfully"
        ;;

    2)
        # Build and push Docker images
        print_info "Building and pushing Docker images to ECR..."
        echo ""

        # Get ECR repository URLs from Terraform output (if already created)
        if terraform output >/dev/null 2>&1; then
            BACKEND_REPO=$(terraform output -raw ecr_backend_repository_url 2>/dev/null || echo "")
            FRONTEND_REPO=$(terraform output -raw ecr_frontend_repository_url 2>/dev/null || echo "")
        fi

        if [ -z "$BACKEND_REPO" ]; then
            print_warning "ECR repositories not found. Run Terraform apply first."
            exit 1
        fi

        # Login to ECR
        print_info "Logging into ECR..."
        aws ecr get-login-password --region $REGION | \
            docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

        # Build and push backend
        print_info "Building backend image..."
        cd ../../..
        docker build -f deployment/minimal-deployment/Dockerfile.backend -t mantrix-backend:latest .
        docker tag mantrix-backend:latest $BACKEND_REPO:latest
        print_info "Pushing backend image..."
        docker push $BACKEND_REPO:latest
        print_success "Backend image pushed successfully"

        # Build and push frontend
        print_info "Building frontend image..."
        docker build -f deployment/minimal-deployment/Dockerfile.frontend -t mantrix-frontend:latest .
        docker tag mantrix-frontend:latest $FRONTEND_REPO:latest
        print_info "Pushing frontend image..."
        docker push $FRONTEND_REPO:latest
        print_success "Frontend image pushed successfully"

        cd deployment/minimal-deployment/terraform
        ;;

    3)
        # Initialize Terraform
        print_info "Initializing Terraform..."
        terraform init
        print_success "Terraform initialized successfully"
        ;;

    4)
        # Plan infrastructure
        print_info "Planning infrastructure changes..."
        terraform plan -out=tfplan
        print_success "Plan created successfully"
        echo ""
        print_info "Review the plan above. Run option 5 to apply changes."
        ;;

    5)
        # Apply infrastructure
        print_warning "This will create AWS resources and incur costs!"
        read -p "Are you sure you want to proceed? (yes/no): " confirm

        if [ "$confirm" = "yes" ]; then
            print_info "Applying infrastructure..."

            if [ -f tfplan ]; then
                terraform apply tfplan
            else
                terraform apply
            fi

            print_success "Infrastructure deployed successfully!"
            echo ""

            # Display outputs
            print_info "Deployment Information:"
            echo "========================"
            echo "ALB URL: http://$(terraform output -raw alb_dns_name)"
            echo "ECS Cluster: $(terraform output -raw ecs_cluster_name)"
            echo ""
            print_info "Note: It may take a few minutes for services to be fully available"
        else
            print_info "Deployment cancelled"
        fi
        ;;

    6)
        # Full deployment
        print_info "Starting full deployment..."

        # Run all steps in sequence
        $0 1  # Create secrets
        $0 3  # Initialize Terraform
        $0 5  # Apply infrastructure
        $0 2  # Build and push images

        print_success "Full deployment completed!"
        ;;

    7)
        # Destroy infrastructure
        print_warning "This will destroy all AWS resources created by Terraform!"
        read -p "Are you sure you want to destroy the infrastructure? Type 'destroy' to confirm: " confirm

        if [ "$confirm" = "destroy" ]; then
            print_info "Destroying infrastructure..."
            terraform destroy
            print_success "Infrastructure destroyed"
        else
            print_info "Destroy cancelled"
        fi
        ;;

    8)
        print_info "Exiting..."
        exit 0
        ;;

    *)
        print_error "Invalid choice. Please select 1-8."
        exit 1
        ;;
esac

echo ""
print_success "Operation completed!"