"""Tests for performance threshold monitoring and alerting system.

These tests verify that the performance threshold system correctly identifies
performance regressions, triggers appropriate alerts, and maintains threshold
status information.
"""

import time
import unittest
from unittest.mock import AsyncMock, patch

from simplenote_mcp.server.alerting import AlertSeverity, AlertType
from simplenote_mcp.server.monitoring.thresholds import (
    DEFAULT_THRESHOLDS,
    MetricType,
    PerformanceThreshold,
    PerformanceThresholdMonitor,
    ThresholdOperator,
    check_performance_thresholds,
    get_performance_threshold_status,
    trigger_performance_alerts,
)


class TestPerformanceThreshold(unittest.TestCase):
    """Test suite for PerformanceThreshold class."""

    def test_threshold_creation(self):
        """Test creating a performance threshold."""
        threshold = PerformanceThreshold(
            name="Test Threshold",
            metric_type=MetricType.RESPONSE_TIME,
            metric_path="api.response_times.test.p95_time",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=1.0,
            critical_value=3.0,
            unit="s",
            description="Test response time threshold",
        )

        self.assertEqual(threshold.name, "Test Threshold")
        self.assertEqual(threshold.metric_type, MetricType.RESPONSE_TIME)
        self.assertEqual(threshold.warning_value, 1.0)
        self.assertEqual(threshold.critical_value, 3.0)
        self.assertTrue(threshold.enabled)

    def test_threshold_evaluation_no_violation(self):
        """Test threshold evaluation with no violation."""
        threshold = PerformanceThreshold(
            name="CPU Usage",
            metric_type=MetricType.RESOURCE_USAGE,
            metric_path="resources.cpu.current",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=80.0,
            critical_value=90.0,
            consecutive_violations=2,
        )

        # Test normal value
        severity, message = threshold.evaluate(75.0)
        self.assertIsNone(severity)
        self.assertEqual(message, "")

    def test_threshold_evaluation_warning(self):
        """Test threshold evaluation with warning violation."""
        threshold = PerformanceThreshold(
            name="CPU Usage",
            metric_type=MetricType.RESOURCE_USAGE,
            metric_path="resources.cpu.current",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=80.0,
            critical_value=90.0,
            consecutive_violations=2,
        )

        # First violation - should not alert yet
        severity, message = threshold.evaluate(85.0)
        self.assertIsNone(severity)

        # Second consecutive violation - should alert
        severity, message = threshold.evaluate(85.0)
        self.assertEqual(severity, AlertSeverity.MEDIUM)
        self.assertIn("CPU Usage", message)
        self.assertIn("85.000", message)
        self.assertIn("2 consecutive violations", message)

    def test_threshold_evaluation_critical(self):
        """Test threshold evaluation with critical violation."""
        threshold = PerformanceThreshold(
            name="Memory Usage",
            metric_type=MetricType.MEMORY_USAGE,
            metric_path="resources.memory.current",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=80.0,
            critical_value=90.0,
            consecutive_violations=1,  # Alert immediately for testing
        )

        severity, message = threshold.evaluate(95.0)
        self.assertEqual(severity, AlertSeverity.CRITICAL)
        self.assertIn("Memory Usage", message)
        self.assertIn("95.000", message)

    def test_threshold_evaluation_disabled(self):
        """Test threshold evaluation when disabled."""
        threshold = PerformanceThreshold(
            name="Disabled Threshold",
            metric_type=MetricType.RESPONSE_TIME,
            metric_path="api.response_times.test.p95_time",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=1.0,
            critical_value=3.0,
            enabled=False,
        )

        severity, message = threshold.evaluate(5.0)  # Would normally trigger
        self.assertIsNone(severity)
        self.assertEqual(message, "")

    def test_regression_detection_response_time(self):
        """Test regression detection for response time metrics."""
        threshold = PerformanceThreshold(
            name="API Response Time",
            metric_type=MetricType.RESPONSE_TIME,
            metric_path="api.response_times.test.p95_time",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=1.0,
            critical_value=3.0,
            regression_multiplier=1.5,
        )

        # Test no regression
        severity, message = threshold.check_regression(1.0, 1.0)
        self.assertIsNone(severity)

        # Test mild regression
        severity, message = threshold.check_regression(1.5, 1.0)
        self.assertEqual(severity, AlertSeverity.MEDIUM)
        self.assertIn("regression detected", message)
        self.assertIn("1.5x increase", message)

        # Test severe regression
        severity, message = threshold.check_regression(2.1, 1.0)
        self.assertEqual(severity, AlertSeverity.HIGH)
        self.assertIn("2.1x increase", message)

    def test_regression_detection_hit_rate(self):
        """Test regression detection for hit rate metrics (lower is worse)."""
        threshold = PerformanceThreshold(
            name="Cache Hit Rate",
            metric_type=MetricType.CACHE_HIT_RATE,
            metric_path="cache.hit_rate",
            operator=ThresholdOperator.LESS_THAN,
            warning_value=50.0,
            critical_value=25.0,
            regression_multiplier=1.5,
        )

        # Test no regression
        severity, message = threshold.check_regression(80.0, 80.0)
        self.assertIsNone(severity)

        # Test regression (from 80% to 50% hit rate)
        severity, message = threshold.check_regression(50.0, 80.0)
        self.assertEqual(severity, AlertSeverity.MEDIUM)
        self.assertIn("regression detected", message)
        self.assertIn("1.6x decrease", message)

    def test_threshold_operators(self):
        """Test different threshold operators."""
        # Greater than
        threshold_gt = PerformanceThreshold(
            name="GT Test",
            metric_type=MetricType.RESPONSE_TIME,
            metric_path="test.path",
            operator=ThresholdOperator.GREATER_THAN,
            warning_value=5.0,
            critical_value=10.0,
        )
        self.assertTrue(threshold_gt._check_threshold(6.0, 5.0))
        self.assertFalse(threshold_gt._check_threshold(4.0, 5.0))

        # Less than
        threshold_lt = PerformanceThreshold(
            name="LT Test",
            metric_type=MetricType.CACHE_HIT_RATE,
            metric_path="test.path",
            operator=ThresholdOperator.LESS_THAN,
            warning_value=50.0,
            critical_value=25.0,
        )
        self.assertTrue(threshold_lt._check_threshold(40.0, 50.0))
        self.assertFalse(threshold_lt._check_threshold(60.0, 50.0))


class TestPerformanceThresholdMonitor(unittest.TestCase):
    """Test suite for PerformanceThresholdMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create simple test thresholds
        self.test_thresholds = [
            PerformanceThreshold(
                name="Test API Response Time",
                metric_type=MetricType.RESPONSE_TIME,
                metric_path="api.response_times.test.p95_time",
                operator=ThresholdOperator.GREATER_THAN,
                warning_value=1.0,
                critical_value=3.0,
                consecutive_violations=1,  # Alert immediately for testing
            ),
            PerformanceThreshold(
                name="Test Cache Hit Rate",
                metric_type=MetricType.CACHE_HIT_RATE,
                metric_path="cache.hit_rate",
                operator=ThresholdOperator.LESS_THAN,
                warning_value=50.0,
                critical_value=25.0,
                consecutive_violations=1,
            ),
        ]
        self.monitor = PerformanceThresholdMonitor(self.test_thresholds)

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(len(self.monitor.thresholds), 2)
        self.assertIn(
            "Test API Response Time", [t.name for t in self.monitor.thresholds]
        )
        self.assertIn("Test Cache Hit Rate", [t.name for t in self.monitor.thresholds])

    def test_extract_simple_metric_value(self):
        """Test extracting simple metric values."""
        metrics = {
            "api": {"response_times": {"test": {"p95_time": 2.5}}},
            "cache": {"hit_rate": 75.0},
        }

        # Test simple path
        value = self.monitor._extract_metric_value(metrics, "cache.hit_rate")
        self.assertEqual(value, 75.0)

        # Test nested path
        value = self.monitor._extract_metric_value(
            metrics, "api.response_times.test.p95_time"
        )
        self.assertEqual(value, 2.5)

        # Test missing path
        value = self.monitor._extract_metric_value(metrics, "nonexistent.path")
        self.assertIsNone(value)

    def test_extract_aggregated_metric_value(self):
        """Test extracting aggregated metric values with wildcards."""
        metrics = {
            "api": {
                "response_times": {
                    "create_note": {"p95_time": 1.5},
                    "get_note": {"p95_time": 0.8},
                    "update_note": {"p95_time": 2.1},
                }
            },
            "tools": {
                "execution_times": {
                    "search_notes": {"p95_time": 3.2},
                    "add_tags": {"p95_time": 1.1},
                }
            },
        }

        # Test max aggregation for response times (worst case)
        value = self.monitor._extract_aggregated_value(
            metrics, "api.response_times.*.p95_time"
        )
        self.assertEqual(value, 2.1)  # Maximum value

        # Test with tool execution times
        value = self.monitor._extract_aggregated_value(
            metrics, "tools.execution_times.*.p95_time"
        )
        self.assertEqual(value, 3.2)  # Maximum value

    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    def test_check_all_thresholds_no_violations(self, mock_get_metrics):
        """Test checking thresholds with no violations."""
        mock_get_metrics.return_value = {
            "api": {"response_times": {"test": {"p95_time": 0.5}}},
            "cache": {"hit_rate": 75.0},
        }

        violations = self.monitor.check_all_thresholds()
        self.assertEqual(len(violations), 0)

    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    def test_check_all_thresholds_with_violations(self, mock_get_metrics):
        """Test checking thresholds with violations."""
        mock_get_metrics.return_value = {
            "api": {
                "response_times": {
                    "test": {"p95_time": 2.0}  # Exceeds warning threshold
                }
            },
            "cache": {"hit_rate": 30.0},  # Below warning threshold
        }

        violations = self.monitor.check_all_thresholds()
        self.assertEqual(len(violations), 2)

        # Check violation details
        api_violation = next(
            v for v in violations if "API Response Time" in v["threshold_name"]
        )
        cache_violation = next(
            v for v in violations if "Cache Hit Rate" in v["threshold_name"]
        )

        self.assertEqual(api_violation["severity"], AlertSeverity.MEDIUM)
        self.assertEqual(api_violation["current_value"], 2.0)

        self.assertEqual(cache_violation["severity"], AlertSeverity.MEDIUM)
        self.assertEqual(cache_violation["current_value"], 30.0)

    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    def test_baseline_history_tracking(self, mock_get_metrics):
        """Test baseline history tracking for regression detection."""
        # Simulate metrics over time
        mock_get_metrics.return_value = {
            "api": {"response_times": {"test": {"p95_time": 1.0}}},
            "cache": {"hit_rate": 80.0},
        }

        # First check - establishes baseline
        self.monitor.check_all_thresholds()

        # Check that baseline history was updated
        self.assertIn("Test API Response Time", self.monitor.baseline_history)
        history = self.monitor.baseline_history["Test API Response Time"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1], 1.0)  # Value recorded

    def test_should_alert_cooldown(self):
        """Test alert cooldown functionality."""
        # Should allow first alert
        self.assertTrue(self.monitor._should_alert("test_alert"))

        # Record alert time
        self.monitor.last_alert_time["test_alert"] = time.time()

        # Should not allow immediate second alert
        self.assertFalse(self.monitor._should_alert("test_alert"))

        # Should allow alert after cooldown (mock old timestamp)
        self.monitor.last_alert_time["test_alert"] = time.time() - 400
        self.assertTrue(self.monitor._should_alert("test_alert"))

    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    def test_get_threshold_status(self, mock_get_metrics):
        """Test getting threshold status."""
        mock_get_metrics.return_value = {
            "api": {"response_times": {"test": {"p95_time": 0.8}}},
            "cache": {"hit_rate": 65.0},
        }

        status = self.monitor.get_threshold_status()

        self.assertEqual(status["total_thresholds"], 2)
        self.assertEqual(status["enabled_thresholds"], 2)
        self.assertEqual(len(status["thresholds"]), 2)

        # Check individual threshold status
        api_status = next(
            t for t in status["thresholds"] if t["name"] == "Test API Response Time"
        )
        self.assertEqual(api_status["status"], "healthy")
        self.assertEqual(api_status["current_value"], 0.8)


class TestThresholdAlertIntegration(unittest.TestCase):
    """Test suite for threshold alerting integration."""

    @patch("simplenote_mcp.server.monitoring.thresholds.get_alerter")
    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    async def test_trigger_performance_alerts(self, mock_get_metrics, mock_get_alerter):
        """Test triggering performance alerts."""
        # Mock alerter
        mock_alerter = AsyncMock()
        mock_get_alerter.return_value = mock_alerter

        # Mock metrics with violations
        mock_get_metrics.return_value = {
            "resources": {"cpu": {"current": 85.0}},  # Exceeds default threshold
            "api": {"success_rate": 88.0},  # Below success rate threshold
        }

        # Trigger alerts
        alert_count = await trigger_performance_alerts()

        # Should have triggered alerts
        self.assertGreater(alert_count, 0)

        # Verify alerter was called
        mock_alerter.create_alert.assert_called()
        call_args = mock_alerter.create_alert.call_args_list

        # Check that alerts were created with correct parameters
        for call in call_args:
            args, kwargs = call
            alert_type, severity, message, context = args[:4]

            self.assertEqual(alert_type, AlertType.SECURITY_THRESHOLD_EXCEEDED)
            self.assertIn(severity, [AlertSeverity.MEDIUM, AlertSeverity.CRITICAL])
            self.assertIsInstance(message, str)
            self.assertIsInstance(context, dict)

    @patch("simplenote_mcp.server.monitoring.thresholds.get_metrics")
    async def test_check_performance_thresholds_function(self, mock_get_metrics):
        """Test the standalone check_performance_thresholds function."""
        mock_get_metrics.return_value = {
            "resources": {"memory": {"current": 95.0}},  # Critical violation
        }

        violations = await check_performance_thresholds()

        # Should find violations
        self.assertGreater(len(violations), 0)

        # Check violation structure
        violation = violations[0]
        self.assertIn("threshold_name", violation)
        self.assertIn("severity", violation)
        self.assertIn("message", violation)
        self.assertIn("current_value", violation)

    def test_get_performance_threshold_status_function(self):
        """Test the standalone get_performance_threshold_status function."""
        with patch(
            "simplenote_mcp.server.monitoring.thresholds.get_metrics"
        ) as mock_get_metrics:
            mock_get_metrics.return_value = {
                "api": {"success_rate": 95.0},
                "cache": {"hit_rate": 60.0},
                "resources": {"cpu": {"current": 50.0}, "memory": {"current": 60.0}},
            }

            status = get_performance_threshold_status()

            self.assertIsInstance(status, dict)
            self.assertIn("total_thresholds", status)
            self.assertIn("enabled_thresholds", status)
            self.assertIn("thresholds", status)


class TestDefaultThresholds(unittest.TestCase):
    """Test suite for default threshold definitions."""

    def test_default_thresholds_structure(self):
        """Test that default thresholds are properly structured."""
        self.assertGreater(len(DEFAULT_THRESHOLDS), 0)

        for threshold in DEFAULT_THRESHOLDS:
            self.assertIsInstance(threshold, PerformanceThreshold)
            self.assertIsInstance(threshold.name, str)
            self.assertIsInstance(threshold.metric_type, MetricType)
            self.assertIsInstance(threshold.operator, ThresholdOperator)
            self.assertIsInstance(threshold.warning_value, (int, float))
            self.assertIsInstance(threshold.critical_value, (int, float))

    def test_threshold_coverage(self):
        """Test that thresholds cover important metric types."""
        metric_types = {threshold.metric_type for threshold in DEFAULT_THRESHOLDS}

        # Should cover key metric types
        expected_types = {
            MetricType.RESPONSE_TIME,
            MetricType.ERROR_RATE,
            MetricType.CACHE_HIT_RATE,
            MetricType.RESOURCE_USAGE,
            MetricType.MEMORY_USAGE,
        }

        self.assertTrue(expected_types.issubset(metric_types))

    def test_threshold_sanity_checks(self):
        """Test that threshold values are sensible."""
        for threshold in DEFAULT_THRESHOLDS:
            if threshold.enabled:
                # Warning should be less severe than critical
                if threshold.operator in [
                    ThresholdOperator.GREATER_THAN,
                    ThresholdOperator.GREATER_EQUAL,
                ]:
                    self.assertLess(threshold.warning_value, threshold.critical_value)
                elif threshold.operator in [
                    ThresholdOperator.LESS_THAN,
                    ThresholdOperator.LESS_EQUAL,
                ]:
                    self.assertGreater(
                        threshold.warning_value, threshold.critical_value
                    )

                # Regression multiplier should be reasonable
                self.assertGreater(threshold.regression_multiplier, 1.0)
                self.assertLessEqual(threshold.regression_multiplier, 10.0)

                # Consecutive violations should be reasonable
                self.assertGreaterEqual(threshold.consecutive_violations, 1)
                self.assertLessEqual(threshold.consecutive_violations, 10)


if __name__ == "__main__":
    unittest.main()
