"""Tests for the __main__ module."""

import subprocess
import sys


class TestMainModule:
    """Test the __main__ module functionality."""

    def test_help_argument_subprocess(self):
        """Test that --help works when run as subprocess."""
        result = subprocess.run(
            [sys.executable, "-m", "simplenote_mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.returncode == 0
        assert "Simplenote MCP Server" in result.stdout
        assert result.returncode == 0
        assert "Simplenote MCP Server" in result.stdout
        assert "Usage:" in result.stdout

    def test_h_argument_subprocess(self):
        """Test that -h works when run as subprocess."""
        result = subprocess.run(
            [sys.executable, "-m", "simplenote_mcp", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        assert result.returncode == 0
        assert "Simplenote MCP Server" in result.stdout
        assert "Usage:" in result.stdout

    def test_main_imports_correctly(self):
        """Test that the module can be imported without errors."""
        # Test that importing __main__ works
        import simplenote_mcp.__main__  # noqa: F401
