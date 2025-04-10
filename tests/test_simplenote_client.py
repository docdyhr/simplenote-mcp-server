"""Basic tests for Simplenote client interaction."""

import pytest
from unittest.mock import patch
from simplenote_mcp.server import get_simplenote_client

def test_simplenote_client_creation(simplenote_env_vars):
    """Test creation of Simplenote client with environment variables."""
    with patch('simplenote_mcp.server.server.Simplenote') as mock_simplenote:
        mock_simplenote.return_value = "test_client"
        client = get_simplenote_client()
        assert client == "test_client"
        # Verify client was created with credentials from environment
        mock_simplenote.assert_called_once()

def test_missing_credentials():
    """Test that missing credentials raise an error."""
    with patch.dict('os.environ', {}, clear=True):
        with patch('simplenote_mcp.server.server.Simplenote'):
            with pytest.raises(ValueError) as excinfo:
                get_simplenote_client()
            assert "SIMPLENOTE_EMAIL" in str(excinfo.value)
            assert "SIMPLENOTE_PASSWORD" in str(excinfo.value)