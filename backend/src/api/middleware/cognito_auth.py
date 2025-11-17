"""
AWS Cognito Authentication Middleware

Validates JWT tokens from AWS Cognito User Pools and manages user authentication.
Supports user and admin roles with organization-level isolation.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from functools import lru_cache
import structlog
from src.config import settings

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)


class CognitoAuth:
    """
    AWS Cognito authentication handler.

    Validates JWT tokens from Cognito User Pool and extracts user information.
    """

    def __init__(self):
        self.region = getattr(settings, 'aws_region', 'us-east-1')
        self.user_pool_id = getattr(settings, 'cognito_user_pool_id', None)
        self.app_client_id = getattr(settings, 'cognito_app_client_id', None)
        self.admin_group_name = getattr(settings, 'cognito_admin_group', 'Admins')

        if not self.user_pool_id or not self.app_client_id:
            logger.warning("Cognito configuration missing - authentication will be disabled")
            self._jwks_client = None
        else:
            # Construct JWKS URL for Cognito
            self.jwks_url = (
                f"https://cognito-idp.{self.region}.amazonaws.com/"
                f"{self.user_pool_id}/.well-known/jwks.json"
            )
            self._jwks_client = PyJWKClient(self.jwks_url)
            logger.info(f"Cognito auth initialized for user pool: {self.user_pool_id}")

    def is_configured(self) -> bool:
        """Check if Cognito is properly configured."""
        return self._jwks_client is not None

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode Cognito JWT token.

        Args:
            token: JWT token from Cognito

        Returns:
            Decoded token payload with user information

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=500,
                detail="Cognito authentication is not configured"
            )

        try:
            # Get the signing key from JWKS
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify the token
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.app_client_id,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True
                }
            )

            # Verify token_use claim
            if decoded.get("token_use") != "access":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type. Expected access token."
                )

            return decoded

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

    def extract_user_info(self, token_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from decoded token.

        Args:
            token_payload: Decoded JWT token payload

        Returns:
            Dictionary with user information:
                - id: User ID (sub claim)
                - username: Username
                - email: Email address (if available)
                - groups: List of Cognito groups
                - role: Derived role (admin or user)
                - organization_id: Organization ID (from custom attributes)
        """
        user_id = token_payload.get("sub")
        username = token_payload.get("username")
        email = token_payload.get("email")

        # Extract Cognito groups
        groups = token_payload.get("cognito:groups", [])

        # Determine role based on groups
        is_admin = self.admin_group_name in groups
        role = "admin" if is_admin else "user"

        # Extract organization ID from custom attributes
        # Cognito custom attributes are prefixed with "custom:"
        organization_id = token_payload.get("custom:organization_id")

        return {
            "id": user_id,
            "username": username,
            "email": email,
            "groups": groups,
            "role": role,
            "is_admin": is_admin,
            "organization_id": organization_id,
            "raw_token": token_payload
        }

    def check_admin(self, user_info: Dict[str, Any]) -> bool:
        """Check if user has admin privileges."""
        return user_info.get("is_admin", False)


# Singleton instance
cognito_auth = CognitoAuth()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Extract and validate current user from JWT token.

    This is a soft authentication check - returns None if no valid token.
    Use require_auth() or require_admin() for protected endpoints.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User information dict or None if not authenticated
    """
    # If Cognito is not configured, allow unauthenticated access
    if not cognito_auth.is_configured():
        logger.debug("Cognito not configured - allowing unauthenticated access")
        return {
            "id": "anonymous",
            "username": "anonymous",
            "email": "anonymous@localhost",
            "role": "user",
            "is_admin": False,
            "organization_id": None
        }

    # If no credentials provided, return None
    if not credentials:
        return None

    try:
        # Verify token
        token_payload = cognito_auth.verify_token(credentials.credentials)

        # Extract user info
        user_info = cognito_auth.extract_user_info(token_payload)

        logger.debug(
            f"Authenticated user: {user_info['username']}",
            user_id=user_info['id'],
            role=user_info['role']
        )

        return user_info

    except HTTPException:
        # Re-raise authentication errors
        raise
    except Exception as e:
        logger.error(f"Error extracting user from token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def require_auth(
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require authentication for endpoint.

    Use this as a dependency to protect endpoints that require any authenticated user.

    Args:
        user: User info from get_current_user dependency

    Returns:
        User information dict

    Raises:
        HTTPException 401: If user is not authenticated

    Example:
        @router.get("/protected")
        async def protected_endpoint(user: Dict = Depends(require_auth)):
            return {"message": f"Hello {user['username']}"}
    """
    if not user or user.get("id") == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_admin(
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require admin role for endpoint.

    Use this as a dependency to protect admin-only endpoints.

    Args:
        user: User info from get_current_user dependency

    Returns:
        User information dict

    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user is not an admin

    Example:
        @router.post("/admin/settings")
        async def admin_endpoint(user: Dict = Depends(require_admin)):
            return {"message": "Admin access granted"}
    """
    if not user or user.get("id") == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not cognito_auth.check_admin(user):
        logger.warning(
            f"User {user.get('username')} attempted admin access",
            user_id=user.get('id')
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, None otherwise.

    This doesn't raise exceptions - useful for endpoints that work with or without auth.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User information dict or None
    """
    if not credentials:
        return None

    try:
        token_payload = cognito_auth.verify_token(credentials.credentials)
        return cognito_auth.extract_user_info(token_payload)
    except Exception:
        # Silently fail for optional auth
        return None
