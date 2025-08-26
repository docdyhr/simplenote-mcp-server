"""Authentication and session management for Simplenote MCP Server."""

from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from simplenote import Simplenote

from .config import get_config
from .errors import AuthenticationError, SessionTimeoutError
from .logging import logger


class SessionManager:
    """Manages authentication sessions with timeout capabilities."""

    def __init__(self, default_timeout: int = 3600):
        """Initialize session manager.

        Args:
            default_timeout: Default session timeout in seconds (1 hour default)
        """
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        self._default_timeout = default_timeout

        # Global client instance with session management
        self._client: Simplenote | None = None
        self._client_created_at: datetime | None = None
        self._client_last_used: datetime | None = None
        self._client_timeout = default_timeout

        logger.info(f"SessionManager initialized with {default_timeout}s timeout")

    def create_session(
        self, session_id: str, user_data: dict[str, Any], timeout: int | None = None
    ) -> None:
        """Create a new session.

        Args:
            session_id: Unique session identifier
            user_data: User data to store in session
            timeout: Custom timeout for this session (seconds)
        """
        with self._lock:
            timeout = timeout or self._default_timeout
            expires_at = datetime.now() + timedelta(seconds=timeout)

            self._sessions[session_id] = {
                "user_data": user_data,
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "expires_at": expires_at,
                "timeout": timeout,
                "active": True,
            }

            logger.info(f"Created session {session_id} with {timeout}s timeout")

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data if valid and not expired.

        Args:
            session_id: Session identifier

        Returns:
            Session data if valid, None if expired or not found

        Raises:
            SessionTimeoutError: If session has expired
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"Session {session_id} not found")
                return None

            session = self._sessions[session_id]

            # Check if session is active
            if not session.get("active", False):
                logger.warning(f"Session {session_id} is inactive")
                return None

            now = datetime.now()

            # Check expiration
            if now > session["expires_at"]:
                logger.warning(f"Session {session_id} has expired")
                self._invalidate_session(session_id)
                raise SessionTimeoutError(
                    f"Session {session_id} has expired at {session['expires_at']}"
                )

            # Update last accessed time
            session["last_accessed"] = now

            # Extend session if configured for sliding expiration
            if session.get("sliding_expiration", True):
                session["expires_at"] = now + timedelta(seconds=session["timeout"])

            logger.debug(
                f"Session {session_id} accessed, expires at {session['expires_at']}"
            )
            return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was invalidated, False if not found
        """
        with self._lock:
            return self._invalidate_session(session_id)

    def _invalidate_session(self, session_id: str) -> bool:
        """Internal method to invalidate session (must hold lock)."""
        if session_id in self._sessions:
            self._sessions[session_id]["active"] = False
            logger.info(f"Invalidated session {session_id}")
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            now = datetime.now()
            expired_sessions = []

            for session_id, session in self._sessions.items():
                if now > session["expires_at"] or not session.get("active", False):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._sessions[session_id]

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

            return len(expired_sessions)

    def extend_session(self, session_id: str, additional_time: int = None) -> bool:
        """Extend session expiration time.

        Args:
            session_id: Session identifier
            additional_time: Additional seconds to extend (defaults to original timeout)

        Returns:
            True if extended successfully, False if session not found
        """
        with self._lock:
            if session_id not in self._sessions:
                return False

            session = self._sessions[session_id]
            if not session.get("active", False):
                return False

            extension = additional_time or session["timeout"]
            session["expires_at"] = datetime.now() + timedelta(seconds=extension)

            logger.info(f"Extended session {session_id} by {extension}s")
            return True

    def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """Get session information without updating access time.

        Args:
            session_id: Session identifier

        Returns:
            Session info dict or None if not found
        """
        with self._lock:
            if session_id not in self._sessions:
                return None

            session = self._sessions[session_id].copy()
            session["is_expired"] = datetime.now() > session["expires_at"]
            session["time_remaining"] = (
                session["expires_at"] - datetime.now()
            ).total_seconds()

            return session

    def list_active_sessions(self) -> dict[str, dict[str, Any]]:
        """List all active sessions with their info.

        Returns:
            Dict mapping session IDs to session info
        """
        with self._lock:
            active_sessions = {}
            now = datetime.now()

            for session_id, session in self._sessions.items():
                if session.get("active", False) and now <= session["expires_at"]:
                    info = session.copy()
                    info["time_remaining"] = (
                        session["expires_at"] - now
                    ).total_seconds()
                    active_sessions[session_id] = info

            return active_sessions


class AuthenticationManager:
    """Manages Simplenote authentication with session timeouts."""

    def __init__(self, session_timeout: int = 3600):
        """Initialize authentication manager.

        Args:
            session_timeout: Default session timeout in seconds
        """
        self._session_manager = SessionManager(session_timeout)
        self._client: Simplenote | None = None
        self._client_created_at: datetime | None = None
        self._client_last_used: datetime | None = None
        self._client_lock = RLock()
        self._client_timeout = session_timeout

        logger.info(
            f"AuthenticationManager initialized with {session_timeout}s timeout"
        )

    def get_authenticated_client(self, force_refresh: bool = False) -> Simplenote:
        """Get authenticated Simplenote client with session management.

        Args:
            force_refresh: Force creation of new client

        Returns:
            Authenticated Simplenote client

        Raises:
            AuthenticationError: If authentication fails
            SessionTimeoutError: If session has expired
        """
        with self._client_lock:
            now = datetime.now()

            # Check if we need to create/refresh client
            should_refresh = (
                force_refresh
                or self._client is None
                or self._client_created_at is None
                or (now - self._client_created_at).total_seconds()
                > self._client_timeout
            )

            if should_refresh:
                logger.info("Creating new authenticated Simplenote client")
                self._client = self._create_client()
                self._client_created_at = now

            # Update last used time
            self._client_last_used = now

            return self._client

    def _create_client(self) -> Simplenote:
        """Create new Simplenote client with authentication."""
        try:
            config = get_config()

            # Check for offline mode
            if config.offline_mode:
                logger.info("Creating mock Simplenote client for offline mode")
                from unittest.mock import MagicMock

                mock_client = MagicMock()
                mock_client.get_note_list.return_value = ([], 0)
                mock_client.get_note.return_value = ({}, 0)
                mock_client.add_note.return_value = ({}, 0)
                mock_client.update_note.return_value = ({}, 0)
                mock_client.trash_note.return_value = 0

                return mock_client

            if not config.has_credentials:
                logger.error("Missing Simplenote credentials")
                raise AuthenticationError("Simplenote credentials not configured")

            logger.info(
                f"Authenticating with Simplenote as {config.simplenote_email[:3]}***"
            )

            client = Simplenote(config.simplenote_email, config.simplenote_password)

            # Test authentication with a simple API call
            try:
                notes, status = client.get_note_list()
                if status != 0:
                    raise AuthenticationError(
                        f"Simplenote authentication failed with status {status}"
                    )

                logger.info("Simplenote authentication successful")
                return client

            except Exception as e:
                logger.error(f"Simplenote authentication test failed: {e}")
                raise AuthenticationError(
                    f"Failed to authenticate with Simplenote: {e}"
                )

        except Exception as e:
            logger.error(f"Failed to create Simplenote client: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")

    def invalidate_client(self) -> None:
        """Invalidate current client, forcing re-authentication on next use."""
        with self._client_lock:
            self._client = None
            self._client_created_at = None
            self._client_last_used = None
            logger.info("Simplenote client invalidated")

    def is_client_valid(self) -> bool:
        """Check if current client is valid and not expired."""
        with self._client_lock:
            if self._client is None or self._client_created_at is None:
                return False

            age = (datetime.now() - self._client_created_at).total_seconds()
            return age <= self._client_timeout

    def get_client_info(self) -> dict[str, Any]:
        """Get information about current client session."""
        with self._client_lock:
            if self._client is None:
                return {"authenticated": False}

            now = datetime.now()
            age = (
                (now - self._client_created_at).total_seconds()
                if self._client_created_at
                else 0
            )
            last_used_age = (
                (now - self._client_last_used).total_seconds()
                if self._client_last_used
                else 0
            )
            time_remaining = max(0, self._client_timeout - age)

            return {
                "authenticated": True,
                "created_at": self._client_created_at.isoformat()
                if self._client_created_at
                else None,
                "last_used": self._client_last_used.isoformat()
                if self._client_last_used
                else None,
                "age_seconds": age,
                "last_used_age_seconds": last_used_age,
                "timeout_seconds": self._client_timeout,
                "time_remaining_seconds": time_remaining,
                "is_expired": time_remaining <= 0,
            }

    def extend_session(self, additional_seconds: int = None) -> bool:
        """Extend current client session.

        Args:
            additional_seconds: Additional time to extend (defaults to original timeout)

        Returns:
            True if extended successfully
        """
        with self._client_lock:
            if self._client is None or self._client_created_at is None:
                return False

            extension = additional_seconds or self._client_timeout
            # Effectively extend by updating the creation time
            self._client_created_at = datetime.now() - timedelta(
                seconds=max(0, self._client_timeout - extension)
            )

            logger.info(f"Extended client session by {extension}s")
            return True

    def cleanup_expired(self) -> None:
        """Clean up expired authentication state."""
        with self._client_lock:
            if self._client and self._client_created_at:
                age = (datetime.now() - self._client_created_at).total_seconds()
                if age > self._client_timeout:
                    logger.info("Cleaning up expired authentication session")
                    self.invalidate_client()


# Global authentication manager instance
_auth_manager: AuthenticationManager | None = None


def get_auth_manager() -> AuthenticationManager:
    """Get global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        config = get_config()
        timeout = getattr(config, "session_timeout", 3600)  # 1 hour default
        _auth_manager = AuthenticationManager(timeout)
    return _auth_manager


def get_authenticated_simplenote_client(force_refresh: bool = False) -> Simplenote:
    """Get authenticated Simplenote client with session management.

    This is the main entry point for getting an authenticated client.

    Args:
        force_refresh: Force creation of new client

    Returns:
        Authenticated Simplenote client

    Raises:
        AuthenticationError: If authentication fails
        SessionTimeoutError: If session has expired
    """
    return get_auth_manager().get_authenticated_client(force_refresh)
