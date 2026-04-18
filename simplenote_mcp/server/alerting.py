"""Security alerting system for suspicious activities.

This module provides real-time alerting for security events including failed authentication,
rate limit violations, dangerous input patterns, and other suspicious activities.
"""

import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Use standard logging to avoid circular import with .logging module
logger = logging.getLogger("simplenote_mcp.alerting")


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
        import os
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        # Get email configuration from environment
        smtp_host = os.environ.get("ALERT_SMTP_HOST")
        smtp_port = int(os.environ.get("ALERT_SMTP_PORT", "587"))
        smtp_user = os.environ.get("ALERT_SMTP_USER")
        smtp_password = os.environ.get("ALERT_SMTP_PASSWORD")
        alert_from = os.environ.get("ALERT_EMAIL_FROM")
        alert_to = os.environ.get("ALERT_EMAIL_TO")

        if not all([smtp_host, smtp_user, smtp_password, alert_from, alert_to]):
            logger.debug(
                "Email alerting not configured. Set ALERT_SMTP_HOST, ALERT_SMTP_USER, "
                "ALERT_SMTP_PASSWORD, ALERT_EMAIL_FROM, and ALERT_EMAIL_TO environment variables."
            )
            return

        try:
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"[{alert.severity.value}] Security Alert: {alert.alert_type.value}"
            )
            msg["From"] = alert_from
            msg["To"] = alert_to

            # Create plain text and HTML versions
            text_content = f"""
Security Alert

Severity: {alert.severity.value}
Type: {alert.alert_type.value}
Time: {alert.timestamp.isoformat()}
Alert ID: {alert.alert_id}

Message: {alert.message}

User ID: {alert.user_id or "N/A"}

Context:
{json.dumps(alert.context, indent=2)}

Client Info:
{json.dumps(alert.client_info, indent=2)}
"""

            html_content = f"""
<html>
<body>
<h2 style="color: {"red" if alert.severity == AlertSeverity.CRITICAL else "orange"};">
    [{alert.severity.value}] Security Alert
</h2>
<table border="1" cellpadding="5">
    <tr><td><strong>Type</strong></td><td>{alert.alert_type.value}</td></tr>
    <tr><td><strong>Time</strong></td><td>{alert.timestamp.isoformat()}</td></tr>
    <tr><td><strong>Alert ID</strong></td><td>{alert.alert_id}</td></tr>
    <tr><td><strong>Message</strong></td><td>{alert.message}</td></tr>
    <tr><td><strong>User ID</strong></td><td>{alert.user_id or "N/A"}</td></tr>
</table>
<h3>Context</h3>
<pre>{json.dumps(alert.context, indent=2)}</pre>
<h3>Client Info</h3>
<pre>{json.dumps(alert.client_info, indent=2)}</pre>
</body>
</html>
"""

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            use_ssl = os.environ.get("ALERT_SMTP_SSL", "false").lower() == "true"

            if use_ssl:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(alert_from, alert_to.split(","), msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(alert_from, alert_to.split(","), msg.as_string())

            logger.info(f"Email alert sent successfully for {alert.alert_id}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    async def _send_webhook_alert(self, alert: SecurityAlert) -> None:
        """Send webhook alert for high-severity incidents.

        Supports multiple webhook URLs and common formats (Slack, Discord, generic).

        Args:
            alert: Security alert to send
        """
        import os

        import aiohttp

        # Get webhook URLs from environment (comma-separated)
        webhook_urls = os.environ.get("ALERT_WEBHOOK_URLS", "")
        webhook_secret = os.environ.get("ALERT_WEBHOOK_SECRET", "")

        if not webhook_urls:
            logger.debug(
                "Webhook alerting not configured. Set ALERT_WEBHOOK_URLS environment variable."
            )
            return

        urls = [url.strip() for url in webhook_urls.split(",") if url.strip()]

        for url in urls:
            try:
                # Prepare payload based on URL pattern (Slack, Discord, or generic)
                payload = self._prepare_webhook_payload(alert, url)
                headers = {"Content-Type": "application/json"}

                # Add HMAC signature if secret is configured
                if webhook_secret:
                    import hashlib
                    import hmac

                    payload_bytes = json.dumps(payload).encode()
                    signature = hmac.new(
                        webhook_secret.encode(), payload_bytes, hashlib.sha256
                    ).hexdigest()
                    headers["X-Signature-256"] = f"sha256={signature}"

                async with (
                    aiohttp.ClientSession() as session,
                    session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response,
                ):
                    if response.status >= 400:
                        logger.error(
                            f"Webhook alert failed for {url}: HTTP {response.status}"
                        )
                    else:
                        logger.info(
                            f"Webhook alert sent successfully to {url} for {alert.alert_id}"
                        )

            except Exception as e:
                logger.error(f"Failed to send webhook alert to {url}: {e}")

    def _prepare_webhook_payload(
        self, alert: SecurityAlert, url: str
    ) -> dict[str, Any]:
        """Prepare webhook payload based on the target service.

        Args:
            alert: Security alert to send
            url: Webhook URL (used to detect service type)

        Returns:
            Formatted payload dictionary
        """
        # Detect service type from URL by checking the parsed hostname
        _hostname = urlparse(url).hostname or ""
        if _hostname == "hooks.slack.com" or _hostname.endswith(".slack.com"):
            # Slack format
            color = (
                "#FF0000"
                if alert.severity == AlertSeverity.CRITICAL
                else "#FFA500"
                if alert.severity == AlertSeverity.HIGH
                else "#FFFF00"
                if alert.severity == AlertSeverity.MEDIUM
                else "#00FF00"
            )
            return {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.severity.value}] {alert.alert_type.value}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Alert ID",
                                "value": alert.alert_id,
                                "short": True,
                            },
                            {
                                "title": "User ID",
                                "value": alert.user_id or "N/A",
                                "short": True,
                            },
                            {
                                "title": "Time",
                                "value": alert.timestamp.isoformat(),
                                "short": True,
                            },
                        ],
                        "footer": "Simplenote MCP Server Security",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ]
            }

        elif (
            _hostname.endswith(".discord.com")
            or _hostname == "discord.com"
            or _hostname.endswith(".discordapp.com")
            or _hostname == "discordapp.com"
        ):
            # Discord format
            color = (
                0xFF0000
                if alert.severity == AlertSeverity.CRITICAL
                else 0xFFA500
                if alert.severity == AlertSeverity.HIGH
                else 0xFFFF00
                if alert.severity == AlertSeverity.MEDIUM
                else 0x00FF00
            )
            return {
                "embeds": [
                    {
                        "title": f"[{alert.severity.value}] {alert.alert_type.value}",
                        "description": alert.message,
                        "color": color,
                        "fields": [
                            {
                                "name": "Alert ID",
                                "value": alert.alert_id,
                                "inline": True,
                            },
                            {
                                "name": "User ID",
                                "value": alert.user_id or "N/A",
                                "inline": True,
                            },
                            {
                                "name": "Time",
                                "value": alert.timestamp.isoformat(),
                                "inline": True,
                            },
                        ],
                        "footer": {"text": "Simplenote MCP Server Security"},
                        "timestamp": alert.timestamp.isoformat(),
                    }
                ]
            }

        else:
            # Generic JSON format
            return {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": alert.message,
                "context": alert.context,
                "user_id": alert.user_id,
                "client_info": alert.client_info,
                "timestamp": alert.timestamp.isoformat(),
                "source": "simplenote-mcp-server",
            }

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
