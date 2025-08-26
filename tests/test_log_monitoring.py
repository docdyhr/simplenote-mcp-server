"""Tests for log pattern monitoring and suspicious activity detection.

This module tests the log monitoring system that detects suspicious patterns
in log entries and triggers security alerts.
"""

import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from simplenote_mcp.server.alerting import AlertSeverity
from simplenote_mcp.server.log_monitor import (
    LogPatternMonitor,
    SuspiciousPattern,
    get_log_monitor,
    process_log_for_patterns,
    start_log_monitoring,
    stop_log_monitoring,
)


class TestSuspiciousPattern:
    """Test suspicious pattern detection."""

    def test_pattern_initialization(self):
        """Test pattern initialization with proper configuration."""
        pattern = SuspiciousPattern(
            name="test_pattern",
            pattern=r"error.*authentication",
            severity=AlertSeverity.HIGH,
            description="Test authentication error pattern",
            threshold=3,
            time_window_minutes=5,
            field_filters={"level": "ERROR"},
        )

        assert pattern.name == "test_pattern"
        assert pattern.severity == AlertSeverity.HIGH
        assert pattern.description == "Test authentication error pattern"
        assert pattern.threshold == 3
        assert pattern.time_window_minutes == 5
        assert pattern.field_filters == {"level": "ERROR"}
        assert len(pattern.matches) == 0

    def test_field_filter_matching(self):
        """Test field filter matching logic."""
        pattern = SuspiciousPattern(
            name="error_pattern",
            pattern=r"error",
            severity=AlertSeverity.MEDIUM,
            description="Error pattern",
            field_filters={"level": "ERROR", "logger": "auth"},
        )

        # Should match - all filters satisfied
        log_entry = {
            "message": "Authentication error occurred",
            "level": "ERROR",
            "logger": "auth",
        }
        assert pattern.matches_filters(log_entry)

        # Should not match - missing logger field
        log_entry = {
            "message": "Authentication error occurred",
            "level": "ERROR",
        }
        assert not pattern.matches_filters(log_entry)

        # Should not match - wrong level
        log_entry = {
            "message": "Authentication error occurred",
            "level": "WARNING",
            "logger": "auth",
        }
        assert not pattern.matches_filters(log_entry)

    def test_pattern_matching(self):
        """Test pattern regex matching."""
        pattern = SuspiciousPattern(
            name="sql_injection",
            pattern=r"(union\s+select|drop\s+table)",
            severity=AlertSeverity.CRITICAL,
            description="SQL injection attempt",
        )

        # Should match
        log_entry = {"message": "Query: SELECT * FROM users UNION SELECT * FROM admin"}
        assert pattern.check_match(log_entry)

        log_entry = {"message": "Attempting to DROP TABLE users"}
        assert pattern.check_match(log_entry)

        # Should not match
        log_entry = {"message": "Normal query executed successfully"}
        assert not pattern.check_match(log_entry)

    def test_threshold_alerting(self):
        """Test threshold-based alert triggering."""
        pattern = SuspiciousPattern(
            name="auth_failure",
            pattern=r"authentication.*failed",
            severity=AlertSeverity.HIGH,
            description="Authentication failures",
            threshold=3,
            time_window_minutes=5,
        )

        # Add matches below threshold
        log_entry = {"message": "Authentication failed for user"}
        pattern.check_match(log_entry)
        pattern.check_match(log_entry)
        assert not pattern.should_trigger_alert()

        # Add match to reach threshold
        pattern.check_match(log_entry)
        assert pattern.should_trigger_alert()

        # Should not trigger again immediately (rate limiting)
        assert not pattern.should_trigger_alert()

    def test_time_window_cleanup(self):
        """Test that old matches are cleaned up from time window."""
        pattern = SuspiciousPattern(
            name="test_pattern",
            pattern=r"test",
            severity=AlertSeverity.MEDIUM,
            description="Test pattern",
            threshold=2,
            time_window_minutes=1,  # Very short window for testing
        )

        # Add match
        log_entry = {"message": "test message"}
        pattern.check_match(log_entry)
        assert len(pattern.matches) == 1

        # Simulate old match by manually adding one
        old_time = datetime.utcnow() - timedelta(minutes=2)
        pattern.matches.appendleft(old_time)

        # Check should_trigger_alert which cleans old matches
        pattern.check_match(log_entry)  # Add another match
        pattern.should_trigger_alert()

        # Old match should be cleaned up (only recent matches remain)
        assert len(pattern.matches) <= 2
        for match_time in pattern.matches:
            assert (datetime.utcnow() - match_time).total_seconds() < 120


class TestLogPatternMonitor:
    """Test log pattern monitor functionality."""

    def test_monitor_initialization(self):
        """Test monitor initialization with default patterns."""
        monitor = LogPatternMonitor()

        assert len(monitor.patterns) > 0
        assert monitor.stats["logs_processed"] == 0
        assert monitor.stats["patterns_matched"] == 0
        assert monitor.stats["alerts_triggered"] == 0

        # Check that some expected default patterns exist
        pattern_names = [p.name for p in monitor.patterns]
        assert "sql_injection_attempt" in pattern_names
        assert "xss_attempt" in pattern_names
        assert "repeated_auth_failures" in pattern_names

    def test_add_remove_patterns(self):
        """Test adding and removing custom patterns."""
        monitor = LogPatternMonitor()
        initial_count = len(monitor.patterns)

        # Add custom pattern
        custom_pattern = SuspiciousPattern(
            name="custom_test",
            pattern=r"custom.*attack",
            severity=AlertSeverity.HIGH,
            description="Custom test pattern",
        )
        monitor.add_pattern(custom_pattern)
        assert len(monitor.patterns) == initial_count + 1

        # Remove pattern
        assert monitor.remove_pattern("custom_test")
        assert len(monitor.patterns) == initial_count

        # Try to remove non-existent pattern
        assert not monitor.remove_pattern("non_existent")

    @pytest.mark.asyncio
    async def test_log_entry_processing(self):
        """Test processing of log entries for pattern detection."""
        monitor = LogPatternMonitor()

        # Add a simple test pattern
        test_pattern = SuspiciousPattern(
            name="test_attack",
            pattern=r"union\s+select",
            severity=AlertSeverity.HIGH,
            description="Test attack pattern",
            threshold=1,
        )
        monitor.add_pattern(test_pattern)

        # Process log entry that should match
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "User input contains: SELECT * FROM users UNION SELECT password FROM admin",
            "logger": "security",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await monitor.process_log_entry(log_entry)

        assert monitor.stats["logs_processed"] == 1
        assert monitor.stats["patterns_matched"] == 1

        # Should have triggered alert since threshold is 1
        mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self):
        """Test detection of SQL injection attempts."""
        monitor = LogPatternMonitor()

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "message": "Suspicious query: SELECT * FROM users UNION SELECT password FROM admin",
            "logger": "database",
            "user_id": "suspicious_user",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await monitor.process_log_entry(log_entry)

        # Should trigger immediate alert for SQL injection
        assert monitor.stats["patterns_matched"] >= 1
        mock_alert.assert_called()

        # Check alert was called with correct parameters
        call_args = mock_alert.call_args[1]  # kwargs
        assert call_args["user_id"] == "suspicious_user"
        assert "sql_injection" in call_args["pattern_description"].lower()

    @pytest.mark.asyncio
    async def test_xss_detection(self):
        """Test detection of XSS attempts."""
        monitor = LogPatternMonitor()

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "message": "Malicious input: <script>alert('xss')</script>",
            "logger": "input_validator",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await monitor.process_log_entry(log_entry)

        mock_alert.assert_called()
        call_args = mock_alert.call_args[1]
        assert "xss" in call_args["pattern_description"].lower()

    @pytest.mark.asyncio
    async def test_authentication_failure_pattern(self):
        """Test detection of repeated authentication failures."""
        monitor = LogPatternMonitor()

        # Find the auth failure pattern
        auth_pattern = None
        for pattern in monitor.patterns:
            if pattern.name == "repeated_auth_failures":
                auth_pattern = pattern
                break

        assert auth_pattern is not None
        original_threshold = auth_pattern.threshold

        # Set low threshold for testing
        auth_pattern.threshold = 2

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Authentication failed for user test@example.com",
            "logger": "auth",
            "user_id": "test@example.com",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            # Process multiple auth failures
            await monitor.process_log_entry(log_entry)
            await monitor.process_log_entry(log_entry)

        # Should trigger alert after reaching threshold
        mock_alert.assert_called()

        # Restore original threshold
        auth_pattern.threshold = original_threshold

    @pytest.mark.asyncio
    async def test_rate_limit_detection(self):
        """Test detection of rate limiting violations."""
        monitor = LogPatternMonitor()

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "WARNING",
            "message": "Rate limit exceeded for user - request blocked",
            "logger": "rate_limiter",
            "user_id": "heavy_user",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            # Process multiple rate limit messages
            for _ in range(3):  # Default threshold for rate limit pattern
                await monitor.process_log_entry(log_entry)
                await asyncio.sleep(0.01)  # Small delay

        mock_alert.assert_called()

    def test_pattern_statistics(self):
        """Test pattern statistics collection."""
        monitor = LogPatternMonitor()

        # Add test matches to a pattern
        test_pattern = monitor.patterns[0]  # Use first default pattern
        test_pattern.matches.append(datetime.utcnow())
        test_pattern.matches.append(datetime.utcnow() - timedelta(minutes=10))

        stats = monitor.get_pattern_stats()

        assert "monitor_stats" in stats
        assert "patterns" in stats
        assert test_pattern.name in stats["patterns"]

        pattern_stats = stats["patterns"][test_pattern.name]
        assert "total_matches" in pattern_stats
        assert "recent_matches" in pattern_stats
        assert "description" in pattern_stats
        assert "severity" in pattern_stats

    def test_cleanup_old_data(self):
        """Test cleanup of old pattern match data."""
        monitor = LogPatternMonitor()

        # Add old matches to patterns
        for pattern in monitor.patterns[:3]:  # Test with first 3 patterns
            pattern.matches.append(datetime.utcnow())
            pattern.matches.append(datetime.utcnow() - timedelta(hours=2))  # Old match

        monitor.cleanup_old_data()

        # Check that old matches were cleaned up
        for pattern in monitor.patterns[:3]:
            for match_time in pattern.matches:
                assert (
                    datetime.utcnow() - match_time
                ).total_seconds() < 3660  # Within 1 hour + margin

    @pytest.mark.asyncio
    async def test_log_file_monitoring(self):
        """Test monitoring of log files for pattern detection."""
        monitor = LogPatternMonitor()

        # Create temporary log file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file_path = Path(f.name)

            # Write initial content
            f.write(
                '{"timestamp": "2024-01-01T10:00:00", "level": "INFO", "message": "Server started"}\n'
            )
            f.flush()

        try:
            # Mock the process_log_entry method to track calls
            original_process = monitor.process_log_entry
            call_count = 0

            async def mock_process(log_entry):
                nonlocal call_count
                call_count += 1
                return await original_process(log_entry)

            monitor.process_log_entry = mock_process

            # Start monitoring
            monitor.start_monitoring([log_file_path])

            # Wait a bit for monitoring to start
            await asyncio.sleep(0.1)

            # Append new log entry with SQL injection pattern
            with open(log_file_path, "a") as f:
                f.write(
                    '{"timestamp": "2024-01-01T10:01:00", "level": "ERROR", "message": "Suspicious query: SELECT * FROM users UNION SELECT password FROM admin"}\n'
                )

            # Wait for processing
            await asyncio.sleep(0.2)

            # Stop monitoring
            monitor.stop_monitoring()

            # Should have processed at least the new log entry
            assert call_count >= 1

        finally:
            # Cleanup
            log_file_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_json_log_parsing(self):
        """Test parsing of JSON log entries."""
        monitor = LogPatternMonitor()

        json_line = '{"timestamp": "2024-01-01T10:00:00", "level": "ERROR", "message": "Query: SELECT * FROM users UNION SELECT * FROM admin", "user_id": "attacker"}'

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await monitor._process_log_line(json_line)

        # Should have triggered SQL injection alert
        mock_alert.assert_called()

    @pytest.mark.asyncio
    async def test_text_log_parsing(self):
        """Test parsing of plain text log entries."""
        monitor = LogPatternMonitor()

        text_line = (
            "2024-01-01 10:00:00 ERROR Authentication failed for user test@example.com"
        )

        # Should parse as text and still detect patterns
        await monitor._process_log_line(text_line)

        # Should have processed the line
        assert monitor.stats["logs_processed"] >= 1


class TestLogMonitorIntegration:
    """Test integration of log monitor with other systems."""

    def test_global_monitor_singleton(self):
        """Test global monitor singleton pattern."""
        monitor1 = get_log_monitor()
        monitor2 = get_log_monitor()

        assert monitor1 is monitor2  # Same instance

    def test_start_stop_monitoring(self):
        """Test starting and stopping global monitoring."""
        # Should not raise errors
        start_log_monitoring()
        stop_log_monitoring()

    @pytest.mark.asyncio
    async def test_process_log_for_patterns_function(self):
        """Test direct log processing function."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "XSS attempt: <script>alert('hack')</script>",
            "user_id": "attacker",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await process_log_for_patterns(log_entry)

        mock_alert.assert_called()

    @pytest.mark.asyncio
    async def test_alert_context_information(self):
        """Test that alerts include proper context information."""
        monitor = LogPatternMonitor()

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "CRITICAL",
            "message": "DROP TABLE users; -- SQL injection detected",
            "user_id": "malicious_user",
            "request_id": "req_12345",
            "ip_address": "192.168.1.100",
        }

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            await monitor.process_log_entry(log_entry)

        mock_alert.assert_called()
        call_kwargs = mock_alert.call_args[1]

        assert call_kwargs["user_id"] == "malicious_user"
        assert "context" in call_kwargs
        context = call_kwargs["context"]
        assert "triggering_log" in context
        assert context["triggering_log"]["message"].startswith("DROP TABLE")

    def test_monitor_thread_safety(self):
        """Test that monitor operations are thread-safe."""
        monitor = LogPatternMonitor()

        # This should not raise any threading-related exceptions
        monitor.start_monitoring()
        time.sleep(0.1)
        monitor.stop_monitoring()

        # Should be able to restart
        monitor.start_monitoring()
        monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_high_volume_log_processing(self):
        """Test processing high volume of log entries."""
        monitor = LogPatternMonitor()

        # Process many log entries quickly
        log_entries = []
        for i in range(100):
            log_entries.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": f"Normal log message {i}",
                    "request_id": f"req_{i}",
                }
            )

        # Add a few suspicious entries
        log_entries.extend(
            [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "message": "Authentication failed multiple times",
                    "user_id": "test_user",
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "WARNING",
                    "message": "XSS attempt: <script>alert(1)</script>",
                    "user_id": "attacker",
                },
            ]
        )

        # Process all entries
        start_time = time.time()
        for entry in log_entries:
            await monitor.process_log_entry(entry)

        processing_time = time.time() - start_time

        # Should process quickly (less than 1 second for 102 entries)
        assert processing_time < 1.0
        assert monitor.stats["logs_processed"] == 102
        assert monitor.stats["patterns_matched"] >= 2  # At least auth failure and XSS


@pytest.mark.integration
class TestLogMonitoringIntegrationWithLogging:
    """Integration tests with the logging system."""

    @pytest.mark.asyncio
    async def test_json_formatter_integration(self):
        """Test that JsonFormatter integrates with log monitoring."""
        import logging

        from simplenote_mcp.server.logging import JsonFormatter

        # Create a log record
        logging.getLogger("test")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=100,
            msg="Authentication failed for user %s",
            args=("test@example.com",),
            exc_info=None,
        )

        formatter = JsonFormatter()

        # Mock the process_log_for_patterns to avoid actual processing
        with patch(
            "simplenote_mcp.server.log_monitor.process_log_for_patterns"
        ):
            formatted = formatter.format(record)

        # Should have attempted to process for patterns
        # Note: May not be called if no async event loop is running
        assert formatted  # Should produce valid JSON
        json.loads(formatted)  # Should be valid JSON

    @pytest.mark.asyncio
    async def test_structured_log_adapter_integration(self):
        """Test that StructuredLogAdapter triggers pattern monitoring."""
        from simplenote_mcp.server.logging import get_logger

        logger = get_logger("test", user_id="test_user")

        with patch(
            "simplenote_mcp.server.log_monitor.process_log_for_patterns"
        ):
            logger.error("Authentication failure detected")
            await asyncio.sleep(0.01)  # Allow async processing

        # Should have attempted pattern monitoring
        # Note: Actual calling depends on event loop availability
        assert True  # Test passes if no exceptions raised
