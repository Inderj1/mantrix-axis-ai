"""
Google OAuth Service for BigQuery Authentication

Handles OAuth 2.0 flow for BigQuery connections:
- Authorization URL generation
- Code-to-token exchange
- Token encryption/decryption
- Token refresh
"""
import secrets
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog

from cryptography.fernet import Fernet, InvalidToken
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from src.config import settings

logger = structlog.get_logger()

# Required OAuth scopes for BigQuery access
BIGQUERY_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/cloud-platform.read-only",
    "openid",
    "email",
]


class GoogleOAuthService:
    """
    Service for managing Google OAuth authentication for BigQuery.

    Provides methods for the complete OAuth flow and secure token management.
    """

    def __init__(self):
        """Initialize the OAuth service with encryption key."""
        self._fernet = None
        if settings.oauth_encryption_key:
            try:
                self._fernet = Fernet(settings.oauth_encryption_key.encode())
            except Exception as e:
                logger.warning(f"Invalid OAuth encryption key, tokens will not be encrypted: {e}")

        # In-memory state storage for CSRF protection
        # In production, use Redis or another persistent store
        self._pending_states: Dict[str, Dict[str, Any]] = {}

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(
            settings.google_oauth_client_id and
            settings.google_oauth_client_secret
        )

    def get_oauth_config(self) -> Dict[str, Any]:
        """Get OAuth configuration status (safe for API response)."""
        return {
            "enabled": self.is_configured(),
            "encryption_enabled": self._fernet is not None,
            "redirect_uri": settings.google_oauth_redirect_uri,
        }

    def generate_authorization_url(
        self,
        organization_id: str,
        user_id: str,
        redirect_uri: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate the Google OAuth authorization URL.

        Args:
            organization_id: The organization initiating the OAuth flow
            user_id: The user initiating the OAuth flow
            redirect_uri: Optional custom redirect URI

        Returns:
            Tuple of (authorization_url, state)

        Raises:
            ValueError: If OAuth is not configured
        """
        if not self.is_configured():
            raise ValueError("Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.")

        # Generate secure state token for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state with metadata
        self._pending_states[state] = {
            "organization_id": organization_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        }

        # Build OAuth client config
        client_config = {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri or settings.google_oauth_redirect_uri]
            }
        }

        # Create OAuth flow
        flow = Flow.from_client_config(
            client_config,
            scopes=BIGQUERY_OAUTH_SCOPES,
            redirect_uri=redirect_uri or settings.google_oauth_redirect_uri
        )

        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type="offline",  # Get refresh token
            include_granted_scopes="true",
            prompt="consent",  # Force consent to get refresh token
            state=state
        )

        logger.info(f"Generated OAuth authorization URL for org={organization_id}, user={user_id}")
        return authorization_url, state

    def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth state token and return associated metadata.

        Args:
            state: The state token to validate

        Returns:
            State metadata if valid, None if invalid or expired
        """
        if state not in self._pending_states:
            logger.warning(f"Invalid OAuth state token")
            return None

        state_data = self._pending_states[state]
        expires_at = datetime.fromisoformat(state_data["expires_at"])

        if datetime.utcnow() > expires_at:
            # Expired state
            del self._pending_states[state]
            logger.warning(f"Expired OAuth state token")
            return None

        # Remove used state (one-time use)
        del self._pending_states[state]
        return state_data

    def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: The authorization code from Google
            redirect_uri: The redirect URI used in the authorization request

        Returns:
            Dictionary with token information

        Raises:
            ValueError: If exchange fails
        """
        if not self.is_configured():
            raise ValueError("Google OAuth is not configured")

        # Build OAuth client config
        client_config = {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri or settings.google_oauth_redirect_uri]
            }
        }

        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                client_config,
                scopes=BIGQUERY_OAUTH_SCOPES,
                redirect_uri=redirect_uri or settings.google_oauth_redirect_uri
            )

            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Extract token info
            token_info = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "scopes": list(credentials.scopes) if credentials.scopes else BIGQUERY_OAUTH_SCOPES,
            }

            # Get user email from ID token if available
            if hasattr(credentials, 'id_token') and credentials.id_token:
                # ID token contains user info
                token_info["id_token"] = credentials.id_token

            logger.info("Successfully exchanged OAuth code for tokens")
            return token_info

        except Exception as e:
            logger.error(f"Failed to exchange OAuth code: {e}")
            raise ValueError(f"Failed to exchange authorization code: {e}")

    def encrypt_tokens(self, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive token fields for storage.

        Args:
            token_info: Dictionary with token information

        Returns:
            Dictionary with encrypted sensitive fields
        """
        if not self._fernet:
            logger.warning("Token encryption not available, storing tokens in plaintext")
            return token_info

        encrypted = token_info.copy()
        sensitive_fields = ["access_token", "refresh_token", "client_secret"]

        for field in sensitive_fields:
            if field in encrypted and encrypted[field]:
                encrypted[field] = self._fernet.encrypt(
                    encrypted[field].encode()
                ).decode()

        encrypted["_encrypted"] = True
        return encrypted

    def decrypt_tokens(self, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive token fields.

        Args:
            token_info: Dictionary with encrypted token information

        Returns:
            Dictionary with decrypted sensitive fields
        """
        if not token_info.get("_encrypted"):
            return token_info

        if not self._fernet:
            raise ValueError("Cannot decrypt tokens: encryption key not configured")

        decrypted = token_info.copy()
        sensitive_fields = ["access_token", "refresh_token", "client_secret"]

        try:
            for field in sensitive_fields:
                if field in decrypted and decrypted[field]:
                    decrypted[field] = self._fernet.decrypt(
                        decrypted[field].encode()
                    ).decode()

            decrypted.pop("_encrypted", None)
            return decrypted

        except InvalidToken:
            raise ValueError("Failed to decrypt tokens: invalid encryption key")

    def refresh_access_token(self, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refresh an expired access token using the refresh token.

        Args:
            token_info: Dictionary with token information (may be encrypted)

        Returns:
            Updated dictionary with new access token

        Raises:
            ValueError: If refresh fails
        """
        # Decrypt if needed
        decrypted = self.decrypt_tokens(token_info)

        refresh_token = decrypted.get("refresh_token")
        if not refresh_token:
            raise ValueError("No refresh token available")

        try:
            credentials = Credentials(
                token=decrypted.get("access_token"),
                refresh_token=refresh_token,
                token_uri=decrypted.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=decrypted.get("client_id") or settings.google_oauth_client_id,
                client_secret=decrypted.get("client_secret") or settings.google_oauth_client_secret,
            )

            # Refresh the token
            credentials.refresh(Request())

            # Update token info
            decrypted["access_token"] = credentials.token
            decrypted["expiry"] = credentials.expiry.isoformat() if credentials.expiry else None

            logger.info("Successfully refreshed OAuth access token")

            # Re-encrypt if originally encrypted
            if token_info.get("_encrypted"):
                return self.encrypt_tokens(decrypted)
            return decrypted

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise ValueError(f"Failed to refresh access token: {e}")

    def is_token_expired(self, token_info: Dict[str, Any], buffer_minutes: int = 5) -> bool:
        """
        Check if an access token is expired or will expire soon.

        Args:
            token_info: Dictionary with token information
            buffer_minutes: Minutes before expiry to consider expired

        Returns:
            True if token is expired or will expire within buffer
        """
        expiry = token_info.get("expiry")
        if not expiry:
            return True  # No expiry info, assume expired

        try:
            expiry_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            # Remove timezone info for comparison
            if expiry_dt.tzinfo:
                expiry_dt = expiry_dt.replace(tzinfo=None)
            buffer = timedelta(minutes=buffer_minutes)
            return datetime.utcnow() + buffer >= expiry_dt
        except Exception:
            return True  # Can't parse expiry, assume expired

    def get_valid_credentials(self, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get valid OAuth credentials, refreshing if necessary.

        Args:
            token_info: Dictionary with token information (may be encrypted)

        Returns:
            Dictionary with valid (possibly refreshed) credentials
        """
        if self.is_token_expired(token_info):
            logger.info("Access token expired, refreshing...")
            return self.refresh_access_token(token_info)
        return token_info


# Singleton instance
_oauth_service: Optional[GoogleOAuthService] = None


def get_google_oauth_service() -> GoogleOAuthService:
    """Get the singleton GoogleOAuthService instance."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = GoogleOAuthService()
    return _oauth_service
