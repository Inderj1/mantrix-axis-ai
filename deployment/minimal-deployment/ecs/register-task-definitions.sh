#!/bin/bash

# Script to register ECS task definitions
# Usage: ./register-task-definitions.sh ACCOUNT_ID REGION

set -e

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 ACCOUNT_ID REGION"
    echo "Example: $0 123456789012 us-east-1"
    exit 1
fi

ACCOUNT_ID=$1
REGION=$2

echo "Registering ECS Task Definitions"
echo "================================"
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Function to replace placeholders in JSON
prepare_task_definition() {
    local file=$1
    local temp_file="${file}.tmp"

    sed "s/ACCOUNT_ID/$ACCOUNT_ID/g; s/REGION/$REGION/g" "$file" > "$temp_file"
    echo "$temp_file"
}

# Register backend task definition
echo "Registering backend task definition..."
BACKEND_TEMP=$(prepare_task_definition "task-definition-backend.json")
aws ecs register-task-definition \
    --cli-input-json file://"$BACKEND_TEMP" \
    --region "$REGION" \
    --output table
rm "$BACKEND_TEMP"
echo "✓ Backend task definition registered"
echo ""

# Register frontend task definition
echo "Registering frontend task definition..."
FRONTEND_TEMP=$(prepare_task_definition "task-definition-frontend.json")
aws ecs register-task-definition \
    --cli-input-json file://"$FRONTEND_TEMP" \
    --region "$REGION" \
    --output table
rm "$FRONTEND_TEMP"
echo "✓ Frontend task definition registered"
echo ""

# List registered task definitions
echo "Registered task definitions:"
aws ecs list-task-definitions \
    --family-prefix mantrix \
    --region "$REGION" \
    --output table

echo ""
echo "Task definitions registered successfully!"
echo ""
echo "Next steps:"
echo "1. Create ECS cluster: aws ecs create-cluster --cluster-name mantrix-cluster"
echo "2. Create ECS services using these task definitions"
echo "3. Configure Application Load Balancer"
echo "4. Set up auto-scaling policies"