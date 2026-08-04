"""Tests for HTTP health and metrics endpoints."""

import socket
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from simplenote_mcp.server.errors import ConfigurationError
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


def _wait_until_listening(port: int, timeout: float = 5.0) -> None:
    """Poll a raw TCP connect until the server's background thread is
    actually accepting connections, instead of a blind sleep — avoids
    flakiness on slower environments where serve_forever() hasn't started
    yet by the time a fixed delay elapses."""
    deadline = time.monotonic() + timeout
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError as e:
            last_error = e
            time.sleep(0.02)
    raise TimeoutError(
        f"Server did not start listening on port {port} within {timeout}s"
    ) from last_error


class TestHealthStatus:
    """Tests for HealthStatus class."""

    def test_init(self):
        """Test HealthStatus initialization."""
        status = HealthStatus()
        assert status.overall_status == "healthy"
        assert status.checks == {}
        assert isinstance(status.start_time, datetime)
        assert isinstance(status.last_check, datetime)

    def test_add_check_healthy(self):
        """Test adding a healthy check."""
        status = HealthStatus()
        status.add_check("test", "healthy", "All good")

        assert "test" in status.checks
        assert status.checks["test"]["status"] == "healthy"
        assert status.checks["test"]["message"] == "All good"
        assert status.overall_status == "healthy"

    def test_add_check_degraded(self):
        """Test adding a degraded check affects overall status."""
        status = HealthStatus()
        status.add_check("healthy_check", "healthy", "OK")
        status.add_check("degraded_check", "degraded", "Slow response")

        assert status.overall_status == "degraded"

    def test_add_check_unhealthy(self):
        """Test adding an unhealthy check affects overall status."""
        status = HealthStatus()
        status.add_check("healthy_check", "healthy", "OK")
        status.add_check("degraded_check", "degraded", "Slow")
        status.add_check("unhealthy_check", "unhealthy", "Failed")

        assert status.overall_status == "unhealthy"

    def test_add_check_with_details(self):
        """Test adding a check with details."""
        status = HealthStatus()
        details = {"memory_mb": 512, "cpu_percent": 25}
        status.add_check("resources", "healthy", "Resources OK", details)

        assert status.checks["resources"]["details"] == details

    def test_get_uptime_seconds(self):
        """Test uptime calculation."""
        status = HealthStatus()
        time.sleep(0.1)
        uptime = status.get_uptime_seconds()

        assert uptime >= 0.1
        assert uptime < 1.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        status = HealthStatus()
        status.add_check("test", "healthy", "OK")

        result = status.to_dict()

        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "checks" in result
        assert result["status"] == "healthy"


class TestReadinessChecker:
    """Tests for ReadinessChecker class."""

    def test_init(self):
        """Test ReadinessChecker initialization."""
        checker = ReadinessChecker()
        assert checker.ready is False
        assert checker.ready_since is None
        assert checker.checks == {}

    def test_set_component_ready_single(self):
        """Test setting a single component ready."""
        checker = ReadinessChecker()
        checker.set_component_ready("database", True)

        assert checker.checks["database"] is True
        assert checker.ready is True
        assert checker.ready_since is not None

    def test_set_component_ready_multiple(self):
        """Test multiple components must all be ready."""
        checker = ReadinessChecker()
        checker.set_component_ready("database", True)
        checker.set_component_ready("cache", False)

        assert checker.ready is False

    def test_set_component_ready_all(self):
        """Test system ready when all components ready."""
        checker = ReadinessChecker()
        checker.set_component_ready("database", True)
        checker.set_component_ready("cache", True)
        checker.set_component_ready("api", True)

        assert checker.ready is True

    def test_set_component_not_ready(self):
        """Test component becoming not ready."""
        checker = ReadinessChecker()
        checker.set_component_ready("database", True)
        assert checker.ready is True

        checker.set_component_ready("database", False)
        assert checker.ready is False
        assert checker.ready_since is None

    def test_is_ready(self):
        """Test is_ready method."""
        checker = ReadinessChecker()
        assert checker.is_ready() is False

        checker.set_component_ready("test", True)
        assert checker.is_ready() is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        checker = ReadinessChecker()
        checker.set_component_ready("test", True)

        result = checker.to_dict()

        assert "ready" in result
        assert "ready_since" in result
        assert "components" in result
        assert "timestamp" in result
        assert result["ready"] is True


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_init(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        assert collector.custom_metrics == {}

    def test_add_metric(self):
        """Test adding a custom metric."""
        collector = MetricsCollector()
        collector.add_metric("request_count", 100)

        assert "request_count" in collector.custom_metrics
        assert collector.custom_metrics["request_count"]["value"] == 100

    def test_add_metric_with_labels(self):
        """Test adding a metric with labels."""
        collector = MetricsCollector()
        labels = {"method": "GET", "path": "/health"}
        collector.add_metric("http_requests", 50, labels)

        metric = collector.custom_metrics["http_requests"]
        assert metric["value"] == 50
        assert metric["labels"] == labels

    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_performance_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_cache_metrics")
    def test_get_all_metrics(self, mock_cache, mock_perf, mock_memory):
        """Test getting all metrics."""
        mock_memory.return_value = {"memory_usage": 1024}
        mock_perf.return_value = {"latency_ms": 10}
        mock_cache.return_value = {"hits": 100, "misses": 10}

        collector = MetricsCollector()
        collector.add_metric("custom", 42)

        metrics = collector.get_all_metrics()

        assert "timestamp" in metrics
        assert "uptime_seconds" in metrics
        assert "memory" in metrics
        assert "performance" in metrics
        assert "cache" in metrics
        assert "custom" in metrics

    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_performance_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_cache_metrics")
    def test_get_all_metrics_with_error(self, mock_cache, mock_perf, mock_memory):
        """Test metrics collection handles errors gracefully."""
        mock_memory.side_effect = Exception("Memory error")
        mock_perf.return_value = {}
        mock_cache.return_value = {}

        collector = MetricsCollector()
        metrics = collector.get_all_metrics()

        assert "metrics_error" in metrics

    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_performance_metrics")
    @patch("simplenote_mcp.server.http_endpoints.get_cache_metrics")
    def test_get_prometheus_format(self, mock_cache, mock_perf, mock_memory):
        """Test Prometheus format output."""
        mock_memory.return_value = {"memory_usage": 1024000}
        mock_perf.return_value = {}
        mock_cache.return_value = {"hits": 100, "misses": 10}

        collector = MetricsCollector()
        collector.add_metric("test_metric", 42, {"env": "test"})

        prometheus_output = collector.get_prometheus_format()

        assert "simplenote_mcp_uptime_seconds" in prometheus_output
        assert "simplenote_mcp_memory_usage_bytes" in prometheus_output
        assert "simplenote_mcp_cache_hits_total" in prometheus_output
        assert "simplenote_mcp_cache_misses_total" in prometheus_output
        assert "simplenote_mcp_test_metric" in prometheus_output
        assert 'env="test"' in prometheus_output


class TestHTTPEndpointsHandler:
    """Tests for HTTPEndpointsHandler class."""

    def setup_method(self):
        """Reset handler state before each test."""
        HTTPEndpointsHandler.health_status = HealthStatus()
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

    def test_class_level_instances(self):
        """Test that handler has class-level shared instances."""
        assert isinstance(HTTPEndpointsHandler.health_status, HealthStatus)
        assert isinstance(HTTPEndpointsHandler.readiness_checker, ReadinessChecker)
        assert isinstance(HTTPEndpointsHandler.metrics_collector, MetricsCollector)


class TestHealthEndpointStatusCode:
    """/health must only fail (503) on a genuine 'unhealthy' check.

    Regression test: it used to fail on 'degraded' too — e.g. a low cache
    hit rate, which is completely normal right after startup or during a
    quiet period, not a sign the process is actually broken. Wired to a
    Docker HEALTHCHECK or a Kubernetes livenessProbe (both added as part of
    the 2026-07-13 audit remediation), that caused spurious restarts.
    Uses a real running HTTPEndpointsServer + real HTTP requests rather
    than mocking BaseHTTPRequestHandler internals, to exercise the exact
    code path a real probe hits.
    """

    def setup_method(self):
        HTTPEndpointsHandler.health_status = HealthStatus()
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

    def _start_server(self, mock_config):
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="127.0.0.1",
            http_port=0,  # OS-assigned free port
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
            cache_health_checks=False,  # isolate from real cache state
        )
        server = HTTPEndpointsServer()
        server.start()
        time.sleep(0.1)  # let the background thread bind the socket
        port = server.server.server_port
        return server, port

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    def test_degraded_check_returns_200(self, mock_memory, mock_config):
        import urllib.request

        mock_memory.return_value = {"memory_usage": 0}
        server, port = self._start_server(mock_config)
        # Simulate a degraded (not unhealthy) subsystem, e.g. a low cache
        # hit rate — must not fail the probe.
        HTTPEndpointsHandler.health_status.add_check(
            "cache", "degraded", "Low cache hit rate: 0.0%"
        )
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=5
            ) as response:
                assert response.status == 200
        finally:
            server.stop()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    def test_unhealthy_check_returns_503(self, mock_memory, mock_config):
        import urllib.error
        import urllib.request

        mock_memory.return_value = {"memory_usage": 0}
        server, port = self._start_server(mock_config)
        HTTPEndpointsHandler.health_status.add_check(
            "dependency", "unhealthy", "A required subsystem failed"
        )
        try:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
                raise AssertionError("expected HTTPError for a 503 response")
            except urllib.error.HTTPError as e:
                assert e.code == 503
        finally:
            server.stop()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    def test_all_healthy_returns_200(self, mock_memory, mock_config):
        import urllib.request

        mock_memory.return_value = {"memory_usage": 0}
        server, port = self._start_server(mock_config)
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=5
            ) as response:
                assert response.status == 200
        finally:
            server.stop()


class TestHTTPEndpointsServer:
    """Tests for HTTPEndpointsServer class."""

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_init(self, mock_config):
        """Test server initialization."""
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="localhost",
            http_port=8080,
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
        )

        server = HTTPEndpointsServer()

        assert server.server is None
        assert server.server_thread is None
        assert server.running is False

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_start_disabled(self, mock_config):
        """Test server doesn't start when disabled."""
        mock_config.return_value = MagicMock(enable_http_endpoint=False)

        server = HTTPEndpointsServer()
        server.start()

        assert server.running is False

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_start_already_running(self, mock_config):
        """Test server warns when already running."""
        mock_config.return_value = MagicMock(enable_http_endpoint=True)

        server = HTTPEndpointsServer()
        server.running = True

        # Should not raise, just log warning
        server.start()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_stop_not_running(self, mock_config):
        """Test stopping a non-running server."""
        mock_config.return_value = MagicMock(enable_http_endpoint=True)

        server = HTTPEndpointsServer()
        # Should not raise
        server.stop()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_is_running(self, mock_config):
        """Test is_running method."""
        mock_config.return_value = MagicMock(enable_http_endpoint=True)

        server = HTTPEndpointsServer()
        assert server.is_running() is False

        server.running = True
        assert server.is_running() is True

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_get_server_info_not_running(self, mock_config):
        """Test get_server_info when not running."""
        mock_config.return_value = MagicMock(enable_http_endpoint=True)

        server = HTTPEndpointsServer()
        info = server.get_server_info()

        assert info == {"running": False}

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_get_server_info_running(self, mock_config):
        """Test get_server_info when running."""
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="localhost",
            http_port=8080,
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
        )

        server = HTTPEndpointsServer()
        server.running = True

        info = server.get_server_info()

        assert info["running"] is True
        assert info["host"] == "localhost"
        assert info["port"] == 8080
        assert "endpoints" in info


class TestModuleFunctions:
    """Tests for module-level functions."""

    def setup_method(self):
        """Reset state before each test."""
        HTTPEndpointsHandler.health_status = HealthStatus()
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

    def test_set_component_ready(self):
        """Test set_component_ready function."""
        set_component_ready("test_component", True)

        assert HTTPEndpointsHandler.readiness_checker.checks["test_component"] is True

    def test_add_health_check(self):
        """Test add_health_check function."""
        add_health_check("test_check", "healthy", "All good", {"key": "value"})

        check = HTTPEndpointsHandler.health_status.checks["test_check"]
        assert check["status"] == "healthy"
        assert check["message"] == "All good"
        assert check["details"] == {"key": "value"}

    def test_add_metric(self):
        """Test add_metric function."""
        add_metric("test_metric", 42, {"label": "value"})

        metric = HTTPEndpointsHandler.metrics_collector.custom_metrics["test_metric"]
        assert metric["value"] == 42
        assert metric["labels"] == {"label": "value"}

    @patch("simplenote_mcp.server.http_endpoints._http_server", None)
    def test_get_http_server_creates_instance(self):
        """Test get_http_server creates new instance."""
        with patch("simplenote_mcp.server.http_endpoints.get_config") as mock_config:
            mock_config.return_value = MagicMock(enable_http_endpoint=True)
            server = get_http_server()
            assert isinstance(server, HTTPEndpointsServer)

    @patch("simplenote_mcp.server.http_endpoints.get_http_server")
    def test_start_http_endpoints(self, mock_get_server):
        """Test start_http_endpoints function."""
        mock_server = MagicMock()
        mock_get_server.return_value = mock_server

        start_http_endpoints()

        mock_server.start.assert_called_once()

    @patch("simplenote_mcp.server.http_endpoints.get_http_server")
    def test_stop_http_endpoints(self, mock_get_server):
        """Test stop_http_endpoints function."""
        mock_server = MagicMock()
        mock_get_server.return_value = mock_server

        stop_http_endpoints()

        mock_server.stop.assert_called_once()


class TestHealthStatusEdgeCases:
    """Edge case tests for HealthStatus."""

    def test_multiple_checks_same_name(self):
        """Test updating a check with the same name."""
        status = HealthStatus()
        status.add_check("memory", "healthy", "OK")
        status.add_check("memory", "degraded", "High usage")

        assert status.checks["memory"]["status"] == "degraded"
        assert len(status.checks) == 1

    def test_transition_from_unhealthy_to_healthy(self):
        """Test status can recover from unhealthy."""
        status = HealthStatus()
        status.add_check("service", "unhealthy", "Down")
        assert status.overall_status == "unhealthy"

        status.add_check("service", "healthy", "Recovered")
        assert status.overall_status == "healthy"

    def test_empty_details(self):
        """Test check with None details."""
        status = HealthStatus()
        status.add_check("test", "healthy", "OK", None)

        assert status.checks["test"]["details"] == {}


class TestReadinessCheckerEdgeCases:
    """Edge case tests for ReadinessChecker."""

    def test_empty_components(self):
        """Test readiness with no components."""
        checker = ReadinessChecker()
        assert checker.is_ready() is False

    def test_component_toggle(self):
        """Test component ready/not ready toggle."""
        checker = ReadinessChecker()

        checker.set_component_ready("db", True)
        ready_since_first = checker.ready_since

        checker.set_component_ready("db", False)
        assert checker.ready_since is None

        checker.set_component_ready("db", True)
        assert checker.ready_since is not None
        assert checker.ready_since != ready_since_first


class TestMetricsCollectorEdgeCases:
    """Edge case tests for MetricsCollector."""

    def test_metric_update(self):
        """Test updating an existing metric."""
        collector = MetricsCollector()
        collector.add_metric("counter", 1)
        collector.add_metric("counter", 2)

        assert collector.custom_metrics["counter"]["value"] == 2

    def test_metric_special_characters_in_name(self):
        """Test metric names with special characters in Prometheus format."""
        collector = MetricsCollector()
        collector.add_metric("my-metric.name", 42)

        with (
            patch(
                "simplenote_mcp.server.http_endpoints.get_memory_metrics"
            ) as mock_mem,
            patch(
                "simplenote_mcp.server.http_endpoints.get_performance_metrics"
            ) as mock_perf,
            patch(
                "simplenote_mcp.server.http_endpoints.get_cache_metrics"
            ) as mock_cache,
        ):
            mock_mem.return_value = {}
            mock_perf.return_value = {}
            mock_cache.return_value = {}

            output = collector.get_prometheus_format()

            # Special chars should be replaced with underscores
            assert "simplenote_mcp_my_metric_name" in output


class TestBearerTokenAuth:
    """Unit tests for HTTPEndpointsHandler._is_authorized.

    Constructs the handler via __new__ to test the auth check in isolation,
    without a real socket/request — matches this project's convention of
    not spinning up a live server for pure logic tests.
    """

    @staticmethod
    def _make_handler(client_ip: str, headers: dict | None = None):
        handler = HTTPEndpointsHandler.__new__(HTTPEndpointsHandler)
        handler.client_address = (client_ip, 12345)
        handler.headers = headers or {}
        return handler

    def test_no_token_configured_always_authorized(self):
        handler = self._make_handler("203.0.113.5")
        config = MagicMock(http_endpoint_auth_token=None)
        assert handler._is_authorized(config) is True

    def test_loopback_caller_trusted_without_header(self):
        handler = self._make_handler("127.0.0.1")
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is True

    def test_ipv6_loopback_caller_trusted(self):
        handler = self._make_handler("::1")
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is True

    def test_non_loopback_caller_without_header_rejected(self):
        handler = self._make_handler("203.0.113.5")
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is False

    def test_non_loopback_caller_with_wrong_token_rejected(self):
        handler = self._make_handler(
            "203.0.113.5", headers={"Authorization": "Bearer wrong-token"}
        )
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is False

    def test_non_loopback_caller_with_non_bearer_scheme_rejected(self):
        handler = self._make_handler(
            "203.0.113.5", headers={"Authorization": "Basic secret-token"}
        )
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is False

    def test_non_loopback_caller_with_correct_token_authorized(self):
        handler = self._make_handler(
            "203.0.113.5", headers={"Authorization": "Bearer secret-token"}
        )
        config = MagicMock(http_endpoint_auth_token="secret-token")
        assert handler._is_authorized(config) is True


class TestBearerTokenAuthIntegration:
    """End-to-end: a real server, with a token configured, against a real
    loopback request — confirms the container's own exec-based liveness
    probe (which always connects via 127.0.0.1) keeps working without
    needing the secret on its command line."""

    def setup_method(self):
        HTTPEndpointsHandler.health_status = HealthStatus()
        HTTPEndpointsHandler.readiness_checker = ReadinessChecker()
        HTTPEndpointsHandler.metrics_collector = MetricsCollector()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    @patch("simplenote_mcp.server.http_endpoints.get_memory_metrics")
    def test_loopback_request_succeeds_with_token_configured(
        self, mock_memory, mock_config
    ):
        import urllib.request

        mock_memory.return_value = {"memory_usage": 0}
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="127.0.0.1",
            http_port=0,  # OS-assigned free port
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
            http_endpoint_auth_token="secret-token",
            cache_health_checks=False,
        )
        server = HTTPEndpointsServer()
        server.start()
        port = server.server.server_port
        _wait_until_listening(port)
        try:
            # No Authorization header at all — must still succeed, since
            # the request originates from 127.0.0.1.
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=5
            ) as response:
                assert response.status == 200
        finally:
            server.stop()

    @patch.object(HTTPEndpointsHandler, "_is_authorized", return_value=False)
    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_unauthorized_request_gets_401_with_www_authenticate(
        self, mock_config, _mock_authorized
    ):
        """Real end-to-end 401: do_GET must route a failed _is_authorized
        check to _send_unauthorized rather than any handler, and the
        response must carry the WWW-Authenticate header real clients rely
        on. All test connections are loopback, so _is_authorized is
        patched directly to force the rejection path rather than faking a
        non-loopback client address."""
        import urllib.error
        import urllib.request

        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="127.0.0.1",
            http_port=0,
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
            http_endpoint_auth_token="secret-token",
            cache_health_checks=False,
        )
        server = HTTPEndpointsServer()
        server.start()
        port = server.server.server_port
        _wait_until_listening(port)
        try:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
                raise AssertionError("expected HTTPError for a 401 response")
            except urllib.error.HTTPError as e:
                assert e.code == 401
                assert (
                    e.headers.get("WWW-Authenticate")
                    == 'Bearer realm="simplenote-mcp-monitoring"'
                )
        finally:
            server.stop()


class TestNonLoopbackAuthGuard:
    """HTTPEndpointsServer.start() must fail closed on a non-loopback bind
    with no HTTP_ENDPOINT_AUTH_TOKEN, and start normally when one is set."""

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_non_loopback_without_token_raises(self, mock_config):
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="0.0.0.0",
            http_endpoint_auth_token=None,
        )

        server = HTTPEndpointsServer()
        with pytest.raises(ConfigurationError):
            server.start()

        assert server.running is False

    @patch("simplenote_mcp.server.http_endpoints.HTTPServer")
    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_non_loopback_with_token_starts(self, mock_config, mock_http_server_cls):
        # HTTPServer itself is mocked so this never binds a real socket —
        # only the guard logic in start() is under test here.
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="0.0.0.0",
            http_port=8080,
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
            http_endpoint_auth_token="secret-token",
        )
        mock_http_server_cls.return_value = MagicMock(server_port=8080)

        server = HTTPEndpointsServer()
        server.start()

        assert server.running is True
        server.stop()

    @patch("simplenote_mcp.server.http_endpoints.get_config")
    def test_loopback_without_token_does_not_raise(self, mock_config):
        mock_config.return_value = MagicMock(
            enable_http_endpoint=True,
            http_host="127.0.0.1",
            http_port=0,
            http_health_path="/health",
            http_ready_path="/ready",
            http_metrics_path="/metrics",
            http_endpoint_auth_token=None,
            cache_health_checks=False,
        )

        server = HTTPEndpointsServer()
        try:
            server.start()
            assert server.running is True
        finally:
            server.stop()
