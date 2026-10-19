"""Tests for performance threshold evaluation, regression detection and alerting.

``simplenote_mcp.server.monitoring.thresholds`` holds process-global state: the
``_global_monitor`` singleton and the module-level ``DEFAULT_THRESHOLDS`` objects
(monitors deep-copy them; a regression to a shallow copy would mutate them).
The autouse fixture below snapshots and restores both so these tests never leak
state into the rest of the suite (see ``simplenote_mcp/server/monitoring/AGENTS.md``).

Time is controlled by swapping the module's ``time`` reference for a fake clock,
so no test depends on wall-clock time or sleeps.
"""

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from simplenote_mcp.server.alerting import AlertSeverity, AlertType
from simplenote_mcp.server.monitoring import thresholds as th
from simplenote_mcp.server.monitoring.thresholds import (
    DEFAULT_THRESHOLDS,
    MetricType,
    PerformanceThreshold,
    PerformanceThresholdMonitor,
    ThresholdOperator,
)

pytestmark = pytest.mark.unit

NOW = 1_000_000.0
_STATE_FIELDS = (
    "enabled",
    "last_check_time",
    "consecutive_warning_count",
    "consecutive_critical_count",
    "baseline_value",
    "violation_history",
)


class FakeClock:
    """Stand-in for the ``time`` module as referenced inside ``thresholds``."""

    def __init__(self, now: float = NOW) -> None:
        self.now = now

    def time(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def restore_threshold_globals():
    """Snapshot and restore the module singleton and shared default thresholds."""
    saved_monitor = th._global_monitor
    saved_state = [
        {name: copy.deepcopy(getattr(t, name)) for name in _STATE_FIELDS}
        for t in DEFAULT_THRESHOLDS
    ]
    th._global_monitor = None
    yield
    th._global_monitor = saved_monitor
    for threshold, state in zip(DEFAULT_THRESHOLDS, saved_state, strict=True):
        for name, value in state.items():
            setattr(threshold, name, value)


@pytest.fixture
def clock():
    """Patch the clock used by ``thresholds`` (not the global ``time`` module)."""
    fake = FakeClock()
    with patch.object(th, "time", fake):
        yield fake


def make_threshold(**overrides: Any) -> PerformanceThreshold:
    """Build a response-time style threshold that alerts on the first violation."""
    params: dict[str, Any] = {
        "name": "Latency",
        "metric_type": MetricType.RESPONSE_TIME,
        "metric_path": "api.latency",
        "operator": ThresholdOperator.GREATER_THAN,
        "warning_value": 1.0,
        "critical_value": 3.0,
        "unit": "s",
        "consecutive_violations": 1,
    }
    params.update(overrides)
    return PerformanceThreshold(**params)


def seed_baseline(
    monitor: PerformanceThresholdMonitor,
    name: str,
    values: list[float],
    minutes_ago: float = 45,
) -> None:
    """Place readings inside the baseline window (first half of a 60 min window)."""
    monitor.baseline_history[name] = [
        (NOW - minutes_ago * 60 + i, value) for i, value in enumerate(values)
    ]


class TestEvaluate:
    """``PerformanceThreshold.evaluate``: streaks, severities and recovery."""

    def test_disabled_threshold_never_alerts_or_counts(self):
        threshold = make_threshold(enabled=False)

        assert threshold.evaluate(100.0) == (None, "")
        assert threshold.consecutive_critical_count == 0
        assert threshold.consecutive_warning_count == 0

    def test_critical_alert_requires_consecutive_violations(self):
        threshold = make_threshold(consecutive_violations=3)

        assert threshold.evaluate(3.5) == (None, "")
        assert threshold.evaluate(3.5) == (None, "")
        severity, message = threshold.evaluate(3.5)

        assert severity is AlertSeverity.CRITICAL
        assert message == "Latency: 3.500s > 3.000s (3 consecutive violations)"
        assert threshold.consecutive_critical_count == 3

    def test_alert_repeats_while_streak_continues(self):
        threshold = make_threshold(consecutive_violations=2)
        threshold.evaluate(4.0)
        threshold.evaluate(4.0)

        severity, message = threshold.evaluate(4.0)

        assert severity is AlertSeverity.CRITICAL
        assert "(3 consecutive violations)" in message

    def test_warning_alert_reports_warning_value(self):
        threshold = make_threshold(consecutive_violations=2)

        assert threshold.evaluate(1.5) == (None, "")
        severity, message = threshold.evaluate(1.5)

        assert severity is AlertSeverity.MEDIUM
        assert message == "Latency: 1.500s > 1.000s (2 consecutive violations)"

    def test_critical_below_streak_does_not_fall_back_to_warning(self):
        threshold = make_threshold(consecutive_violations=2)

        # 3.5 also exceeds the warning level, but a single critical reading
        # short of the streak returns nothing rather than a MEDIUM alert.
        assert threshold.evaluate(3.5) == (None, "")
        assert threshold.consecutive_warning_count == 0

    def test_switching_between_levels_resets_the_other_counter(self):
        threshold = make_threshold(consecutive_violations=3)
        threshold.evaluate(1.5)
        threshold.evaluate(1.5)
        assert threshold.consecutive_warning_count == 2

        threshold.evaluate(3.5)
        assert threshold.consecutive_critical_count == 1
        assert threshold.consecutive_warning_count == 0

        threshold.evaluate(1.5)
        assert threshold.consecutive_warning_count == 1
        assert threshold.consecutive_critical_count == 0

    def test_recovery_resets_counters_and_requires_a_fresh_streak(self):
        threshold = make_threshold(consecutive_violations=2)
        threshold.evaluate(3.5)
        assert threshold.evaluate(3.5)[0] is AlertSeverity.CRITICAL

        assert threshold.evaluate(0.5) == (None, "")
        assert threshold.consecutive_critical_count == 0
        assert threshold.consecutive_warning_count == 0

        # One violation after recovery is not enough to alert again.
        assert threshold.evaluate(3.5) == (None, "")

    def test_less_than_operator_checks_critical_first(self):
        threshold = make_threshold(
            name="Hit Rate",
            metric_type=MetricType.CACHE_HIT_RATE,
            operator=ThresholdOperator.LESS_THAN,
            warning_value=50.0,
            critical_value=25.0,
            unit="%",
        )

        assert threshold.evaluate(40.0)[0] is AlertSeverity.MEDIUM
        severity, message = threshold.evaluate(10.0)
        assert severity is AlertSeverity.CRITICAL
        assert message == "Hit Rate: 10.000% < 25.000% (1 consecutive violations)"


class TestClassify:
    """``PerformanceThreshold.classify``: the reading against the limits, no state."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(4.0, AlertSeverity.CRITICAL), (2.0, AlertSeverity.MEDIUM), (0.5, None)],
    )
    def test_classifies_without_touching_counters(self, value, expected):
        threshold = make_threshold(consecutive_violations=3)
        threshold.consecutive_warning_count = 1

        severity, _ = threshold.classify(value)

        assert severity == expected
        assert threshold.consecutive_warning_count == 1
        assert threshold.consecutive_critical_count == 0

    def test_disabled_threshold_classifies_as_healthy(self):
        assert make_threshold(enabled=False).classify(99.0) == (None, "")


class TestCheckThreshold:
    """``PerformanceThreshold._check_threshold`` for every operator."""

    @pytest.mark.parametrize(
        ("operator", "value", "expected"),
        [
            (ThresholdOperator.GREATER_THAN, 3.1, True),
            (ThresholdOperator.GREATER_THAN, 3.0, False),
            (ThresholdOperator.LESS_THAN, 2.9, True),
            (ThresholdOperator.LESS_THAN, 3.0, False),
            (ThresholdOperator.GREATER_EQUAL, 3.0, True),
            (ThresholdOperator.GREATER_EQUAL, 2.9, False),
            (ThresholdOperator.LESS_EQUAL, 3.0, True),
            (ThresholdOperator.LESS_EQUAL, 3.1, False),
            (ThresholdOperator.EQUAL, 3.0005, True),
            (ThresholdOperator.EQUAL, 3.01, False),
            (ThresholdOperator.NOT_EQUAL, 3.01, True),
            (ThresholdOperator.NOT_EQUAL, 3.0005, False),
        ],
    )
    def test_operator_semantics(self, operator, value, expected):
        threshold = make_threshold(operator=operator)

        assert threshold._check_threshold(value, 3.0) is expected

    def test_unknown_operator_never_violates(self):
        threshold = make_threshold()
        threshold.operator = "~"  # not a ThresholdOperator member

        assert threshold._check_threshold(1e9, 0.0) is False


class TestCheckRegression:
    """``PerformanceThreshold.check_regression`` direction and severity."""

    def test_disabled_threshold_skips_regression(self):
        threshold = make_threshold(enabled=False)

        assert threshold.check_regression(100.0, 1.0) == (None, "")

    @pytest.mark.parametrize("baseline", [0.0, -1.0])
    def test_non_positive_baseline_is_ignored(self, baseline):
        threshold = make_threshold()

        assert threshold.check_regression(100.0, baseline) == (None, "")

    @pytest.mark.parametrize(
        "metric_type",
        [
            MetricType.RESPONSE_TIME,
            MetricType.ERROR_RATE,
            MetricType.MEMORY_USAGE,
            MetricType.RESOURCE_USAGE,
        ],
    )
    @pytest.mark.parametrize(
        ("current", "expected"),
        [
            (1.4, None),
            (1.5, AlertSeverity.MEDIUM),
            (1.9, AlertSeverity.MEDIUM),
            (2.0, AlertSeverity.HIGH),
        ],
    )
    def test_higher_is_worse_metrics(self, metric_type, current, expected):
        threshold = make_threshold(metric_type=metric_type, regression_multiplier=1.5)

        severity, message = threshold.check_regression(current, 1.0)

        assert severity is expected
        if expected is None:
            assert message == ""
        else:
            assert "x increase" in message
            assert "vs baseline 1.000s" in message

    @pytest.mark.parametrize(
        "metric_type",
        [MetricType.THROUGHPUT, MetricType.CACHE_HIT_RATE, MetricType.API_SUCCESS_RATE],
    )
    @pytest.mark.parametrize(
        ("current", "expected"),
        [
            (80.0, None),  # 1.25x drop, below multiplier
            (60.0, AlertSeverity.MEDIUM),  # 1.67x drop
            (50.0, AlertSeverity.HIGH),  # 2x drop
            (120.0, None),  # improvement
        ],
    )
    def test_lower_is_worse_metrics(self, metric_type, current, expected):
        threshold = make_threshold(
            metric_type=metric_type, regression_multiplier=1.5, unit="%"
        )

        severity, message = threshold.check_regression(current, 100.0)

        assert severity is expected
        if expected is not None:
            assert "x decrease" in message

    def test_lower_is_worse_metric_dropping_to_zero_is_high(self):
        threshold = make_threshold(metric_type=MetricType.THROUGHPUT)

        severity, message = threshold.check_regression(0.0, 10.0)

        assert severity is AlertSeverity.HIGH
        assert "(infx decrease)" in message

    def test_default_api_error_rate_regression_direction(self):
        default = next(t for t in DEFAULT_THRESHOLDS if t.name == "API Error Rate")
        threshold = copy.deepcopy(default)

        dropped, _ = threshold.check_regression(50.0, 95.0)
        improved, _ = threshold.check_regression(100.0, 80.0)

        assert dropped is not None
        assert improved is None


class TestDefaultThresholds:
    """Invariants the monitor relies on for the shipped defaults."""

    def test_names_are_unique(self):
        # baseline_history and last_alert_time are keyed by threshold name.
        names = [t.name for t in DEFAULT_THRESHOLDS]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize("threshold", DEFAULT_THRESHOLDS, ids=lambda t: t.name)
    def test_critical_level_is_beyond_warning_level(self, threshold):
        # evaluate() checks critical first, so a critical value on the wrong
        # side of the warning value would make the warning branch unreachable.
        assert threshold._check_threshold(
            threshold.critical_value, threshold.warning_value
        )


class TestMonitorInit:
    """``PerformanceThresholdMonitor`` construction."""

    def test_defaults_used_when_none(self):
        monitor = PerformanceThresholdMonitor()

        assert [t.name for t in monitor.thresholds] == [
            t.name for t in DEFAULT_THRESHOLDS
        ]
        assert monitor.thresholds is not DEFAULT_THRESHOLDS
        assert monitor.baseline_history == {}
        assert monitor.last_alert_time == {}
        assert monitor.alert_cooldown_seconds == 300

    def test_custom_thresholds_used_as_given(self):
        custom = [make_threshold()]

        monitor = PerformanceThresholdMonitor(custom)

        assert monitor.thresholds is custom

    def test_empty_list_means_no_thresholds(self):
        monitor = PerformanceThresholdMonitor([])

        assert monitor.thresholds == []

    def test_default_monitors_do_not_share_threshold_state(self):
        first = PerformanceThresholdMonitor()
        second = PerformanceThresholdMonitor()
        cpu_first = next(t for t in first.thresholds if t.name == "CPU Usage")
        cpu_second = next(t for t in second.thresholds if t.name == "CPU Usage")

        cpu_first.evaluate(99.0)

        assert cpu_second.consecutive_critical_count == 0

    def test_default_monitor_leaves_module_defaults_untouched(self):
        monitor = PerformanceThresholdMonitor()
        cpu = next(t for t in monitor.thresholds if t.name == "CPU Usage")

        cpu.evaluate(99.0)

        module_cpu = next(t for t in DEFAULT_THRESHOLDS if t.name == "CPU Usage")
        assert cpu is not module_cpu
        assert module_cpu.consecutive_critical_count == 0


class TestExtractMetricValue:
    """Dot-path and wildcard metric extraction."""

    @pytest.fixture
    def monitor(self):
        return PerformanceThresholdMonitor([make_threshold()])

    def test_simple_path_returns_float(self, monitor):
        value = monitor._extract_metric_value({"cache": {"hits": 7}}, "cache.hits")

        assert value == 7.0
        assert isinstance(value, float)

    @pytest.mark.parametrize(
        ("metrics", "path"),
        [
            ({"cache": {}}, "cache.hits"),  # missing leaf
            ({"cache": 5}, "cache.hits"),  # intermediate is not a dict
            ({"cache": {"hits": "many"}}, "cache.hits"),  # non-numeric leaf
            ({"cache": {"hits": {"total": 3}}}, "cache.hits"),  # dict leaf
            ({"cache": {"hits": None}}, "cache.hits"),
        ],
    )
    def test_unresolvable_simple_path_returns_none(self, monitor, metrics, path):
        assert monitor._extract_metric_value(metrics, path) is None

    def test_invalid_path_type_returns_none(self, monitor):
        assert monitor._extract_metric_value({"a": 1}, None) is None

    @pytest.mark.parametrize(
        ("outer", "inner", "leaf", "expected"),
        [
            ("api", "response_times", "p95_time", 2.5),  # max for timings
            ("tools", "execution_times", "p95_time", 2.5),  # max for timings
            ("cache", "hit_rate", "value", 0.5),  # min for rates
            ("api", "success_rate", "value", 0.5),  # min for rates
            ("api", "calls", "value", 1.5),  # mean otherwise
        ],
    )
    def test_wildcard_aggregation_by_metric_name(
        self, monitor, outer, inner, leaf, expected
    ):
        per_key = {"a": {leaf: 0.5}, "b": {leaf: 2.5}, "c": {leaf: 1.5}}
        metrics = {outer: {inner: per_key}}

        value = monitor._extract_metric_value(metrics, f"{outer}.{inner}.*.{leaf}")

        assert value == expected

    def test_wildcard_skips_entries_without_numeric_leaf(self, monitor):
        metrics = {
            "api": {
                "response_times": {
                    "create": {"p95_time": 0.4},
                    "update": {"p50_time": 9.0},  # missing p95_time
                    "delete": {"p95_time": "slow"},  # not numeric
                    "search": 3,  # not a dict
                }
            }
        }

        value = monitor._extract_metric_value(metrics, "api.response_times.*.p95_time")

        assert value == 0.4

    def test_trailing_wildcard_aggregates_direct_children(self, monitor):
        metrics = {"api": {"counts": {"a": 2, "b": 4, "c": "n/a"}}}

        assert monitor._extract_metric_value(metrics, "api.counts.*") == 3.0

    @pytest.mark.parametrize(
        "metrics",
        [
            {},  # parent missing
            {"api": {"response_times": [1, 2]}},  # parent is not a dict
            {"api": {"response_times": {"a": {"p50_time": 1}}}},  # no values
        ],
    )
    def test_wildcard_without_values_returns_none(self, monitor, metrics):
        path = "api.response_times.*.p95_time"

        assert monitor._extract_metric_value(metrics, path) is None

    def test_wildcard_inside_a_segment_returns_none(self, monitor):
        assert monitor._extract_metric_value({"api": {}}, "api.p*95") is None


class TestBaselineHistory:
    """Baseline bookkeeping and median selection."""

    @pytest.fixture
    def monitor(self):
        return PerformanceThresholdMonitor([make_threshold()])

    def test_update_records_timestamped_value(self, monitor, clock):
        monitor._update_baseline_history("Latency", 1.25)

        assert monitor.baseline_history == {"Latency": [(NOW, 1.25)]}

    def test_update_prunes_entries_older_than_24_hours(self, monitor, clock):
        day = 24 * 60 * 60
        monitor.baseline_history["Latency"] = [
            (NOW - day - 1, 9.0),
            (NOW - day, 8.0),  # exactly at the cutoff is pruned too
            (NOW - 60, 1.0),
        ]

        monitor._update_baseline_history("Latency", 2.0)

        assert monitor.baseline_history["Latency"] == [(NOW - 60, 1.0), (NOW, 2.0)]

    def test_unknown_threshold_has_no_baseline(self, monitor, clock):
        assert monitor._get_baseline_value("nope", 60) is None

    def test_fewer_than_three_points_has_no_baseline(self, monitor, clock):
        seed_baseline(monitor, "Latency", [1.0, 2.0])

        assert monitor._get_baseline_value("Latency", 60) is None

    def test_only_first_half_of_window_counts(self, monitor, clock):
        monitor.baseline_history["Latency"] = [
            (NOW - 61 * 60, 100.0),  # before the window
            (NOW - 60 * 60, 1.0),  # window start, inclusive
            (NOW - 45 * 60, 2.0),
            (NOW - 30 * 60, 3.0),  # window midpoint, inclusive
            (NOW - 29 * 60, 100.0),  # too recent
            (NOW, 100.0),  # current reading
        ]

        assert monitor._get_baseline_value("Latency", 60) == 2.0

    def test_baseline_is_upper_median_for_even_count(self, monitor, clock):
        seed_baseline(monitor, "Latency", [4.0, 1.0, 3.0, 2.0])

        assert monitor._get_baseline_value("Latency", 60) == 3.0

    def test_baseline_is_median_not_mean(self, monitor, clock):
        seed_baseline(monitor, "Latency", [1.0, 1.0, 50.0])

        assert monitor._get_baseline_value("Latency", 60) == 1.0


class TestShouldAlert:
    """Per-key alert cooldown."""

    @pytest.fixture
    def monitor(self):
        return PerformanceThresholdMonitor([make_threshold()])

    def test_first_alert_is_allowed(self, monitor, clock):
        assert monitor._should_alert("Latency") is True

    def test_alert_within_cooldown_is_suppressed(self, monitor, clock):
        monitor.last_alert_time["Latency"] = NOW - 299

        assert monitor._should_alert("Latency") is False

    def test_alert_allowed_once_cooldown_elapses(self, monitor, clock):
        monitor.last_alert_time["Latency"] = NOW - 300

        assert monitor._should_alert("Latency") is True


class TestCheckAllThresholds:
    """``PerformanceThresholdMonitor.check_all_thresholds``."""

    @pytest.fixture
    def metrics(self):
        with patch.object(th, "get_metrics") as mock_get_metrics:
            yield mock_get_metrics

    def test_violation_produces_alert_dict(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 4.0}}
        monitor = PerformanceThresholdMonitor([make_threshold()])

        alerts = monitor.check_all_thresholds()

        assert alerts == [
            {
                "threshold_name": "Latency",
                "severity": AlertSeverity.CRITICAL,
                "message": "Latency: 4.000s > 3.000s (1 consecutive violations)",
                "current_value": 4.0,
                "metric_type": "response_time",
                "metric_path": "api.latency",
            }
        ]
        assert monitor.baseline_history["Latency"] == [(NOW, 4.0)]

    def test_healthy_value_records_history_without_alert(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 0.2}}
        monitor = PerformanceThresholdMonitor([make_threshold()])

        assert monitor.check_all_thresholds() == []
        assert monitor.baseline_history["Latency"] == [(NOW, 0.2)]

    def test_disabled_and_missing_metrics_are_skipped(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 9.0}}
        disabled = make_threshold(name="Disabled", enabled=False)
        missing = make_threshold(name="Missing", metric_path="api.absent")
        monitor = PerformanceThresholdMonitor([disabled, missing])

        assert monitor.check_all_thresholds() == []
        assert monitor.baseline_history == {}
        assert disabled.consecutive_critical_count == 0

    def test_cooldown_suppresses_alert_but_streak_still_advances(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 4.0}}
        threshold = make_threshold()
        monitor = PerformanceThresholdMonitor([threshold])
        monitor.last_alert_time["Latency"] = NOW - 10

        assert monitor.check_all_thresholds() == []
        assert threshold.consecutive_critical_count == 1

    def test_regression_against_baseline_is_reported(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 0.9}}
        threshold = make_threshold(warning_value=5.0, critical_value=10.0)
        monitor = PerformanceThresholdMonitor([threshold])
        seed_baseline(monitor, "Latency", [0.3, 0.3, 0.3])

        alerts = monitor.check_all_thresholds()

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["threshold_name"] == "Latency (Regression)"
        assert alert["severity"] is AlertSeverity.HIGH
        assert alert["baseline_value"] == 0.3
        assert alert["current_value"] == 0.9
        assert "(3.0x increase)" in alert["message"]

    def test_threshold_and_regression_alerts_together(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 4.0}}
        monitor = PerformanceThresholdMonitor([make_threshold()])
        seed_baseline(monitor, "Latency", [1.0, 1.0, 1.0])

        names = [a["threshold_name"] for a in monitor.check_all_thresholds()]

        assert names == ["Latency", "Latency (Regression)"]

    def test_metrics_failure_returns_empty_list(self, clock, metrics):
        metrics.side_effect = RuntimeError("collector down")
        monitor = PerformanceThresholdMonitor([make_threshold()])

        assert monitor.check_all_thresholds() == []

    async def test_regression_alert_respects_cooldown(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 0.9}}
        threshold = make_threshold(warning_value=5.0, critical_value=10.0)
        monitor = PerformanceThresholdMonitor([threshold])
        seed_baseline(monitor, "Latency", [0.3, 0.3, 0.3])
        first = monitor.check_all_thresholds()
        assert len(first) == 1

        with patch.object(th, "get_alerter", return_value=AsyncMock()):
            await monitor.trigger_alerts_for_violations(first)
        clock.now += 1

        assert monitor.check_all_thresholds() == []

    def test_api_success_rate_drop_raises_regression_alert(self, clock, metrics):
        default = next(t for t in DEFAULT_THRESHOLDS if t.name == "API Error Rate")
        monitor = PerformanceThresholdMonitor([copy.deepcopy(default)])
        seed_baseline(monitor, "API Error Rate", [95.0, 95.0, 95.0])
        metrics.return_value = {"api": {"success_rate": 50.0}}

        alerts = monitor.check_all_thresholds()

        assert [a["threshold_name"] for a in alerts] == ["API Error Rate (Regression)"]
        assert alerts[0]["severity"] == AlertSeverity.MEDIUM
        assert alerts[0]["metric_type"] == "api_success_rate"


class TestTriggerAlertsForViolations:
    """``PerformanceThresholdMonitor.trigger_alerts_for_violations``."""

    @pytest.fixture
    def alerter(self):
        mock_alerter = MagicMock()
        mock_alerter.create_alert = AsyncMock()
        with patch.object(th, "get_alerter", return_value=mock_alerter):
            yield mock_alerter

    @staticmethod
    def violation(**overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "threshold_name": "Latency",
            "severity": AlertSeverity.CRITICAL,
            "message": "Latency too high",
            "current_value": 4.0,
            "metric_type": "response_time",
            "metric_path": "api.latency",
        }
        data.update(overrides)
        return data

    async def test_creates_alert_and_starts_cooldown(self, clock, alerter):
        monitor = PerformanceThresholdMonitor([make_threshold()])

        await monitor.trigger_alerts_for_violations([self.violation()])

        alerter.create_alert.assert_awaited_once_with(
            AlertType.SECURITY_THRESHOLD_EXCEEDED,
            AlertSeverity.CRITICAL,
            "Latency too high",
            {
                "threshold_name": "Latency",
                "current_value": 4.0,
                "metric_type": "response_time",
                "metric_path": "api.latency",
                "baseline_value": None,
            },
        )
        assert monitor.last_alert_time == {"Latency": NOW}
        assert monitor._should_alert("Latency") is False

    async def test_regression_violation_passes_baseline(self, clock, alerter):
        monitor = PerformanceThresholdMonitor([make_threshold()])
        regression = self.violation(
            threshold_name="Latency (Regression)",
            severity=AlertSeverity.HIGH,
            baseline_value=1.0,
        )

        await monitor.trigger_alerts_for_violations([regression])

        context = alerter.create_alert.await_args.args[3]
        assert context["baseline_value"] == 1.0
        assert monitor.last_alert_time == {"Latency (Regression)": NOW}

    async def test_no_violations_creates_no_alerts(self, clock, alerter):
        monitor = PerformanceThresholdMonitor([make_threshold()])

        await monitor.trigger_alerts_for_violations([])

        alerter.create_alert.assert_not_awaited()
        assert monitor.last_alert_time == {}

    async def test_alerter_failure_is_swallowed(self, clock, alerter):
        alerter.create_alert.side_effect = RuntimeError("alert sink down")
        monitor = PerformanceThresholdMonitor([make_threshold()])

        await monitor.trigger_alerts_for_violations([self.violation()])

        # The failed alert must not start a cooldown.
        assert monitor.last_alert_time == {}


class TestThresholdStatus:
    """``PerformanceThresholdMonitor.get_threshold_status``."""

    @pytest.fixture
    def metrics(self):
        with patch.object(th, "get_metrics") as mock_get_metrics:
            yield mock_get_metrics

    def test_status_reports_each_threshold(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 4.0, "rate": 0.5}}
        violating = make_threshold()
        healthy = make_threshold(name="Rate", metric_path="api.rate")
        disabled = make_threshold(name="Off", enabled=False)
        missing = make_threshold(name="Gone", metric_path="api.gone")
        monitor = PerformanceThresholdMonitor([violating, healthy, disabled, missing])
        seed_baseline(monitor, "Rate", [0.4, 0.5, 0.6])

        status = monitor.get_threshold_status()

        assert status["total_thresholds"] == 4
        assert status["enabled_thresholds"] == 3
        by_name = {entry["name"]: entry for entry in status["thresholds"]}
        assert by_name["Latency"]["status"] == "violation"
        assert by_name["Latency"]["severity"] == "CRITICAL"
        assert by_name["Latency"]["current_value"] == 4.0
        assert by_name["Latency"]["warning_threshold"] == 1.0
        assert by_name["Latency"]["critical_threshold"] == 3.0
        assert by_name["Latency"]["unit"] == "s"
        assert by_name["Rate"]["status"] == "healthy"
        assert by_name["Rate"]["severity"] is None
        assert by_name["Rate"]["message"] == ""
        assert by_name["Rate"]["baseline_value"] == 0.5
        assert by_name["Off"]["enabled"] is False
        assert by_name["Off"]["current_value"] is None
        assert by_name["Off"]["baseline_value"] is None
        assert by_name["Off"]["status"] == "healthy"
        assert by_name["Gone"]["current_value"] is None
        assert by_name["Gone"]["status"] == "healthy"

    def test_status_does_not_touch_baseline_history(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 0.2}}
        monitor = PerformanceThresholdMonitor([make_threshold()])

        monitor.get_threshold_status()

        assert monitor.baseline_history == {}

    def test_metrics_failure_returns_error(self, clock, metrics):
        metrics.side_effect = RuntimeError("collector down")
        monitor = PerformanceThresholdMonitor([make_threshold()])

        assert monitor.get_threshold_status() == {"error": "collector down"}

    def test_status_is_read_only(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 4.0}}
        threshold = make_threshold(consecutive_violations=3)
        monitor = PerformanceThresholdMonitor([threshold])

        monitor.get_threshold_status()
        monitor.get_threshold_status()

        assert threshold.consecutive_critical_count == 0

    def test_status_reports_recorded_counts_without_projecting_a_check(
        self, clock, metrics
    ):
        # With 2 of 3 violations recorded, a status read must not claim a third
        # (review on #993).
        metrics.return_value = {"api": {"latency": 4.0}}
        threshold = make_threshold(consecutive_violations=3)
        threshold.consecutive_critical_count = 2
        monitor = PerformanceThresholdMonitor([threshold])

        entry = monitor.get_threshold_status()["thresholds"][0]

        assert entry["status"] == "violation"
        assert entry["severity"] == "CRITICAL"
        assert entry["message"] == "Latency: 4.000s > 3.000s"
        assert entry["consecutive_criticals"] == 2
        assert threshold.consecutive_critical_count == 2

    def test_status_classifies_reading_before_any_check(self, clock, metrics):
        metrics.return_value = {"api": {"latency": 2.0}}
        monitor = PerformanceThresholdMonitor(
            [make_threshold(consecutive_violations=3)]
        )

        entry = monitor.get_threshold_status()["thresholds"][0]

        assert entry["status"] == "violation"
        assert entry["severity"] == "MEDIUM"
        assert entry["message"] == "Latency: 2.000s > 1.000s"
        assert entry["consecutive_warnings"] == 0


class TestModuleFunctions:
    """Module-level singleton accessor and async entry points."""

    @pytest.fixture
    def installed_monitor(self):
        monitor = PerformanceThresholdMonitor([make_threshold()])
        th._global_monitor = monitor
        return monitor

    def test_get_threshold_monitor_is_a_lazy_singleton(self):
        assert th._global_monitor is None

        first = th.get_threshold_monitor()

        assert isinstance(first, PerformanceThresholdMonitor)
        assert th.get_threshold_monitor() is first
        assert len(first.thresholds) == len(DEFAULT_THRESHOLDS)

    async def test_check_performance_thresholds_uses_global_monitor(
        self, clock, installed_monitor
    ):
        with patch.object(th, "get_metrics", return_value={"api": {"latency": 4.0}}):
            violations = await th.check_performance_thresholds()

        assert [v["threshold_name"] for v in violations] == ["Latency"]
        assert installed_monitor.baseline_history["Latency"] == [(NOW, 4.0)]

    async def test_trigger_performance_alerts_sends_and_counts(
        self, clock, installed_monitor
    ):
        alerter = MagicMock()
        alerter.create_alert = AsyncMock()
        with (
            patch.object(th, "get_metrics", return_value={"api": {"latency": 4.0}}),
            patch.object(th, "get_alerter", return_value=alerter),
        ):
            count = await th.trigger_performance_alerts()

        assert count == 1
        alerter.create_alert.assert_awaited_once()
        assert installed_monitor.last_alert_time == {"Latency": NOW}

    async def test_trigger_performance_alerts_without_violations(
        self, clock, installed_monitor
    ):
        with (
            patch.object(th, "get_metrics", return_value={"api": {"latency": 0.1}}),
            patch.object(th, "get_alerter") as get_alerter,
        ):
            count = await th.trigger_performance_alerts()

        assert count == 0
        get_alerter.assert_not_called()

    def test_get_performance_threshold_status_uses_global_monitor(
        self, clock, installed_monitor
    ):
        with patch.object(th, "get_metrics", return_value={"api": {"latency": 0.1}}):
            status = th.get_performance_threshold_status()

        assert status["total_thresholds"] == 1
        assert status["thresholds"][0]["name"] == "Latency"
        assert status["thresholds"][0]["status"] == "healthy"

    def test_polling_status_endpoint_does_not_advance_counters(
        self, clock, installed_monitor
    ):
        # get_performance_threshold_status backs GET /thresholds
        # (http_endpoints.py::_handle_thresholds); reading it must not count as
        # a check.
        installed_monitor.thresholds[0].consecutive_violations = 3
        with patch.object(th, "get_metrics", return_value={"api": {"latency": 4.0}}):
            th.get_performance_threshold_status()
            status = th.get_performance_threshold_status()

        assert installed_monitor.thresholds[0].consecutive_critical_count == 0
        assert status["thresholds"][0]["status"] == "violation"
        assert status["thresholds"][0]["consecutive_criticals"] == 0
