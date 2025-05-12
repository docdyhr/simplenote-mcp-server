"""Basic tests for Simplenote client interaction."""

from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server import get_simplenote_client
from simplenote_mcp.server.errors import AuthenticationError


def test_simplenote_client_creation(simplenote_env_vars):
    """Test creation of Simplenote client with environment variables."""
    # We need to patch both the Simplenote class and the config
    with (
        patch("simplenote_mcp.server.server.Simplenote") as mock_simplenote,
        patch("simplenote_mcp.server.server.get_config") as mock_get_config,
    ):
        # Configure mock config with valid credentials
        mock_config = MagicMock()
        mock_config.has_credentials = True
        mock_config.simplenote_email = "test@example.com"
        mock_config.simplenote_password = "testpass"
        mock_get_config.return_value = mock_config

        # Setup mock client
        mock_client = MagicMock()
        mock_simplenote.return_value = mock_client

        # Reset client
        import sys

        sys.modules["simplenote_mcp.server.server"].simplenote_client = None

        # Get client
        client = get_simplenote_client()
        assert client == mock_client

        # Verify client was created with credentials from environment
        mock_simplenote.assert_called_once_with("test@example.com", "testpass")


def test_missing_credentials():
    """Test that missing credentials raise an error."""
    # Reset the simplenote_client global variable
    import sys

    sys.modules["simplenote_mcp.server.server"].simplenote_client = None

    # Mock config with missing credentials
    with patch("simplenote_mcp.server.server.get_config") as mock_get_config:
        mock_config = MagicMock()
        mock_config.has_credentials = False
        mock_get_config.return_value = mock_config

        with pytest.raises(AuthenticationError) as excinfo:
            get_simplenote_client()

        assert "SIMPLENOTE_EMAIL" in str(excinfo.value)
        assert "SIMPLENOTE_PASSWORD" in str(excinfo.value)
