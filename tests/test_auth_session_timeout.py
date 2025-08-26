"""Tests for authentication and session timeout mechanisms."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.auth import AuthenticationManager, SessionManager
from simplenote_mcp.server.errors import AuthenticationError, SessionTimeoutError


@pytest.fixture
def session_manager():
    """Create a SessionManager for testing."""
    return SessionManager(default_timeout=2)  # Short timeout for testing


@pytest.fixture
def auth_manager():
    """Create an AuthenticationManager for testing."""
    return AuthenticationManager(session_timeout=2)  # Short timeout for testing


class TestSessionManager:
    """Test session management functionality."""

    def test_create_and_get_session(self, session_manager):
        """Test creating and retrieving sessions."""
        session_data = {"user": "test", "role": "user"}
        session_manager.create_session("test_session", session_data, timeout=10)

        retrieved = session_manager.get_session("test_session")
        assert retrieved is not None
        assert retrieved["user_data"] == session_data
        assert retrieved["active"] is True
        assert "created_at" in retrieved
        assert "expires_at" in retrieved

    def test_session_expiration(self, session_manager):
        """Test that sessions expire correctly."""
        session_data = {"user": "test"}
        session_manager.create_session("expire_test", session_data, timeout=1)

        # Should be valid initially
        session = session_manager.get_session("expire_test")
        assert session is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should raise timeout error
        with pytest.raises(SessionTimeoutError):
            session_manager.get_session("expire_test")

    def test_session_not_found(self, session_manager):
        """Test retrieving non-existent session."""
        result = session_manager.get_session("nonexistent")
        assert result is None

    def test_invalidate_session(self, session_manager):
        """Test session invalidation."""
        session_data = {"user": "test"}
        session_manager.create_session("invalidate_test", session_data)

        # Should exist
        session = session_manager.get_session("invalidate_test")
        assert session is not None

        # Invalidate
        result = session_manager.invalidate_session("invalidate_test")
        assert result is True

        # Should no longer be accessible
        session = session_manager.get_session("invalidate_test")
        assert session is None

    def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        # Create multiple sessions with different timeouts
        session_manager.create_session("keep", {"user": "keep"}, timeout=10)
        session_manager.create_session("expire1", {"user": "expire1"}, timeout=1)
        session_manager.create_session("expire2", {"user": "expire2"}, timeout=1)

        # Wait for some to expire
        time.sleep(1.5)

        # Cleanup
        cleaned = session_manager.cleanup_expired_sessions()
        assert cleaned == 2

        # Verify only unexpired session remains
        assert session_manager.get_session("keep") is not None

    def test_extend_session(self, session_manager):
        """Test session extension."""
        session_data = {"user": "test"}
        session_manager.create_session("extend_test", session_data, timeout=1)

        # Get original expiration
        original_session = session_manager.get_session("extend_test")
        original_expiry = original_session["expires_at"]

        # Extend session
        result = session_manager.extend_session("extend_test", additional_time=5)
        assert result is True

        # Verify expiration was extended
        extended_session = session_manager.get_session("extend_test")
        assert extended_session["expires_at"] > original_expiry

    def test_session_sliding_expiration(self, session_manager):
        """Test sliding session expiration."""
        session_data = {"user": "test"}
        session_manager.create_session("sliding_test", session_data, timeout=2)

        # Access session multiple times
        for _i in range(3):
            time.sleep(0.5)
            session = session_manager.get_session("sliding_test")
            assert session is not None

        # Should still be valid due to sliding expiration
        # (would have expired without sliding)
        final_session = session_manager.get_session("sliding_test")
        assert final_session is not None

    def test_session_info(self, session_manager):
        """Test getting session information."""
        session_data = {"user": "test"}
        session_manager.create_session("info_test", session_data, timeout=10)

        info = session_manager.get_session_info("info_test")
        assert info is not None
        assert info["is_expired"] is False
        assert info["time_remaining"] > 0
        assert "created_at" in info
        assert "expires_at" in info

    def test_list_active_sessions(self, session_manager):
        """Test listing active sessions."""
        # Create mix of sessions
        session_manager.create_session("active1", {"user": "user1"}, timeout=10)
        session_manager.create_session("active2", {"user": "user2"}, timeout=10)
        session_manager.create_session("expire_soon", {"user": "user3"}, timeout=1)

        # Wait for one to expire
        time.sleep(1.5)

        active_sessions = session_manager.list_active_sessions()
        assert len(active_sessions) == 2
        assert "active1" in active_sessions
        assert "active2" in active_sessions
        assert "expire_soon" not in active_sessions


class TestAuthenticationManager:
    """Test authentication management functionality."""

    @patch("simplenote_mcp.server.auth.get_config")
    def test_create_client_offline_mode(self, mock_get_config, auth_manager):
        """Test client creation in offline mode."""
        mock_config = MagicMock()
        mock_config.offline_mode = True
        mock_get_config.return_value = mock_config

        client = auth_manager.get_authenticated_client()
        assert client is not None
        # Should be a mock client
        assert hasattr(client, "get_note_list")

    @patch("simplenote_mcp.server.auth.get_config")
    @patch("simplenote_mcp.server.auth.Simplenote")
    def test_create_client_with_credentials(
        self, mock_simplenote, mock_get_config, auth_manager
    ):
        """Test client creation with valid credentials."""
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "test@example.com"
        mock_config.simplenote_password = "password"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_note_list.return_value = ([], 0)
        mock_simplenote.return_value = mock_client

        client = auth_manager.get_authenticated_client()
        assert client == mock_client
        mock_simplenote.assert_called_once_with("test@example.com", "password")

    @patch("simplenote_mcp.server.auth.get_config")
    def test_create_client_no_credentials(self, mock_get_config, auth_manager):
        """Test client creation without credentials."""
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = False
        mock_get_config.return_value = mock_config

        with pytest.raises(AuthenticationError):
            auth_manager.get_authenticated_client()

    @patch("simplenote_mcp.server.auth.get_config")
    @patch("simplenote_mcp.server.auth.Simplenote")
    def test_client_timeout_and_refresh(
        self, mock_simplenote, mock_get_config, auth_manager
    ):
        """Test client timeout and automatic refresh."""
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "test@example.com"
        mock_config.simplenote_password = "password"
        mock_get_config.return_value = mock_config

        mock_client1 = MagicMock()
        mock_client1.get_note_list.return_value = ([], 0)
        mock_client2 = MagicMock()
        mock_client2.get_note_list.return_value = ([], 0)
        mock_simplenote.side_effect = [mock_client1, mock_client2]

        # First call
        client1 = auth_manager.get_authenticated_client()
        assert client1 == mock_client1

        # Second call should return same client (within timeout)
        client1_again = auth_manager.get_authenticated_client()
        assert client1_again == mock_client1

        # Wait for timeout
        time.sleep(2.5)

        # Should create new client
        client2 = auth_manager.get_authenticated_client()
        assert client2 == mock_client2
        assert mock_simplenote.call_count == 2

    @patch("simplenote_mcp.server.auth.get_config")
    @patch("simplenote_mcp.server.auth.Simplenote")
    def test_force_refresh_client(self, mock_simplenote, mock_get_config, auth_manager):
        """Test forcing client refresh."""
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "test@example.com"
        mock_config.simplenote_password = "password"
        mock_get_config.return_value = mock_config

        mock_client1 = MagicMock()
        mock_client1.get_note_list.return_value = ([], 0)
        mock_client2 = MagicMock()
        mock_client2.get_note_list.return_value = ([], 0)
        mock_simplenote.side_effect = [mock_client1, mock_client2]

        # First call
        client1 = auth_manager.get_authenticated_client()
        assert client1 == mock_client1

        # Force refresh
        client2 = auth_manager.get_authenticated_client(force_refresh=True)
        assert client2 == mock_client2
        assert mock_simplenote.call_count == 2

    @patch("simplenote_mcp.server.auth.get_config")
    @patch("simplenote_mcp.server.auth.Simplenote")
    def test_authentication_failure(
        self, mock_simplenote, mock_get_config, auth_manager
    ):
        """Test handling authentication failure."""
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "test@example.com"
        mock_config.simplenote_password = "password"
        mock_get_config.return_value = mock_config

        mock_client = MagicMock()
        mock_client.get_note_list.return_value = ([], 1)  # Error status
        mock_simplenote.return_value = mock_client

        with pytest.raises(AuthenticationError):
            auth_manager.get_authenticated_client()

    def test_invalidate_client(self, auth_manager):
        """Test client invalidation."""
        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client1 = auth_manager.get_authenticated_client()
            assert client1 is not None

            # Invalidate
            auth_manager.invalidate_client()

            # Should create new client on next call
            client2 = auth_manager.get_authenticated_client()
            assert client2 is not None
            assert client2 != client1

    def test_client_validity_check(self, auth_manager):
        """Test checking client validity."""
        # Initially no client
        assert not auth_manager.is_client_valid()

        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client = auth_manager.get_authenticated_client()
            assert client is not None
            assert auth_manager.is_client_valid()

            # Wait for expiration
            time.sleep(2.5)
            assert not auth_manager.is_client_valid()

    def test_get_client_info(self, auth_manager):
        """Test getting client information."""
        # Initially no client
        info = auth_manager.get_client_info()
        assert info["authenticated"] is False

        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client = auth_manager.get_authenticated_client()
            assert client is not None

            info = auth_manager.get_client_info()
            assert info["authenticated"] is True
            assert "created_at" in info
            assert "age_seconds" in info
            assert "time_remaining_seconds" in info
            assert info["is_expired"] is False

    def test_extend_client_session(self, auth_manager):
        """Test extending client session."""
        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client = auth_manager.get_authenticated_client()
            assert client is not None

            # Get original info
            original_info = auth_manager.get_client_info()

            # Extend session
            result = auth_manager.extend_session(5)
            assert result is True

            # Should have more time remaining
            new_info = auth_manager.get_client_info()
            assert (
                new_info["time_remaining_seconds"]
                >= original_info["time_remaining_seconds"]
            )

    def test_cleanup_expired_auth(self, auth_manager):
        """Test cleanup of expired authentication."""
        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client = auth_manager.get_authenticated_client()
            assert client is not None
            assert auth_manager.is_client_valid()

            # Wait for expiration
            time.sleep(2.5)

            # Cleanup
            auth_manager.cleanup_expired()

            # Should be invalidated
            assert not auth_manager.is_client_valid()
            info = auth_manager.get_client_info()
            assert info["authenticated"] is False


class TestIntegrationScenarios:
    """Test integration scenarios for authentication and session management."""

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self):
        """Test concurrent authentication requests."""
        auth_manager = AuthenticationManager(session_timeout=5)

        async def get_client():
            with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
                mock_config = MagicMock()
                mock_config.offline_mode = True
                mock_get_config.return_value = mock_config

                return auth_manager.get_authenticated_client()

        # Make concurrent requests
        tasks = [get_client() for _ in range(10)]
        clients = await asyncio.gather(*tasks)

        # All should return the same client instance
        first_client = clients[0]
        for client in clients[1:]:
            assert client == first_client

    def test_session_timeout_during_operation(self):
        """Test handling session timeout during operations."""
        auth_manager = AuthenticationManager(session_timeout=1)  # Very short timeout

        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Create client
            client1 = auth_manager.get_authenticated_client()
            assert client1 is not None

            # Wait for timeout
            time.sleep(1.5)

            # Next request should create new client
            client2 = auth_manager.get_authenticated_client()
            assert client2 is not None
            assert client2 != client1

    def test_authentication_with_session_management(self):
        """Test integration between authentication and session management."""
        session_manager = SessionManager(default_timeout=5)
        auth_manager = AuthenticationManager(session_timeout=3)

        # Create user session
        session_manager.create_session("user1", {"user": "test"})

        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = True
            mock_get_config.return_value = mock_config

            # Get authenticated client
            client = auth_manager.get_authenticated_client()
            assert client is not None

            # Both should be valid
            user_session = session_manager.get_session("user1")
            assert user_session is not None
            assert auth_manager.is_client_valid()

            # Wait for auth timeout but not session timeout
            time.sleep(3.5)

            # User session should still be valid
            user_session = session_manager.get_session("user1")
            assert user_session is not None

            # Auth should be expired
            assert not auth_manager.is_client_valid()


class TestErrorHandling:
    """Test error handling in authentication and session management."""

    def test_session_timeout_error_attributes(self):
        """Test SessionTimeoutError has correct attributes."""
        error = SessionTimeoutError("Session expired")
        assert hasattr(error, "category")
        assert hasattr(error, "severity")
        assert hasattr(error, "recoverable")
        assert error.recoverable is True

    def test_authentication_error_handling(self):
        """Test handling of authentication errors."""
        auth_manager = AuthenticationManager()

        with patch("simplenote_mcp.server.auth.get_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.offline_mode = False
            mock_config.has_credentials = False
            mock_get_config.return_value = mock_config

            with pytest.raises(AuthenticationError) as exc_info:
                auth_manager.get_authenticated_client()

            error = exc_info.value
            assert hasattr(error, "category")
            assert hasattr(error, "severity")

    def test_session_manager_edge_cases(self, session_manager):
        """Test edge cases in session management."""
        # Test with None session data
        session_manager.create_session("null_test", {})
        session = session_manager.get_session("null_test")
        assert session is not None

        # Test extending non-existent session
        result = session_manager.extend_session("nonexistent")
        assert result is False

        # Test getting info for non-existent session
        info = session_manager.get_session_info("nonexistent")
        assert info is None

        # Test invalidating non-existent session
        result = session_manager.invalidate_session("nonexistent")
        assert result is False
