"""
Performance metrics collection and reporting for Simplenote MCP Server.

This module provides classes and functions for collecting and reporting
performance metrics from the Simplenote MCP Server, including API call statistics,
response times, cache performance, and server resource usage.
"""

import json
import platform
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    import sys
    import types

    psutil = types.ModuleType("psutil")

    def cpu_percent(_interval: float = 0.1) -> float:
        """Mock CPU percent function when psutil is not available."""
        return 0.0

    def virtual_memory() -> Any:
        """Mock virtual memory function when psutil is not available."""

        class VirtualMemory:
            percent = 0.0

        return VirtualMemory()

    def disk_usage(_path: str) -> Any:
        """Mock disk usage function when psutil is not available."""

        class DiskUsage:
            percent = 0.0

        return DiskUsage()

    psutil.cpu_percent = cpu_percent
    psutil.virtual_memory = virtual_memory
    psutil.disk_usage = disk_usage
    sys.modules["psutil"] = psutil

from ..logging import get_logger

# Set up logging
logger = get_logger("monitoring.metrics")

# Constants
MAX_SAMPLES = 1000  # Maximum number of samples to keep for time-series metrics
METRICS_DIR = Path.home() / ".simplenote_mcp" / "logs" / "metrics"
METRICS_FILE = METRICS_DIR / "performance_metrics.json"

# Ensure metrics directory exists
METRICS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Histogram:
    """Latency histogram with configurable buckets."""

    # Default buckets: 1ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s, +Inf
    DEFAULT_BUCKETS = [
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        float("inf"),
    ]

    buckets: list[float] = field(
        default_factory=lambda: Histogram.DEFAULT_BUCKETS.copy()
    )
    counts: dict[float, int] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize bucket counts."""
        for bucket in self.buckets:
            self.counts[bucket] = 0

    def observe(self, value: float) -> None:
        """Add an observation to the histogram."""
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1

    def get_bucket_counts(self) -> dict[str, int]:
        """Get counts for each bucket with string keys for JSON serialization."""
        result = {}
        for bucket, count in self.counts.items():
            if bucket == float("inf"):
                result["+Inf"] = count
            else:
                result[str(bucket)] = count
        return result

    def get_quantile(self, quantile: float) -> float:
        """Get approximate quantile value from histogram buckets."""
        if not any(self.counts.values()):
            return 0.0

        total_count = sum(self.counts.values())
        target_count = total_count * quantile

        cumulative = 0
        prev_bucket = 0.0

        for bucket in sorted(self.buckets):
            bucket_count = self.counts[bucket]
            if cumulative + bucket_count >= target_count:
                # Found the bucket containing our quantile
                if bucket_count == 0:
                    # Empty bucket, return previous bucket value
                    return prev_bucket
                elif cumulative == target_count:
                    # Exactly at bucket boundary
                    return prev_bucket if prev_bucket > 0 else bucket * 0.1
                else:
                    # Interpolate within bucket
                    bucket_position = (target_count - cumulative) / bucket_count
                    if bucket == float("inf"):
                        # For infinity bucket, estimate based on previous
                        return prev_bucket * (1 + bucket_position)
                    return prev_bucket + (bucket - prev_bucket) * bucket_position

            cumulative += bucket_count
            prev_bucket = bucket

        return prev_bucket if prev_bucket < float("inf") else 10.0


@dataclass
class TimeMetric:
    """Time-based metric with statistical tracking and histogram."""

    count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    recent_times: deque[float] = field(
        default_factory=lambda: deque(maxlen=MAX_SAMPLES)
    )
    histogram: Histogram = field(default_factory=Histogram)

    def add(self, duration: float) -> None:
        """Add a new time measurement to this metric."""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.recent_times.append(duration)
        self.histogram.observe(duration)

    @property
    def avg_time(self) -> float:
        """Get the average time for this metric."""
        return self.total_time / self.count if self.count > 0 else 0.0

    @property
    def median_time(self) -> float:
        """Get the median time for recent measurements."""
        if not self.recent_times:
            return 0.0
        return statistics.median(self.recent_times)

    @property
    def p50_time(self) -> float:
        """Get the 50th percentile (median) from histogram."""
        return self.histogram.get_quantile(0.5)

    @property
    def p90_time(self) -> float:
        """Get the 90th percentile time from histogram."""
        return self.histogram.get_quantile(0.9)

    @property
    def p95_time(self) -> float:
        """Get the 95th percentile time from histogram."""
        return self.histogram.get_quantile(0.95)

    @property
    def p99_time(self) -> float:
        """Get the 99th percentile time from histogram."""
        return self.histogram.get_quantile(0.99)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "count": self.count,
            "total_time": self.total_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0,
            "max_time": self.max_time,
            "avg_time": self.avg_time,
            "median_time": self.median_time,
            "p50_time": self.p50_time,
            "p90_time": self.p90_time,
            "p95_time": self.p95_time,
            "p99_time": self.p99_time,
            "histogram_buckets": self.histogram.get_bucket_counts(),
        }


@dataclass
class CounterMetric:
    """Counter metric for tracking counts of events."""

    count: int = 0
    timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_SAMPLES))

    def increment(self) -> None:
        """Increment this counter."""
        self.count += 1
        self.timestamps.append(time.time())

    @property
    def rate_1min(self) -> float:
        """Get the rate per minute for the last minute."""
        now = time.time()
        one_min_ago = now - 60
        recent = [ts for ts in self.timestamps if ts > one_min_ago]
        return len(recent) * 60 / max(now - one_min_ago, 1)

    @property
    def rate_5min(self) -> float:
        """Get the rate per minute for the last 5 minutes."""
        now = time.time()
        five_min_ago = now - 300
        recent = [ts for ts in self.timestamps if ts > five_min_ago]
        return len(recent) * 60 / max(now - five_min_ago, 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "count": self.count,
            "rate_1min": self.rate_1min,
            "rate_5min": self.rate_5min,
        }


@dataclass
class ApiMetrics:
    """Metrics for API calls."""

    calls: CounterMetric = field(default_factory=CounterMetric)
    successes: CounterMetric = field(default_factory=CounterMetric)
    failures: CounterMetric = field(default_factory=CounterMetric)
    response_times: dict[str, TimeMetric] = field(
        default_factory=lambda: defaultdict(TimeMetric)
    )
    errors_by_type: dict[str, CounterMetric] = field(
        default_factory=lambda: defaultdict(CounterMetric)
    )

    def record_call(
        self, _endpoint: str, success: bool = True, error_type: str | None = None
    ) -> None:
        """Record an API call with its outcome."""
        self.calls.increment()
        if success:
            self.successes.increment()
        else:
            self.failures.increment()
            if error_type:
                self.errors_by_type[error_type].increment()

    def record_response_time(self, endpoint: str, duration: float) -> None:
        """Record the response time for an API call."""
        self.response_times[endpoint].add(duration)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "calls": self.calls.to_dict(),
            "successes": self.successes.to_dict(),
            "failures": self.failures.to_dict(),
            "success_rate": (
                (self.successes.count / self.calls.count * 100)
                if self.calls.count > 0
                else 100.0
            ),
            "response_times": {
                endpoint: metric.to_dict()
                for endpoint, metric in self.response_times.items()
            },
            "errors_by_type": {
                error_type: counter.to_dict()
                for error_type, counter in self.errors_by_type.items()
            },
        }


@dataclass
class CacheMetrics:
    """Enhanced metrics for cache performance."""

    hits: CounterMetric = field(default_factory=CounterMetric)
    misses: CounterMetric = field(default_factory=CounterMetric)
    evictions: CounterMetric = field(default_factory=CounterMetric)
    size: int = 0
    max_size: int = 0
    access_times: TimeMetric = field(default_factory=TimeMetric)

    # Cache efficacy tracking
    hit_streak: int = 0
    max_hit_streak: int = 0
    miss_streak: int = 0
    max_miss_streak: int = 0

    # Memory efficiency
    total_memory_bytes: int = 0
    avg_item_size_bytes: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Get the cache hit rate (percentage)."""
        total = self.hits.count + self.misses.count
        return (self.hits.count / total * 100) if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Get the cache miss rate (percentage)."""
        return 100.0 - self.hit_rate

    @property
    def efficacy_score(self) -> float:
        """Calculate cache efficacy score (0-100) based on hit rate, streaks, and memory usage."""
        if self.hits.count + self.misses.count == 0:
            return 0.0

        # Base score from hit rate (0-70 points)
        hit_score = self.hit_rate * 0.7

        # Streak bonus/penalty (0-20 points)
        streak_score = min(20, self.max_hit_streak) - min(
            10, self.max_miss_streak * 0.5
        )

        # Memory efficiency (0-10 points)
        utilization = self.size / self.max_size if self.max_size > 0 else 0
        memory_score = 10 * (
            1 - abs(utilization - 0.75)
        )  # Optimal around 75% utilization

        return max(0, min(100, hit_score + streak_score + memory_score))

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits.increment()
        self.hit_streak += 1
        self.max_hit_streak = max(self.max_hit_streak, self.hit_streak)
        self.miss_streak = 0

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses.increment()
        self.miss_streak += 1
        self.max_miss_streak = max(self.max_miss_streak, self.miss_streak)
        self.hit_streak = 0

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        self.evictions.increment()

    def record_access_time(self, duration: float) -> None:
        """Record the time taken for a cache access."""
        self.access_times.add(duration)

    def update_size(self, current_size: int, max_size: int) -> None:
        """Update the cache size metrics."""
        self.size = current_size
        self.max_size = max_size

    def update_memory_usage(self, total_bytes: int) -> None:
        """Update memory usage statistics."""
        self.total_memory_bytes = total_bytes
        if self.size > 0:
            self.avg_item_size_bytes = total_bytes / self.size

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hits": self.hits.to_dict(),
            "misses": self.misses.to_dict(),
            "evictions": self.evictions.to_dict(),
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "efficacy_score": self.efficacy_score,
            "size": self.size,
            "max_size": self.max_size,
            "utilization": (
                (self.size / self.max_size * 100) if self.max_size > 0 else 0.0
            ),
            "streaks": {
                "current_hit_streak": self.hit_streak,
                "max_hit_streak": self.max_hit_streak,
                "current_miss_streak": self.miss_streak,
                "max_miss_streak": self.max_miss_streak,
            },
            "access_times": self.access_times.to_dict(),
            "memory": {
                "total_bytes": self.total_memory_bytes,
                "avg_item_size_bytes": self.avg_item_size_bytes,
            },
        }


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""

    cpu_samples: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_SAMPLES))
    memory_samples: deque[float] = field(
        default_factory=lambda: deque(maxlen=MAX_SAMPLES)
    )
    disk_usage: float = 0.0

    def update(self) -> None:
        """Update resource metrics with current system values."""
        try:
            # CPU usage (percentage)
            cpu_percent = psutil.cpu_percent(None)
            self.cpu_samples.append(cpu_percent)

            # Memory usage (percentage)
            memory_info = psutil.virtual_memory()
            self.memory_samples.append(memory_info.percent)

            # Disk usage for the logs directory
            disk_usage = psutil.disk_usage(str(METRICS_DIR.parent))
            self.disk_usage = disk_usage.percent
        except Exception as e:
            logger.error(f"Error updating resource metrics: {str(e)}")

    @property
    def avg_cpu(self) -> float:
        """Get average CPU usage."""
        return statistics.mean(self.cpu_samples) if self.cpu_samples else 0.0

    @property
    def max_cpu(self) -> float:
        """Get maximum CPU usage."""
        return max(self.cpu_samples) if self.cpu_samples else 0.0

    @property
    def avg_memory(self) -> float:
        """Get average memory usage."""
        return statistics.mean(self.memory_samples) if self.memory_samples else 0.0

    @property
    def max_memory(self) -> float:
        """Get maximum memory usage."""
        return max(self.memory_samples) if self.memory_samples else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cpu": {
                "current": self.cpu_samples[-1] if self.cpu_samples else 0.0,
                "avg": self.avg_cpu,
                "max": self.max_cpu,
            },
            "memory": {
                "current": self.memory_samples[-1] if self.memory_samples else 0.0,
                "avg": self.avg_memory,
                "max": self.max_memory,
            },
            "disk": {"usage_percent": self.disk_usage},
        }


@dataclass
class ToolMetrics:
    """Metrics for tool usage."""

    tool_calls: dict[str, CounterMetric] = field(
        default_factory=lambda: defaultdict(CounterMetric)
    )
    execution_times: dict[str, TimeMetric] = field(
        default_factory=lambda: defaultdict(TimeMetric)
    )

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_calls[tool_name].increment()

    def record_execution_time(self, tool_name: str, duration: float) -> None:
        """Record the execution time for a tool call."""
        self.execution_times[tool_name].add(duration)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_calls": {
                tool: counter.to_dict() for tool, counter in self.tool_calls.items()
            },
            "execution_times": {
                tool: metric.to_dict() for tool, metric in self.execution_times.items()
            },
        }


@dataclass
class PerformanceMetrics:
    """Overall performance metrics collection."""

    api: ApiMetrics = field(default_factory=ApiMetrics)
    cache: CacheMetrics = field(default_factory=CacheMetrics)
    resources: ResourceMetrics = field(default_factory=ResourceMetrics)
    tools: ToolMetrics = field(default_factory=ToolMetrics)

    server_start_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        now = time.time()
        uptime_seconds = now - self.server_start_time

        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

        return {
            "timestamp": datetime.now().isoformat(),
            "server_info": {
                "start_time": datetime.fromtimestamp(
                    self.server_start_time
                ).isoformat(),
                "uptime_seconds": uptime_seconds,
                "uptime": uptime_str,
                "platform": platform.system(),
                "python_version": platform.python_version(),
            },
            "api": self.api.to_dict(),
            "cache": self.cache.to_dict(),
            "resources": self.resources.to_dict(),
            "tools": self.tools.to_dict(),
        }

    def save_to_file(self) -> None:
        """Save metrics to a JSON file."""
        try:
            # Determine the file path: support Path, callable, or raw path
            if isinstance(METRICS_FILE, Path):
                file_path = METRICS_FILE
            elif callable(METRICS_FILE):
                file_path = METRICS_FILE()
            else:
                file_path = Path(METRICS_FILE)
            with open(file_path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            self.last_updated = time.time()
            logger.debug("Performance metrics saved to file")
        except Exception as e:
            logger.error(f"Error saving performance metrics: {str(e)}")


class MetricsCollector:
    """Singleton class for collecting and managing performance metrics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsCollector":
        """Create a singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        if self._initialized:
            return

        self.metrics = PerformanceMetrics()
        self._collection_thread: threading.Thread | None = None
        self._running = False
        self._collection_interval = 60  # seconds
        self._initialized = True
        logger.info("Metrics collector initialized")

    def start_collection(self, interval: int = 60) -> None:
        """Start collecting metrics at the specified interval."""
        if self._running:
            return

        self._collection_interval = interval
        self._running = True

        def collection_task() -> None:
            logger.info(f"Starting metrics collection (interval: {interval}s)")
            while self._running:
                try:
                    # Update resource metrics
                    self.metrics.resources.update()

                    # Save metrics to file
                    self.metrics.save_to_file()

                    # Check performance thresholds and trigger alerts
                    try:
                        # Import here to avoid circular imports
                        import asyncio
                        import threading

                        from .thresholds import trigger_performance_alerts

                        # Run in a separate thread with its own event loop for async tasks
                        def run_threshold_check():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(trigger_performance_alerts())
                                loop.close()
                            except Exception as e:
                                logger.error(
                                    f"Error in threshold check thread: {str(e)}"
                                )

                        # Run threshold checks in background thread
                        threshold_thread = threading.Thread(
                            target=run_threshold_check, daemon=True
                        )
                        threshold_thread.start()
                    except Exception as threshold_error:
                        logger.error(
                            f"Error in threshold monitoring: {str(threshold_error)}"
                        )

                    # Sleep for the collection interval
                    time.sleep(self._collection_interval)
                except Exception as e:
                    logger.error(f"Error in metrics collection: {str(e)}")
                    time.sleep(5)  # Sleep briefly before retrying

        self._collection_thread = threading.Thread(
            target=collection_task, daemon=True, name="MetricsCollector"
        )
        self._collection_thread.start()

    def stop_collection(self) -> None:
        """Stop collecting metrics."""
        if not self._running:
            return

        self._running = False
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5)
        logger.info("Metrics collection stopped")

    def get_metrics(self) -> dict[str, Any]:
        """Get a dictionary representation of current metrics."""
        return self.metrics.to_dict()

    def record_api_call(
        self, endpoint: str, success: bool = True, error_type: str | None = None
    ) -> None:
        """Record an API call with outcome."""
        self.metrics.api.record_call(endpoint, success, error_type)

    def record_response_time(self, endpoint: str, duration: float) -> None:
        """Record an API response time."""
        self.metrics.api.record_response_time(endpoint, duration)

    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.metrics.cache.record_hit()

    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.metrics.cache.record_miss()

    def update_cache_size(self, current_size: int, max_size: int) -> None:
        """Update cache size metrics."""
        self.metrics.cache.update_size(current_size, max_size)

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.metrics.tools.record_tool_call(tool_name)

    def record_tool_execution_time(self, tool_name: str, duration: float) -> None:
        """Record a tool execution time."""
        self.metrics.tools.record_execution_time(tool_name, duration)


# Singleton metrics collector instance
_metrics_collector = MetricsCollector()


def start_metrics_collection(interval: int = 60) -> None:
    """Start collecting metrics at the specified interval (in seconds)."""
    _metrics_collector.start_collection(interval)


def get_metrics() -> dict[str, Any]:
    """Get current performance metrics."""
    return _metrics_collector.get_metrics()


def record_api_call(
    endpoint: str, success: bool = True, error_type: str | None = None
) -> None:
    """Record an API call with outcome."""
    _metrics_collector.record_api_call(endpoint, success, error_type)


def record_response_time(endpoint: str, duration: float) -> None:
    """Record an API response time."""
    _metrics_collector.record_response_time(endpoint, duration)


def record_cache_hit() -> None:
    """Record a cache hit."""
    _metrics_collector.record_cache_hit()


def record_cache_miss() -> None:
    """Record a cache miss."""
    _metrics_collector.record_cache_miss()


def update_cache_size(current_size: int, max_size: int) -> None:
    """Update cache size metrics."""
    _metrics_collector.update_cache_size(current_size, max_size)


def record_tool_call(tool_name: str) -> None:
    """Record a tool call."""
    _metrics_collector.record_tool_call(tool_name)


def record_tool_execution_time(tool_name: str, duration: float) -> None:
    """Record a tool execution time."""
    _metrics_collector.record_tool_execution_time(tool_name, duration)


def record_cache_eviction() -> None:
    """Record a cache eviction."""
    _metrics_collector.metrics.cache.record_eviction()


def record_cache_access_time(duration: float) -> None:
    """Record cache access time."""
    _metrics_collector.metrics.cache.record_access_time(duration)


def update_cache_memory_usage(total_bytes: int) -> None:
    """Update cache memory usage."""
    _metrics_collector.metrics.cache.update_memory_usage(total_bytes)


# HTTP endpoint bridge functions
def get_performance_metrics() -> dict[str, Any]:
    """Get performance metrics for HTTP endpoints."""
    return _metrics_collector.get_metrics()


def get_cache_metrics() -> dict[str, Any]:
    """Get cache metrics for HTTP endpoints."""
    return _metrics_collector.metrics.cache.to_dict()


def get_memory_metrics() -> dict[str, Any]:
    """Get memory/resource metrics for HTTP endpoints."""
    resources = _metrics_collector.metrics.resources
    return {
        "memory_usage": getattr(resources, "total_memory_bytes", 0),
        "cpu_usage": resources.avg_cpu,
        "memory_percent": resources.avg_memory,
        "disk_usage_percent": resources.disk_usage,
    }


# Initialize metrics collection when this module is imported
logger.info("Performance metrics module initialized")
