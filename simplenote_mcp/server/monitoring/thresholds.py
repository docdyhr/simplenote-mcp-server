"""Performance regression alert threshold definitions and monitoring.

This module defines performance thresholds and implements regression detection
for the Simplenote MCP Server. It monitors key metrics and triggers alerts
when performance degrades beyond acceptable levels.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..alerting import AlertSeverity, AlertType, get_alerter
from ..logging import get_logger
from .metrics import get_metrics

logger = get_logger("monitoring.thresholds")


class MetricType(Enum):
    """Types of metrics for threshold monitoring."""

    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    RESOURCE_USAGE = "resource_usage"
    MEMORY_USAGE = "memory_usage"
    API_SUCCESS_RATE = "api_success_rate"


class ThresholdOperator(Enum):
    """Operators for threshold comparisons."""

    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="


@dataclass
class PerformanceThreshold:
    """Defines a performance threshold for monitoring."""

    name: str
    metric_type: MetricType
    metric_path: str  # JSON path to extract from metrics, e.g., "api.response_times.create_note.p95_time"
    operator: ThresholdOperator
    warning_value: float
    critical_value: float
    unit: str = ""
    description: str = ""
    enabled: bool = True

    # Regression detection settings
    baseline_window_minutes: int = 60  # How far back to look for baseline
    regression_multiplier: float = 1.5  # 50% increase triggers regression alert
    consecutive_violations: int = 3  # Number of consecutive violations needed

    # State tracking
    last_check_time: float = field(default_factory=time.time)
    consecutive_warning_count: int = 0
    consecutive_critical_count: int = 0
    baseline_value: float | None = None
    violation_history: list[tuple[float, float]] = field(default_factory=list)

    def evaluate(self, current_value: float) -> tuple[AlertSeverity | None, str]:
        """Evaluate threshold against current value.

        Args:
            current_value: Current metric value to evaluate

        Returns:
            Tuple of (alert_severity, message) or (None, "") if no violation
        """
        if not self.enabled:
            return None, ""

        # Check critical threshold first
        if self._check_threshold(current_value, self.critical_value):
            self.consecutive_critical_count += 1
            self.consecutive_warning_count = 0

            if self.consecutive_critical_count >= self.consecutive_violations:
                return AlertSeverity.CRITICAL, (
                    f"{self.name}: {current_value:.3f}{self.unit} "
                    f"{self.operator.value} {self.critical_value:.3f}{self.unit} "
                    f"({self.consecutive_critical_count} consecutive violations)"
                )

        # Check warning threshold
        elif self._check_threshold(current_value, self.warning_value):
            self.consecutive_warning_count += 1
            self.consecutive_critical_count = 0

            if self.consecutive_warning_count >= self.consecutive_violations:
                return AlertSeverity.MEDIUM, (
                    f"{self.name}: {current_value:.3f}{self.unit} "
                    f"{self.operator.value} {self.warning_value:.3f}{self.unit} "
                    f"({self.consecutive_warning_count} consecutive violations)"
                )

        else:
            # Reset counters if within acceptable range
            self.consecutive_warning_count = 0
            self.consecutive_critical_count = 0

        return None, ""

    def check_regression(
        self, current_value: float, baseline: float
    ) -> tuple[AlertSeverity | None, str]:
        """Check for performance regression against baseline.

        Args:
            current_value: Current metric value
            baseline: Baseline value to compare against

        Returns:
            Tuple of (alert_severity, message) or (None, "") if no regression
        """
        if not self.enabled or baseline <= 0:
            return None, ""

        # Calculate regression based on metric type
        if self.metric_type in [
            MetricType.RESPONSE_TIME,
            MetricType.ERROR_RATE,
            MetricType.MEMORY_USAGE,
            MetricType.RESOURCE_USAGE,
        ]:
            # For these metrics, higher is worse
            regression_ratio = current_value / baseline
            if regression_ratio >= self.regression_multiplier:
                severity = (
                    AlertSeverity.HIGH
                    if regression_ratio >= 2.0
                    else AlertSeverity.MEDIUM
                )
                return severity, (
                    f"Performance regression detected for {self.name}: "
                    f"{current_value:.3f}{self.unit} vs baseline {baseline:.3f}{self.unit} "
                    f"({regression_ratio:.1f}x increase)"
                )

        else:
            # For throughput, hit rate, success rate - lower is worse
            regression_ratio = (
                baseline / current_value if current_value > 0 else float("inf")
            )
            if regression_ratio >= self.regression_multiplier:
                severity = (
                    AlertSeverity.HIGH
                    if regression_ratio >= 2.0
                    else AlertSeverity.MEDIUM
                )
                return severity, (
                    f"Performance regression detected for {self.name}: "
                    f"{current_value:.3f}{self.unit} vs baseline {baseline:.3f}{self.unit} "
                    f"({regression_ratio:.1f}x decrease)"
                )

        return None, ""

    def _check_threshold(self, current_value: float, threshold_value: float) -> bool:
        """Check if current value violates threshold.

        Args:
            current_value: Value to check
            threshold_value: Threshold to compare against

        Returns:
            True if threshold is violated
        """
        if self.operator == ThresholdOperator.GREATER_THAN:
            return current_value > threshold_value
        elif self.operator == ThresholdOperator.LESS_THAN:
            return current_value < threshold_value
        elif self.operator == ThresholdOperator.GREATER_EQUAL:
            return current_value >= threshold_value
        elif self.operator == ThresholdOperator.LESS_EQUAL:
            return current_value <= threshold_value
        elif self.operator == ThresholdOperator.EQUAL:
            return abs(current_value - threshold_value) < 0.001
        elif self.operator == ThresholdOperator.NOT_EQUAL:
            return abs(current_value - threshold_value) >= 0.001
        return False


# Default performance thresholds based on analysis of existing metrics and health checks
DEFAULT_THRESHOLDS = [
    # API Response Time Thresholds
    PerformanceThreshold(
        name="API P95 Response Time",
        metric_type=MetricType.RESPONSE_TIME,
        metric_path="api.response_times.*.p95_time",  # Aggregate across all endpoints
        operator=ThresholdOperator.GREATER_THAN,
        warning_value=1.0,  # 1 second
        critical_value=3.0,  # 3 seconds
        unit="s",
        description="95th percentile API response time",
        regression_multiplier=1.3,  # 30% increase triggers regression
        consecutive_violations=2,
    ),
    PerformanceThreshold(
        name="API P99 Response Time",
        metric_type=MetricType.RESPONSE_TIME,
        metric_path="api.response_times.*.p99_time",
        operator=ThresholdOperator.GREATER_THAN,
        warning_value=2.0,  # 2 seconds
        critical_value=5.0,  # 5 seconds
        unit="s",
        description="99th percentile API response time",
        regression_multiplier=1.5,
        consecutive_violations=2,
    ),
    # Error Rate Thresholds
    PerformanceThreshold(
        name="API Error Rate",
        metric_type=MetricType.ERROR_RATE,
        metric_path="api.success_rate",
        operator=ThresholdOperator.LESS_THAN,
        warning_value=95.0,  # 95% success rate (5% error rate)
        critical_value=90.0,  # 90% success rate (10% error rate)
        unit="%",
        description="API success rate percentage",
        regression_multiplier=1.2,  # 20% decrease triggers regression
        consecutive_violations=3,
    ),
    # Cache Performance Thresholds (based on existing health check)
    PerformanceThreshold(
        name="Cache Hit Rate",
        metric_type=MetricType.CACHE_HIT_RATE,
        metric_path="cache.hit_rate",
        operator=ThresholdOperator.LESS_THAN,
        warning_value=50.0,  # Based on existing health check threshold
        critical_value=25.0,  # Severely degraded cache performance
        unit="%",
        description="Cache hit rate percentage",
        regression_multiplier=1.3,
        consecutive_violations=3,
    ),
    PerformanceThreshold(
        name="Cache Efficacy Score",
        metric_type=MetricType.CACHE_HIT_RATE,
        metric_path="cache.efficacy_score",
        operator=ThresholdOperator.LESS_THAN,
        warning_value=60.0,  # Good cache performance
        critical_value=30.0,  # Poor cache performance
        unit="",
        description="Overall cache efficacy score (0-100)",
        regression_multiplier=1.4,
        consecutive_violations=4,
    ),
    # Resource Usage Thresholds
    PerformanceThreshold(
        name="CPU Usage",
        metric_type=MetricType.RESOURCE_USAGE,
        metric_path="resources.cpu.current",
        operator=ThresholdOperator.GREATER_THAN,
        warning_value=80.0,  # 80% CPU usage
        critical_value=95.0,  # 95% CPU usage
        unit="%",
        description="Current CPU usage percentage",
        regression_multiplier=1.25,
        consecutive_violations=4,
    ),
    PerformanceThreshold(
        name="Memory Usage",
        metric_type=MetricType.MEMORY_USAGE,
        metric_path="resources.memory.current",
        operator=ThresholdOperator.GREATER_THAN,
        warning_value=80.0,  # 80% memory usage
        critical_value=90.0,  # 90% memory usage
        unit="%",
        description="Current memory usage percentage",
        regression_multiplier=1.2,
        consecutive_violations=5,
    ),
    # Throughput Thresholds
    PerformanceThreshold(
        name="API Request Rate",
        metric_type=MetricType.THROUGHPUT,
        metric_path="api.calls.rate_5min",
        operator=ThresholdOperator.LESS_THAN,
        warning_value=1.0,  # Less than 1 request per minute might indicate issues
        critical_value=0.1,  # Very low throughput
        unit=" req/min",
        description="API request rate over 5 minutes",
        enabled=False,  # Disabled by default - depends on usage patterns
        regression_multiplier=2.0,
        consecutive_violations=10,  # Longer window for throughput changes
    ),
    # Tool Performance Thresholds
    PerformanceThreshold(
        name="Tool Execution Time P95",
        metric_type=MetricType.RESPONSE_TIME,
        metric_path="tools.execution_times.*.p95_time",
        operator=ThresholdOperator.GREATER_THAN,
        warning_value=2.0,  # 2 seconds for tool execution
        critical_value=5.0,  # 5 seconds
        unit="s",
        description="95th percentile tool execution time",
        regression_multiplier=1.4,
        consecutive_violations=2,
    ),
]


class PerformanceThresholdMonitor:
    """Monitors performance metrics against defined thresholds."""

    def __init__(self, thresholds: list[PerformanceThreshold] = None):
        """Initialize threshold monitor.

        Args:
            thresholds: List of thresholds to monitor, uses defaults if None
        """
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self.baseline_history: dict[
            str, list[tuple[float, float]]
        ] = {}  # metric_name -> [(timestamp, value), ...]
        self.last_alert_time: dict[str, float] = {}  # Prevent alert spam
        self.alert_cooldown_seconds = 300  # 5 minutes between same alerts

        logger.info(
            f"Performance threshold monitor initialized with {len(self.thresholds)} thresholds"
        )

    def check_all_thresholds(self) -> list[dict[str, Any]]:
        """Check all thresholds against current metrics.

        Returns:
            List of alert dictionaries for violations found
        """
        try:
            metrics = get_metrics()
            alerts = []

            for threshold in self.thresholds:
                if not threshold.enabled:
                    continue

                # Extract metric value using JSON path
                current_value = self._extract_metric_value(
                    metrics, threshold.metric_path
                )
                if current_value is None:
                    logger.debug(
                        f"Could not extract metric value for {threshold.name} at path {threshold.metric_path}"
                    )
                    continue

                # Update baseline history
                self._update_baseline_history(threshold.name, current_value)

                # Check threshold violation
                severity, message = threshold.evaluate(current_value)
                if severity and self._should_alert(threshold.name):
                    alerts.append(
                        {
                            "threshold_name": threshold.name,
                            "severity": severity,
                            "message": message,
                            "current_value": current_value,
                            "metric_type": threshold.metric_type.value,
                            "metric_path": threshold.metric_path,
                        }
                    )

                # Check for regression against baseline
                baseline = self._get_baseline_value(
                    threshold.name, threshold.baseline_window_minutes
                )
                if baseline is not None:
                    regression_severity, regression_message = (
                        threshold.check_regression(current_value, baseline)
                    )
                    if regression_severity and self._should_alert(
                        f"{threshold.name}_regression"
                    ):
                        alerts.append(
                            {
                                "threshold_name": f"{threshold.name} (Regression)",
                                "severity": regression_severity,
                                "message": regression_message,
                                "current_value": current_value,
                                "baseline_value": baseline,
                                "metric_type": threshold.metric_type.value,
                                "metric_path": threshold.metric_path,
                            }
                        )

            return alerts

        except Exception as e:
            logger.error(f"Error checking performance thresholds: {e}")
            return []

    async def trigger_alerts_for_violations(
        self, violations: list[dict[str, Any]]
    ) -> None:
        """Trigger alerts for threshold violations.

        Args:
            violations: List of violation dictionaries from check_all_thresholds
        """
        try:
            alerter = get_alerter()

            for violation in violations:
                await alerter.create_alert(
                    AlertType.SECURITY_THRESHOLD_EXCEEDED,  # Reusing existing alert type
                    violation["severity"],
                    violation["message"],
                    {
                        "threshold_name": violation["threshold_name"],
                        "current_value": violation["current_value"],
                        "metric_type": violation["metric_type"],
                        "metric_path": violation["metric_path"],
                        "baseline_value": violation.get("baseline_value"),
                    },
                )

                # Update last alert time to prevent spam
                self.last_alert_time[violation["threshold_name"]] = time.time()

        except Exception as e:
            logger.error(f"Error triggering threshold alerts: {e}")

    def _extract_metric_value(
        self, metrics: dict[str, Any], metric_path: str
    ) -> float | None:
        """Extract metric value using JSON path notation.

        Args:
            metrics: Metrics dictionary
            metric_path: Dot-notation path to extract value, supports * for aggregation

        Returns:
            Extracted metric value or None if not found
        """
        try:
            # Handle wildcard aggregation (e.g., "api.response_times.*.p95_time")
            if "*" in metric_path:
                return self._extract_aggregated_value(metrics, metric_path)

            # Simple path traversal
            parts = metric_path.split(".")
            current = metrics

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

            return float(current) if isinstance(current, int | float) else None

        except (ValueError, TypeError, KeyError):
            return None

    def _extract_aggregated_value(
        self, metrics: dict[str, Any], metric_path: str
    ) -> float | None:
        """Extract aggregated value for wildcard paths.

        Args:
            metrics: Metrics dictionary
            metric_path: Path with * wildcard

        Returns:
            Aggregated value (max for response times, min for hit rates, avg for others)
        """
        try:
            parts = metric_path.split(".")
            wildcard_index = parts.index("*")

            # Navigate to parent of wildcard
            current = metrics
            for part in parts[:wildcard_index]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

            if not isinstance(current, dict):
                return None

            # Extract values from all keys at wildcard level
            values = []
            remaining_path = parts[wildcard_index + 1 :]

            for key in current:
                temp = current[key]
                for part in remaining_path:
                    if isinstance(temp, dict) and part in temp:
                        temp = temp[part]
                    else:
                        temp = None
                        break

                if temp is not None and isinstance(temp, int | float):
                    values.append(float(temp))

            if not values:
                return None

            # Choose aggregation method based on metric type
            if (
                "response_time" in metric_path.lower()
                or "execution_time" in metric_path.lower()
            ):
                return max(values)  # Worst case for timing metrics
            elif (
                "hit_rate" in metric_path.lower()
                or "success_rate" in metric_path.lower()
            ):
                return min(values)  # Worst case for rate metrics
            else:
                return sum(values) / len(values)  # Average for others

        except (ValueError, TypeError, IndexError):
            return None

    def _update_baseline_history(self, threshold_name: str, value: float) -> None:
        """Update baseline history for regression detection.

        Args:
            threshold_name: Name of threshold
            value: Current metric value
        """
        current_time = time.time()

        if threshold_name not in self.baseline_history:
            self.baseline_history[threshold_name] = []

        history = self.baseline_history[threshold_name]
        history.append((current_time, value))

        # Keep only last 24 hours of history
        cutoff_time = current_time - (24 * 60 * 60)
        self.baseline_history[threshold_name] = [
            (ts, val) for ts, val in history if ts > cutoff_time
        ]

    def _get_baseline_value(
        self, threshold_name: str, window_minutes: int
    ) -> float | None:
        """Get baseline value for regression comparison.

        Args:
            threshold_name: Name of threshold
            window_minutes: How many minutes back to look for baseline

        Returns:
            Baseline value or None if insufficient history
        """
        if threshold_name not in self.baseline_history:
            return None

        current_time = time.time()
        baseline_start = current_time - (window_minutes * 60)
        baseline_end = current_time - (
            window_minutes * 60 * 0.5
        )  # Look at first half of window

        baseline_values = [
            val
            for ts, val in self.baseline_history[threshold_name]
            if baseline_start <= ts <= baseline_end
        ]

        if len(baseline_values) < 3:  # Need at least 3 data points
            return None

        # Use median for stability
        baseline_values.sort()
        mid = len(baseline_values) // 2
        return baseline_values[mid]

    def _should_alert(self, alert_key: str) -> bool:
        """Check if we should alert based on cooldown period.

        Args:
            alert_key: Key for alert cooldown tracking

        Returns:
            True if alert should be sent
        """
        current_time = time.time()
        last_alert = self.last_alert_time.get(alert_key, 0)

        return current_time - last_alert >= self.alert_cooldown_seconds

    def get_threshold_status(self) -> dict[str, Any]:
        """Get status summary of all thresholds.

        Returns:
            Dictionary with threshold status information
        """
        try:
            metrics = get_metrics()
            status = {
                "total_thresholds": len(self.thresholds),
                "enabled_thresholds": len([t for t in self.thresholds if t.enabled]),
                "thresholds": [],
            }

            for threshold in self.thresholds:
                current_value = (
                    self._extract_metric_value(metrics, threshold.metric_path)
                    if threshold.enabled
                    else None
                )
                baseline_value = (
                    self._get_baseline_value(
                        threshold.name, threshold.baseline_window_minutes
                    )
                    if threshold.enabled
                    else None
                )

                severity, message = (
                    threshold.evaluate(current_value)
                    if current_value is not None
                    else (None, "")
                )

                status["thresholds"].append(
                    {
                        "name": threshold.name,
                        "enabled": threshold.enabled,
                        "metric_type": threshold.metric_type.value,
                        "current_value": current_value,
                        "baseline_value": baseline_value,
                        "warning_threshold": threshold.warning_value,
                        "critical_threshold": threshold.critical_value,
                        "unit": threshold.unit,
                        "status": "violation" if severity else "healthy",
                        "severity": severity.value if severity else None,
                        "message": message,
                        "consecutive_warnings": threshold.consecutive_warning_count,
                        "consecutive_criticals": threshold.consecutive_critical_count,
                    }
                )

            return status

        except Exception as e:
            logger.error(f"Error getting threshold status: {e}")
            return {"error": str(e)}


# Global threshold monitor instance
_global_monitor: PerformanceThresholdMonitor | None = None


def get_threshold_monitor() -> PerformanceThresholdMonitor:
    """Get global threshold monitor instance.

    Returns:
        Global PerformanceThresholdMonitor instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceThresholdMonitor()
    return _global_monitor


async def check_performance_thresholds() -> list[dict[str, Any]]:
    """Check all performance thresholds and return violations.

    Returns:
        List of threshold violations
    """
    monitor = get_threshold_monitor()
    return monitor.check_all_thresholds()


async def trigger_performance_alerts() -> int:
    """Check thresholds and trigger alerts for violations.

    Returns:
        Number of alerts triggered
    """
    monitor = get_threshold_monitor()
    violations = monitor.check_all_thresholds()

    if violations:
        await monitor.trigger_alerts_for_violations(violations)
        logger.info(f"Triggered {len(violations)} performance alerts")

    return len(violations)


def get_performance_threshold_status() -> dict[str, Any]:
    """Get status of all performance thresholds.

    Returns:
        Threshold status dictionary
    """
    monitor = get_threshold_monitor()
    return monitor.get_threshold_status()
