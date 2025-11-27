#!/bin/bash
# Deploy Mantrix AI to AWS using CDK
# This script handles everything: building Docker images, pushing to ECR, and deploying to ECS

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AWS_PROFILE="${AWS_PROFILE:-cloudmantra-admin}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT="${AWS_ACCOUNT:-709141244278}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Mantrix AI CDK Deployment ===${NC}"
echo "Profile: $AWS_PROFILE"
echo "Region:  $AWS_REGION"
echo "Account: $AWS_ACCOUNT"
echo ""

# Change to CDK directory
cd "$SCRIPT_DIR"

# Export environment variables for CDK
export CDK_DEFAULT_ACCOUNT="$AWS_ACCOUNT"
export CDK_DEFAULT_REGION="$AWS_REGION"

# Parse command line arguments
STACK_NAME="Mantrix-dev-Application"
REQUIRE_APPROVAL="never"

while [[ $# -gt 0 ]]; do
    case $1 in
        --stack)
            STACK_NAME="$2"
            shift 2
            ;;
        --approval)
            REQUIRE_APPROVAL="$2"
            shift 2
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: ./deploy_cdk.sh [options]"
            echo ""
            echo "Options:"
            echo "  --stack NAME      Stack to deploy (default: Mantrix-dev-Application)"
            echo "  --profile NAME    AWS profile to use (default: cloudmantra-admin)"
            echo "  --approval MODE   Approval mode: never, broadening, any-change (default: never)"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./deploy_cdk.sh                                    # Deploy application stack"
            echo "  ./deploy_cdk.sh --stack Mantrix-dev-Network        # Deploy network stack only"
            echo "  ./deploy_cdk.sh --approval broadening              # Require approval for IAM changes"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check for AWS credentials
echo -e "${YELLOW}Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
    echo -e "${RED}Error: Unable to authenticate with AWS profile '$AWS_PROFILE'${NC}"
    echo "Please run: aws sso login --profile $AWS_PROFILE"
    exit 1
fi
echo -e "${GREEN}AWS credentials valid${NC}"
echo ""

# Clean CDK output to avoid stale assets
echo -e "${YELLOW}Cleaning CDK output directory...${NC}"
rm -rf cdk.out
echo -e "${GREEN}Done${NC}"
echo ""

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing CDK dependencies...${NC}"
    npm install
fi

# Run CDK deploy
echo -e "${YELLOW}Starting CDK deployment...${NC}"
echo "Stack: $STACK_NAME"
echo ""

npx cdk deploy "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --require-approval "$REQUIRE_APPROVAL"

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Application URL: https://axis-dev.cloudmantra.ai"
echo ""
echo "To check service status:"
echo "  aws ecs describe-services --cluster mantrix-dev --services mantrix-dev-backend mantrix-dev-frontend mantrix-dev-data-services --profile $AWS_PROFILE --region $AWS_REGION --query 'services[*].{Name:serviceName,Running:runningCount,Desired:desiredCount,Status:status}' --output table"
