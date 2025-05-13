"""
Performance monitoring and metrics for Simplenote MCP Server.

This module provides utilities for tracking performance metrics,
such as response times, API call statistics, and cache performance.
"""

from .metrics import (
    MetricsCollector,
    PerformanceMetrics,
    get_metrics,
    record_api_call,
    record_cache_hit,
    record_cache_miss,
    record_response_time,
    start_metrics_collection,
)

__all__ = [
    "MetricsCollector",
    "PerformanceMetrics",
    "start_metrics_collection",
    "get_metrics",
    "record_api_call",
    "record_response_time",
    "record_cache_hit",
    "record_cache_miss",
]
