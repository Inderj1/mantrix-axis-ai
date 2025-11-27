# AWS Cognito Authentication Setup

This document provides step-by-step instructions for setting up AWS Cognito authentication for the Mantrix Axis AI backend.

## Overview

The backend uses AWS Cognito User Pools for authentication, providing:
- JWT token validation
- User and admin role management
- Organization-level user isolation
- Integration with database permissions system

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Backend deployed to ECS or ready for deployment

## Step 1: Create Cognito User Pool

### Using AWS Console

1. **Navigate to Cognito**
   - Open AWS Console
   - Go to Amazon Cognito service
   - Click "Create user pool"

2. **Configure Sign-in Experience**
   - Sign-in options: Select "Email" and/or "Username"
   - Cognito user pool sign-in options: Email
   - Click "Next"

3. **Configure Security Requirements**
   - Password policy: Choose your requirements (recommend: At least 8 characters, require uppercase, lowercase, numbers, special characters)
   - Multi-factor authentication: Optional (recommended for production)
   - User account recovery: Email only
   - Click "Next"

4. **Configure Sign-up Experience**
   - Self-registration: Allow users to sign themselves up (or disable for invite-only)
   - Attribute verification: Email
   - Required attributes: email, name
   - Custom attributes:
     - Add custom attribute: `organization_id` (String, mutable)
   - Click "Next"

5. **Configure Message Delivery**
   - Email provider: Cognito default (or configure SES for production)
   - Click "Next"

6. **Integrate Your App**
   - User pool name: `mantrix-axis-ai-users`
   - App type: Public client
   - App client name: `mantrix-backend-client`
   - Authentication flows:
     - ☑ ALLOW_USER_PASSWORD_AUTH
     - ☑ ALLOW_REFRESH_TOKEN_AUTH
   - Click "Next"

7. **Review and Create**
   - Review settings
   - Click "Create user pool"

### Using AWS CLI

```bash
# Create user pool
aws cognito-idp create-user-pool \
  --pool-name mantrix-axis-ai-users \
  --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=true}" \
  --auto-verified-attributes email \
  --username-attributes email \
  --schema Name=email,Required=true Name=name,Required=true Name=organization_id,AttributeDataType=String,Mutable=true \
  --region us-east-1

# Note the UserPoolId from the output

# Create app client
aws cognito-idp create-user-pool-client \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --client-name mantrix-backend-client \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --region us-east-1

# Note the ClientId from the output
```

## Step 2: Create Cognito Groups

Create groups for role-based access control:

### Using AWS Console

1. Navigate to your user pool
2. Go to "Groups" tab
3. Create groups:
   - **Admins**: Admin users who can manage permissions
   - **Users**: Regular users

### Using AWS CLI

```bash
# Create Admins group
aws cognito-idp create-group \
  --group-name Admins \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --description "Administrator users with full permissions" \
  --region us-east-1

# Create Users group
aws cognito-idp create-group \
  --group-name Users \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --description "Regular users with standard permissions" \
  --region us-east-1
```

## Step 3: Configure Environment Variables

Add the following environment variables to your backend configuration:

### For Local Development (.env file)

```bash
# AWS Cognito Configuration
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
COGNITO_ADMIN_GROUP=Admins
```

### For ECS Deployment (Task Definition)

```json
{
  "environment": [
    {
      "name": "AWS_REGION",
      "value": "us-east-1"
    },
    {
      "name": "COGNITO_USER_POOL_ID",
      "value": "us-east-1_XXXXXXXXX"
    },
    {
      "name": "COGNITO_APP_CLIENT_ID",
      "value": "XXXXXXXXXXXXXXXXXXXXXXXXXX"
    },
    {
      "name": "COGNITO_ADMIN_GROUP",
      "value": "Admins"
    }
  ]
}
```

### Using AWS Secrets Manager (Recommended for Production)

```bash
# Store Cognito configuration in Secrets Manager
aws secretsmanager create-secret \
  --name mantrix/cognito/config \
  --secret-string '{"user_pool_id":"us-east-1_XXXXXXXXX","app_client_id":"XXXXXXXXXXXXXXXXXXXXXXXXXX","admin_group":"Admins"}' \
  --region us-east-1

# Reference in ECS task definition
{
  "secrets": [
    {
      "name": "COGNITO_USER_POOL_ID",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:mantrix/cognito/config:user_pool_id::"
    },
    {
      "name": "COGNITO_APP_CLIENT_ID",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:mantrix/cognito/config:app_client_id::"
    }
  ]
}
```

## Step 4: Create Test Users

### Using AWS Console

1. Navigate to your user pool
2. Go to "Users" tab
3. Click "Create user"
4. Fill in user details:
   - Email
   - Temporary password
   - Mark email as verified
5. After creation, add user to a group:
   - Select the user
   - Click "Add user to group"
   - Select "Admins" or "Users"

### Using AWS CLI

```bash
# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true Name=custom:organization_id,Value=org_001 \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS \
  --region us-east-1

# Add user to Admins group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username admin@example.com \
  --group-name Admins \
  --region us-east-1

# Create regular user
aws cognito-idp admin-create-user \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true Name=custom:organization_id,Value=org_001 \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS \
  --region us-east-1

# Add user to Users group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id <YOUR_USER_POOL_ID> \
  --username user@example.com \
  --group-name Users \
  --region us-east-1
```

## Step 5: Install Required Python Packages

The backend requires the following packages for Cognito authentication:

```bash
pip install PyJWT python-jose[cryptography]
```

Add to `requirements.txt`:
```
PyJWT>=2.8.0
python-jose[cryptography]>=3.3.0
```

## Step 6: Test Authentication

### 1. Get Access Token

```bash
# Use AWS CLI to get tokens
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <YOUR_APP_CLIENT_ID> \
  --auth-parameters USERNAME=admin@example.com,PASSWORD=<PASSWORD> \
  --region us-east-1
```

Or use a test script:

```python
import boto3

client = boto3.client('cognito-idp', region_name='us-east-1')

response = client.initiate_auth(
    ClientId='<YOUR_APP_CLIENT_ID>',
    AuthFlow='USER_PASSWORD_AUTH',
    AuthParameters={
        'USERNAME': 'admin@example.com',
        'PASSWORD': '<PASSWORD>'
    }
)

access_token = response['AuthenticationResult']['AccessToken']
print(f"Access Token: {access_token}")
```

### 2. Test API with Token

```bash
# Test protected endpoint
curl -X GET \
  http://localhost:8000/api/v1/permissions/databases/available \
  -H "Authorization: Bearer <ACCESS_TOKEN>"

# Test admin endpoint (grant permission)
curl -X POST \
  http://localhost:8000/api/v1/permissions/grant \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_12345",
    "permission": {
      "database_type": "bigquery",
      "access_level": "read"
    }
  }'
```

## Step 7: Frontend Integration

### React/Next.js with AWS Amplify

```bash
npm install aws-amplify @aws-amplify/ui-react
```

```javascript
// Configure Amplify
import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.REACT_APP_COGNITO_APP_CLIENT_ID,
      region: 'us-east-1'
    }
  }
});

// Use in components
import { withAuthenticator } from '@aws-amplify/ui-react';
import { fetchAuthSession } from 'aws-amplify/auth';

async function getAccessToken() {
  const session = await fetchAuthSession();
  return session.tokens?.accessToken?.toString();
}

// Make API requests with token
async function fetchData() {
  const token = await getAccessToken();
  const response = await fetch('/api/v1/permissions/databases/available', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
}
```

## Step 8: ECS IAM Permissions

Ensure your ECS task execution role has permissions to read Secrets Manager (if using):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:mantrix/cognito/*"
      ]
    }
  ]
}
```

## Security Best Practices

1. **Use Secrets Manager** for storing Cognito configuration in production
2. **Enable MFA** for admin users
3. **Configure HTTPS only** for API endpoints
4. **Set token expiration** appropriately (default: 1 hour for access token)
5. **Use refresh tokens** for long-lived sessions
6. **Implement rate limiting** on auth endpoints
7. **Enable CloudWatch logging** for Cognito events
8. **Regular security audits** of user permissions

## Troubleshooting

### Token Verification Fails

- **Check region**: Ensure `AWS_REGION` matches your user pool region
- **Verify pool ID**: Confirm `COGNITO_USER_POOL_ID` is correct
- **Check client ID**: Ensure `COGNITO_APP_CLIENT_ID` matches your app client
- **Token expiration**: Access tokens expire after 1 hour by default

### Permission Denied

- **Check user groups**: Ensure user is in the correct Cognito group
- **Verify COGNITO_ADMIN_GROUP**: Confirm the admin group name matches
- **Check logs**: Review backend logs for permission denial reasons

### JWKS Fetch Errors

- **Network connectivity**: Ensure ECS tasks can reach Cognito endpoints
- **VPC configuration**: If using private subnets, configure NAT gateway or VPC endpoints
- **Security groups**: Allow outbound HTTPS (port 443) traffic

## Monitoring

### CloudWatch Metrics

Monitor these Cognito metrics:
- `SignInSuccesses`
- `SignInThrottles`
- `TokenRefreshSuccesses`
- `UserAuthenticationFailures`

### Backend Metrics

Log and monitor:
- Authentication attempts (success/failure)
- Permission checks
- Token verification errors
- API endpoint access patterns

## Cost Optimization

- **MAUs**: Cognito charges based on Monthly Active Users
- **Advanced security**: Additional cost for risk-based authentication
- **SMS MFA**: Charges per SMS sent
- **First 50,000 MAUs**: Free tier

## Support

For issues or questions:
- AWS Cognito Documentation: https://docs.aws.amazon.com/cognito/
- Backend issues: Check `backend/src/api/middleware/cognito_auth.py`
- Permission system: See `backend/src/core/database_permissions.py`
