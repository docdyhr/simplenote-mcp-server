"""Security alerting system for suspicious activities.

This module provides real-time alerting for security events including failed authentication,
rate limit violations, dangerous input patterns, and other suspicious activities.
"""

import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .logging import logger


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(Enum):
    """Types of security alerts."""

    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    DANGEROUS_INPUT = "dangerous_input"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    REPEATED_FAILURES = "repeated_failures"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    SECURITY_THRESHOLD_EXCEEDED = "security_threshold_exceeded"


class SecurityAlert:
    """Represents a security alert."""

    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        context: dict[str, Any],
        user_id: str | None = None,
        client_info: dict[str, Any] | None = None,
    ):
        """Initialize security alert.

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Human-readable alert message
            context: Additional context data
            user_id: User ID if applicable
            client_info: Client information if available
        """
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.context = context
        self.user_id = user_id
        self.client_info = client_info or {}
        self.timestamp = datetime.utcnow()
        self.alert_id = f"{alert_type.value}_{int(time.time() * 1000)}"

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "user_id": self.user_id,
            "client_info": self.client_info,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of alert."""
        return f"[{self.severity.value}] {self.alert_type.value}: {self.message}"


class SecurityAlerter:
    """Real-time security alerting system."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize security alerter.

        Args:
            config: Alerting configuration
        """
        self.config = config or {}
        self.alert_history: deque = deque(maxlen=1000)  # Keep last 1000 alerts
        self.failure_counts = defaultdict(int)
        self.rate_limit_violations = defaultdict(list)
        self.suspicious_patterns = defaultdict(list)

        # Alert thresholds
        self.thresholds = {
            "failed_auth_threshold": self.config.get("failed_auth_threshold", 5),
            "rate_limit_threshold": self.config.get("rate_limit_threshold", 3),
            "suspicious_pattern_threshold": self.config.get(
                "suspicious_pattern_threshold", 3
            ),
            "time_window_minutes": self.config.get("time_window_minutes", 5),
        }

        # Setup alert output
        self.alert_log_path = Path(
            self.config.get(
                "alert_log_path", "simplenote_mcp/logs/security_alerts.json"
            )
        )
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Notification settings
        self.enable_email_alerts = self.config.get("enable_email_alerts", False)
        self.enable_webhook_alerts = self.config.get("enable_webhook_alerts", False)
        self.enable_file_alerts = self.config.get("enable_file_alerts", True)

        logger.info(
            "Security alerter initialized",
            extra={
                "thresholds": self.thresholds,
                "email_alerts": self.enable_email_alerts,
                "webhook_alerts": self.enable_webhook_alerts,
                "file_alerts": self.enable_file_alerts,
            },
        )

    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        context: dict[str, Any],
        user_id: str | None = None,
        client_info: dict[str, Any] | None = None,
    ) -> SecurityAlert:
        """Create and process a security alert.

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Human-readable alert message
            context: Additional context data
            user_id: User ID if applicable
            client_info: Client information if available

        Returns:
            Created SecurityAlert instance
        """
        alert = SecurityAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            context=context,
            user_id=user_id,
            client_info=client_info,
        )

        # Add to history
        self.alert_history.append(alert)

        # Log alert
        logger.error(
            f"SECURITY ALERT [{alert.alert_type.value}]: {alert.message}",
            extra={
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "context": alert.context,
                "user_id": alert.user_id,
            },
        )

        # Process alert
        await self._process_alert(alert)

        return alert

    async def _process_alert(self, alert: SecurityAlert) -> None:
        """Process and distribute alert.

        Args:
            alert: Security alert to process
        """
        # Save to file
        if self.enable_file_alerts:
            await self._save_alert_to_file(alert)

        # Check for patterns and escalate if needed
        await self._check_alert_patterns(alert)

        # Send notifications based on severity
        if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            if self.enable_email_alerts:
                await self._send_email_alert(alert)
            if self.enable_webhook_alerts:
                await self._send_webhook_alert(alert)

    async def _save_alert_to_file(self, alert: SecurityAlert) -> None:
        """Save alert to JSON log file.

        Args:
            alert: Security alert to save
        """
        try:
            alert_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "alert": alert.to_dict(),
            }

            # Append to log file
            with open(self.alert_log_path, "a") as f:
                f.write(json.dumps(alert_data) + "\n")

        except Exception as e:
            logger.error(f"Failed to save alert to file: {e}")

    async def _check_alert_patterns(self, alert: SecurityAlert) -> None:
        """Check for concerning patterns in alerts.

        Args:
            alert: Security alert to analyze
        """
        current_time = datetime.utcnow()
        time_window = timedelta(minutes=self.thresholds["time_window_minutes"])

        # Check for repeated failures from same user/IP
        if alert.alert_type == AlertType.AUTHENTICATION_FAILURE:
            if alert.user_id:
                self.failure_counts[alert.user_id] += 1

                if (
                    self.failure_counts[alert.user_id]
                    >= self.thresholds["failed_auth_threshold"]
                ):
                    await self.create_alert(
                        AlertType.REPEATED_FAILURES,
                        AlertSeverity.HIGH,
                        f"User {alert.user_id} has {self.failure_counts[alert.user_id]} "
                        f"failed authentication attempts",
                        {"failed_attempts": self.failure_counts[alert.user_id]},
                        user_id=alert.user_id,
                    )

        # Check for rate limit violation patterns
        elif alert.alert_type == AlertType.RATE_LIMIT_VIOLATION:
            if alert.user_id:
                violations = self.rate_limit_violations[alert.user_id]
                violations.append(current_time)

                # Remove old violations outside time window
                violations[:] = [
                    v for v in violations if current_time - v <= time_window
                ]

                if len(violations) >= self.thresholds["rate_limit_threshold"]:
                    await self.create_alert(
                        AlertType.ANOMALOUS_BEHAVIOR,
                        AlertSeverity.HIGH,
                        f"User {alert.user_id} has {len(violations)} rate limit "
                        f"violations in {self.thresholds['time_window_minutes']} minutes",
                        {"violation_count": len(violations)},
                        user_id=alert.user_id,
                    )

        # Check for suspicious input patterns
        elif alert.alert_type == AlertType.DANGEROUS_INPUT:
            if alert.user_id:
                patterns = self.suspicious_patterns[alert.user_id]
                patterns.append(current_time)

                # Remove old patterns outside time window
                patterns[:] = [p for p in patterns if current_time - p <= time_window]

                if len(patterns) >= self.thresholds["suspicious_pattern_threshold"]:
                    await self.create_alert(
                        AlertType.SECURITY_THRESHOLD_EXCEEDED,
                        AlertSeverity.CRITICAL,
                        f"User {alert.user_id} has {len(patterns)} suspicious input "
                        f"patterns in {self.thresholds['time_window_minutes']} minutes",
                        {"pattern_count": len(patterns)},
                        user_id=alert.user_id,
                    )

    async def _send_email_alert(self, alert: SecurityAlert) -> None:
        """Send email alert for high-severity incidents.

        Args:
            alert: Security alert to send
        """
        # TODO: Implement email alerting
        # This would integrate with SMTP server or email service
        logger.info(f"Would send email alert: {alert}")

    async def _send_webhook_alert(self, alert: SecurityAlert) -> None:
        """Send webhook alert for high-severity incidents.

        Args:
            alert: Security alert to send
        """
        # TODO: Implement webhook alerting
        # This would send HTTP POST to configured webhook URLs
        logger.info(f"Would send webhook alert: {alert}")

    def get_recent_alerts(
        self,
        minutes: int = 60,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
    ) -> list[SecurityAlert]:
        """Get recent alerts matching criteria.

        Args:
            minutes: Number of minutes to look back
            severity: Filter by severity level
            alert_type: Filter by alert type

        Returns:
            List of matching alerts
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        alerts = []
        for alert in self.alert_history:
            if alert.timestamp >= cutoff_time:
                if severity and alert.severity != severity:
                    continue
                if alert_type and alert.alert_type != alert_type:
                    continue
                alerts.append(alert)

        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)

    def get_alert_summary(self, minutes: int = 60) -> dict[str, Any]:
        """Get summary of recent alerts.

        Args:
            minutes: Number of minutes to look back

        Returns:
            Alert summary statistics
        """
        recent_alerts = self.get_recent_alerts(minutes)

        summary = {
            "time_window_minutes": minutes,
            "total_alerts": len(recent_alerts),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "affected_users": set(),
            "latest_alert": None,
        }

        for alert in recent_alerts:
            summary["by_severity"][alert.severity.value] += 1
            summary["by_type"][alert.alert_type.value] += 1
            if alert.user_id:
                summary["affected_users"].add(alert.user_id)

        if recent_alerts:
            summary["latest_alert"] = recent_alerts[0].to_dict()

        summary["by_severity"] = dict(summary["by_severity"])
        summary["by_type"] = dict(summary["by_type"])
        summary["affected_users"] = list(summary["affected_users"])

        return summary

    def cleanup_old_data(self, days: int = 7) -> None:
        """Clean up old tracking data.

        Args:
            days: Number of days to keep data
        """

        # Clean up failure counts (simplified - in production would need timestamps)
        # For now, just reset counts periodically
        if len(self.failure_counts) > 1000:
            self.failure_counts.clear()
            logger.info("Cleaned up old failure count data")

        # Clean up rate limit violations
        for user_id in list(self.rate_limit_violations.keys()):
            violations = self.rate_limit_violations[user_id]
            violations[:] = [
                v for v in violations if datetime.utcnow() - v <= timedelta(days=1)
            ]
            if not violations:
                del self.rate_limit_violations[user_id]

        # Clean up suspicious patterns
        for user_id in list(self.suspicious_patterns.keys()):
            patterns = self.suspicious_patterns[user_id]
            patterns[:] = [
                p for p in patterns if datetime.utcnow() - p <= timedelta(days=1)
            ]
            if not patterns:
                del self.suspicious_patterns[user_id]


# Global alerter instance
_global_alerter: SecurityAlerter | None = None


def get_alerter() -> SecurityAlerter:
    """Get global security alerter instance.

    Returns:
        Global SecurityAlerter instance
    """
    global _global_alerter
    if _global_alerter is None:
        _global_alerter = SecurityAlerter()
    return _global_alerter


async def alert_authentication_failure(
    user_id: str,
    reason: str,
    client_info: dict[str, Any] | None = None,
) -> None:
    """Create alert for authentication failure.

    Args:
        user_id: User ID that failed authentication
        reason: Reason for authentication failure
        client_info: Client information
    """
    alerter = get_alerter()
    await alerter.create_alert(
        AlertType.AUTHENTICATION_FAILURE,
        AlertSeverity.MEDIUM,
        f"Authentication failed for user {user_id}: {reason}",
        {"reason": reason},
        user_id=user_id,
        client_info=client_info,
    )


async def alert_rate_limit_violation(
    user_id: str,
    request_count: int,
    limit: int,
    client_info: dict[str, Any] | None = None,
) -> None:
    """Create alert for rate limit violation.

    Args:
        user_id: User ID that exceeded rate limit
        request_count: Number of requests made
        limit: Rate limit that was exceeded
        client_info: Client information
    """
    alerter = get_alerter()
    await alerter.create_alert(
        AlertType.RATE_LIMIT_VIOLATION,
        AlertSeverity.MEDIUM,
        f"Rate limit exceeded by user {user_id}: {request_count}/{limit}",
        {"request_count": request_count, "limit": limit},
        user_id=user_id,
        client_info=client_info,
    )


async def alert_dangerous_input(
    user_id: str | None,
    input_type: str,
    pattern_matched: str,
    client_info: dict[str, Any] | None = None,
) -> None:
    """Create alert for dangerous input detection.

    Args:
        user_id: User ID that submitted dangerous input
        input_type: Type of input (e.g., "note_content", "search_query")
        pattern_matched: The dangerous pattern that was matched
        client_info: Client information
    """
    alerter = get_alerter()
    await alerter.create_alert(
        AlertType.DANGEROUS_INPUT,
        AlertSeverity.HIGH,
        f"Dangerous input detected in {input_type}: {pattern_matched}",
        {"input_type": input_type, "pattern": pattern_matched},
        user_id=user_id,
        client_info=client_info,
    )


async def alert_suspicious_pattern(
    user_id: str | None,
    pattern_description: str,
    context: dict[str, Any],
    client_info: dict[str, Any] | None = None,
) -> None:
    """Create alert for suspicious behavior pattern.

    Args:
        user_id: User ID exhibiting suspicious behavior
        pattern_description: Description of the suspicious pattern
        context: Additional context about the pattern
        client_info: Client information
    """
    alerter = get_alerter()
    await alerter.create_alert(
        AlertType.SUSPICIOUS_PATTERN,
        AlertSeverity.MEDIUM,
        f"Suspicious behavior pattern detected: {pattern_description}",
        context,
        user_id=user_id,
        client_info=client_info,
    )
