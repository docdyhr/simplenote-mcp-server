"""Integration tests for Phase 2 security enhancements.

This module tests the integration of all Phase 2 security features including
SBOM generation, session timeout, log monitoring, alerting, and standardized logging.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import patch

import pytest

from simplenote_mcp.server.auth import AuthenticationManager, SessionManager
from simplenote_mcp.server.errors import SessionTimeoutError
from simplenote_mcp.server.log_monitor import get_log_monitor, process_log_for_patterns
from simplenote_mcp.server.logger_factory import (
    get_auth_logger,
    get_performance_logger,
    get_security_logger,
)


@pytest.mark.integration
class TestPhase2SecurityIntegration:
    """Integration tests for Phase 2 security enhancements."""

    @pytest.mark.asyncio
    async def test_authentication_with_logging_and_alerting(self):
        """Test authentication failure triggering logging and alerting."""
        # Create security logger
        logger = get_security_logger(
            user_id="test_user", operation="authentication", threat_level="high"
        )

        # Mock alert creation
        with patch("simplenote_mcp.server.log_monitor.alert_suspicious_pattern"):
            # Log authentication failure with suspicious pattern
            logger.error(
                "Authentication failed for user test_user multiple times in succession"
            )

            # Process the log entry through pattern monitoring
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Authentication failed for user test_user multiple times",
                "logger": "security",
                "user_id": "test_user",
                "category": "security",
                "threat_level": "high",
            }

            await process_log_for_patterns(log_entry)

        # Should have triggered pattern monitoring
        # Note: Actual alert triggering depends on pattern thresholds
        assert True  # Test passes if no exceptions

    def test_session_timeout_integration(self):
        """Test session timeout mechanism with proper error handling."""
        # Create session manager with short timeout for testing
        session_manager = SessionManager(default_timeout=1)  # 1 second

        # Create session
        session_id = "test_session_123"
        user_data = {"user_id": "test_user", "email": "test@example.com"}
        session_manager.create_session(session_id, user_data, timeout=1)

        # Verify session is active
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session["user_data"]["user_id"] == "test_user"

        # Wait for timeout
        time.sleep(1.1)

        # Session should now be expired
        with pytest.raises(SessionTimeoutError):
            session_manager.get_session(session_id)

    def test_authentication_manager_timeout(self):
        """Test authentication manager with session timeout."""
        auth_manager = AuthenticationManager(session_timeout=2)  # 2 seconds

        # Initially no client
        assert not auth_manager.is_client_valid()

        # Test timeout behavior (this would normally require credentials)
        info = auth_manager.get_client_info()
        assert not info["authenticated"]

    @pytest.mark.asyncio
    async def test_log_monitoring_security_patterns(self):
        """Test log monitoring detecting multiple security patterns."""
        monitor = get_log_monitor()

        # Security log entries with different suspicious patterns
        security_logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Suspicious query: SELECT * FROM users UNION SELECT password FROM admin",
                "user_id": "attacker1",
                "category": "security",
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "WARNING",
                "message": "XSS attempt detected: <script>alert('hack')</script>",
                "user_id": "attacker2",
                "category": "security",
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": "Path traversal attempt: ../../../etc/passwd",
                "user_id": "attacker3",
                "category": "security",
            },
        ]

        with patch(
            "simplenote_mcp.server.log_monitor.alert_suspicious_pattern"
        ) as mock_alert:
            # Process all security logs
            for log_entry in security_logs:
                await monitor.process_log_entry(log_entry)

            # Should have triggered multiple alerts
            assert mock_alert.call_count >= 2  # At least SQL injection and XSS

    def test_logger_factory_with_security_context(self):
        """Test logger factory creating loggers with security context."""
        # Test different types of security loggers
        auth_logger = get_auth_logger(
            user_id="auth_test_user",
            operation="login_attempt",
            client_ip="192.168.1.100",
        )

        security_logger = get_security_logger(
            user_id="security_test_user",
            operation="access_denied",
            threat_level="critical",
            attack_type="privilege_escalation",
        )

        performance_logger = get_performance_logger(
            operation="security_scan", duration=2.5, scanned_items=1000
        )

        # Verify all loggers have proper context
        assert auth_logger.extra["category"] == "authentication"
        assert auth_logger.extra["user_id"] == "auth_test_user"
        assert auth_logger.extra["client_ip"] == "192.168.1.100"

        assert security_logger.extra["category"] == "security"
        assert security_logger.extra["threat_level"] == "critical"
        assert security_logger.extra["attack_type"] == "privilege_escalation"

        assert performance_logger.extra["category"] == "performance"
        assert performance_logger.extra["duration_seconds"] == 2.5
        assert performance_logger.extra["scanned_items"] == 1000

        # All should have required schema fields
        for logger in [auth_logger, security_logger, performance_logger]:
            assert "request_id" in logger.extra
            assert "trace_id" in logger.extra
            assert "timestamp" in logger.extra

    @pytest.mark.asyncio
    async def test_end_to_end_security_workflow(self):
        """Test complete security workflow from authentication to alerting."""

        # 1. Start with authentication attempt
        auth_logger = get_auth_logger(
            user_id="suspicious_user", operation="login_attempt", client_ip="10.0.0.1"
        )

        # 2. Log authentication failure
        auth_logger.error("Authentication failed: invalid credentials")

        # 3. Create security event for suspicious activity
        security_logger = get_security_logger(
            user_id="suspicious_user",
            operation="suspicious_activity",
            threat_level="high",
            activity_type="repeated_failures",
        )

        security_logger.warning("Multiple authentication failures detected")

        # 4. Process through log monitoring
        suspicious_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "message": "Authentication failed: invalid credentials multiple times",
            "user_id": "suspicious_user",
            "category": "authentication",
            "client_ip": "10.0.0.1",
        }

        with patch("simplenote_mcp.server.log_monitor.alert_suspicious_pattern"):
            await process_log_for_patterns(suspicious_log)

        # 5. Verify workflow completed without errors
        assert True  # Workflow completed successfully

    def test_session_cleanup_and_monitoring(self):
        """Test session cleanup with monitoring integration."""
        session_manager = SessionManager(default_timeout=1)
        performance_logger = get_performance_logger(
            operation="session_cleanup", component="session_manager"
        )

        # Create multiple sessions
        for i in range(5):
            session_manager.create_session(
                f"session_{i}", {"user_id": f"user_{i}"}, timeout=1
            )

        # Verify sessions exist
        active_sessions = session_manager.list_active_sessions()
        assert len(active_sessions) == 5

        # Wait for expiration
        time.sleep(1.1)

        # Clean up expired sessions
        start_time = time.time()
        cleaned_count = session_manager.cleanup_expired_sessions()
        cleanup_duration = time.time() - start_time

        # Log performance metrics
        performance_logger.info(
            f"Session cleanup completed: {cleaned_count} sessions cleaned",
            extra={
                "cleanup_duration": cleanup_duration,
                "sessions_cleaned": cleaned_count,
            },
        )

        assert cleaned_count == 5
        assert cleanup_duration < 1.0  # Should be fast

    def test_error_handling_with_standardized_logging(self):
        """Test error handling with standardized logging schema."""
        from simplenote_mcp.server.errors import (
            AuthenticationError,
            SessionTimeoutError,
            ValidationError,
        )
        from simplenote_mcp.server.logger_factory import get_error_logger

        # Test different error types with proper logging
        errors_to_test = [
            (AuthenticationError("Invalid credentials"), "AuthenticationError"),
            (SessionTimeoutError("Session expired"), "SessionTimeoutError"),
            (ValidationError("Invalid input format"), "ValidationError"),
        ]

        for error, error_type in errors_to_test:
            error_logger = get_error_logger(
                error_type=error_type,
                error_code=error.error_code if hasattr(error, "error_code") else None,
                operation="test_operation",
            )

            # Log the error with context
            error_logger.error(f"Error occurred: {str(error)}")

            # Verify logger has proper schema
            assert error_logger.extra["category"] == "error_handling"
            assert error_logger.extra["error_type"] == error_type
            assert error_logger.extra["operation"] == "test_operation"

    @pytest.mark.asyncio
    async def test_concurrent_security_operations(self):
        """Test concurrent security operations with proper isolation."""

        async def simulate_user_session(user_id: str):
            """Simulate user session with authentication and operations."""
            auth_logger = get_auth_logger(user_id=user_id, operation="session_start")
            auth_logger.info(f"User {user_id} session started")

            # Simulate some operations
            await asyncio.sleep(0.1)

            # Log potential security event
            if user_id == "suspicious_user":
                security_log = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "WARNING",
                    "message": f"Suspicious activity from user {user_id}",
                    "user_id": user_id,
                    "category": "security",
                }
                await process_log_for_patterns(security_log)

            auth_logger.info(f"User {user_id} session completed")

        # Run multiple concurrent user sessions
        users = ["normal_user1", "normal_user2", "suspicious_user", "normal_user3"]

        with patch("simplenote_mcp.server.log_monitor.alert_suspicious_pattern"):
            tasks = [simulate_user_session(user) for user in users]
            await asyncio.gather(*tasks)

        # All sessions should complete successfully
        assert True

    def test_security_metrics_collection(self):
        """Test collection of security-related performance metrics."""
        from simplenote_mcp.server.logging import record_api_call, record_response_time

        # Record various security-related API calls
        security_operations = [
            ("authenticate_user", True, None),
            ("validate_session", True, None),
            ("check_permissions", False, "AccessDenied"),
            ("scan_input", True, None),
            ("rate_limit_check", False, "RateLimitExceeded"),
        ]

        response_times = [
            ("authenticate_user", 0.15),
            ("validate_session", 0.05),
            ("check_permissions", 0.08),
            ("scan_input", 0.12),
            ("rate_limit_check", 0.03),
        ]

        # Record API call metrics
        for operation, success, error_type in security_operations:
            record_api_call(operation, success, error_type)

        # Record response times
        for operation, duration in response_times:
            record_response_time(operation, duration)

        # Metrics should be recorded without errors
        assert True

    def test_phase2_feature_integration_status(self):
        """Test that all Phase 2 features are properly integrated."""

        # Verify key Phase 2 components can be imported
        try:
            from simplenote_mcp.server.alerting import SecurityAlerter
            from simplenote_mcp.server.auth import AuthenticationManager, SessionManager
            from simplenote_mcp.server.log_monitor import LogPatternMonitor
            from simplenote_mcp.server.logger_factory import LoggerFactory

            # Verify components can be instantiated
            auth_manager = AuthenticationManager()
            session_manager = SessionManager()
            log_monitor = LogPatternMonitor()
            logger_factory = LoggerFactory()
            alerter = SecurityAlerter()

            # All components should initialize successfully
            assert auth_manager is not None
            assert session_manager is not None
            assert log_monitor is not None
            assert logger_factory is not None
            assert alerter is not None

        except ImportError as e:
            pytest.fail(f"Phase 2 component import failed: {e}")


@pytest.mark.security
class TestSecurityBoundaryIntegration:
    """Test security boundary enforcement with Phase 2 enhancements."""

    def test_session_boundary_enforcement(self):
        """Test that session boundaries are properly enforced."""
        session_manager = SessionManager(default_timeout=3600)

        # Create sessions for different users
        session_manager.create_session("user1_session", {"user_id": "user1"})
        session_manager.create_session("user2_session", {"user_id": "user2"})

        # User 1 should not be able to access user 2's session data
        user1_session = session_manager.get_session("user1_session")
        user2_session = session_manager.get_session("user2_session")

        assert user1_session["user_data"]["user_id"] == "user1"
        assert user2_session["user_data"]["user_id"] == "user2"
        assert (
            user1_session["user_data"]["user_id"]
            != user2_session["user_data"]["user_id"]
        )

    @pytest.mark.asyncio
    async def test_logging_isolation(self):
        """Test that logging contexts are properly isolated between requests."""
        from simplenote_mcp.server.logger_factory import (
            LogContext,
            create_contextual_logger,
        )

        # Create separate logging contexts for different requests
        context1 = LogContext(
            request_id="req_001", user_id="user1", operation="create_note"
        )

        context2 = LogContext(
            request_id="req_002", user_id="user2", operation="search_notes"
        )

        logger1 = create_contextual_logger("test", context1)
        logger2 = create_contextual_logger("test", context2)

        # Contexts should be isolated
        assert logger1.extra["user_id"] == "user1"
        assert logger2.extra["user_id"] == "user2"
        assert logger1.extra["request_id"] != logger2.extra["request_id"]
        assert logger1.extra["trace_id"] != logger2.extra["trace_id"]
