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
from typing import Any, Deque, Dict, Optional

try:
    import psutil
except ImportError:
    import sys
    import types

    psutil = types.ModuleType("psutil")

    def cpu_percent(interval=0.1):
        return 0.0

    def virtual_memory():
        class VirtualMemory:
            percent = 0.0

        return VirtualMemory()

    def disk_usage(path):
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
METRICS_DIR = Path(__file__).parent.parent.parent / "logs" / "metrics"
METRICS_FILE = METRICS_DIR / "performance_metrics.json"

# Ensure metrics directory exists
METRICS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TimeMetric:
    """Time-based metric with statistical tracking."""

    count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    recent_times: Deque[float] = field(
        default_factory=lambda: deque(maxlen=MAX_SAMPLES)
    )

    def add(self, duration: float) -> None:
        """Add a new time measurement to this metric."""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.recent_times.append(duration)

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
    def p95_time(self) -> float:
        """Get the 95th percentile time for recent measurements."""
        if len(self.recent_times) < 5:  # Need at least a few samples for percentiles
            return self.max_time
        return statistics.quantiles(self.recent_times, n=20)[-1]  # 95th percentile

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "count": self.count,
            "total_time": self.total_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0,
            "max_time": self.max_time,
            "avg_time": self.avg_time,
            "median_time": self.median_time,
            "p95_time": self.p95_time,
        }


@dataclass
class CounterMetric:
    """Counter metric for tracking counts of events."""

    count: int = 0
    timestamps: Deque[float] = field(default_factory=lambda: deque(maxlen=MAX_SAMPLES))

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

    def to_dict(self) -> Dict[str, Any]:
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
    response_times: Dict[str, TimeMetric] = field(
        default_factory=lambda: defaultdict(TimeMetric)
    )
    errors_by_type: Dict[str, CounterMetric] = field(
        default_factory=lambda: defaultdict(CounterMetric)
    )

    def record_call(
        self, endpoint: str, success: bool = True, error_type: Optional[str] = None
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "calls": self.calls.to_dict(),
            "successes": self.successes.to_dict(),
            "failures": self.failures.to_dict(),
            "success_rate": (self.successes.count / self.calls.count * 100)
            if self.calls.count > 0
            else 100.0,
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
    """Metrics for cache performance."""

    hits: CounterMetric = field(default_factory=CounterMetric)
    misses: CounterMetric = field(default_factory=CounterMetric)
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Get the cache hit rate (percentage)."""
        total = self.hits.count + self.misses.count
        return (self.hits.count / total * 100) if total > 0 else 0.0

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits.increment()

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses.increment()

    def update_size(self, current_size: int, max_size: int) -> None:
        """Update the cache size metrics."""
        self.size = current_size
        self.max_size = max_size

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "hits": self.hits.to_dict(),
            "misses": self.misses.to_dict(),
            "hit_rate": self.hit_rate,
            "size": self.size,
            "max_size": self.max_size,
            "utilization": (self.size / self.max_size * 100)
            if self.max_size > 0
            else 0.0,
        }


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""

    cpu_samples: Deque[float] = field(default_factory=lambda: deque(maxlen=MAX_SAMPLES))
    memory_samples: Deque[float] = field(
        default_factory=lambda: deque(maxlen=MAX_SAMPLES)
    )
    disk_usage: float = 0.0

    def update(self) -> None:
        """Update resource metrics with current system values."""
        try:
            # CPU usage (percentage)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_samples.append(cpu_percent)

            # Memory usage (percentage)
            memory_info = psutil.virtual_memory()
            self.memory_samples.append(memory_info.percent)

            # Disk usage for the logs directory
            disk_usage = psutil.disk_usage(METRICS_DIR.parent)
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

    def to_dict(self) -> Dict[str, Any]:
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

    tool_calls: Dict[str, CounterMetric] = field(
        default_factory=lambda: defaultdict(CounterMetric)
    )
    execution_times: Dict[str, TimeMetric] = field(
        default_factory=lambda: defaultdict(TimeMetric)
    )

    def record_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_calls[tool_name].increment()

    def record_execution_time(self, tool_name: str, duration: float) -> None:
        """Record the execution time for a tool call."""
        self.execution_times[tool_name].add(duration)

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
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

    def __new__(cls):
        """Create a singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MetricsCollector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the metrics collector."""
        if self._initialized:
            return

        self.metrics = PerformanceMetrics()
        self._collection_thread = None
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

        def collection_task():
            logger.info(f"Starting metrics collection (interval: {interval}s)")
            while self._running:
                try:
                    # Update resource metrics
                    self.metrics.resources.update()

                    # Save metrics to file
                    self.metrics.save_to_file()

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

    def get_metrics(self) -> Dict[str, Any]:
        """Get a dictionary representation of current metrics."""
        return self.metrics.to_dict()

    def record_api_call(
        self, endpoint: str, success: bool = True, error_type: Optional[str] = None
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


def get_metrics() -> Dict[str, Any]:
    """Get current performance metrics."""
    return _metrics_collector.get_metrics()


def record_api_call(
    endpoint: str, success: bool = True, error_type: Optional[str] = None
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


# Initialize metrics collection when this module is imported
logger.info("Performance metrics module initialized")
