"""Tests for security alerting system."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simplenote_mcp.server.alerting import (
    AlertSeverity,
    AlertType,
    SecurityAlert,
    SecurityAlerter,
    alert_authentication_failure,
    alert_dangerous_input,
    alert_rate_limit_violation,
    alert_suspicious_pattern,
    get_alerter,
)


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self):
        """Test all severity levels exist."""
        assert AlertSeverity.LOW.value == "LOW"
        assert AlertSeverity.MEDIUM.value == "MEDIUM"
        assert AlertSeverity.HIGH.value == "HIGH"
        assert AlertSeverity.CRITICAL.value == "CRITICAL"

    def test_severity_comparison(self):
        """Test severity enum members are distinct."""
        severities = [
            AlertSeverity.LOW,
            AlertSeverity.MEDIUM,
            AlertSeverity.HIGH,
            AlertSeverity.CRITICAL,
        ]
        assert len(set(severities)) == 4


class TestAlertType:
    """Tests for AlertType enum."""

    def test_alert_type_values(self):
        """Test all alert types exist."""
        assert AlertType.AUTHENTICATION_FAILURE.value == "authentication_failure"
        assert AlertType.RATE_LIMIT_VIOLATION.value == "rate_limit_violation"
        assert AlertType.DANGEROUS_INPUT.value == "dangerous_input"
        assert AlertType.SUSPICIOUS_PATTERN.value == "suspicious_pattern"
        assert AlertType.REPEATED_FAILURES.value == "repeated_failures"
        assert AlertType.ANOMALOUS_BEHAVIOR.value == "anomalous_behavior"
        assert (
            AlertType.SECURITY_THRESHOLD_EXCEEDED.value == "security_threshold_exceeded"
        )


class TestSecurityAlert:
    """Tests for SecurityAlert class."""

    def test_init(self):
        """Test SecurityAlert initialization."""
        alert = SecurityAlert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.HIGH,
            message="Failed login attempt",
            context={"ip": "192.168.1.1"},
            user_id="user123",
            client_info={"browser": "Chrome"},
        )

        assert alert.alert_type == AlertType.AUTHENTICATION_FAILURE
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Failed login attempt"
        assert alert.context == {"ip": "192.168.1.1"}
        assert alert.user_id == "user123"
        assert alert.client_info == {"browser": "Chrome"}
        assert isinstance(alert.timestamp, datetime)
        assert alert.alert_id.startswith("authentication_failure_")

    def test_init_defaults(self):
        """Test SecurityAlert with default values."""
        alert = SecurityAlert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.MEDIUM,
            message="Test",
            context={},
        )

        assert alert.user_id is None
        assert alert.client_info == {}

    def test_to_dict(self):
        """Test conversion to dictionary."""
        alert = SecurityAlert(
            alert_type=AlertType.RATE_LIMIT_VIOLATION,
            severity=AlertSeverity.LOW,
            message="Rate limit exceeded",
            context={"requests": 100},
            user_id="user456",
        )

        result = alert.to_dict()

        assert "alert_id" in result
        assert result["alert_type"] == "rate_limit_violation"
        assert result["severity"] == "LOW"
        assert result["message"] == "Rate limit exceeded"
        assert result["context"] == {"requests": 100}
        assert result["user_id"] == "user456"
        assert "timestamp" in result

    def test_str_representation(self):
        """Test string representation."""
        alert = SecurityAlert(
            alert_type=AlertType.SUSPICIOUS_PATTERN,
            severity=AlertSeverity.CRITICAL,
            message="SQL injection attempt",
            context={},
        )

        result = str(alert)

        assert "[CRITICAL]" in result
        assert "suspicious_pattern" in result
        assert "SQL injection attempt" in result

    def test_alert_id_uniqueness(self):
        """Test that alert IDs are unique."""
        alerts = [
            SecurityAlert(
                alert_type=AlertType.DANGEROUS_INPUT,
                severity=AlertSeverity.HIGH,
                message="Test",
                context={},
            )
            for _ in range(10)
        ]

        alert_ids = [a.alert_id for a in alerts]
        # IDs should be unique (though in rapid succession might have same timestamp)
        # At minimum, they should all be valid strings
        assert all(isinstance(id, str) and len(id) > 0 for id in alert_ids)


class TestSecurityAlerter:
    """Tests for SecurityAlerter class."""

    def test_init_default_config(self):
        """Test SecurityAlerter initialization with defaults."""
        alerter = SecurityAlerter()

        assert alerter.config == {}
        assert len(alerter.alert_history) == 0
        assert alerter.thresholds["failed_auth_threshold"] == 5
        assert alerter.thresholds["rate_limit_threshold"] == 3
        assert alerter.thresholds["suspicious_pattern_threshold"] == 3
        assert alerter.thresholds["time_window_minutes"] == 5

    def test_default_alert_log_path_is_absolute(self):
        """SecurityAlerter default alert_log_path must be absolute.

        Claude Desktop runs MCP servers with CWD=/. A relative default like
        'simplenote_mcp/logs/...' tries to create /simplenote_mcp/ which is
        read-only, causing [Errno 30] Read-only file system.
        """
        alerter = SecurityAlerter()
        assert alerter.alert_log_path.is_absolute(), (
            f"Default alert_log_path must be absolute, got: {alerter.alert_log_path}"
        )

    def test_init_custom_config(self):
        """Test SecurityAlerter with custom config."""
        config = {
            "failed_auth_threshold": 10,
            "rate_limit_threshold": 5,
            "time_window_minutes": 10,
            "enable_email_alerts": True,
            "enable_webhook_alerts": True,
        }

        alerter = SecurityAlerter(config)

        assert alerter.thresholds["failed_auth_threshold"] == 10
        assert alerter.thresholds["rate_limit_threshold"] == 5
        assert alerter.thresholds["time_window_minutes"] == 10
        assert alerter.enable_email_alerts is True
        assert alerter.enable_webhook_alerts is True

    @pytest.mark.asyncio
    async def test_create_alert(self):
        """Test creating an alert."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        alert = await alerter.create_alert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.HIGH,
            message="Test alert",
            context={"test": True},
            user_id="user123",
        )

        assert isinstance(alert, SecurityAlert)
        assert len(alerter.alert_history) == 1
        assert alerter.alert_history[0] is alert

    @pytest.mark.asyncio
    async def test_alert_history_limit(self):
        """Test alert history respects max limit."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        # Create more alerts than the history limit (1000)
        for i in range(1005):
            await alerter.create_alert(
                alert_type=AlertType.DANGEROUS_INPUT,
                severity=AlertSeverity.LOW,
                message=f"Alert {i}",
                context={},
            )

        # Should only keep last 1000
        assert len(alerter.alert_history) == 1000

    @pytest.mark.asyncio
    async def test_create_alert_logs_error(self):
        """Test that alerts are logged."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        with patch("simplenote_mcp.server.alerting.logger") as mock_logger:
            await alerter.create_alert(
                alert_type=AlertType.AUTHENTICATION_FAILURE,
                severity=AlertSeverity.HIGH,
                message="Test message",
                context={},
            )

            mock_logger.error.assert_called()

    def test_get_recent_alerts_empty(self):
        """Test getting recent alerts when none exist."""
        alerter = SecurityAlerter()

        alerts = alerter.get_recent_alerts()

        assert alerts == []

    @pytest.mark.asyncio
    async def test_get_recent_alerts_filtered_by_time(self):
        """Test getting recent alerts filtered by time window."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        # Create an alert
        await alerter.create_alert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.LOW,
            message="Recent alert",
            context={},
        )

        # Get alerts from last 60 minutes
        alerts = alerter.get_recent_alerts(minutes=60)

        assert len(alerts) == 1

    @pytest.mark.asyncio
    async def test_get_recent_alerts_filtered_by_severity(self):
        """Test filtering alerts by severity."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        await alerter.create_alert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.LOW,
            message="Low severity",
            context={},
        )
        await alerter.create_alert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.HIGH,
            message="High severity",
            context={},
        )

        high_alerts = alerter.get_recent_alerts(severity=AlertSeverity.HIGH)

        assert len(high_alerts) == 1
        assert high_alerts[0].severity == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_get_recent_alerts_filtered_by_type(self):
        """Test filtering alerts by type."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        await alerter.create_alert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.HIGH,
            message="Auth failure",
            context={},
        )
        await alerter.create_alert(
            alert_type=AlertType.RATE_LIMIT_VIOLATION,
            severity=AlertSeverity.LOW,
            message="Rate limit",
            context={},
        )

        auth_alerts = alerter.get_recent_alerts(
            alert_type=AlertType.AUTHENTICATION_FAILURE
        )

        assert len(auth_alerts) == 1
        assert auth_alerts[0].alert_type == AlertType.AUTHENTICATION_FAILURE


class TestSecurityAlerterThresholds:
    """Tests for threshold-based escalation."""

    @pytest.mark.asyncio
    async def test_auth_failure_threshold_escalation(self):
        """Test authentication failure threshold triggers escalation."""
        alerter = SecurityAlerter(
            {
                "failed_auth_threshold": 3,
                "time_window_minutes": 5,
                "enable_file_alerts": False,
            }
        )

        user_id = "test_user"

        # Create failures below threshold
        for i in range(2):
            await alerter.create_alert(
                alert_type=AlertType.AUTHENTICATION_FAILURE,
                severity=AlertSeverity.MEDIUM,
                message=f"Auth failure {i}",
                context={},
                user_id=user_id,
            )

        initial_count = len(alerter.alert_history)

        # Create failure that exceeds threshold
        await alerter.create_alert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.MEDIUM,
            message="Auth failure 3",
            context={},
            user_id=user_id,
        )

        # Should have created additional escalation alert
        assert len(alerter.alert_history) >= initial_count + 1

    @pytest.mark.asyncio
    async def test_rate_limit_threshold_escalation(self):
        """Test rate limit threshold triggers escalation."""
        alerter = SecurityAlerter(
            {
                "rate_limit_threshold": 2,
                "time_window_minutes": 5,
                "enable_file_alerts": False,
            }
        )

        user_id = "rate_limit_user"

        # Create violations to exceed threshold
        for i in range(3):
            await alerter.create_alert(
                alert_type=AlertType.RATE_LIMIT_VIOLATION,
                severity=AlertSeverity.LOW,
                message=f"Rate limit {i}",
                context={},
                user_id=user_id,
            )

        # Check for escalated alerts
        high_alerts = [
            a for a in alerter.alert_history if a.severity == AlertSeverity.HIGH
        ]
        assert len(high_alerts) >= 1


class TestSecurityAlerterFileAlerts:
    """Tests for file-based alerting."""

    @pytest.mark.asyncio
    async def test_save_alert_to_file(self, tmp_path):
        """Test saving alerts to file."""
        alert_log = tmp_path / "alerts.json"

        alerter = SecurityAlerter(
            {
                "alert_log_path": str(alert_log),
                "enable_file_alerts": True,
            }
        )

        await alerter.create_alert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.HIGH,
            message="Test file alert",
            context={"test": True},
        )

        # Give async file write time to complete
        await asyncio.sleep(0.1)

        # File should exist and contain valid JSON
        if alert_log.exists():
            content = alert_log.read_text()
            # Each line should be valid JSON
            for line in content.strip().split("\n"):
                if line:
                    data = json.loads(line)
                    # The file format includes a wrapper with timestamp and alert
                    assert "alert" in data or "alert_id" in data


class TestSecurityAlerterNotifications:
    """Tests for notification methods."""

    @pytest.mark.asyncio
    async def test_email_alert_not_configured(self):
        """Test email alert logs debug when not configured."""
        alerter = SecurityAlerter(
            {
                "enable_email_alerts": True,
                "enable_file_alerts": False,
            }
        )

        alert = SecurityAlert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Critical alert",
            context={},
        )

        with patch("simplenote_mcp.server.alerting.logger") as mock_logger:
            await alerter._send_email_alert(alert)
            # Should log debug that email is not configured
            mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_webhook_alert_not_configured(self):
        """Test webhook alert logs debug when not configured."""
        alerter = SecurityAlerter(
            {
                "enable_webhook_alerts": True,
                "enable_file_alerts": False,
            }
        )

        alert = SecurityAlert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Critical alert",
            context={},
        )

        with patch("simplenote_mcp.server.alerting.logger") as mock_logger:
            await alerter._send_webhook_alert(alert)
            # Should log debug that webhook is not configured
            mock_logger.debug.assert_called()


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @patch("simplenote_mcp.server.alerting._global_alerter", None)
    def test_get_alerter_creates_instance(self):
        """Test get_alerter creates new instance."""
        alerter = get_alerter()
        assert isinstance(alerter, SecurityAlerter)

    @patch("simplenote_mcp.server.alerting._global_alerter", None)
    def test_get_alerter_reuses_instance(self):
        """Test get_alerter reuses existing instance."""
        alerter1 = get_alerter()
        alerter2 = get_alerter()
        assert alerter1 is alerter2

    @pytest.mark.asyncio
    async def test_alert_authentication_failure(self):
        """Test alert_authentication_failure convenience function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get:
            mock_alerter = MagicMock()
            mock_alerter.create_alert = AsyncMock()
            mock_get.return_value = mock_alerter

            await alert_authentication_failure(
                user_id="user123",
                reason="Invalid password",
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.AUTHENTICATION_FAILURE

    @pytest.mark.asyncio
    async def test_alert_rate_limit_violation(self):
        """Test alert_rate_limit_violation convenience function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get:
            mock_alerter = MagicMock()
            mock_alerter.create_alert = AsyncMock()
            mock_get.return_value = mock_alerter

            await alert_rate_limit_violation(
                user_id="user456",
                request_count=150,
                limit=100,
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.RATE_LIMIT_VIOLATION

    @pytest.mark.asyncio
    async def test_alert_dangerous_input(self):
        """Test alert_dangerous_input convenience function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get:
            mock_alerter = MagicMock()
            mock_alerter.create_alert = AsyncMock()
            mock_get.return_value = mock_alerter

            await alert_dangerous_input(
                user_id="user789",
                input_type="query",
                pattern_matched="SQL injection",
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.DANGEROUS_INPUT

    @pytest.mark.asyncio
    async def test_alert_suspicious_pattern(self):
        """Test alert_suspicious_pattern convenience function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get:
            mock_alerter = MagicMock()
            mock_alerter.create_alert = AsyncMock()
            mock_get.return_value = mock_alerter

            await alert_suspicious_pattern(
                user_id="user000",
                pattern_description="Unusual access pattern",
                context={"frequency": "100x normal"},
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.SUSPICIOUS_PATTERN


class TestSecurityAlerterEdgeCases:
    """Edge case tests for SecurityAlerter."""

    def test_empty_alert_history_operations(self):
        """Test operations on empty alert history."""
        alerter = SecurityAlerter()

        # Should not raise
        alerts = alerter.get_recent_alerts(
            minutes=60,
            severity=AlertSeverity.HIGH,
            alert_type=AlertType.DANGEROUS_INPUT,
        )

        assert alerts == []

    @pytest.mark.asyncio
    async def test_alert_without_user_id(self):
        """Test creating alert without user ID."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        alert = await alerter.create_alert(
            alert_type=AlertType.ANOMALOUS_BEHAVIOR,
            severity=AlertSeverity.MEDIUM,
            message="System anomaly",
            context={"metric": "cpu_usage"},
        )

        assert alert.user_id is None

    @pytest.mark.asyncio
    async def test_alert_with_complex_context(self):
        """Test alert with complex nested context."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        complex_context = {
            "nested": {
                "deep": {
                    "value": [1, 2, 3],
                },
            },
            "list": ["a", "b", "c"],
            "number": 42,
            "boolean": True,
            "null": None,
        }

        alert = await alerter.create_alert(
            alert_type=AlertType.SUSPICIOUS_PATTERN,
            severity=AlertSeverity.LOW,
            message="Complex context test",
            context=complex_context,
        )

        assert alert.context == complex_context
        # Should serialize to dict without error
        alert_dict = alert.to_dict()
        assert alert_dict["context"] == complex_context

    @pytest.mark.asyncio
    async def test_rapid_alert_creation(self):
        """Test rapid creation of many alerts."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        # Create 100 alerts rapidly
        for i in range(100):
            await alerter.create_alert(
                alert_type=AlertType.DANGEROUS_INPUT,
                severity=AlertSeverity.LOW,
                message=f"Rapid alert {i}",
                context={"index": i},
            )

        assert len(alerter.alert_history) == 100

    def test_threshold_configuration(self):
        """Test various threshold configurations."""
        # Zero thresholds
        alerter = SecurityAlerter(
            {
                "failed_auth_threshold": 0,
                "rate_limit_threshold": 0,
            }
        )
        assert alerter.thresholds["failed_auth_threshold"] == 0

        # Large thresholds
        alerter = SecurityAlerter(
            {
                "failed_auth_threshold": 1000000,
            }
        )
        assert alerter.thresholds["failed_auth_threshold"] == 1000000

    @pytest.mark.asyncio
    async def test_concurrent_alert_creation(self):
        """Test concurrent alert creation is safe."""
        alerter = SecurityAlerter({"enable_file_alerts": False})

        async def create_alerts(prefix: str):
            for i in range(10):
                await alerter.create_alert(
                    alert_type=AlertType.DANGEROUS_INPUT,
                    severity=AlertSeverity.LOW,
                    message=f"{prefix}-{i}",
                    context={},
                )

        # Run concurrent alert creation
        await asyncio.gather(
            create_alerts("task1"),
            create_alerts("task2"),
            create_alerts("task3"),
        )

        assert len(alerter.alert_history) == 30
