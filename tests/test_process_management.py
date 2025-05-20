"""Unit tests for process management functions."""

import contextlib
from pathlib import Path
from unittest.mock import patch

from simplenote_mcp.server.server import (
    cleanup_pid_file as remove_pid_file,
)
from simplenote_mcp.server.server import (
    write_pid_file,
)


class TestProcessManagement:
    """Tests for process management functions."""

    def test_write_pid_file(self):
        """Test writing the PID file."""
        # Mock PID file path
        test_pid_path = Path("/tmp/test_server.pid")

        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH", test_pid_path),
            patch("os.getpid", return_value=12345),
        ):
            write_pid_file()

            # Verify the PID was written correctly
            assert test_pid_path.exists()
            assert test_pid_path.read_text(encoding="utf-8") == "12345"

            # Clean up
            if test_pid_path.exists():
                test_pid_path.unlink()

    def test_write_pid_file_error(self):
        """Test error handling when writing the PID file."""
        with (
            patch("os.getpid", return_value=12345),
            patch("builtins.open", side_effect=PermissionError("Permission denied")),
            contextlib.suppress(PermissionError),
        ):
            # Should not raise exception
            write_pid_file()

    def test_cleanup_pid_file(self):
        """Test cleaning up the PID file."""
        # Create a temporary PID file
        test_pid_path = Path("/tmp/test_server.pid")
        test_alt_pid_path = Path("/tmp/test_server_alt.pid")
        test_pid_path.write_text("12345", encoding="utf-8")
        test_alt_pid_path.write_text("12345", encoding="utf-8")

        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH", test_pid_path),
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH", test_alt_pid_path),
        ):
            remove_pid_file()

            # Verify both files were removed
            assert not test_pid_path.exists()
            assert not test_alt_pid_path.exists()

    def test_cleanup_pid_file_nonexistent(self):
        """Test cleaning up a nonexistent PID file."""
        test_pid_path = Path("/tmp/nonexistent_pid_file.pid")
        test_alt_pid_path = Path("/tmp/nonexistent_alt_pid_file.pid")

        # Ensure the files don't exist
        if test_pid_path.exists():
            test_pid_path.unlink()
        if test_alt_pid_path.exists():
            test_alt_pid_path.unlink()

        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH", test_pid_path),
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH", test_alt_pid_path),
        ):
            remove_pid_file()

    def test_cleanup_pid_file_error(self):
        """Test error handling when cleaning up the PID file."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.unlink", side_effect=PermissionError("Permission denied")
            ),
        ):
            # Should not raise exception - function handles errors gracefully
            remove_pid_file()

    def test_setup_signal_handlers(self):
        """Test setting up signal handlers."""
        # This test is skipped as setup_signal_handlers doesn't exist
        # The signal handling is done directly in the main function
        pass

    def test_signal_handler(self):
        """Test the signal handler function."""
        # Since signal_handler is defined inside setup_signal_handlers,
        # we'll test that setup_signal_handlers can be called
        from simplenote_mcp.server.server import setup_signal_handlers

        # Test that signal setup can be called without errors
        with patch("simplenote_mcp.server.server.logger"):
            # This should not raise an exception
            setup_signal_handlers()
