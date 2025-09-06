"""Tests for HTTP health and metrics endpoints.

This module tests the optional HTTP endpoints that provide health checks,
readiness probes, and metrics for production observability.
"""

import json
import os
import time
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from simplenote_mcp.server.config import Config
from simplenote_mcp.server.http_endpoints import (
    HealthStatus,
    HTTPEndpointsHandler,
    HTTPEndpointsServer,
    MetricsCollector,
    ReadinessChecker,
    add_health_check,
    add_metric,
    get_http_server,
    set_component_ready,
    start_http_endpoints,
    stop_http_endpoints,
)


class TestHealthStatus:
    """Test health status functionality."""

    def test_health_status_initialization(self):
        """Test health status initialization."""
        health = HealthStatus()

        assert health.overall_status == "healthy"
        assert len(health.checks) == 0
        assert health.get_uptime_seconds() >= 0

    def test_add_health_check(self):
        """Test adding health checks."""
        health = HealthStatus()

        health.add_check("test_service", "healthy", "Service is running")

        assert len(health.checks) == 1
        assert health.checks["test_service"]["status"] == "healthy"
        assert health.checks["test_service"]["message"] == "Service is running"
        assert health.overall_status == "healthy"

    def test_health_status_degraded(self):
        """Test health status with degraded components."""
        health = HealthStatus()

        health.add_check("service1", "healthy", "Good")
        health.add_check("service2", "degraded", "Slow response")

        assert health.overall_status == "degraded"

    def test_health_status_unhealthy(self):
        """Test health status with unhealthy components."""
        health = HealthStatus()

        health.add_check("service1", "healthy", "Good")
        health.add_check("service2", "degraded", "Slow")
        health.add_check("service3", "unhealthy", "Down")

        assert health.overall_status == "unhealthy"

    def test_health_status_to_dict(self):
        """Test converting health status to dictionary."""
        health = HealthStatus()
        health.add_check("test", "healthy", "OK", {"detail": "value"})

        data = health.to_dict()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "test" in data["checks"]
        assert data["checks"]["test"]["details"]["detail"] == "value"


class TestReadinessChecker:
    """Test readiness checker functionality."""

    def test_readiness_initialization(self):
        """Test readiness checker initialization."""
        checker = ReadinessChecker()

        assert not checker.is_ready()
        assert checker.ready_since is None
        assert len(checker.checks) == 0

    def test_component_readiness(self):
        """Test setting component readiness."""
        checker = ReadinessChecker()

        checker.set_component_ready("component1", True)
        assert checker.is_ready()
        assert checker.ready_since is not None

    def test_multiple_components_readiness(self):
        """Test readiness with multiple components."""
        checker = ReadinessChecker()

        checker.set_component_ready("component1", True)
        checker.set_component_ready("component2", False)

        assert not checker.is_ready()
        assert checker.ready_since is None

        checker.set_component_ready("component2", True)
        assert checker.is_ready()

    def test_readiness_to_dict(self):
        """Test converting readiness to dictionary."""
        checker = ReadinessChecker()
        checker.set_component_ready("test_component", True)

        data = checker.to_dict()

        assert data["ready"]
        assert "ready_since" in data
        assert data["components"]["test_component"]


class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_metrics_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()

        assert len(collector.custom_metrics) == 0

    def test_add_metric(self):
        """Test adding custom metrics."""
        collector = MetricsCollector()

        collector.add_metric("test_metric", 42, {"label": "value"})

        assert "test_metric" in collector.custom_metrics
        assert collector.custom_metrics["test_metric"]["value"] == 42
        assert collector.custom_metrics["test_metric"]["labels"]["label"] == "value"

    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()
        collector.add_metric("custom_metric", 100)

        metrics = collector.get_all_metrics()

        assert "timestamp" in metrics
        assert "uptime_seconds" in metrics
        assert "custom" in metrics
        assert metrics["custom"]["custom_metric"]["value"] == 100

    def test_prometheus_format(self):
        """Test Prometheus format output."""
        collector = MetricsCollector()
        collector.add_metric("test_counter", 5, {"instance": "test"})

        prometheus_output = collector.get_prometheus_format()

        assert "simplenote_mcp_uptime_seconds" in prometheus_output
        assert "simplenote_mcp_test_counter" in prometheus_output
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output
        assert 'instance="test"' in prometheus_output


class TestHTTPEndpointsHandler:
    """Test HTTP endpoints handler."""

    def setup_method(self):
        """Setup test method."""
        # Reset class-level instances for clean tests
        HTTPEndpointsHandler.health_status = HealthStatus()
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

    def test_handler_initialization(self):
        """Test handler has proper class attributes."""
        assert hasattr(HTTPEndpointsHandler, "health_status")
        assert hasattr(HTTPEndpointsHandler, "readiness_checker")
        assert hasattr(HTTPEndpointsHandler, "metrics_collector")


@pytest.mark.integration
class TestHTTPEndpointsServer:
    """Test HTTP endpoints server integration."""

    def test_server_initialization(self):
        """Test server initialization."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            mock_config.return_value.enable_http_endpoint = False

            server = HTTPEndpointsServer()

            assert not server.is_running()
            assert server.server is None

    def test_server_disabled_by_config(self):
        """Test server doesn't start when disabled by config."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            mock_config.return_value.enable_http_endpoint = False

            server = HTTPEndpointsServer()
            server.start()

            assert not server.is_running()

    def test_get_server_info_not_running(self):
        """Test server info when not running."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            mock_config.return_value.enable_http_endpoint = False

            server = HTTPEndpointsServer()
            info = server.get_server_info()

            assert not info["running"]

    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("CI") == "true", reason="Flaky in CI environment"
    )
    def test_server_start_and_stop(self):
        """Test starting and stopping the HTTP server."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            # Configure mock to enable HTTP endpoint
            mock_config_obj = MagicMock()
            mock_config_obj.enable_http_endpoint = True
            mock_config_obj.http_host = "127.0.0.1"
            mock_config_obj.http_port = 18080  # Use different port for tests
            mock_config_obj.http_health_path = "/health"
            mock_config_obj.http_ready_path = "/ready"
            mock_config_obj.http_metrics_path = "/metrics"
            mock_config.return_value = mock_config_obj

            server = HTTPEndpointsServer()

            try:
                server.start()

                # Wait for server to start with timeout
                for _ in range(10):  # Try for up to 1 second
                    if server.is_running():
                        break
                    time.sleep(0.1)

                assert server.is_running()

                info = server.get_server_info()
                assert info["running"]
                assert info["host"] == "127.0.0.1"
                assert info["port"] == 18080

            finally:
                server.stop()
                time.sleep(0.1)  # Give server time to stop

            assert not server.is_running()

    @pytest.mark.slow
    @pytest.mark.skipif(
        os.environ.get("CI") == "true", reason="Flaky in CI environment"
    )
    def test_http_endpoints_integration(self):
        """Test actual HTTP requests to endpoints."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            # Configure mock
            mock_config_obj = MagicMock()
            mock_config_obj.enable_http_endpoint = True
            mock_config_obj.http_host = "127.0.0.1"
            mock_config_obj.http_port = 18081  # Different port
            mock_config_obj.http_health_path = "/health"
            mock_config_obj.http_ready_path = "/ready"
            mock_config_obj.http_metrics_path = "/metrics"
            mock_config.return_value = mock_config_obj

            server = HTTPEndpointsServer()

            # Mock the metrics functions to avoid import errors
            with (
                patch(
                    "simplenote_mcp.server.http_endpoints.get_memory_metrics"
                ) as mock_memory,
                patch(
                    "simplenote_mcp.server.http_endpoints.get_performance_metrics"
                ) as mock_perf,
                patch(
                    "simplenote_mcp.server.http_endpoints.get_cache_metrics"
                ) as mock_cache,
            ):
                mock_memory.return_value = {"memory_usage": 100 * 1024 * 1024}  # 100MB
                mock_perf.return_value = {"cpu_usage": 25.0}
                mock_cache.return_value = {"hits": 100, "misses": 20, "hit_rate": 0.83}

                try:
                    server.start()
                    time.sleep(0.2)  # Give server more time to fully start

                    # Test health endpoint
                    try:
                        with urlopen(
                            "http://127.0.0.1:18081/health", timeout=5
                        ) as response:
                            health_data = json.loads(response.read().decode())
                            assert "status" in health_data
                            assert "checks" in health_data
                            assert "uptime_seconds" in health_data
                    except URLError:
                        pytest.skip(
                            "Could not connect to test server - port may be in use"
                        )

                    # Test readiness endpoint
                    with urlopen("http://127.0.0.1:18081/ready", timeout=5) as response:
                        ready_data = json.loads(response.read().decode())
                        assert "ready" in ready_data
                        assert "components" in ready_data

                    # Test metrics endpoint (JSON format)
                    with urlopen(
                        "http://127.0.0.1:18081/metrics", timeout=5
                    ) as response:
                        metrics_data = json.loads(response.read().decode())
                        assert "timestamp" in metrics_data
                        assert "uptime_seconds" in metrics_data

                    # Test metrics endpoint (Prometheus format)
                    with urlopen(
                        "http://127.0.0.1:18081/metrics?format=prometheus", timeout=5
                    ) as response:
                        prometheus_data = response.read().decode()
                        assert "simplenote_mcp_uptime_seconds" in prometheus_data
                        assert "# HELP" in prometheus_data

                finally:
                    server.stop()
                    time.sleep(0.1)


class TestGlobalFunctions:
    """Test global functions for HTTP endpoints."""

    def test_get_http_server_singleton(self):
        """Test that get_http_server returns singleton."""
        server1 = get_http_server()
        server2 = get_http_server()

        assert server1 is server2

    def test_set_component_ready(self):
        """Test setting component readiness."""
        # Reset state
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()

        set_component_ready("test_component", True)

        assert HTTPEndpointsHandler.readiness_checker.checks["test_component"]

    def test_add_health_check_global(self):
        """Test adding health check globally."""
        # Reset state
        HTTPEndpointsHandler.health_status = HealthStatus()

        add_health_check("test_service", "healthy", "All good")

        assert "test_service" in HTTPEndpointsHandler.health_status.checks
        assert (
            HTTPEndpointsHandler.health_status.checks["test_service"]["status"]
            == "healthy"
        )

    def test_add_metric_global(self):
        """Test adding metric globally."""
        # Reset state
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

        add_metric("test_metric", 42, {"env": "test"})

        assert "test_metric" in HTTPEndpointsHandler.metrics_collector.custom_metrics
        assert (
            HTTPEndpointsHandler.metrics_collector.custom_metrics["test_metric"][
                "value"
            ]
            == 42
        )

    def test_start_stop_http_endpoints_global(self):
        """Test global start/stop functions."""
        with patch("simplenote_mcp.server.config.get_config") as mock_config:
            mock_config.return_value.enable_http_endpoint = False

            # These should not raise errors
            start_http_endpoints()
            stop_http_endpoints()


class TestConfigurationIntegration:
    """Test HTTP endpoints configuration integration."""

    def test_config_validation_valid(self):
        """Test valid HTTP endpoint configuration."""
        config = Config()
        config.enable_http_endpoint = True
        config.http_port = 8080
        config.http_host = "0.0.0.0"
        config.http_health_path = "/health"
        config.http_ready_path = "/ready"
        config.http_metrics_path = "/metrics"

        # Should not raise
        config.validate()

    def test_config_validation_invalid_port(self):
        """Test invalid port configuration."""
        config = Config()
        config.enable_http_endpoint = True
        config.http_port = 80  # Below 1024

        with pytest.raises(
            ValueError, match="HTTP_PORT must be between 1024 and 65535"
        ):
            config.validate()

    def test_config_validation_invalid_path(self):
        """Test invalid path configuration."""
        config = Config()
        config.enable_http_endpoint = True
        config.http_port = 8080
        config.http_health_path = "health"  # Missing leading slash

        with pytest.raises(ValueError, match="HTTP_HEALTH_PATH must start with"):
            config.validate()

    def test_config_validation_empty_host(self):
        """Test empty host configuration."""
        config = Config()
        config.enable_http_endpoint = True
        config.http_host = ""

        with pytest.raises(ValueError, match="HTTP_HOST cannot be empty"):
            config.validate()


@pytest.mark.performance
class TestHTTPEndpointsPerformance:
    """Test HTTP endpoints performance."""

    @pytest.mark.slow
    def test_metrics_collection_performance(self):
        """Test that metrics collection doesn't significantly impact performance."""
        collector = MetricsCollector()

        start_time = time.time()

        # Add many metrics quickly
        for i in range(1000):
            collector.add_metric(f"metric_{i}", i, {"iteration": str(i)})

        end_time = time.time()
        duration = end_time - start_time

        # Should be very fast (under 100ms for 1000 metrics)
        assert duration < 0.1

        # Getting all metrics should also be fast
        start_time = time.time()
        with (
            patch("simplenote_mcp.server.http_endpoints.get_memory_metrics"),
            patch("simplenote_mcp.server.http_endpoints.get_performance_metrics"),
            patch("simplenote_mcp.server.http_endpoints.get_cache_metrics"),
        ):
            metrics = collector.get_all_metrics()
        end_time = time.time()

        assert end_time - start_time < 0.1
        assert len(metrics["custom"]) == 1000

    def test_health_check_performance(self):
        """Test that health checks are fast."""
        health = HealthStatus()

        start_time = time.time()

        # Add many health checks
        for i in range(100):
            health.add_check(f"service_{i}", "healthy", f"Service {i} OK")

        end_time = time.time()

        # Should be very fast (under 10ms for 100 checks)
        assert end_time - start_time < 0.01


@pytest.mark.security
class TestHTTPEndpointsSecurity:
    """Test security aspects of HTTP endpoints."""

    def test_no_sensitive_data_in_health_response(self):
        """Test that health responses don't contain sensitive data."""
        health = HealthStatus()
        health.add_check("database", "healthy", "Connected to DB")

        health_data = health.to_dict()
        health_json = json.dumps(health_data)

        # Should not contain common sensitive keywords
        sensitive_keywords = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "api_key",
            "private",
            "confidential",
        ]

        for keyword in sensitive_keywords:
            assert keyword.lower() not in health_json.lower()

    def test_no_sensitive_data_in_metrics_response(self):
        """Test that metrics responses don't expose sensitive data."""
        collector = MetricsCollector()

        # Add some test metrics
        collector.add_metric("request_count", 100)
        collector.add_metric("response_time", 0.25)

        with (
            patch(
                "simplenote_mcp.server.http_endpoints.get_memory_metrics"
            ) as mock_memory,
            patch(
                "simplenote_mcp.server.http_endpoints.get_performance_metrics"
            ) as mock_perf,
            patch(
                "simplenote_mcp.server.http_endpoints.get_cache_metrics"
            ) as mock_cache,
        ):
            mock_memory.return_value = {"memory_usage": 1000000}
            mock_perf.return_value = {"cpu_usage": 15.0}
            mock_cache.return_value = {"hits": 50, "misses": 10}

            metrics = collector.get_all_metrics()
            metrics_json = json.dumps(metrics)

            # Should not contain sensitive data
            sensitive_keywords = ["password", "secret", "key", "token", "credential"]

            for keyword in sensitive_keywords:
                assert keyword.lower() not in metrics_json.lower()

    def test_prometheus_format_safe(self):
        """Test that Prometheus format doesn't expose sensitive data."""
        collector = MetricsCollector()
        collector.add_metric("safe_metric", 42, {"env": "production"})

        prometheus_output = collector.get_prometheus_format()

        # Should contain expected safe content
        assert "simplenote_mcp_safe_metric" in prometheus_output
        assert 'env="production"' in prometheus_output

        # Should not contain sensitive keywords
        sensitive_keywords = ["password", "secret", "token"]
        for keyword in sensitive_keywords:
            assert keyword.lower() not in prometheus_output.lower()
