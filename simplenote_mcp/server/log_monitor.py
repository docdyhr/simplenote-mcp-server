"""Log pattern monitoring and alerting for suspicious activities.

This module provides real-time monitoring of log entries to detect suspicious patterns
and automatically trigger security alerts. It acts as a bridge between the logging
system and the alerting system.
"""

import asyncio
import json
import logging
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .alerting import AlertSeverity, alert_suspicious_pattern

# Use standard logging to avoid circular import with .logging module
logger = logging.getLogger("simplenote_mcp.log_monitor")


class SuspiciousPattern:
    """Defines a suspicious pattern to monitor in logs."""

    def __init__(
        self,
        name: str,
        pattern: str,
        severity: AlertSeverity,
        description: str,
        threshold: int = 1,
        time_window_minutes: int = 5,
        field_filters: dict[str, Any] | None = None,
    ):
        """Initialize suspicious pattern.

        Args:
            name: Pattern name/identifier
            pattern: Regex pattern to match against log messages
            severity: Alert severity level for this pattern
            description: Human-readable description
            threshold: Number of matches needed to trigger alert
            time_window_minutes: Time window for threshold counting
            field_filters: Additional field filters (e.g., {"level": "ERROR"})
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.severity = severity
        self.description = description
        self.threshold = threshold
        self.time_window_minutes = time_window_minutes
        self.field_filters = field_filters or {}

        # Tracking data
        self.matches: deque = deque(maxlen=1000)
        self.last_alert_time: datetime | None = None

    def matches_filters(self, log_entry: dict[str, Any]) -> bool:
        """Check if log entry matches additional field filters.

        Args:
            log_entry: Log entry data

        Returns:
            True if entry matches all field filters
        """
        for field, expected_value in self.field_filters.items():
            if field not in log_entry:
                return False
            if log_entry[field] != expected_value:
                return False
        return True

    def check_match(self, log_entry: dict[str, Any]) -> bool:
        """Check if log entry matches this pattern.

        Args:
            log_entry: Log entry data

        Returns:
            True if pattern matches
        """
        # Check field filters first
        if not self.matches_filters(log_entry):
            return False

        # Check pattern match in message
        message = log_entry.get("message", "")
        if self.pattern.search(message):
            self.matches.append(datetime.utcnow())
            return True

        return False

    def should_trigger_alert(self) -> bool:
        """Check if pattern should trigger an alert based on threshold.

        Returns:
            True if alert should be triggered
        """
        now = datetime.utcnow()
        time_window = timedelta(minutes=self.time_window_minutes)

        # Clean old matches
        cutoff_time = now - time_window
        while self.matches and self.matches[0] < cutoff_time:
            self.matches.popleft()

        # Check threshold
        recent_matches = len(self.matches)
        if recent_matches >= self.threshold:
            # Check if we recently alerted (avoid spam)
            if self.last_alert_time is None or now - self.last_alert_time > time_window:
                self.last_alert_time = now
                return True

        return False


class LogPatternMonitor:
    """Monitors log entries for suspicious patterns and triggers alerts."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize log pattern monitor.

        Args:
            config: Monitor configuration
        """
        self.config = config or {}
        self.patterns: list[SuspiciousPattern] = []
        self.is_running = False
        self.monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Statistics
        self.stats = {
            "logs_processed": 0,
            "patterns_matched": 0,
            "alerts_triggered": 0,
            "start_time": None,
        }

        # Initialize default patterns
        self._initialize_default_patterns()

        logger.info(
            "Log pattern monitor initialized",
            extra={
                "pattern_count": len(self.patterns),
                "config": self.config,
            },
        )

    def _initialize_default_patterns(self) -> None:
        """Initialize default suspicious patterns."""
        default_patterns = [
            # Authentication failures
            SuspiciousPattern(
                name="repeated_auth_failures",
                pattern=r"authentication.*(fail|error|invalid|denied)",
                severity=AlertSeverity.HIGH,
                description="Repeated authentication failures detected",
                threshold=5,
                time_window_minutes=5,
            ),
            # SQL injection attempts
            SuspiciousPattern(
                name="sql_injection_attempt",
                pattern=r"(union\s+select|drop\s+table|insert\s+into|delete\s+from|exec\s*\(|script\s*>)",
                severity=AlertSeverity.CRITICAL,
                description="Potential SQL injection attempt detected",
                threshold=1,
                time_window_minutes=1,
            ),
            # XSS attempts
            SuspiciousPattern(
                name="xss_attempt",
                pattern=r"(<script|javascript:|onclick=|onerror=|onload=)",
                severity=AlertSeverity.HIGH,
                description="Potential XSS attack attempt detected",
                threshold=1,
                time_window_minutes=1,
            ),
            # Path traversal attempts
            SuspiciousPattern(
                name="path_traversal_attempt",
                pattern=r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e\\)",
                severity=AlertSeverity.HIGH,
                description="Path traversal attempt detected",
                threshold=1,
                time_window_minutes=1,
            ),
            # Rate limit violations
            SuspiciousPattern(
                name="rate_limit_exceeded",
                pattern=r"rate.limit.*(exceed|violation|blocked)",
                severity=AlertSeverity.MEDIUM,
                description="Rate limiting violations detected",
                threshold=3,
                time_window_minutes=5,
            ),
            # Unusual error patterns
            SuspiciousPattern(
                name="multiple_errors",
                pattern=r"(error|exception|failure|crash)",
                severity=AlertSeverity.MEDIUM,
                description="High frequency of errors detected",
                threshold=10,
                time_window_minutes=5,
                field_filters={"level": "ERROR"},
            ),
            # Security-related warnings (WARNING+ only to avoid matching routine
            # INFO messages like "Security alerter initialized")
            SuspiciousPattern(
                name="security_warnings",
                pattern=r"(security|suspicious|malicious|attack|breach|unauthorized)",
                severity=AlertSeverity.HIGH,
                description="Security-related warnings detected",
                threshold=3,
                time_window_minutes=10,
                field_filters={"level": "WARNING"},
            ),
            # Unusual resource access patterns
            SuspiciousPattern(
                name="resource_access_anomaly",
                pattern=r"(access.*denied|permission.*denied|unauthorized.*access)",
                severity=AlertSeverity.MEDIUM,
                description="Unusual resource access patterns detected",
                threshold=5,
                time_window_minutes=5,
            ),
            # Large data operations (potential data exfiltration)
            SuspiciousPattern(
                name="large_data_operation",
                pattern=r"(export|download|fetch).*large|processing.*\d{4,}.*items",
                severity=AlertSeverity.MEDIUM,
                description="Large data operation detected",
                threshold=2,
                time_window_minutes=10,
            ),
            # Suspicious user agent patterns
            SuspiciousPattern(
                name="suspicious_user_agent",
                pattern=r"(bot|crawler|scraper|scanner|exploit|attack)",
                severity=AlertSeverity.LOW,
                description="Suspicious user agent detected",
                threshold=3,
                time_window_minutes=15,
            ),
        ]

        self.patterns.extend(default_patterns)

    def add_pattern(self, pattern: SuspiciousPattern) -> None:
        """Add a new pattern to monitor.

        Args:
            pattern: Suspicious pattern to add
        """
        self.patterns.append(pattern)
        logger.info(
            f"Added suspicious pattern: {pattern.name}",
            extra={"pattern_name": pattern.name, "description": pattern.description},
        )

    def remove_pattern(self, name: str) -> bool:
        """Remove a pattern by name.

        Args:
            name: Pattern name to remove

        Returns:
            True if pattern was removed, False if not found
        """
        for i, pattern in enumerate(self.patterns):
            if pattern.name == name:
                del self.patterns[i]
                logger.info(f"Removed suspicious pattern: {name}")
                return True
        return False

    async def process_log_entry(self, log_entry: dict[str, Any]) -> None:
        """Process a single log entry for suspicious patterns.

        Args:
            log_entry: Log entry data to analyze
        """
        # Skip own-logger entries to prevent a feedback loop: the debug message
        # "Pattern matched: security_warnings" contains "security", which
        # matches the security_warnings pattern, which logs again, and so on.
        if log_entry.get("logger", "").startswith("simplenote_mcp.log_monitor"):
            return

        self.stats["logs_processed"] += 1

        # Check each pattern
        for pattern in self.patterns:
            if pattern.check_match(log_entry):
                self.stats["patterns_matched"] += 1

                # Check if we should trigger an alert
                if pattern.should_trigger_alert():
                    await self._trigger_pattern_alert(pattern, log_entry)

    async def _trigger_pattern_alert(
        self, pattern: SuspiciousPattern, triggering_log: dict[str, Any]
    ) -> None:
        """Trigger an alert for a suspicious pattern.

        Args:
            pattern: Pattern that triggered the alert
            triggering_log: Log entry that triggered the pattern
        """
        self.stats["alerts_triggered"] += 1

        # Extract user info if available
        user_id = triggering_log.get("user_id")
        if not user_id and "extra" in triggering_log:
            user_id = triggering_log["extra"].get("user_id")

        # Build context
        context = {
            "pattern_name": pattern.name,
            "pattern_description": pattern.description,
            "match_count": len(pattern.matches),
            "time_window_minutes": pattern.time_window_minutes,
            "threshold": pattern.threshold,
            "triggering_log": {
                "timestamp": triggering_log.get("timestamp"),
                "level": triggering_log.get("level"),
                "message": triggering_log.get("message", "")[:200],  # Truncate
                "logger": triggering_log.get("logger"),
            },
            "recent_match_times": [
                match.isoformat() for match in list(pattern.matches)[-5:]
            ],
        }

        # Add extra context if available
        if "extra" in triggering_log and triggering_log["extra"]:
            context["log_context"] = triggering_log["extra"]

        # Create alert
        await alert_suspicious_pattern(
            user_id=user_id,
            pattern_description=f"{pattern.name}: {pattern.description}",
            context=context,
        )

        logger.warning(
            f"Suspicious pattern alert triggered: {pattern.name}",
            extra={
                "pattern_name": pattern.name,
                "severity": pattern.severity.value,
                "user_id": user_id,
                "match_count": len(pattern.matches),
            },
        )

    def start_monitoring(self, log_sources: list[Path] | None = None) -> None:
        """Start monitoring log files for suspicious patterns.

        Args:
            log_sources: List of log file paths to monitor
        """
        if self.is_running:
            logger.warning("Log pattern monitor is already running")
            return

        self.is_running = True
        self.stats["start_time"] = datetime.utcnow()
        self._stop_event.clear()

        # Default log sources
        if log_sources is None:
            log_sources = [
                Path(__file__).parent.parent / "logs" / "server.log",
                Path(__file__).parent.parent / "logs" / "security_alerts.json",
            ]

        self.monitor_thread = threading.Thread(
            target=self._monitor_logs, args=(log_sources,), daemon=True
        )
        self.monitor_thread.start()

        logger.info(
            "Started log pattern monitoring",
            extra={"log_sources": [str(path) for path in log_sources]},
        )

    def stop_monitoring(self) -> None:
        """Stop monitoring log files."""
        if not self.is_running:
            return

        self._stop_event.set()
        self.is_running = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)

        logger.info("Stopped log pattern monitoring")

    def _monitor_logs(self, log_sources: list[Path]) -> None:
        """Monitor log files in a separate thread.

        Args:
            log_sources: List of log file paths to monitor
        """
        file_positions = dict.fromkeys(log_sources, 0)

        while not self._stop_event.is_set():
            try:
                for log_file in log_sources:
                    if log_file.exists():
                        self._process_log_file(log_file, file_positions)

                # Sleep between checks
                time.sleep(1.0)

            except Exception as e:
                logger.error(
                    f"Error in log monitoring: {e}",
                    extra={"exception": str(e)},
                )
                time.sleep(5.0)  # Wait longer on error

    def _process_log_file(
        self, log_file: Path, file_positions: dict[Path, int]
    ) -> None:
        """Process new lines in a log file.

        Args:
            log_file: Path to log file
            file_positions: Dictionary tracking file positions
        """
        try:
            current_size = log_file.stat().st_size
            last_position = file_positions[log_file]

            if current_size < last_position:
                # File was truncated/rotated
                file_positions[log_file] = 0
                last_position = 0

            if current_size > last_position:
                with open(log_file, encoding="utf-8", errors="ignore") as f:
                    f.seek(last_position)
                    new_content = f.read()
                    file_positions[log_file] = f.tell()

                    # Process new lines
                    lines = new_content.strip().split("\n")
                    for line in lines:
                        if line.strip():
                            try:
                                # Try to run in existing event loop if available
                                asyncio.get_running_loop()  # raises RuntimeError if none
                                task = asyncio.create_task(self._process_log_line(line))
                                # Store task reference to prevent warning about unawaited coroutine
                                # The task will run in background and we don't need to await it
                                task.add_done_callback(lambda t: None)
                            except RuntimeError:
                                # No running event loop in this thread — run
                                # the coroutine synchronously on a fresh loop.
                                # (run_coroutine_threadsafe requires a *running*
                                # loop; scheduling onto a stopped loop leaves the
                                # coroutine unawaited and triggers a
                                # RuntimeWarning in Python 3.13+.)
                                loop = self._get_or_create_event_loop()
                                try:
                                    loop.run_until_complete(
                                        self._process_log_line(line)
                                    )
                                except Exception as exc:
                                    logger.debug(
                                        f"Log line processing error in background thread: {exc}"
                                    )

        except Exception as e:
            logger.error(
                f"Error processing log file {log_file}: {e}",
                extra={"log_file": str(log_file), "exception": str(e)},
            )

    def _has_event_loop(self) -> bool:
        """Check if there's an active event loop."""
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def _get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create an event loop for the current thread."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    async def _process_log_line(self, line: str) -> None:
        """Process a single log line.

        Args:
            line: Log line to process
        """
        try:
            # Try to parse as JSON first
            if line.startswith("{"):
                log_entry = json.loads(line)
            else:
                # Simple text log format
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": line,
                    "level": "INFO",
                }

            await self.process_log_entry(log_entry)

        except json.JSONDecodeError:
            # Fallback for non-JSON logs
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "message": line,
                "level": "INFO",
            }
            await self.process_log_entry(log_entry)
        except Exception as e:
            logger.error(
                f"Error processing log line: {e}",
                extra={"line": line[:100], "exception": str(e)},
            )

    def get_pattern_stats(self) -> dict[str, Any]:
        """Get statistics for all patterns.

        Returns:
            Dictionary with pattern statistics
        """
        pattern_stats = {}
        for pattern in self.patterns:
            pattern_stats[pattern.name] = {
                "description": pattern.description,
                "severity": pattern.severity.value,
                "threshold": pattern.threshold,
                "time_window_minutes": pattern.time_window_minutes,
                "total_matches": len(pattern.matches),
                "recent_matches": len(
                    [
                        m
                        for m in pattern.matches
                        if datetime.utcnow() - m
                        <= timedelta(minutes=pattern.time_window_minutes)
                    ]
                ),
                "last_alert_time": (
                    pattern.last_alert_time.isoformat()
                    if pattern.last_alert_time
                    else None
                ),
            }

        return {
            "monitor_stats": self.stats.copy(),
            "patterns": pattern_stats,
        }

    def cleanup_old_data(self) -> None:
        """Clean up old pattern match data."""
        cleaned_patterns = 0
        for pattern in self.patterns:
            original_count = len(pattern.matches)
            # Keep only matches from the last hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            pattern.matches = deque(
                [m for m in pattern.matches if m >= cutoff_time],
                maxlen=pattern.matches.maxlen,
            )
            if len(pattern.matches) < original_count:
                cleaned_patterns += 1

        if cleaned_patterns > 0:
            logger.info(f"Cleaned up old match data for {cleaned_patterns} patterns")


# Global monitor instance
_global_monitor: LogPatternMonitor | None = None


def get_log_monitor() -> LogPatternMonitor:
    """Get global log pattern monitor instance.

    Returns:
        Global LogPatternMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = LogPatternMonitor()
    return _global_monitor


def start_log_monitoring(log_sources: list[Path] | None = None) -> None:
    """Start global log pattern monitoring.

    Args:
        log_sources: List of log file paths to monitor
    """
    monitor = get_log_monitor()
    monitor.start_monitoring(log_sources)


def stop_log_monitoring() -> None:
    """Stop global log pattern monitoring."""
    monitor = get_log_monitor()
    monitor.stop_monitoring()


async def process_log_for_patterns(log_entry: dict[str, Any]) -> None:
    """Process a log entry for suspicious patterns.

    This function can be called directly from logging code to
    process entries in real-time.

    Args:
        log_entry: Log entry data to analyze
    """
    monitor = get_log_monitor()
    await monitor.process_log_entry(log_entry)


def reset_log_monitor() -> None:
    """Reset global log pattern monitor for test isolation.

    This function clears the global monitor instance and its state,
    ensuring clean state between test runs.
    """
    global _global_monitor
    if _global_monitor is not None:
        _global_monitor.stop_monitoring()
        _global_monitor = None
