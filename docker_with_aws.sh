#!/bin/bash

# Script to run docker-compose with AWS SSO credentials

echo "Setting up AWS credentials for Docker..."

# Check if logged in to SSO
if ! aws sts get-caller-identity --profile cloudmantra-admin &>/dev/null; then
    echo "Not logged in to AWS SSO. Logging in..."
    aws sso login --profile cloudmantra-admin
fi

# Export AWS credentials from SSO profile
echo "Exporting AWS credentials from SSO profile..."

# Get the role credentials from SSO cache
AWS_CONFIG_FILE="${HOME}/.aws/config"
AWS_SSO_CACHE_DIR="${HOME}/.aws/sso/cache"

# Find the most recent SSO cache file
SSO_CACHE_FILE=$(ls -t ${AWS_SSO_CACHE_DIR}/*.json 2>/dev/null | head -1)

if [ -z "$SSO_CACHE_FILE" ]; then
    echo "❌ No SSO cache found. Please run: aws sso login --profile cloudmantra-admin"
    exit 1
fi

# Extract access token from cache
ACCESS_TOKEN=$(cat "$SSO_CACHE_FILE" | jq -r '.accessToken' 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" = "null" ]; then
    echo "❌ Invalid SSO session. Please run: aws sso login --profile cloudmantra-admin"
    exit 1
fi

# Get account and role from AWS config
ACCOUNT_ID=$(aws configure get sso_account_id --profile cloudmantra-admin)
ROLE_NAME=$(aws configure get sso_role_name --profile cloudmantra-admin)
REGION=$(aws configure get sso_region --profile cloudmantra-admin)

if [ -z "$ACCOUNT_ID" ] || [ -z "$ROLE_NAME" ]; then
    echo "❌ Could not get account/role info from profile"
    exit 1
fi

# Get role credentials using SSO
CREDS=$(aws sso get-role-credentials \
    --role-name "$ROLE_NAME" \
    --account-id "$ACCOUNT_ID" \
    --access-token "$ACCESS_TOKEN" \
    --region "$REGION" \
    --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "❌ Failed to get role credentials. Token might be expired."
    echo "Please run: aws sso login --profile cloudmantra-admin"
    exit 1
fi

# Extract and export credentials
export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.roleCredentials.accessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.roleCredentials.secretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.roleCredentials.sessionToken')
export AWS_REGION=${AWS_REGION:-us-east-1}

echo "✅ AWS credentials exported successfully"
echo ""
echo "Starting Docker Compose with AWS credentials..."
echo ""

# Run docker-compose with the credentials
docker-compose "$@"