"""Memory monitoring and leak detection for Simplenote MCP server.

This module provides comprehensive memory monitoring capabilities including:
- Memory usage tracking
- Leak detection during long sessions
- Garbage collection monitoring
- Memory profiling hooks
- Alert triggers for memory issues
"""

import gc
import os
import threading
import time
import weakref
from collections import defaultdict, deque
from typing import Any

import psutil

from .logging import logger


class MemoryMonitor:
    """Comprehensive memory monitoring and leak detection."""

    def __init__(self):
        """Initialize memory monitor."""
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.get_memory_usage()
        self.memory_samples = deque(maxlen=1000)  # Keep last 1000 samples
        self.leak_threshold_mb = 100  # Alert if memory grows by 100MB
        self.monitoring_active = False
        self.monitor_thread = None
        self.sample_interval = 30  # Sample every 30 seconds

        # Object tracking for leak detection
        self.object_counts = defaultdict(int)
        self.tracked_objects = weakref.WeakSet()
        self.creation_timestamps = {}

        # Long session tracking
        self.session_start_time = time.time()
        self.session_memory_growth = []

        # Alert thresholds
        self.memory_growth_alert_threshold = 200  # MB
        self.gc_collection_alert_threshold = 100  # collections per minute

    def start_monitoring(self) -> None:
        """Start continuous memory monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()
        logger.info("Memory monitoring started")

    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)  # Wait up to 5 seconds
        logger.info("Memory monitoring stopped")

    def get_memory_usage(self) -> dict[str, float]:
        """Get current memory usage statistics.

        Returns:
            Dictionary with memory usage in MB
        """
        memory_info = self.process.memory_info()
        return {
            "rss": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            "vms": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            "percent": self.process.memory_percent(),
            "available": psutil.virtual_memory().available / 1024 / 1024,
            "total": psutil.virtual_memory().total / 1024 / 1024,
        }

    def get_gc_stats(self) -> dict[str, Any]:
        """Get garbage collection statistics.

        Returns:
            Dictionary with GC statistics
        """
        stats = gc.get_stats()
        counts = gc.get_count()

        return {
            "counts": counts,  # Objects in each generation
            "collections": [stat["collections"] for stat in stats],
            "collected": [stat["collected"] for stat in stats],
            "uncollectable": [stat["uncollectable"] for stat in stats],
            "total_objects": len(gc.get_objects()),
        }

    def track_object(self, obj: Any, name: str = None) -> None:
        """Track an object for leak detection.

        Args:
            obj: Object to track
            name: Optional name for the object
        """
        if name is None:
            name = type(obj).__name__

        self.object_counts[name] += 1
        self.tracked_objects.add(obj)
        self.creation_timestamps[id(obj)] = time.time()

    def get_object_counts(self) -> dict[str, int]:
        """Get current counts of tracked objects.

        Returns:
            Dictionary mapping object names to counts
        """
        # Update counts based on still-alive objects
        current_counts = defaultdict(int)
        for obj in self.tracked_objects:
            current_counts[type(obj).__name__] += 1

        return dict(current_counts)

    def detect_memory_leaks(self) -> dict[str, Any]:
        """Detect potential memory leaks.

        Returns:
            Dictionary with leak detection results
        """
        current_memory = self.get_memory_usage()
        memory_growth = current_memory["rss"] - self.baseline_memory["rss"]

        # Check for sustained memory growth
        if len(self.memory_samples) >= 10:  # Need at least 10 samples
            recent_samples = list(self.memory_samples)[-10:]
            memory_trend = self._calculate_memory_trend(recent_samples)

            leak_detected = (
                memory_growth > self.leak_threshold_mb
                and memory_trend > 1.0  # Growing trend
            )
        else:
            leak_detected = memory_growth > self.leak_threshold_mb
            memory_trend = 0.0

        # Check for object count anomalies
        object_counts = self.get_object_counts()
        suspicious_objects = {
            name: count
            for name, count in object_counts.items()
            if count > 1000  # More than 1000 objects of same type
        }

        # Check GC statistics
        gc_stats = self.get_gc_stats()
        excessive_gc = any(count > 10000 for count in gc_stats["counts"])

        return {
            "leak_detected": leak_detected,
            "memory_growth_mb": memory_growth,
            "memory_trend": memory_trend,
            "current_memory": current_memory,
            "baseline_memory": self.baseline_memory,
            "suspicious_objects": suspicious_objects,
            "excessive_gc": excessive_gc,
            "gc_stats": gc_stats,
            "session_duration_hours": (time.time() - self.session_start_time) / 3600,
        }

    def force_garbage_collection(self) -> dict[str, Any]:
        """Force garbage collection and return statistics.

        Returns:
            Dictionary with collection results
        """
        before_counts = gc.get_count()

        # Collect all generations
        collected = {}
        for generation in range(3):
            collected[f"gen_{generation}"] = gc.collect(generation)

        after_counts = gc.get_count()

        logger.info(f"Forced GC: collected {sum(collected.values())} objects")

        return {
            "before_counts": {
                f"gen_{i}": count for i, count in enumerate(before_counts)
            },
            "after_counts": {f"gen_{i}": count for i, count in enumerate(after_counts)},
            "collected": collected,
        }

    def get_memory_report(self) -> dict[str, Any]:
        """Get comprehensive memory report.

        Returns:
            Dictionary with complete memory analysis
        """
        leak_detection = self.detect_memory_leaks()
        gc_stats = self.get_gc_stats()

        # Calculate session statistics
        session_duration = time.time() - self.session_start_time
        memory_efficiency = self._calculate_memory_efficiency()

        return {
            "monitoring_active": self.monitoring_active,
            "session_duration_hours": session_duration / 3600,
            "memory_efficiency": memory_efficiency,
            "leak_detection": leak_detection,
            "gc_statistics": gc_stats,
            "sample_count": len(self.memory_samples),
            "tracked_objects": len(self.tracked_objects),
            "recommendations": self._generate_recommendations(leak_detection),
        }

    def cleanup_expired_objects(self, max_age_hours: float = 1.0) -> int:
        """Clean up objects that have been tracked for too long.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of objects cleaned up
        """
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        expired_ids = [
            obj_id
            for obj_id, timestamp in self.creation_timestamps.items()
            if timestamp < cutoff_time
        ]

        for obj_id in expired_ids:
            del self.creation_timestamps[obj_id]

        # Force garbage collection to clean up weakrefs
        gc.collect()

        return len(expired_ids)

    def _monitoring_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        while self.monitoring_active:
            try:
                # Sample current memory usage
                memory_usage = self.get_memory_usage()
                sample = {
                    "timestamp": time.time(),
                    "memory": memory_usage,
                    "gc_stats": self.get_gc_stats(),
                }

                self.memory_samples.append(sample)

                # Check for memory issues
                if len(self.memory_samples) > 1:
                    self._check_memory_alerts(sample)

                # Clean up old tracked objects periodically
                if len(self.memory_samples) % 20 == 0:  # Every 20 samples (10 minutes)
                    self.cleanup_expired_objects()

            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")

            # Wait for next sample
            time.sleep(self.sample_interval)

    def _calculate_memory_trend(self, samples: list[dict[str, Any]]) -> float:
        """Calculate memory usage trend from samples.

        Args:
            samples: List of memory samples

        Returns:
            Trend value (positive = growing, negative = shrinking)
        """
        if len(samples) < 2:
            return 0.0

        memory_values = [sample["memory"]["rss"] for sample in samples]

        # Simple linear trend calculation
        n = len(memory_values)
        x_sum = sum(range(n))
        y_sum = sum(memory_values)
        xy_sum = sum(i * memory_values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        # Calculate slope of trend line
        if n * x2_sum - x_sum * x_sum == 0:
            return 0.0

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        return slope

    def _calculate_memory_efficiency(self) -> float:
        """Calculate memory efficiency score (0-100).

        Returns:
            Efficiency score
        """
        if not self.memory_samples:
            return 100.0

        current_memory = self.memory_samples[-1]["memory"]["rss"]
        baseline_memory = self.baseline_memory["rss"]

        # Calculate efficiency based on memory growth
        if baseline_memory == 0:
            return 100.0

        growth_ratio = current_memory / baseline_memory

        # Efficiency decreases as memory grows beyond reasonable limits
        if growth_ratio <= 1.5:  # Up to 50% growth is considered efficient
            return 100.0
        elif growth_ratio <= 2.0:  # 50-100% growth
            return max(50.0, 100.0 - (growth_ratio - 1.5) * 100)
        else:  # More than 100% growth
            return max(0.0, 50.0 - (growth_ratio - 2.0) * 25)

    def _check_memory_alerts(self, current_sample: dict[str, Any]) -> None:
        """Check for memory-related alerts.

        Args:
            current_sample: Current memory sample
        """
        current_memory = current_sample["memory"]["rss"]
        baseline_memory = self.baseline_memory["rss"]
        growth = current_memory - baseline_memory

        # Alert for excessive memory growth
        if growth > self.memory_growth_alert_threshold:
            logger.warning(
                f"HIGH MEMORY USAGE: {growth:.1f}MB growth from baseline "
                f"(current: {current_memory:.1f}MB, baseline: {baseline_memory:.1f}MB)"
            )
            self._trigger_memory_alert(
                "high_memory_usage",
                {
                    "growth_mb": growth,
                    "current_mb": current_memory,
                    "baseline_mb": baseline_memory,
                },
            )

        # Alert for excessive GC activity
        gc_stats = current_sample["gc_stats"]
        if len(self.memory_samples) > 1:
            prev_sample = self.memory_samples[-2]
            time_diff = current_sample["timestamp"] - prev_sample["timestamp"]

            if time_diff > 0:
                for gen in range(3):
                    prev_collections = prev_sample["gc_stats"]["collections"][gen]
                    current_collections = gc_stats["collections"][gen]
                    collections_per_minute = (
                        (current_collections - prev_collections) / time_diff * 60
                    )

                    if collections_per_minute > self.gc_collection_alert_threshold:
                        logger.warning(
                            f"EXCESSIVE GC ACTIVITY: {collections_per_minute:.1f} "
                            f"collections/min in generation {gen}"
                        )

    def _trigger_memory_alert(self, alert_type: str, details: dict[str, Any]) -> None:
        """Trigger memory-related alert.

        Args:
            alert_type: Type of memory alert
            details: Alert details
        """
        try:
            # Lazy import to avoid circular dependency
            import asyncio

            from .alerting import AlertSeverity, AlertType, get_alerter

            alert_type_mapping = {
                "high_memory_usage": AlertType.HIGH_MEMORY_USAGE,
                "memory_leak": AlertType.MEMORY_LEAK,
                "excessive_gc": AlertType.EXCESSIVE_GC,
            }

            mapped_alert_type = alert_type_mapping.get(
                alert_type, AlertType.SUSPICIOUS_PATTERN
            )

            alerter = get_alerter()

            # Try to create alert asynchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        alerter.create_alert(
                            mapped_alert_type,
                            AlertSeverity.HIGH,
                            f"Memory alert: {alert_type}",
                            details,
                        )
                    )
                else:
                    loop.run_until_complete(
                        alerter.create_alert(
                            mapped_alert_type,
                            AlertSeverity.HIGH,
                            f"Memory alert: {alert_type}",
                            details,
                        )
                    )
            except RuntimeError:
                asyncio.run(
                    alerter.create_alert(
                        mapped_alert_type,
                        AlertSeverity.HIGH,
                        f"Memory alert: {alert_type}",
                        details,
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to trigger memory alert: {e}")

    def _generate_recommendations(self, leak_detection: dict[str, Any]) -> list[str]:
        """Generate recommendations based on memory analysis.

        Args:
            leak_detection: Leak detection results

        Returns:
            List of recommendations
        """
        recommendations = []

        if leak_detection["leak_detected"]:
            recommendations.append(
                "Potential memory leak detected. Consider reviewing object lifecycle management."
            )

        if leak_detection["excessive_gc"]:
            recommendations.append(
                "Excessive garbage collection activity. Consider optimizing object creation patterns."
            )

        if leak_detection["suspicious_objects"]:
            for obj_type, count in leak_detection["suspicious_objects"].items():
                recommendations.append(
                    f"High count of {obj_type} objects ({count}). Review creation and cleanup."
                )

        if leak_detection["memory_growth_mb"] > 50:
            recommendations.append(
                "Significant memory growth detected. Consider implementing periodic cleanup."
            )

        if not recommendations:
            recommendations.append("Memory usage appears normal.")

        return recommendations


# Global memory monitor instance
memory_monitor = MemoryMonitor()


def with_memory_monitoring(track_objects: bool = True):
    """Decorator for memory monitoring during function execution.

    Args:
        track_objects: Whether to track objects created during execution
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Start monitoring if not already active
            if not memory_monitor.monitoring_active:
                memory_monitor.start_monitoring()

            # Record memory before function execution
            memory_before = memory_monitor.get_memory_usage()

            try:
                result = await func(*args, **kwargs)

                # Track result object if requested
                if track_objects and result is not None:
                    memory_monitor.track_object(result, f"{func.__name__}_result")

                return result

            finally:
                # Record memory after function execution
                memory_after = memory_monitor.get_memory_usage()
                memory_delta = memory_after["rss"] - memory_before["rss"]

                if abs(memory_delta) > 10:  # Log if > 10MB change
                    logger.debug(
                        f"Function {func.__name__} memory delta: {memory_delta:.1f}MB"
                    )

        return wrapper

    return decorator


def cleanup_memory() -> dict[str, Any]:
    """Perform comprehensive memory cleanup.

    Returns:
        Cleanup results
    """
    logger.info("Starting memory cleanup...")

    # Clean up tracked objects
    expired_count = memory_monitor.cleanup_expired_objects()

    # Force garbage collection
    gc_results = memory_monitor.force_garbage_collection()

    # Get memory usage after cleanup
    memory_after = memory_monitor.get_memory_usage()

    results = {
        "expired_objects_cleaned": expired_count,
        "gc_results": gc_results,
        "memory_after_cleanup": memory_after,
    }

    logger.info(f"Memory cleanup completed: {results}")
    return results
