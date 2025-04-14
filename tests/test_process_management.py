"""Unit tests for process management functions."""

import signal
import threading
from pathlib import Path
from unittest.mock import patch

from simplenote_mcp.server.server import (
    cleanup_pid_file,
    setup_signal_handlers,
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
            assert test_pid_path.read_text() == "12345"

            # Clean up
            if test_pid_path.exists():
                test_pid_path.unlink()

    def test_write_pid_file_error(self):
        """Test error handling when writing the PID file."""
        with (
            patch("os.getpid", return_value=12345),
            patch(
                "pathlib.Path.write_text",
                side_effect=PermissionError("Permission denied"),
            ),
            patch("simplenote_mcp.server.server.logger") as mock_logger,
        ):
            # Should not raise exception
            write_pid_file()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error writing PID file" in mock_logger.error.call_args[0][0]

    def test_cleanup_pid_file(self):
        """Test cleaning up the PID file."""
        # Create a temporary PID file
        test_pid_path = Path("/tmp/test_server.pid")
        test_alt_pid_path = Path("/tmp/test_server_alt.pid")
        test_pid_path.write_text("12345")
        test_alt_pid_path.write_text("12345")

        with (
            patch("simplenote_mcp.server.server.PID_FILE_PATH", test_pid_path),
            patch("simplenote_mcp.server.server.ALT_PID_FILE_PATH", test_alt_pid_path),
        ):
            cleanup_pid_file()

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
            # Should not raise an exception
            cleanup_pid_file()

    def test_cleanup_pid_file_error(self):
        """Test error handling when cleaning up the PID file."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.unlink", side_effect=PermissionError("Permission denied")
            ),
            patch("simplenote_mcp.server.server.logger") as mock_logger,
        ):
            # Should not raise exception
            cleanup_pid_file()

            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error removing PID file" in mock_logger.error.call_args[0][0]

    def test_setup_signal_handlers(self):
        """Test setting up signal handlers."""
        with (
            patch("signal.signal") as mock_signal,
            patch("atexit.register") as mock_register,
        ):
            setup_signal_handlers()

            # Verify signal handlers were set up for SIGINT and SIGTERM
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, mock_signal.call_args[0][1])
            mock_signal.assert_any_call(signal.SIGTERM, mock_signal.call_args[0][1])

            # Verify atexit handler was registered
            mock_register.assert_called_once_with(cleanup_pid_file)

    def test_signal_handler(self):
        """Test the signal handler function."""
        # Create proper thread mock objects
        worker_thread_mock = type("MockThread", (), {"name": "worker_thread"})()
        main_thread_mock = type("MockThread", (), {"name": "main_thread"})()

        # Set up all patches
        with (
            patch("signal.signal") as mock_signal,
            patch("atexit.register"),
            patch("threading.current_thread"),
            patch("threading.main_thread"),
            patch("sys.exit") as mock_exit,
            patch("simplenote_mcp.server.server.shutdown_requested", False),
            patch("simplenote_mcp.server.server.logger.info"),  # Prevent actual logging
        ):
            # Call setup_signal_handlers to capture the handler function
            setup_signal_handlers()
            signal_handler = mock_signal.call_args[0][1]

            # Test 1: Signal in non-main thread should exit immediately
            threading.current_thread.return_value = worker_thread_mock
            threading.main_thread.return_value = main_thread_mock
            signal_handler(signal.SIGTERM, None)
            # Verify sys.exit was called when in non-main thread
            mock_exit.assert_called_once_with(0)

            # Reset mocks
            mock_exit.reset_mock()

            # Test 2: Signal in main thread should set flag but not exit
            threading.current_thread.return_value = main_thread_mock
            threading.main_thread.return_value = main_thread_mock
            with patch("simplenote_mcp.server.server.shutdown_requested", False):
                signal_handler(signal.SIGTERM, None)
                # Verify sys.exit was NOT called when in main thread
                mock_exit.assert_not_called()
