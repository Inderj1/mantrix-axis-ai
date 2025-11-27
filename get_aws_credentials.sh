#!/bin/bash

# Script to get AWS credentials from SSO and export them for Docker

echo "Getting AWS credentials from SSO profile: cloudmantra-admin"

# Get credentials using aws configure export-credentials (works with SSO)
CREDS=$(aws configure export-credentials --profile cloudmantra-admin --format json 2>/dev/null)

if [ $? -eq 0 ]; then
    export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
    export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
    export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')

    echo "✅ AWS credentials exported successfully"
    echo ""
    echo "Add these to your .env file or export them:"
    echo "export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID"
    echo "export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY"
    echo "export AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN"

    # Optionally update .env file
    if [ -f .env ]; then
        # Remove old AWS credentials
        sed -i '' '/^AWS_ACCESS_KEY_ID=/d' .env
        sed -i '' '/^AWS_SECRET_ACCESS_KEY=/d' .env
        sed -i '' '/^AWS_SESSION_TOKEN=/d' .env

        # Add new credentials
        echo "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" >> .env
        echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" >> .env
        echo "AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN" >> .env

        echo ""
        echo "✅ .env file updated with credentials"
    fi
else
    echo "❌ Failed to get AWS credentials. Please ensure you're logged in:"
    echo "aws sso login --profile cloudmantra-admin"
fi