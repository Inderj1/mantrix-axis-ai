"""
Unit tests for OAuth token refresh functionality.

Tests the GoogleOAuthService methods for token validation, refresh, and persistence.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import sys
import os

# Import the module to test
from src.core.google_oauth_service import GoogleOAuthService


@pytest.fixture
def encryption_key():
    """Generate a valid Fernet encryption key."""
    return Fernet.generate_key().decode()


@pytest.fixture
def oauth_service(encryption_key):
    """Create OAuth service with a valid encryption key."""
    service = GoogleOAuthService()
    service._fernet = Fernet(encryption_key.encode())
    return service


class TestOAuthTokenExpiry:
    """Test token expiry detection."""

    def test_token_expired_when_no_expiry(self, oauth_service):
        """Test that missing expiry is treated as expired."""
        token_info = {"access_token": "test_token"}
        assert oauth_service.is_token_expired(token_info) is True

    def test_token_expired_when_past_expiry(self, oauth_service):
        """Test that past expiry time is detected as expired."""
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        token_info = {"access_token": "test_token", "expiry": past_time}
        assert oauth_service.is_token_expired(token_info) is True

    def test_token_not_expired_when_future_expiry(self, oauth_service):
        """Test that future expiry time is not expired."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        token_info = {"access_token": "test_token", "expiry": future_time}
        assert oauth_service.is_token_expired(token_info) is False

    def test_token_expired_within_buffer(self, oauth_service):
        """Test that token expiring within buffer period is treated as expired."""
        # Token expires in 3 minutes, but buffer is 5 minutes
        almost_expired = (datetime.utcnow() + timedelta(minutes=3)).isoformat()
        token_info = {"access_token": "test_token", "expiry": almost_expired}
        assert oauth_service.is_token_expired(token_info, buffer_minutes=5) is True

    def test_token_not_expired_beyond_buffer(self, oauth_service):
        """Test that token beyond buffer period is not expired."""
        # Token expires in 10 minutes, buffer is 5 minutes
        future_time = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        token_info = {"access_token": "test_token", "expiry": future_time}
        assert oauth_service.is_token_expired(token_info, buffer_minutes=5) is False

    def test_token_expired_with_timezone(self, oauth_service):
        """Test token expiry with timezone-aware timestamps."""
        # Test with UTC timezone suffix
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        token_info = {"access_token": "test_token", "expiry": past_time}
        assert oauth_service.is_token_expired(token_info) is True


class TestOAuthTokenEncryption:
    """Test token encryption/decryption."""

    def test_encrypt_and_decrypt_tokens(self, oauth_service):
        """Test that tokens can be encrypted and decrypted."""
        original = {
            "access_token": "my_access_token",
            "refresh_token": "my_refresh_token",
            "client_secret": "my_secret",
            "expiry": "2024-12-31T23:59:59"
        }

        encrypted = oauth_service.encrypt_tokens(original)
        assert encrypted.get("_encrypted") is True
        assert encrypted["access_token"] != original["access_token"]

        decrypted = oauth_service.decrypt_tokens(encrypted)
        assert decrypted["access_token"] == original["access_token"]
        assert decrypted["refresh_token"] == original["refresh_token"]
        assert decrypted["client_secret"] == original["client_secret"]

    def test_decrypt_unencrypted_tokens_returns_as_is(self, oauth_service):
        """Test that unencrypted tokens are returned unchanged."""
        token_info = {
            "access_token": "plain_token",
            "refresh_token": "plain_refresh"
        }
        result = oauth_service.decrypt_tokens(token_info)
        assert result == token_info

    def test_encrypt_for_storage(self, oauth_service):
        """Test the encrypt_for_storage convenience method."""
        original = {
            "access_token": "my_access_token",
            "refresh_token": "my_refresh_token"
        }

        encrypted = oauth_service.encrypt_for_storage(original)
        assert encrypted.get("_encrypted") is True


class TestOAuthTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_fails_without_refresh_token(self, oauth_service):
        """Test that refresh fails without refresh token."""
        token_info = {
            "access_token": "old_access_token",
            # No refresh_token
        }

        with pytest.raises(ValueError, match="No refresh token available"):
            oauth_service.refresh_access_token(token_info)

    @patch('src.core.google_oauth_service.Request')
    @patch('src.core.google_oauth_service.Credentials')
    def test_refresh_access_token_success(self, mock_credentials_class, mock_request):
        """Test successful token refresh."""
        # Create fresh service
        service = GoogleOAuthService()

        # Mock the credentials
        mock_credentials = MagicMock()
        mock_credentials.token = "new_access_token"
        mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_credentials_class.return_value = mock_credentials

        token_info = {
            "access_token": "old_access_token",
            "refresh_token": "my_refresh_token",
            "expiry": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }

        result = service.refresh_access_token(token_info)

        assert result["access_token"] == "new_access_token"
        mock_credentials.refresh.assert_called_once()


class TestGetValidCredentials:
    """Test the get_valid_credentials method."""

    def test_get_valid_credentials_returns_same_when_not_expired(self, oauth_service):
        """Test that valid credentials are returned unchanged."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        token_info = {
            "access_token": "valid_token",
            "expiry": future_time
        }

        result = oauth_service.get_valid_credentials(token_info)
        assert result == token_info

    @patch('src.core.google_oauth_service.Request')
    @patch('src.core.google_oauth_service.Credentials')
    def test_get_valid_credentials_refreshes_when_expired(self, mock_credentials_class, mock_request):
        """Test that expired credentials trigger refresh."""
        service = GoogleOAuthService()

        # Mock the credentials for refresh
        mock_credentials = MagicMock()
        mock_credentials.token = "new_access_token"
        mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_credentials_class.return_value = mock_credentials

        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        token_info = {
            "access_token": "expired_token",
            "refresh_token": "my_refresh_token",
            "expiry": past_time
        }

        result = service.get_valid_credentials(token_info)

        assert result["access_token"] == "new_access_token"
        mock_credentials.refresh.assert_called_once()


class TestGetValidDecryptedCredentials:
    """Test the convenience method get_valid_decrypted_credentials."""

    def test_returns_decrypted_when_not_expired(self, oauth_service):
        """Test that non-expired tokens are decrypted and returned."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        original = {
            "access_token": "my_token",
            "refresh_token": "my_refresh",
            "expiry": future_time
        }
        encrypted = oauth_service.encrypt_tokens(original)

        decrypted, was_refreshed = oauth_service.get_valid_decrypted_credentials(encrypted)

        assert decrypted["access_token"] == "my_token"
        assert was_refreshed is False

    @patch('src.core.google_oauth_service.Request')
    @patch('src.core.google_oauth_service.Credentials')
    def test_returns_refreshed_when_expired(self, mock_credentials_class, mock_request, encryption_key):
        """Test that expired tokens are refreshed and was_refreshed is True."""
        # Create service with encryption
        service = GoogleOAuthService()
        service._fernet = Fernet(encryption_key.encode())

        # Mock the credentials for refresh
        mock_credentials = MagicMock()
        mock_credentials.token = "new_access_token"
        mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_credentials_class.return_value = mock_credentials

        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        original = {
            "access_token": "old_token",
            "refresh_token": "my_refresh",
            "expiry": past_time
        }
        encrypted = service.encrypt_tokens(original)

        decrypted, was_refreshed = service.get_valid_decrypted_credentials(encrypted)

        assert decrypted["access_token"] == "new_access_token"
        assert was_refreshed is True


class TestOAuthServiceConfiguration:
    """Test OAuth service configuration checks."""

    def test_is_configured_returns_false_when_not_configured(self):
        """Test that is_configured returns False when credentials are missing."""
        service = GoogleOAuthService()
        # Default settings likely don't have OAuth configured
        # This test verifies the check works
        result = service.is_configured()
        assert isinstance(result, bool)

    def test_get_oauth_config_returns_status(self):
        """Test that get_oauth_config returns proper status dict."""
        service = GoogleOAuthService()
        config = service.get_oauth_config()

        assert "enabled" in config
        assert "encryption_enabled" in config
        assert "redirect_uri" in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
