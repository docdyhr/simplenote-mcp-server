"""Tests for enhanced metrics with histograms and cache efficacy."""

from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.monitoring.metrics import (
    CacheMetrics,
    Histogram,
    TimeMetric,
    get_cache_metrics,
    get_memory_metrics,
    get_performance_metrics,
    record_cache_access_time,
    record_cache_eviction,
    record_cache_hit,
    record_cache_miss,
    update_cache_memory_usage,
)


class TestHistogram:
    """Test histogram functionality."""

    def test_histogram_initialization(self):
        """Test histogram initializes with default buckets."""
        hist = Histogram()
        assert len(hist.buckets) == 13  # Default bucket count
        assert float("inf") in hist.buckets
        assert all(count == 0 for count in hist.counts.values())

    def test_histogram_observe_single_value(self):
        """Test observing a single value."""
        hist = Histogram()
        hist.observe(0.05)  # 50ms

        # Should increment all buckets >= 50ms
        assert hist.counts[0.001] == 0  # 1ms bucket
        assert hist.counts[0.005] == 0  # 5ms bucket
        assert hist.counts[0.01] == 0  # 10ms bucket
        assert hist.counts[0.025] == 0  # 25ms bucket
        assert hist.counts[0.05] == 1  # 50ms bucket - first bucket >= value
        assert hist.counts[0.1] == 1  # 100ms bucket
        assert hist.counts[float("inf")] == 1  # +Inf bucket

    def test_histogram_observe_multiple_values(self):
        """Test observing multiple values."""
        hist = Histogram()
        values = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]

        for value in values:
            hist.observe(value)

        # Check that buckets accumulate correctly
        assert hist.counts[0.001] == 1  # Only 0.001 value
        assert hist.counts[0.005] == 2  # 0.001 + 0.005 values
        assert hist.counts[0.01] == 3  # 0.001 + 0.005 + 0.01 values
        assert hist.counts[float("inf")] == len(values)  # All values

    def test_histogram_get_bucket_counts(self):
        """Test getting bucket counts for JSON serialization."""
        hist = Histogram()
        hist.observe(0.05)

        counts = hist.get_bucket_counts()
        assert "+Inf" in counts
        assert counts["+Inf"] == 1
        assert counts["0.05"] == 1
        assert counts["0.001"] == 0

    def test_histogram_quantile_empty(self):
        """Test quantile calculation with no data."""
        hist = Histogram()
        assert hist.get_quantile(0.5) == 0.0
        assert hist.get_quantile(0.95) == 0.0

    def test_histogram_quantile_single_bucket(self):
        """Test quantile when all values fall in one bucket."""
        hist = Histogram()
        hist.observe(0.05)  # Falls in 0.05 bucket

        # All quantiles should return reasonable values
        p50 = hist.get_quantile(0.5)
        p95 = hist.get_quantile(0.95)

        # Values should be positive and finite
        assert p50 > 0
        assert p95 > 0
        assert p50 < float("inf")
        assert p95 < float("inf")

    def test_histogram_quantile_distributed(self):
        """Test quantile calculation with distributed values."""
        hist = Histogram()

        # Add values in a simple pattern
        for _ in range(50):
            hist.observe(0.01)  # 50% at 10ms
        for _ in range(50):
            hist.observe(0.1)  # 50% at 100ms

        # Test that quantiles are monotonic
        p25 = hist.get_quantile(0.25)
        p50 = hist.get_quantile(0.5)
        p75 = hist.get_quantile(0.75)
        p95 = hist.get_quantile(0.95)

        # Quantiles should be non-decreasing
        assert p25 <= p50 <= p75 <= p95
        # All should be positive
        assert p25 > 0 and p50 > 0 and p75 > 0 and p95 > 0


class TestEnhancedTimeMetric:
    """Test enhanced TimeMetric with histogram."""

    def test_time_metric_with_histogram(self):
        """Test TimeMetric creates and uses histogram."""
        metric = TimeMetric()

        # Add some timing data
        values = [0.001, 0.005, 0.01, 0.05, 0.1]
        for value in values:
            metric.add(value)

        assert metric.count == len(values)
        assert metric.avg_time == sum(values) / len(values)

        # Test histogram integration
        data = metric.to_dict()
        assert "histogram_buckets" in data
        assert "p50_time" in data
        assert "p90_time" in data
        assert "p95_time" in data
        assert "p99_time" in data

        # Verify histogram was populated
        assert data["histogram_buckets"]["+Inf"] == len(values)
        assert data["p50_time"] > 0
        assert data["p95_time"] >= data["p50_time"]

    def test_time_metric_percentiles_ordering(self):
        """Test that percentiles are properly ordered."""
        metric = TimeMetric()

        # Add values with known distribution
        for _ in range(50):
            metric.add(0.01)  # 50% at 10ms
        for _ in range(50):
            metric.add(0.1)  # 50% at 100ms

        data = metric.to_dict()

        # Percentiles should be ordered
        assert data["p50_time"] <= data["p90_time"]
        assert data["p90_time"] <= data["p95_time"]
        assert data["p95_time"] <= data["p99_time"]


class TestEnhancedCacheMetrics:
    """Test enhanced CacheMetrics with efficacy scoring."""

    def test_cache_metrics_initialization(self):
        """Test CacheMetrics initializes with enhanced fields."""
        cache_metrics = CacheMetrics()

        assert cache_metrics.hit_streak == 0
        assert cache_metrics.max_hit_streak == 0
        assert cache_metrics.miss_streak == 0
        assert cache_metrics.max_miss_streak == 0
        assert cache_metrics.total_memory_bytes == 0
        assert cache_metrics.avg_item_size_bytes == 0.0
        assert hasattr(cache_metrics, "evictions")
        assert hasattr(cache_metrics, "access_times")

    def test_cache_hit_tracking(self):
        """Test cache hit tracking with streaks."""
        cache_metrics = CacheMetrics()

        # Record consecutive hits
        cache_metrics.record_hit()
        cache_metrics.record_hit()
        cache_metrics.record_hit()

        assert cache_metrics.hits.count == 3
        assert cache_metrics.hit_streak == 3
        assert cache_metrics.max_hit_streak == 3
        assert cache_metrics.miss_streak == 0
        assert cache_metrics.hit_rate == 100.0

    def test_cache_miss_breaks_hit_streak(self):
        """Test that cache miss breaks hit streak."""
        cache_metrics = CacheMetrics()

        # Build up hit streak
        cache_metrics.record_hit()
        cache_metrics.record_hit()
        assert cache_metrics.hit_streak == 2

        # Miss should reset hit streak
        cache_metrics.record_miss()
        assert cache_metrics.hit_streak == 0
        assert cache_metrics.max_hit_streak == 2  # Preserved
        assert cache_metrics.miss_streak == 1
        assert abs(cache_metrics.hit_rate - 66.67) < 0.01  # 2/3 approximately

    def test_cache_eviction_tracking(self):
        """Test cache eviction tracking."""
        cache_metrics = CacheMetrics()

        cache_metrics.record_eviction()
        cache_metrics.record_eviction()

        assert cache_metrics.evictions.count == 2

    def test_cache_access_time_tracking(self):
        """Test cache access time tracking with histogram."""
        cache_metrics = CacheMetrics()

        cache_metrics.record_access_time(0.001)
        cache_metrics.record_access_time(0.01)
        cache_metrics.record_access_time(0.1)

        assert cache_metrics.access_times.count == 3
        assert cache_metrics.access_times.avg_time > 0

        # Verify histogram data is included
        data = cache_metrics.to_dict()
        assert "access_times" in data
        assert "histogram_buckets" in data["access_times"]

    def test_cache_memory_tracking(self):
        """Test cache memory usage tracking."""
        cache_metrics = CacheMetrics()

        # Update with some items
        cache_metrics.update_size(100, 1000)  # 100 items out of 1000 max
        cache_metrics.update_memory_usage(50000)  # 50KB total

        assert cache_metrics.size == 100
        assert cache_metrics.max_size == 1000
        assert cache_metrics.total_memory_bytes == 50000
        assert cache_metrics.avg_item_size_bytes == 500  # 50000 / 100

        data = cache_metrics.to_dict()
        assert data["utilization"] == 10.0  # 100/1000 * 100
        assert data["memory"]["total_bytes"] == 50000
        assert data["memory"]["avg_item_size_bytes"] == 500

    def test_cache_efficacy_score(self):
        """Test cache efficacy score calculation."""
        cache_metrics = CacheMetrics()

        # Optimal scenario: high hit rate, good streaks, reasonable utilization
        for _ in range(75):
            cache_metrics.record_hit()
        for _ in range(25):
            cache_metrics.record_miss()

        cache_metrics.update_size(750, 1000)  # 75% utilization (optimal)

        score = cache_metrics.efficacy_score
        assert 0 <= score <= 100
        assert score > 50  # Should be reasonably good

        data = cache_metrics.to_dict()
        assert "efficacy_score" in data
        assert data["efficacy_score"] == score

    def test_cache_efficacy_score_poor_performance(self):
        """Test efficacy score with poor cache performance."""
        cache_metrics = CacheMetrics()

        # Poor scenario: low hit rate, bad streaks
        for _ in range(10):
            cache_metrics.record_hit()
        for _ in range(90):
            cache_metrics.record_miss()

        score = cache_metrics.efficacy_score
        assert 0 <= score <= 100
        assert score < 30  # Should be poor

    def test_cache_streak_tracking(self):
        """Test detailed streak tracking."""
        cache_metrics = CacheMetrics()

        # Complex pattern: hits, misses, more hits
        cache_metrics.record_hit()
        cache_metrics.record_hit()
        cache_metrics.record_hit()  # 3-hit streak

        cache_metrics.record_miss()
        cache_metrics.record_miss()  # 2-miss streak, breaks hit streak

        cache_metrics.record_hit()
        cache_metrics.record_hit()
        cache_metrics.record_hit()
        cache_metrics.record_hit()
        cache_metrics.record_hit()  # 5-hit streak

        assert cache_metrics.max_hit_streak == 5
        assert cache_metrics.max_miss_streak == 2
        assert cache_metrics.hit_streak == 5  # Current
        assert cache_metrics.miss_streak == 0  # Reset by hits

        data = cache_metrics.to_dict()
        streaks = data["streaks"]
        assert streaks["max_hit_streak"] == 5
        assert streaks["max_miss_streak"] == 2
        assert streaks["current_hit_streak"] == 5
        assert streaks["current_miss_streak"] == 0


class TestMetricsBridgeFunctions:
    """Test the bridge functions for HTTP endpoints."""

    @patch("simplenote_mcp.server.monitoring.metrics._metrics_collector")
    def test_get_performance_metrics(self, mock_collector):
        """Test get_performance_metrics bridge function."""
        mock_data = {"test": "data"}
        mock_collector.get_metrics.return_value = mock_data

        result = get_performance_metrics()
        assert result == mock_data
        mock_collector.get_metrics.assert_called_once()

    @patch("simplenote_mcp.server.monitoring.metrics._metrics_collector")
    def test_get_cache_metrics(self, mock_collector):
        """Test get_cache_metrics bridge function."""
        mock_cache_metrics = MagicMock()
        mock_cache_data = {"cache": "data"}
        mock_cache_metrics.to_dict.return_value = mock_cache_data
        mock_collector.metrics.cache = mock_cache_metrics

        result = get_cache_metrics()
        assert result == mock_cache_data
        mock_cache_metrics.to_dict.assert_called_once()

    @patch("simplenote_mcp.server.monitoring.metrics._metrics_collector")
    def test_get_memory_metrics(self, mock_collector):
        """Test get_memory_metrics bridge function."""
        # Mock the resources metrics
        mock_resources = MagicMock()
        mock_resources.avg_cpu = 25.5
        mock_resources.avg_memory = 60.0
        mock_resources.disk_usage = 75.0
        mock_collector.metrics.resources = mock_resources

        result = get_memory_metrics()

        # Check that we got the expected structure
        assert "memory_usage" in result
        assert "cpu_usage" in result
        assert "memory_percent" in result
        assert "disk_usage_percent" in result

        # Check the values we set
        assert result["cpu_usage"] == 25.5
        assert result["memory_percent"] == 60.0
        assert result["disk_usage_percent"] == 75.0


class TestCacheIntegration:
    """Test integration of enhanced metrics with cache operations."""

    def test_metrics_functions_available(self):
        """Test that all new metrics functions are importable."""
        # These should not raise ImportError
        from simplenote_mcp.server.monitoring.metrics import (
            get_cache_metrics,
            get_memory_metrics,
            get_performance_metrics,
            record_cache_access_time,
            record_cache_eviction,
            update_cache_memory_usage,
        )

        # Functions should be callable
        assert callable(record_cache_eviction)
        assert callable(record_cache_access_time)
        assert callable(update_cache_memory_usage)
        assert callable(get_cache_metrics)
        assert callable(get_memory_metrics)
        assert callable(get_performance_metrics)

    def test_metrics_recording(self):
        """Test that metrics can be recorded without error."""
        # These should not raise exceptions
        record_cache_hit()
        record_cache_miss()
        record_cache_eviction()
        record_cache_access_time(0.05)
        update_cache_memory_usage(1024)

        # Getting metrics should work
        cache_data = get_cache_metrics()
        assert isinstance(cache_data, dict)

        memory_data = get_memory_metrics()
        assert isinstance(memory_data, dict)
        assert "memory_usage" in memory_data
        assert "cpu_usage" in memory_data

        perf_data = get_performance_metrics()
        assert isinstance(perf_data, dict)


if __name__ == "__main__":
    pytest.main([__file__])
