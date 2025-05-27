"""
Tests for the performance monitoring system.
"""

import asyncio
import json
import os
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.monitoring.metrics import (
    ApiMetrics,
    CacheMetrics,
    CounterMetric,
    MetricsCollector,
    PerformanceMetrics,
    ResourceMetrics,
    TimeMetric,
    ToolMetrics,
    get_metrics,
    record_api_call,
    record_cache_hit,
    record_cache_miss,
    record_response_time,
    record_tool_call,
    record_tool_execution_time,
    start_metrics_collection,
    update_cache_size,
)


class TestTimeMetric:
    """Test TimeMetric class functionality."""

    def test_time_metric_initialization(self):
        """Test TimeMetric initializes correctly."""
        metric = TimeMetric()
        assert metric.count == 0
        assert metric.total_time == 0.0
        assert metric.min_time == float("inf")
        assert metric.max_time == 0.0
        assert len(metric.recent_times) == 0
        assert metric.avg_time == 0.0

    def test_time_metric_add(self):
        """Test adding times to TimeMetric."""
        metric = TimeMetric()
        metric.add(1.5)
        metric.add(2.0)
        metric.add(0.5)

        assert metric.count == 3
        assert metric.total_time == 4.0
        assert metric.min_time == 0.5
        assert metric.max_time == 2.0
        assert metric.avg_time == 4.0 / 3  # (1.5 + 2.0 + 0.5) / 3
        assert len(metric.recent_times) == 3

    def test_time_metric_median_and_percentile(self):
        """Test median and 95th percentile calculations."""
        metric = TimeMetric()
        # Add multiple values to test percentile calculation
        for i in range(10):
            metric.add(i + 1)  # 1, 2, 3, ..., 10

        # Median should be 5.5 for values 1-10
        assert metric.median_time == 5.5
        # p95 should be close to 9.5
        assert metric.p95_time > 9.0

    def test_time_metric_to_dict(self):
        """Test TimeMetric serialization to dict."""
        metric = TimeMetric()
        metric.add(1.0)
        metric.add(2.0)

        data = metric.to_dict()
        assert data["count"] == 2
        assert data["total_time"] == 3.0
        assert data["min_time"] == 1.0
        assert data["max_time"] == 2.0
        assert data["avg_time"] == 1.5


class TestCounterMetric:
    """Test CounterMetric class functionality."""

    def test_counter_metric_initialization(self):
        """Test CounterMetric initializes correctly."""
        metric = CounterMetric()
        assert metric.count == 0
        assert len(metric.timestamps) == 0

    def test_counter_metric_increment(self):
        """Test incrementing counter."""
        metric = CounterMetric()
        metric.increment()
        metric.increment()

        assert metric.count == 2
        assert len(metric.timestamps) == 2

    def test_counter_metric_rate_calculations(self):
        """Test rate calculations."""
        metric = CounterMetric()
        # Add timestamps to simulate events
        current_time = time.time()
        for i in range(5):
            metric.count += 1
            metric.timestamps.append(current_time - i * 10)  # Events 10 seconds apart

        # Should have positive rates
        assert metric.rate_1min >= 0
        assert metric.rate_5min >= 0

    def test_counter_metric_to_dict(self):
        """Test CounterMetric serialization to dict."""
        metric = CounterMetric()
        for _ in range(10):
            metric.increment()

        data = metric.to_dict()
        assert data["count"] == 10
        assert "rate_1min" in data
        assert "rate_5min" in data


class TestApiMetrics:
    """Test ApiMetrics class functionality."""

    def test_api_metrics_initialization(self):
        """Test ApiMetrics initializes correctly."""
        metrics = ApiMetrics()
        assert metrics.calls.count == 0
        assert metrics.successes.count == 0
        assert metrics.failures.count == 0
        assert len(metrics.response_times) == 0
        assert len(metrics.errors_by_type) == 0

    def test_api_metrics_record_call_success(self):
        """Test recording successful API calls."""
        metrics = ApiMetrics()
        metrics.record_call("test_endpoint", success=True)

        assert metrics.calls.count == 1
        assert metrics.successes.count == 1
        assert metrics.failures.count == 0

    def test_api_metrics_record_call_failure(self):
        """Test recording failed API calls."""
        metrics = ApiMetrics()
        metrics.record_call("test_endpoint", success=False, error_type="timeout")

        assert metrics.calls.count == 1
        assert metrics.successes.count == 0
        assert metrics.failures.count == 1
        assert metrics.errors_by_type["timeout"].count == 1

    def test_api_metrics_record_response_time(self):
        """Test recording response times."""
        metrics = ApiMetrics()
        metrics.record_response_time("test_endpoint", 1.5)

        assert "test_endpoint" in metrics.response_times
        assert metrics.response_times["test_endpoint"].count == 1
        assert metrics.response_times["test_endpoint"].total_time == 1.5

    def test_api_metrics_success_rate(self):
        """Test API success rate calculation."""
        metrics = ApiMetrics()
        metrics.record_call("test", success=True)
        metrics.record_call("test", success=True)
        metrics.record_call("test", success=False)

        data = metrics.to_dict()
        # Success rate should be 66.67% (2 out of 3)
        assert abs(data["success_rate"] - 66.67) < 0.01

    def test_api_metrics_to_dict(self):
        """Test ApiMetrics serialization to dict."""
        metrics = ApiMetrics()
        metrics.record_call("test", success=True)
        metrics.record_call("test", success=False, error_type="error")
        metrics.record_response_time("test", 1.0)

        data = metrics.to_dict()
        assert "calls" in data
        assert "successes" in data
        assert "failures" in data
        assert "success_rate" in data
        assert "response_times" in data
        assert "errors_by_type" in data


class TestCacheMetrics:
    """Test CacheMetrics class functionality."""

    def test_cache_metrics_initialization(self):
        """Test CacheMetrics initializes correctly."""
        metrics = CacheMetrics()
        assert metrics.hits.count == 0
        assert metrics.misses.count == 0
        assert metrics.size == 0
        assert metrics.max_size == 0
        assert metrics.hit_rate == 0.0

    def test_cache_metrics_record_hit(self):
        """Test recording cache hits."""
        metrics = CacheMetrics()
        metrics.record_hit()

        assert metrics.hits.count == 1
        assert metrics.misses.count == 0

    def test_cache_metrics_record_miss(self):
        """Test recording cache misses."""
        metrics = CacheMetrics()
        metrics.record_miss()

        assert metrics.hits.count == 0
        assert metrics.misses.count == 1

    def test_cache_metrics_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = CacheMetrics()
        metrics.record_hit()
        metrics.record_hit()
        metrics.record_miss()

        # Hit rate should be 66.67% (2 out of 3)
        assert abs(metrics.hit_rate - 66.67) < 0.01

    def test_cache_metrics_update_size(self):
        """Test updating cache size."""
        metrics = CacheMetrics()
        metrics.update_size(50, 100)

        assert metrics.size == 50
        assert metrics.max_size == 100

    def test_cache_metrics_to_dict(self):
        """Test CacheMetrics serialization to dict."""
        metrics = CacheMetrics()
        metrics.record_hit()
        metrics.record_miss()
        metrics.update_size(50, 100)

        data = metrics.to_dict()
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data
        assert "size" in data
        assert "max_size" in data
        assert "utilization" in data


class TestToolMetrics:
    """Test ToolMetrics class functionality."""

    def test_tool_metrics_initialization(self):
        """Test ToolMetrics initializes correctly."""
        metrics = ToolMetrics()
        assert len(metrics.tool_calls) == 0
        assert len(metrics.execution_times) == 0

    def test_tool_metrics_record_call(self):
        """Test recording tool calls."""
        metrics = ToolMetrics()
        metrics.record_tool_call("search_notes")
        metrics.record_tool_call("search_notes")
        metrics.record_tool_call("create_note")

        assert metrics.tool_calls["search_notes"].count == 2
        assert metrics.tool_calls["create_note"].count == 1

    def test_tool_metrics_record_execution_time(self):
        """Test recording tool execution times."""
        metrics = ToolMetrics()
        metrics.record_execution_time("search_notes", 1.5)

        assert "search_notes" in metrics.execution_times
        assert metrics.execution_times["search_notes"].count == 1
        assert metrics.execution_times["search_notes"].total_time == 1.5

    def test_tool_metrics_to_dict(self):
        """Test ToolMetrics serialization to dict."""
        metrics = ToolMetrics()
        metrics.record_tool_call("search_notes")
        metrics.record_execution_time("search_notes", 1.0)

        data = metrics.to_dict()
        assert "tool_calls" in data
        assert "execution_times" in data
        assert "search_notes" in data["tool_calls"]
        assert "search_notes" in data["execution_times"]


class TestResourceMetrics:
    """Test ResourceMetrics class functionality."""

    def test_resource_metrics_initialization(self):
        """Test ResourceMetrics initializes correctly."""
        metrics = ResourceMetrics()
        assert len(metrics.cpu_samples) == 0
        assert len(metrics.memory_samples) == 0
        assert metrics.disk_usage == 0.0

    @patch("simplenote_mcp.server.monitoring.metrics.psutil")
    def test_resource_metrics_update(self, mock_psutil):
        """Test updating resource metrics."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.percent = 70.0
        mock_psutil.virtual_memory.return_value = mock_memory
        mock_disk = MagicMock()
        mock_disk.percent = 80.0
        mock_psutil.disk_usage.return_value = mock_disk

        metrics = ResourceMetrics()
        metrics.update()

        assert len(metrics.cpu_samples) == 1
        assert len(metrics.memory_samples) == 1
        assert metrics.cpu_samples[0] == 50.0
        assert metrics.memory_samples[0] == 70.0
        assert metrics.disk_usage == 80.0

    def test_resource_metrics_averages(self):
        """Test resource metrics average calculations."""
        metrics = ResourceMetrics()
        # Manually add samples
        metrics.cpu_samples.extend([10.0, 20.0, 30.0])
        metrics.memory_samples.extend([40.0, 50.0, 60.0])

        assert metrics.avg_cpu == 20.0
        assert metrics.max_cpu == 30.0
        assert metrics.avg_memory == 50.0
        assert metrics.max_memory == 60.0

    def test_resource_metrics_to_dict(self):
        """Test ResourceMetrics serialization to dict."""
        metrics = ResourceMetrics()
        metrics.cpu_samples.extend([10.0, 20.0])
        metrics.memory_samples.extend([30.0, 40.0])
        metrics.disk_usage = 50.0

        data = metrics.to_dict()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert data["cpu"]["avg"] == 15.0
        assert data["memory"]["avg"] == 35.0
        assert data["disk"]["usage_percent"] == 50.0


class TestPerformanceMetrics:
    """Test PerformanceMetrics class functionality."""

    def test_performance_metrics_initialization(self):
        """Test PerformanceMetrics initializes correctly."""
        metrics = PerformanceMetrics()
        assert isinstance(metrics.api, ApiMetrics)
        assert isinstance(metrics.cache, CacheMetrics)
        assert isinstance(metrics.resources, ResourceMetrics)
        assert isinstance(metrics.tools, ToolMetrics)
        assert metrics.server_start_time > 0

    def test_performance_metrics_to_dict(self):
        """Test PerformanceMetrics serialization to dict."""
        metrics = PerformanceMetrics()

        data = metrics.to_dict()
        assert "timestamp" in data
        assert "server_info" in data
        assert "api" in data
        assert "cache" in data
        assert "resources" in data
        assert "tools" in data
        assert "uptime_seconds" in data["server_info"]
        assert "uptime" in data["server_info"]


class TestMetricsCollector:
    """Test MetricsCollector class functionality."""

    def test_metrics_collector_singleton(self):
        """Test MetricsCollector follows singleton pattern."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2

    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initializes correctly."""
        collector = MetricsCollector()
        assert isinstance(collector.metrics, PerformanceMetrics)
        assert hasattr(collector, "_collection_thread")
        assert hasattr(collector, "_running")
        assert hasattr(collector, "_collection_interval")

    def test_metrics_collector_record_api_call(self):
        """Test recording API calls through collector."""
        collector = MetricsCollector()
        initial_count = collector.metrics.api.calls.count

        collector.record_api_call("test_endpoint", success=True)

        assert collector.metrics.api.calls.count == initial_count + 1
        assert collector.metrics.api.successes.count >= 1

    def test_metrics_collector_record_cache_operations(self):
        """Test recording cache operations through collector."""
        collector = MetricsCollector()
        initial_hits = collector.metrics.cache.hits.count
        initial_misses = collector.metrics.cache.misses.count

        collector.record_cache_hit()
        collector.record_cache_miss()

        assert collector.metrics.cache.hits.count == initial_hits + 1
        assert collector.metrics.cache.misses.count == initial_misses + 1

    def test_metrics_collector_record_tool_operations(self):
        """Test recording tool operations through collector."""
        collector = MetricsCollector()

        collector.record_tool_call("search_notes")
        collector.record_tool_execution_time("search_notes", 1.5)

        assert "search_notes" in collector.metrics.tools.tool_calls
        assert collector.metrics.tools.tool_calls["search_notes"].count >= 1
        assert "search_notes" in collector.metrics.tools.execution_times

    def test_metrics_collector_get_metrics(self):
        """Test getting all metrics through collector."""
        collector = MetricsCollector()

        # Record some test data
        collector.record_api_call("test", success=True)
        collector.record_cache_hit()

        metrics = collector.get_metrics()
        assert "api" in metrics
        assert "cache" in metrics
        assert "resources" in metrics
        assert "tools" in metrics
        assert "server_info" in metrics


class TestGlobalFunctions:
    """Test global monitoring functions."""

    def test_record_api_call_function(self):
        """Test global record_api_call function."""
        collector = MetricsCollector()
        initial_count = collector.metrics.api.calls.count

        record_api_call("test_endpoint", success=True)

        assert collector.metrics.api.calls.count == initial_count + 1

    def test_record_cache_hit_function(self):
        """Test global record_cache_hit function."""
        collector = MetricsCollector()
        initial_count = collector.metrics.cache.hits.count

        record_cache_hit()

        assert collector.metrics.cache.hits.count == initial_count + 1

    def test_record_cache_miss_function(self):
        """Test global record_cache_miss function."""
        collector = MetricsCollector()
        initial_count = collector.metrics.cache.misses.count

        record_cache_miss()

        assert collector.metrics.cache.misses.count == initial_count + 1

    def test_record_response_time_function(self):
        """Test global record_response_time function."""
        collector = MetricsCollector()

        record_response_time("test_endpoint", 2.5)

        assert "test_endpoint" in collector.metrics.api.response_times
        assert collector.metrics.api.response_times["test_endpoint"].count >= 1

    def test_record_tool_functions(self):
        """Test global tool recording functions."""
        collector = MetricsCollector()

        record_tool_call("search_notes")
        record_tool_execution_time("search_notes", 1.0)

        assert "search_notes" in collector.metrics.tools.tool_calls
        assert "search_notes" in collector.metrics.tools.execution_times

    def test_update_cache_size_function(self):
        """Test global update_cache_size function."""
        collector = MetricsCollector()

        update_cache_size(50, 100)

        assert collector.metrics.cache.size == 50
        assert collector.metrics.cache.max_size == 100

    def test_get_metrics_function(self):
        """Test global get_metrics function."""
        # Record some test data
        record_api_call("test", success=True)
        record_cache_hit()

        metrics = get_metrics()
        assert isinstance(metrics, dict)
        assert "api" in metrics
        assert "cache" in metrics


class TestMetricsCollection:
    """Test metrics collection and persistence functionality."""

    @patch("threading.Thread")
    def test_start_metrics_collection(self, mock_thread):
        """Test starting metrics collection."""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        start_metrics_collection(30)

        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    def test_performance_metrics_save_to_file(self):
        """Test saving metrics to file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name

        try:
            metrics = PerformanceMetrics()
            # Mock the METRICS_FILE to point to our temp file
            with patch(
                "simplenote_mcp.server.monitoring.metrics.METRICS_FILE", temp_path
            ):
                metrics.save_to_file()

            # Verify file was created and has content
            assert os.path.exists(temp_path)
            with open(temp_path) as f:
                data = json.load(f)
                assert "api" in data
                assert "cache" in data
                assert "server_info" in data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestThreadSafety:
    """Test thread safety of metrics collection."""

    def test_concurrent_api_calls(self):
        """Test concurrent API call recording."""
        collector = MetricsCollector()
        initial_count = collector.metrics.api.calls.count

        num_threads = 10
        calls_per_thread = 5

        def record_calls():
            for _ in range(calls_per_thread):
                record_api_call("test", success=True)

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=record_calls)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have recorded all calls
        expected_total = initial_count + (num_threads * calls_per_thread)
        assert collector.metrics.api.calls.count == expected_total

    def test_concurrent_cache_operations(self):
        """Test concurrent cache operation recording."""
        collector = MetricsCollector()
        initial_hits = collector.metrics.cache.hits.count
        initial_misses = collector.metrics.cache.misses.count

        num_threads = 10
        ops_per_thread = 5

        def record_cache_ops():
            for _ in range(ops_per_thread):
                record_cache_hit()
                record_cache_miss()

        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=record_cache_ops)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have recorded all operations
        expected_hits = initial_hits + (num_threads * ops_per_thread)
        expected_misses = initial_misses + (num_threads * ops_per_thread)
        assert collector.metrics.cache.hits.count == expected_hits
        assert collector.metrics.cache.misses.count == expected_misses


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_time_metric_empty_calculations(self):
        """Test calculations with no data."""
        metric = TimeMetric()
        assert metric.avg_time == 0.0
        assert metric.median_time == 0.0
        # p95_time should be 0 when no data
        assert metric.p95_time == 0.0

    def test_cache_metrics_hit_rate_no_operations(self):
        """Test hit rate calculation with no cache operations."""
        metrics = CacheMetrics()
        assert metrics.hit_rate == 0.0

    def test_api_metrics_success_rate_no_requests(self):
        """Test success rate calculation with no requests."""
        metrics = ApiMetrics()
        data = metrics.to_dict()
        assert data["success_rate"] == 100.0  # Default success rate

    def test_time_metric_very_small_values(self):
        """Test handling of very small time values."""
        metric = TimeMetric()
        metric.add(0.000001)  # 1 microsecond

        assert metric.count == 1
        assert metric.total_time == 0.000001
        assert metric.min_time == 0.000001

    def test_counter_metric_very_large_numbers(self):
        """Test handling of very large counter values."""
        metric = CounterMetric()
        large_number = 1000000

        for _ in range(large_number):
            metric.increment()

        assert metric.count == large_number

    def test_tool_metrics_special_characters(self):
        """Test tool names with special characters."""
        metrics = ToolMetrics()
        tool_name = "tool-with_special.chars@123"

        metrics.record_tool_call(tool_name)

        assert tool_name in metrics.tool_calls
        assert metrics.tool_calls[tool_name].count == 1


class TestAsyncCompatibility:
    """Test async compatibility of metrics collection."""

    @pytest.mark.asyncio
    async def test_async_metrics_recording(self):
        """Test that metrics can be recorded from async contexts."""
        collector = MetricsCollector()
        initial_count = collector.metrics.api.calls.count

        async def async_operation():
            record_api_call("async_test", success=True)
            await asyncio.sleep(0.01)
            record_response_time("async_test", 0.01)

        # Run multiple async operations
        await asyncio.gather(*[async_operation() for _ in range(5)])

        assert collector.metrics.api.calls.count == initial_count + 5


if __name__ == "__main__":
    pytest.main([__file__])
