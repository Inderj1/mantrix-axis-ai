"""Authentication middleware"""
# Using AWS Cognito authentication
from .cognito_auth import get_current_user, require_auth, require_admin, get_optional_user

# Deprecated Clerk auth (use cognito_auth instead)
# from .auth import get_current_user, require_auth, require_admin

__all__ = ["get_current_user", "require_auth", "require_admin", "get_optional_user"]