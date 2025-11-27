#!/bin/bash

# Cognito User Pool Configuration
USER_POOL_ID="us-east-1_eMtGDVbAm"
REGION="us-east-1"
AWS_PROFILE="cloudmantra-admin"

echo "Creating Cognito Groups for Mantrix Axis AI"
echo "============================================"
echo "User Pool ID: $USER_POOL_ID"
echo "Region: $REGION"
echo "AWS Profile: $AWS_PROFILE"
echo ""

# Check if AWS SSO session is active
echo "Checking AWS SSO session..."
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
    echo "⚠️  AWS SSO session not active. Logging in..."
    aws sso login --profile "$AWS_PROFILE"
    echo ""
fi

echo "Creating groups..."

# Create Admins group
echo -n "Creating 'Admins' group... "
if aws cognito-idp create-group \
    --group-name Admins \
    --user-pool-id "$USER_POOL_ID" \
    --description "Administrator users with full permissions" \
    --region "$REGION" \
    --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "✅ Created"
else
    # Check if group already exists
    if aws cognito-idp get-group \
        --group-name Admins \
        --user-pool-id "$USER_POOL_ID" \
        --region "$REGION" \
        --profile "$AWS_PROFILE" &>/dev/null; then
        echo "✅ Already exists"
    else
        echo "❌ Failed"
    fi
fi

# Create Users group
echo -n "Creating 'Users' group... "
if aws cognito-idp create-group \
    --group-name Users \
    --user-pool-id "$USER_POOL_ID" \
    --description "Regular users with standard permissions" \
    --region "$REGION" \
    --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "✅ Created"
else
    # Check if group already exists
    if aws cognito-idp get-group \
        --group-name Users \
        --user-pool-id "$USER_POOL_ID" \
        --region "$REGION" \
        --profile "$AWS_PROFILE" &>/dev/null; then
        echo "✅ Already exists"
    else
        echo "❌ Failed"
    fi
fi

echo ""
echo "Listing all groups in the User Pool:"
echo "====================================="
aws cognito-idp list-groups \
    --user-pool-id "$USER_POOL_ID" \
    --region "$REGION" \
    --profile "$AWS_PROFILE" \
    --query 'Groups[*].{GroupName:GroupName,Description:Description}' \
    --output table

echo ""
echo "To add a user to the Admins group, run:"
echo "aws cognito-idp admin-add-user-to-group \\"
echo "    --user-pool-id $USER_POOL_ID \\"
echo "    --username <USERNAME_OR_EMAIL> \\"
echo "    --group-name Admins \\"
echo "    --region $REGION \\"
echo "    --profile $AWS_PROFILE"