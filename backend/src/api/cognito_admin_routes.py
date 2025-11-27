"""
Cognito Admin Routes for User Management
Provides API endpoints for admin operations on AWS Cognito users.
"""

import boto3
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import structlog

from src.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin/cognito", tags=["cognito-admin"])

# Initialize Cognito client with proper configuration
def get_cognito_client():
    """Get a properly configured Cognito client."""
    # Check if we should use a specific AWS profile
    aws_profile = os.getenv('AWS_PROFILE', None)

    if aws_profile:
        # Use session with profile for local development
        session = boto3.Session(profile_name=aws_profile)
        return session.client(
            'cognito-idp',
            region_name=settings.aws_region
        )
    else:
        # Use default credentials (for ECS/Lambda)
        return boto3.client(
            'cognito-idp',
            region_name=settings.aws_region
        )

try:
    cognito_client = get_cognito_client()
    USER_POOL_ID = settings.cognito_user_pool_id
    logger.info(f"Cognito client initialized for pool: {USER_POOL_ID}")
except Exception as e:
    logger.error(f"Failed to initialize Cognito client: {str(e)}")
    cognito_client = None
    USER_POOL_ID = settings.cognito_user_pool_id


# Pydantic Models
class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    temporaryPassword: str
    firstName: str
    lastName: str
    organizationId: Optional[str] = None
    role: str = "user"


class UserResponse(BaseModel):
    username: str
    email: str
    status: str
    created: datetime
    organizationId: Optional[str] = None
    role: Optional[str] = None


# Dependency for admin authentication (placeholder - implement based on your auth system)
async def require_admin(
    # Add your authentication/authorization logic here
    # For example, check JWT token for admin role
):
    """
    Verify that the requesting user has admin privileges.
    This should validate the JWT token and check for admin role/group.
    """
    # TODO: Implement proper admin authorization
    # For now, this is a placeholder
    pass


@router.get("/users", response_model=dict)
async def list_users(admin=Depends(require_admin)):
    """
    List all users in the Cognito User Pool.
    Requires admin privileges.
    """
    if not cognito_client:
        raise HTTPException(
            status_code=503,
            detail="Cognito service is not available. Check AWS credentials configuration."
        )

    try:
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            Limit=60  # Adjust as needed
        )

        users = []
        for user in response.get('Users', []):
            # Extract attributes
            attributes = {attr['Name']: attr['Value'] for attr in user.get('Attributes', [])}

            users.append({
                'username': user['Username'],
                'email': attributes.get('email', ''),
                'status': user['UserStatus'],
                'created': user['UserCreateDate'].isoformat(),
                'organizationId': attributes.get('custom:organization_id'),
                'role': attributes.get('custom:role'),
            })

        logger.info(f"Listed {len(users)} Cognito users")
        return {"users": users}

    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def create_user(user_data: CreateUserRequest, admin=Depends(require_admin)):
    """
    Create a new user in Cognito User Pool with custom attributes.
    Requires admin privileges.
    """
    try:
        user_attributes = [
            {'Name': 'email', 'Value': user_data.email},
            {'Name': 'email_verified', 'Value': 'true'},
            {'Name': 'given_name', 'Value': user_data.firstName},
            {'Name': 'family_name', 'Value': user_data.lastName},
        ]

        # Add custom attributes if provided
        if user_data.organizationId:
            user_attributes.append({
                'Name': 'custom:organization_id',
                'Value': user_data.organizationId
            })

        user_attributes.append({
            'Name': 'custom:role',
            'Value': user_data.role
        })

        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=user_data.username,
            UserAttributes=user_attributes,
            TemporaryPassword=user_data.temporaryPassword,
            MessageAction='SUPPRESS',  # Don't send email automatically
            DesiredDeliveryMediums=['EMAIL']
        )

        logger.info(f"Created Cognito user: {user_data.username}")

        return {
            "message": "User created successfully",
            "username": user_data.username,
            "status": response['User']['UserStatus']
        }

    except cognito_client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{username}/reset-password")
async def reset_user_password(username: str, admin=Depends(require_admin)):
    """
    Send a password reset email to a user.
    Requires admin privileges.
    """
    try:
        response = cognito_client.admin_reset_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username
        )

        logger.info(f"Password reset initiated for user: {username}")

        return {
            "message": "Password reset email sent successfully",
            "username": username
        }

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Failed to reset password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{username}")
async def delete_user(username: str, admin=Depends(require_admin)):
    """
    Delete a user from the Cognito User Pool.
    Requires admin privileges.
    """
    try:
        cognito_client.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )

        logger.info(f"Deleted Cognito user: {username}")

        return {
            "message": "User deleted successfully",
            "username": username
        }

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{username}")
async def get_user(username: str, admin=Depends(require_admin)):
    """
    Get detailed information about a specific user.
    Requires admin privileges.
    """
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )

        attributes = {attr['Name']: attr['Value'] for attr in response.get('UserAttributes', [])}

        return {
            'username': response['Username'],
            'email': attributes.get('email', ''),
            'status': response['UserStatus'],
            'created': response['UserCreateDate'].isoformat(),
            'organizationId': attributes.get('custom:organization_id'),
            'role': attributes.get('custom:role'),
            'enabled': response['Enabled'],
        }

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{username}/attributes")
async def update_user_attributes(
    username: str,
    organizationId: Optional[str] = None,
    role: Optional[str] = None,
    admin=Depends(require_admin)
):
    """
    Update custom attributes for a user.
    Requires admin privileges.
    """
    try:
        user_attributes = []

        if organizationId is not None:
            user_attributes.append({
                'Name': 'custom:organization_id',
                'Value': organizationId
            })

        if role is not None:
            user_attributes.append({
                'Name': 'custom:role',
                'Value': role
            })

        if not user_attributes:
            raise HTTPException(status_code=400, detail="No attributes to update")

        cognito_client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=username,
            UserAttributes=user_attributes
        )

        logger.info(f"Updated attributes for user: {username}")

        return {
            "message": "User attributes updated successfully",
            "username": username
        }

    except cognito_client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Failed to update user attributes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
