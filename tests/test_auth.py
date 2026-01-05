"""Tests for authentication and session management."""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.auth import (
    AuthenticationManager,
    SessionManager,
    get_auth_manager,
    get_authenticated_simplenote_client,
)
from simplenote_mcp.server.errors import AuthenticationError, SessionTimeoutError


class TestSessionManager:
    """Tests for SessionManager class."""

    def test_init(self):
        """Test SessionManager initialization."""
        manager = SessionManager(default_timeout=1800)
        assert manager._default_timeout == 1800
        assert manager._sessions == {}

    def test_init_default_timeout(self):
        """Test default timeout value."""
        manager = SessionManager()
        assert manager._default_timeout == 3600  # 1 hour default

    def test_create_session(self):
        """Test creating a new session."""
        manager = SessionManager()
        manager.create_session("session1", {"user": "test"})

        assert "session1" in manager._sessions
        session = manager._sessions["session1"]
        assert session["user_data"] == {"user": "test"}
        assert session["active"] is True
        assert "created_at" in session
        assert "expires_at" in session

    def test_create_session_custom_timeout(self):
        """Test creating session with custom timeout."""
        manager = SessionManager(default_timeout=3600)
        manager.create_session("session1", {}, timeout=600)

        session = manager._sessions["session1"]
        assert session["timeout"] == 600

    def test_get_session_valid(self):
        """Test getting a valid session."""
        manager = SessionManager()
        manager.create_session("session1", {"user": "test"})

        session = manager.get_session("session1")

        assert session is not None
        assert session["user_data"] == {"user": "test"}

    def test_get_session_not_found(self):
        """Test getting a non-existent session."""
        manager = SessionManager()

        result = manager.get_session("nonexistent")

        assert result is None

    def test_get_session_inactive(self):
        """Test getting an inactive session."""
        manager = SessionManager()
        manager.create_session("session1", {})
        manager._sessions["session1"]["active"] = False

        result = manager.get_session("session1")

        assert result is None

    def test_get_session_expired(self):
        """Test getting an expired session raises error."""
        manager = SessionManager()
        manager.create_session("session1", {}, timeout=0)
        # Force expiration
        manager._sessions["session1"]["expires_at"] = datetime.now() - timedelta(
            seconds=1
        )

        with pytest.raises(SessionTimeoutError):
            manager.get_session("session1")

    def test_get_session_updates_last_accessed(self):
        """Test that getting session updates last_accessed."""
        manager = SessionManager()
        manager.create_session("session1", {})
        original_accessed = manager._sessions["session1"]["last_accessed"]

        time.sleep(0.01)
        manager.get_session("session1")

        assert manager._sessions["session1"]["last_accessed"] > original_accessed

    def test_invalidate_session(self):
        """Test invalidating a session."""
        manager = SessionManager()
        manager.create_session("session1", {})

        result = manager.invalidate_session("session1")

        assert result is True
        assert manager._sessions["session1"]["active"] is False

    def test_invalidate_session_not_found(self):
        """Test invalidating non-existent session."""
        manager = SessionManager()

        result = manager.invalidate_session("nonexistent")

        assert result is False

    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        manager = SessionManager()
        manager.create_session("session1", {})
        manager.create_session("session2", {})

        # Expire one session
        manager._sessions["session1"]["expires_at"] = datetime.now() - timedelta(
            seconds=1
        )

        cleaned = manager.cleanup_expired_sessions()

        assert cleaned == 1
        assert "session1" not in manager._sessions
        assert "session2" in manager._sessions

    def test_cleanup_inactive_sessions(self):
        """Test cleanup removes inactive sessions."""
        manager = SessionManager()
        manager.create_session("session1", {})
        manager._sessions["session1"]["active"] = False

        cleaned = manager.cleanup_expired_sessions()

        assert cleaned == 1
        assert "session1" not in manager._sessions

    def test_extend_session(self):
        """Test extending session expiration."""
        manager = SessionManager()
        manager.create_session("session1", {}, timeout=600)
        original_expires = manager._sessions["session1"]["expires_at"]

        result = manager.extend_session("session1", 1200)

        assert result is True
        assert manager._sessions["session1"]["expires_at"] > original_expires

    def test_extend_session_not_found(self):
        """Test extending non-existent session."""
        manager = SessionManager()

        result = manager.extend_session("nonexistent")

        assert result is False

    def test_extend_session_inactive(self):
        """Test extending inactive session fails."""
        manager = SessionManager()
        manager.create_session("session1", {})
        manager._sessions["session1"]["active"] = False

        result = manager.extend_session("session1")

        assert result is False

    def test_get_session_info(self):
        """Test getting session info."""
        manager = SessionManager()
        manager.create_session("session1", {"user": "test"})

        info = manager.get_session_info("session1")

        assert info is not None
        assert "is_expired" in info
        assert "time_remaining" in info
        assert info["is_expired"] is False

    def test_get_session_info_not_found(self):
        """Test getting info for non-existent session."""
        manager = SessionManager()

        info = manager.get_session_info("nonexistent")

        assert info is None

    def test_list_active_sessions(self):
        """Test listing active sessions."""
        manager = SessionManager()
        manager.create_session("session1", {})
        manager.create_session("session2", {})
        manager._sessions["session2"]["active"] = False

        active = manager.list_active_sessions()

        assert "session1" in active
        assert "session2" not in active
        assert "time_remaining" in active["session1"]


class TestAuthenticationManager:
    """Tests for AuthenticationManager class."""

    def test_init(self):
        """Test AuthenticationManager initialization."""
        manager = AuthenticationManager(session_timeout=1800)
        assert manager._client_timeout == 1800
        assert manager._client is None

    def test_init_default_timeout(self):
        """Test default timeout value."""
        manager = AuthenticationManager()
        assert manager._client_timeout == 3600

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_authenticated_client_offline_mode(self, mock_config):
        """Test getting client in offline mode."""
        mock_config.return_value = MagicMock(
            offline_mode=True,
            has_credentials=False,
        )

        manager = AuthenticationManager()
        client = manager.get_authenticated_client()

        assert client is not None
        # Should be a mock client
        assert hasattr(client, "get_note_list")

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_authenticated_client_no_credentials(self, mock_config):
        """Test getting client without credentials raises error."""
        mock_config.return_value = MagicMock(
            offline_mode=False,
            has_credentials=False,
        )

        manager = AuthenticationManager()

        with pytest.raises(AuthenticationError):
            manager.get_authenticated_client()

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_authenticated_client_reuses_valid_client(self, mock_config):
        """Test that valid client is reused."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()
        client1 = manager.get_authenticated_client()
        client2 = manager.get_authenticated_client()

        assert client1 is client2

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_authenticated_client_force_refresh(self, mock_config):
        """Test force refresh creates new client."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()
        client1 = manager.get_authenticated_client()
        client2 = manager.get_authenticated_client(force_refresh=True)

        assert client1 is not client2

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_authenticated_client_expired(self, mock_config):
        """Test expired client is refreshed."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager(session_timeout=0)
        client1 = manager.get_authenticated_client()

        # Force expiration
        manager._client_created_at = datetime.now() - timedelta(seconds=10)

        client2 = manager.get_authenticated_client()

        assert client1 is not client2

    @patch("simplenote_mcp.server.auth.get_config")
    def test_invalidate_client(self, mock_config):
        """Test invalidating client."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()
        manager.get_authenticated_client()

        manager.invalidate_client()

        assert manager._client is None
        assert manager._client_created_at is None
        assert manager._client_last_used is None

    @patch("simplenote_mcp.server.auth.get_config")
    def test_is_client_valid(self, mock_config):
        """Test checking client validity."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()

        assert manager.is_client_valid() is False

        manager.get_authenticated_client()

        assert manager.is_client_valid() is True

    @patch("simplenote_mcp.server.auth.get_config")
    def test_is_client_valid_expired(self, mock_config):
        """Test expired client is not valid."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager(session_timeout=1)
        manager.get_authenticated_client()

        # Force expiration
        manager._client_created_at = datetime.now() - timedelta(seconds=10)

        assert manager.is_client_valid() is False

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_client_info_not_authenticated(self, mock_config):
        """Test getting client info when not authenticated."""
        manager = AuthenticationManager()

        info = manager.get_client_info()

        assert info == {"authenticated": False}

    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_client_info_authenticated(self, mock_config):
        """Test getting client info when authenticated."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()
        manager.get_authenticated_client()

        info = manager.get_client_info()

        assert info["authenticated"] is True
        assert "created_at" in info
        assert "last_used" in info
        assert "age_seconds" in info
        assert "time_remaining_seconds" in info
        assert "is_expired" in info

    @patch("simplenote_mcp.server.auth.get_config")
    def test_extend_session(self, mock_config):
        """Test extending session."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager()
        manager.get_authenticated_client()

        result = manager.extend_session(7200)

        assert result is True

    @patch("simplenote_mcp.server.auth.get_config")
    def test_extend_session_no_client(self, mock_config):
        """Test extending session when no client exists."""
        manager = AuthenticationManager()

        result = manager.extend_session()

        assert result is False

    @patch("simplenote_mcp.server.auth.get_config")
    def test_cleanup_expired(self, mock_config):
        """Test cleaning up expired authentication."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager(session_timeout=1)
        manager.get_authenticated_client()

        # Force expiration
        manager._client_created_at = datetime.now() - timedelta(seconds=10)

        manager.cleanup_expired()

        assert manager._client is None


class TestModuleFunctions:
    """Tests for module-level functions."""

    @patch("simplenote_mcp.server.auth._auth_manager", None)
    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_auth_manager_creates_instance(self, mock_config):
        """Test get_auth_manager creates new instance."""
        mock_config.return_value = MagicMock(session_timeout=1800)

        manager = get_auth_manager()

        assert isinstance(manager, AuthenticationManager)

    @patch("simplenote_mcp.server.auth._auth_manager", None)
    @patch("simplenote_mcp.server.auth.get_config")
    def test_get_auth_manager_reuses_instance(self, mock_config):
        """Test get_auth_manager reuses existing instance."""
        mock_config.return_value = MagicMock(session_timeout=1800)

        manager1 = get_auth_manager()
        manager2 = get_auth_manager()

        assert manager1 is manager2

    @patch("simplenote_mcp.server.auth.get_auth_manager")
    def test_get_authenticated_simplenote_client(self, mock_get_manager):
        """Test get_authenticated_simplenote_client function."""
        mock_manager = MagicMock()
        mock_client = MagicMock()
        mock_manager.get_authenticated_client.return_value = mock_client
        mock_get_manager.return_value = mock_manager

        client = get_authenticated_simplenote_client()

        assert client is mock_client
        mock_manager.get_authenticated_client.assert_called_once_with(False)

    @patch("simplenote_mcp.server.auth.get_auth_manager")
    def test_get_authenticated_simplenote_client_force_refresh(self, mock_get_manager):
        """Test get_authenticated_simplenote_client with force_refresh."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager

        get_authenticated_simplenote_client(force_refresh=True)

        mock_manager.get_authenticated_client.assert_called_once_with(True)


class TestSessionManagerThreadSafety:
    """Tests for thread safety in SessionManager."""

    def test_concurrent_session_creation(self):
        """Test concurrent session creation is thread-safe."""
        import threading

        manager = SessionManager()
        errors = []

        def create_session(session_id):
            try:
                manager.create_session(session_id, {"id": session_id})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_session, args=(f"session{i}",))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(manager._sessions) == 10

    def test_concurrent_session_access(self):
        """Test concurrent session access is thread-safe."""
        import threading

        manager = SessionManager()
        manager.create_session("shared_session", {"counter": 0})

        errors = []

        def access_session():
            try:
                for _ in range(100):
                    manager.get_session("shared_session")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_session) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestAuthenticationManagerEdgeCases:
    """Edge case tests for AuthenticationManager."""

    @patch("simplenote_mcp.server.auth.get_config")
    @patch("simplenote_mcp.server.auth.Simplenote")
    def test_authentication_failure_propagates(self, mock_simplenote, mock_config):
        """Test authentication failures are properly propagated."""
        mock_config.return_value = MagicMock(
            offline_mode=False,
            has_credentials=True,
            simplenote_email="test@test.com",
            simplenote_password="password",
        )
        mock_client = MagicMock()
        mock_client.get_note_list.return_value = (None, 1)  # Status 1 = error
        mock_simplenote.return_value = mock_client

        manager = AuthenticationManager()

        with pytest.raises(AuthenticationError):
            manager.get_authenticated_client()

    @patch("simplenote_mcp.server.auth.get_config")
    def test_client_info_expired_shows_zero_remaining(self, mock_config):
        """Test client info shows zero time remaining when expired."""
        mock_config.return_value = MagicMock(offline_mode=True)

        manager = AuthenticationManager(session_timeout=1)
        manager.get_authenticated_client()

        # Force expiration
        manager._client_created_at = datetime.now() - timedelta(seconds=100)

        info = manager.get_client_info()

        assert info["time_remaining_seconds"] == 0
        assert info["is_expired"] is True
