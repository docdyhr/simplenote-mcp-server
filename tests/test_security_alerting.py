"""Tests for security alerting system."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

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
from simplenote_mcp.server.errors import SecurityError


class TestSecurityAlert:
    """Test SecurityAlert class."""

    def test_alert_creation(self):
        """Test creating a security alert."""
        alert = SecurityAlert(
            alert_type=AlertType.DANGEROUS_INPUT,
            severity=AlertSeverity.HIGH,
            message="Test alert message",
            context={"key": "value"},
            user_id="test_user",
            client_info={"ip": "127.0.0.1"},
        )

        assert alert.alert_type == AlertType.DANGEROUS_INPUT
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Test alert message"
        assert alert.context == {"key": "value"}
        assert alert.user_id == "test_user"
        assert alert.client_info == {"ip": "127.0.0.1"}
        assert isinstance(alert.timestamp, datetime)
        assert alert.alert_id.startswith("dangerous_input_")

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = SecurityAlert(
            alert_type=AlertType.RATE_LIMIT_VIOLATION,
            severity=AlertSeverity.MEDIUM,
            message="Rate limit exceeded",
            context={"requests": 100},
        )

        alert_dict = alert.to_dict()

        assert alert_dict["alert_type"] == "rate_limit_violation"
        assert alert_dict["severity"] == "MEDIUM"
        assert alert_dict["message"] == "Rate limit exceeded"
        assert alert_dict["context"] == {"requests": 100}
        assert "timestamp" in alert_dict
        assert "alert_id" in alert_dict

    def test_alert_string_representation(self):
        """Test string representation of alert."""
        alert = SecurityAlert(
            alert_type=AlertType.AUTHENTICATION_FAILURE,
            severity=AlertSeverity.LOW,
            message="Login failed",
            context={},
        )

        alert_str = str(alert)
        assert alert_str == "[LOW] authentication_failure: Login failed"


class TestSecurityAlerter:
    """Test SecurityAlerter class."""

    def setup_method(self):
        """Set up test environment."""
        self.test_config = {
            "failed_auth_threshold": 3,
            "rate_limit_threshold": 2,
            "suspicious_pattern_threshold": 2,
            "time_window_minutes": 5,
            "enable_file_alerts": False,  # Disable file alerts for tests
            "enable_email_alerts": False,
            "enable_webhook_alerts": False,
        }
        self.alerter = SecurityAlerter(self.test_config)

    @pytest.mark.asyncio
    async def test_create_alert(self):
        """Test creating an alert."""
        alert = await self.alerter.create_alert(
            AlertType.DANGEROUS_INPUT,
            AlertSeverity.HIGH,
            "Test dangerous input",
            {"pattern": "SELECT * FROM"},
            user_id="test_user",
        )

        assert alert.alert_type == AlertType.DANGEROUS_INPUT
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Test dangerous input"
        assert alert.user_id == "test_user"

        # Check it was added to history
        assert len(self.alerter.alert_history) == 1
        assert self.alerter.alert_history[0] == alert

    @pytest.mark.asyncio
    async def test_authentication_failure_pattern(self):
        """Test authentication failure pattern detection."""
        user_id = "test_user"

        # Create multiple authentication failures
        for i in range(self.test_config["failed_auth_threshold"]):
            await self.alerter.create_alert(
                AlertType.AUTHENTICATION_FAILURE,
                AlertSeverity.MEDIUM,
                f"Auth failure {i}",
                {"attempt": i},
                user_id=user_id,
            )

        # Should have created additional alert for repeated failures
        # Initial alerts + 1 escalation alert
        expected_alerts = self.test_config["failed_auth_threshold"] + 1
        assert len(self.alerter.alert_history) == expected_alerts

        # Check the escalation alert
        escalation_alert = self.alerter.alert_history[-1]
        assert escalation_alert.alert_type == AlertType.REPEATED_FAILURES
        assert escalation_alert.severity == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_rate_limit_violation_pattern(self):
        """Test rate limit violation pattern detection."""
        user_id = "test_user"

        # Create multiple rate limit violations
        for i in range(self.test_config["rate_limit_threshold"]):
            await self.alerter.create_alert(
                AlertType.RATE_LIMIT_VIOLATION,
                AlertSeverity.MEDIUM,
                f"Rate limit violation {i}",
                {"requests": 100 + i},
                user_id=user_id,
            )

        # Should have created additional alert for anomalous behavior
        expected_alerts = self.test_config["rate_limit_threshold"] + 1
        assert len(self.alerter.alert_history) == expected_alerts

        # Check the escalation alert
        escalation_alert = self.alerter.alert_history[-1]
        assert escalation_alert.alert_type == AlertType.ANOMALOUS_BEHAVIOR
        assert escalation_alert.severity == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_suspicious_input_pattern(self):
        """Test suspicious input pattern detection."""
        user_id = "test_user"

        # Create multiple dangerous input alerts
        for i in range(self.test_config["suspicious_pattern_threshold"]):
            await self.alerter.create_alert(
                AlertType.DANGEROUS_INPUT,
                AlertSeverity.HIGH,
                f"Dangerous input {i}",
                {"pattern": f"pattern_{i}"},
                user_id=user_id,
            )

        # Should have created additional alert for security threshold exceeded
        expected_alerts = self.test_config["suspicious_pattern_threshold"] + 1
        assert len(self.alerter.alert_history) == expected_alerts

        # Check the escalation alert
        escalation_alert = self.alerter.alert_history[-1]
        assert escalation_alert.alert_type == AlertType.SECURITY_THRESHOLD_EXCEEDED
        assert escalation_alert.severity == AlertSeverity.CRITICAL

    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Add some test alerts manually
        old_alert = SecurityAlert(
            AlertType.DANGEROUS_INPUT,
            AlertSeverity.LOW,
            "Old alert",
            {},
        )
        old_alert.timestamp = datetime.utcnow() - timedelta(hours=2)

        recent_alert = SecurityAlert(
            AlertType.RATE_LIMIT_VIOLATION,
            AlertSeverity.HIGH,
            "Recent alert",
            {},
        )

        self.alerter.alert_history.extend([old_alert, recent_alert])

        # Get recent alerts (last 60 minutes)
        recent_alerts = self.alerter.get_recent_alerts(minutes=60)
        assert len(recent_alerts) == 1
        assert recent_alerts[0] == recent_alert

        # Get alerts with severity filter
        high_alerts = self.alerter.get_recent_alerts(
            minutes=180, severity=AlertSeverity.HIGH
        )
        assert len(high_alerts) == 1
        assert high_alerts[0] == recent_alert

        # Get alerts with type filter
        dangerous_alerts = self.alerter.get_recent_alerts(
            minutes=180, alert_type=AlertType.DANGEROUS_INPUT
        )
        assert len(dangerous_alerts) == 1
        assert dangerous_alerts[0] == old_alert

    def test_get_alert_summary(self):
        """Test getting alert summary."""
        # Add test alerts
        alerts = [
            SecurityAlert(
                AlertType.DANGEROUS_INPUT, AlertSeverity.HIGH, "Alert 1", {}, "user1"
            ),
            SecurityAlert(
                AlertType.RATE_LIMIT_VIOLATION,
                AlertSeverity.MEDIUM,
                "Alert 2",
                {},
                "user2",
            ),
            SecurityAlert(
                AlertType.DANGEROUS_INPUT, AlertSeverity.HIGH, "Alert 3", {}, "user1"
            ),
        ]

        self.alerter.alert_history.extend(alerts)

        summary = self.alerter.get_alert_summary(minutes=60)

        assert summary["total_alerts"] == 3
        assert summary["by_severity"]["HIGH"] == 2
        assert summary["by_severity"]["MEDIUM"] == 1
        assert summary["by_type"]["dangerous_input"] == 2
        assert summary["by_type"]["rate_limit_violation"] == 1
        assert len(summary["affected_users"]) == 2
        assert "user1" in summary["affected_users"]
        assert "user2" in summary["affected_users"]
        assert summary["latest_alert"] is not None

    def test_cleanup_old_data(self):
        """Test cleaning up old tracking data."""
        # Add some test data
        self.alerter.failure_counts["user1"] = 5
        self.alerter.failure_counts["user2"] = 3

        # Add many entries to trigger cleanup
        for i in range(1001):
            self.alerter.failure_counts[f"user_{i}"] = 1

        self.alerter.cleanup_old_data(days=7)

        # Should have cleared the data
        assert len(self.alerter.failure_counts) == 0


class TestAlertingFunctions:
    """Test alerting convenience functions."""

    @pytest.mark.asyncio
    async def test_alert_authentication_failure(self):
        """Test authentication failure alert function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get_alerter:
            mock_alerter = Mock()
            mock_alerter.create_alert = AsyncMock()
            mock_get_alerter.return_value = mock_alerter

            await alert_authentication_failure(
                "test_user", "Invalid password", {"ip": "127.0.0.1"}
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.AUTHENTICATION_FAILURE
            assert call_args[0][1] == AlertSeverity.MEDIUM
            assert "test_user" in call_args[0][2]
            assert call_args[1]["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_alert_rate_limit_violation(self):
        """Test rate limit violation alert function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get_alerter:
            mock_alerter = Mock()
            mock_alerter.create_alert = AsyncMock()
            mock_get_alerter.return_value = mock_alerter

            await alert_rate_limit_violation("test_user", 150, 100, {"source": "api"})

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.RATE_LIMIT_VIOLATION
            assert call_args[0][1] == AlertSeverity.MEDIUM
            assert "150/100" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_alert_dangerous_input(self):
        """Test dangerous input alert function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get_alerter:
            mock_alerter = Mock()
            mock_alerter.create_alert = AsyncMock()
            mock_get_alerter.return_value = mock_alerter

            await alert_dangerous_input(
                "test_user", "note_content", "SELECT * FROM users", {"client": "web"}
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.DANGEROUS_INPUT
            assert call_args[0][1] == AlertSeverity.HIGH
            assert "note_content" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_alert_suspicious_pattern(self):
        """Test suspicious pattern alert function."""
        with patch("simplenote_mcp.server.alerting.get_alerter") as mock_get_alerter:
            mock_alerter = Mock()
            mock_alerter.create_alert = AsyncMock()
            mock_get_alerter.return_value = mock_alerter

            await alert_suspicious_pattern(
                "test_user",
                "Rapid sequential requests",
                {"request_count": 200, "time_window": "1 minute"},
                {"user_agent": "bot"},
            )

            mock_alerter.create_alert.assert_called_once()
            call_args = mock_alerter.create_alert.call_args
            assert call_args[0][0] == AlertType.SUSPICIOUS_PATTERN
            assert call_args[0][1] == AlertSeverity.MEDIUM
            assert "Rapid sequential requests" in call_args[0][2]


class TestGlobalAlerter:
    """Test global alerter functionality."""

    def test_get_global_alerter(self):
        """Test getting global alerter instance."""
        alerter1 = get_alerter()
        alerter2 = get_alerter()

        # Should return the same instance
        assert alerter1 is alerter2
        assert isinstance(alerter1, SecurityAlerter)

    def test_global_alerter_functionality(self):
        """Test global alerter works correctly."""
        alerter = get_alerter()

        # Should have default configuration
        assert alerter.thresholds["failed_auth_threshold"] == 5
        assert alerter.thresholds["rate_limit_threshold"] == 3
        assert alerter.enable_file_alerts is True


class TestAlertIntegration:
    """Test integration between alerting and other security components."""

    @pytest.mark.asyncio
    async def test_security_event_triggers_alert(self):
        """Test that security events trigger alerts correctly."""
        from simplenote_mcp.server.security import security_validator

        # Note content no longer triggers security errors (notes are plain text).
        # Use search query validation instead, which still applies pattern checks.
        with pytest.raises(SecurityError):
            security_validator.validate_search_query(
                "SELECT * FROM users WHERE 1=1", "test query"
            )

        # Check that alert was triggered (this tests the integration)
        # In a real test, we would mock the alerting system

    def test_rate_limit_triggers_alert(self):
        """Test that rate limit violations trigger alerts."""
        # Trigger multiple rate limit violations
        # This would test the integration with alerting
        # In a real test, we would mock the alerting system
