"""HTTP health and metrics endpoints for production observability.

This module provides optional HTTP endpoints for health checks, readiness probes,
and metrics collection. These are essential for containerized deployments and
production monitoring.
"""

import hmac
import json
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import get_config
from .errors import ConfigurationError
from .logger_factory import get_performance_logger
from .monitoring.metrics import (
    get_cache_metrics,
    get_memory_metrics,
    get_performance_metrics,
)
from .monitoring.thresholds import get_performance_threshold_status

logger = get_performance_logger(operation="http_endpoints")

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_LOOPBACK_ADDRESSES = ("127.0.0.1", "::1")


class HealthStatus:
    """Represents system health status."""

    def __init__(self) -> None:
        self.start_time = datetime.utcnow()
        self.last_check = datetime.utcnow()
        self.checks: dict[str, dict[str, Any]] = {}
        self.overall_status = "healthy"

    def add_check(
        self,
        name: str,
        status: str,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a health check result."""
        self.checks[name] = {
            "status": status,  # "healthy", "degraded", "unhealthy"
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.last_check = datetime.utcnow()

        # Update overall status based on worst check
        statuses = [check["status"] for check in self.checks.values()]
        if "unhealthy" in statuses:
            self.overall_status = "unhealthy"
        elif "degraded" in statuses:
            self.overall_status = "degraded"
        else:
            self.overall_status = "healthy"

    def get_uptime_seconds(self) -> float:
        """Get system uptime in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "status": self.overall_status,
            "timestamp": self.last_check.isoformat(),
            "uptime_seconds": self.get_uptime_seconds(),
            "checks": self.checks,
        }


class ReadinessChecker:
    """Checks system readiness for serving requests."""

    def __init__(self) -> None:
        self.ready = False
        self.ready_since: datetime | None = None
        self.checks: dict[str, bool] = {}

    def set_component_ready(self, component: str, ready: bool) -> None:
        """Set readiness status for a component."""
        self.checks[component] = ready

        # System is ready when all components are ready
        all_ready = all(self.checks.values()) if self.checks else False

        if all_ready and not self.ready:
            self.ready = True
            self.ready_since = datetime.utcnow()
            logger.info("System became ready for serving requests")
        elif not all_ready and self.ready:
            self.ready = False
            self.ready_since = None
            logger.warning("System is no longer ready")

    def is_ready(self) -> bool:
        """Check if system is ready."""
        return self.ready

    def to_dict(self) -> dict[str, Any]:
        """Convert readiness status to dictionary."""
        return {
            "ready": self.ready,
            "ready_since": self.ready_since.isoformat() if self.ready_since else None,
            "components": self.checks,
            "timestamp": datetime.utcnow().isoformat(),
        }


class MetricsCollector:
    """Collects and formats system metrics."""

    def __init__(self) -> None:
        self.custom_metrics: dict[str, Any] = {}

    def add_metric(
        self, name: str, value: Any, labels: dict[str, str] | None = None
    ) -> None:
        """Add a custom metric."""
        self.custom_metrics[name] = {
            "value": value,
            "labels": labels or {},
            "timestamp": time.time(),
        }

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all system metrics."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
        }

        # Add system metrics
        try:
            metrics.update(
                {
                    "memory": get_memory_metrics(),
                    "performance": get_performance_metrics(),
                    "cache": get_cache_metrics(),
                }
            )
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            metrics["metrics_error"] = str(e)

        # Add custom metrics
        metrics["custom"] = self.custom_metrics

        return metrics

    def get_prometheus_format(self) -> str:
        """Get metrics in Prometheus format."""
        lines = []
        metrics = self.get_all_metrics()

        # Helper to format metric name and labels
        def format_metric(
            name: str, value: Any, labels: dict[str, str] | None = None
        ) -> str:
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                return f"{name}{{{label_str}}} {value}"
            return f"{name} {value}"

        # System uptime
        lines.append("# HELP simplenote_mcp_uptime_seconds System uptime in seconds")
        lines.append("# TYPE simplenote_mcp_uptime_seconds counter")
        lines.append(
            format_metric("simplenote_mcp_uptime_seconds", metrics["uptime_seconds"])
        )

        # Memory metrics
        if "memory" in metrics:
            memory = metrics["memory"]
            lines.append(
                "# HELP simplenote_mcp_memory_usage_bytes Memory usage in bytes"
            )
            lines.append("# TYPE simplenote_mcp_memory_usage_bytes gauge")
            lines.append(
                format_metric(
                    "simplenote_mcp_memory_usage_bytes", memory.get("memory_usage", 0)
                )
            )

        # Cache metrics
        if "cache" in metrics:
            cache = metrics["cache"]
            lines.append("# HELP simplenote_mcp_cache_hits_total Cache hits")
            lines.append("# TYPE simplenote_mcp_cache_hits_total counter")
            lines.append(
                format_metric("simplenote_mcp_cache_hits_total", cache.get("hits", 0))
            )

            lines.append("# HELP simplenote_mcp_cache_misses_total Cache misses")
            lines.append("# TYPE simplenote_mcp_cache_misses_total counter")
            lines.append(
                format_metric(
                    "simplenote_mcp_cache_misses_total", cache.get("misses", 0)
                )
            )

        # Custom metrics
        for name, metric_data in self.custom_metrics.items():
            safe_name = name.replace("-", "_").replace(".", "_")
            lines.append(f"# HELP simplenote_mcp_{safe_name} Custom metric: {name}")
            lines.append(f"# TYPE simplenote_mcp_{safe_name} gauge")
            lines.append(
                format_metric(
                    f"simplenote_mcp_{safe_name}",
                    metric_data["value"],
                    metric_data["labels"],
                )
            )

        return "\n".join(lines) + "\n"

    start_time = time.time()


class HTTPEndpointsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health and metrics endpoints."""

    # Class-level instances shared across requests
    health_status = HealthStatus()
    readiness_checker = ReadinessChecker()
    metrics_collector = MetricsCollector()

    def log_message(self, format: str, *args) -> None:
        """Override to use our logging system."""
        logger.info(f"HTTP {self.command} {self.path} - {format % args}")

    def _is_authorized(self, config: Any) -> bool:
        """Check this request against HTTP_ENDPOINT_AUTH_TOKEN, if configured.

        No token configured: every request is allowed — the endpoint relies
        entirely on HTTP_HOST staying loopback (enforced at startup, see
        HTTPEndpointsServer.start()). Token configured: loopback callers are
        still trusted without a token, matching the MCP HTTP transport's
        model and keeping the container's own exec-based liveness/readiness
        probe working without needing the secret in its command line. Any
        other source must present a matching bearer token.
        """
        token = config.http_endpoint_auth_token
        if not token:
            return True
        if self.client_address[0] in _LOOPBACK_ADDRESSES:
            return True
        raw = self.headers.get("Authorization", "")
        if not raw.startswith("Bearer "):
            return False
        return hmac.compare_digest(raw[len("Bearer ") :], token)

    def _send_unauthorized(self) -> None:
        """Send 401 Unauthorized with a WWW-Authenticate header."""
        body = json.dumps(
            {"error": "Unauthorized", "timestamp": datetime.utcnow().isoformat()}
        ).encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("WWW-Authenticate", 'Bearer realm="simplenote-mcp-monitoring"')
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Handle GET requests."""
        config = get_config()
        parsed_url = urlparse(self.path)

        if not self._is_authorized(config):
            self._send_unauthorized()
            return

        start_time = time.time()

        try:
            if parsed_url.path == config.http_health_path:
                self._handle_health()
            elif parsed_url.path == config.http_ready_path:
                self._handle_readiness()
            elif parsed_url.path == config.http_metrics_path:
                self._handle_metrics(parse_qs(parsed_url.query))
            elif parsed_url.path == "/thresholds":
                self._handle_thresholds()
            else:
                self._handle_not_found()

        except Exception as e:
            logger.error(f"Error handling HTTP request: {e}")
            self._send_error_response(500, "Internal Server Error")

        # Record response time
        duration = time.time() - start_time
        self.metrics_collector.add_metric(
            "http_request_duration",
            duration,
            {"method": self.command, "path": parsed_url.path},
        )

    def _handle_health(self) -> None:
        """Handle health check endpoint."""
        # Perform health checks
        self._perform_health_checks()

        health_data = self.health_status.to_dict()

        # Only a genuine "unhealthy" check (e.g. an exception while probing
        # a subsystem) fails the HTTP status — "degraded" (e.g. a low cache
        # hit rate, which is completely normal right after startup or
        # during a quiet period) still means the process is up and able to
        # serve, so it must not fail liveness/readiness probes wired to
        # this endpoint. The degraded detail is still visible in the JSON
        # body for anyone actually monitoring it.
        status_code = 503 if health_data["status"] == "unhealthy" else 200
        if status_code != 200:
            logger.warning(f"Server unhealthy: {health_data}")

        self._send_json_response(health_data, status_code)

    def _handle_readiness(self) -> None:
        """Handle readiness check endpoint."""
        readiness_data = self.readiness_checker.to_dict()
        status_code = 200 if readiness_data["ready"] else 503

        self._send_json_response(readiness_data, status_code)

    def _handle_metrics(self, query_params: dict[str, list]) -> None:
        """Handle metrics endpoint."""
        # Check if Prometheus format is requested
        format_param = query_params.get("format", ["json"])[0].lower()

        if format_param == "prometheus":
            prometheus_data = self.metrics_collector.get_prometheus_format()
            self._send_text_response(
                prometheus_data, content_type="text/plain; version=0.0.4"
            )
        else:
            metrics_data = self.metrics_collector.get_all_metrics()
            self._send_json_response(metrics_data)

    def _handle_thresholds(self) -> None:
        """Handle performance thresholds endpoint."""
        try:
            threshold_status = get_performance_threshold_status()
            self._send_json_response(threshold_status)
        except Exception as e:
            logger.error(f"Error getting threshold status: {e}")
            self._send_json_response(
                {"error": "Failed to retrieve threshold status", "details": str(e)},
                status=500,
            )

    def _handle_not_found(self) -> None:
        """Handle 404 Not Found."""
        config = get_config()
        error_response = {
            "error": "Not Found",
            "message": f"Available endpoints: {config.http_health_path}, {config.http_ready_path}, {config.http_metrics_path}, /thresholds",
        }
        self._send_json_response(error_response, 404)

    def _perform_health_checks(self) -> None:
        """Perform various health checks."""
        try:
            # Check memory usage
            memory_metrics = get_memory_metrics()
            memory_usage_mb = memory_metrics.get("memory_usage", 0) / (1024 * 1024)

            if memory_usage_mb > 1000:  # 1GB threshold
                self.health_status.add_check(
                    "memory",
                    "degraded",
                    f"High memory usage: {memory_usage_mb:.1f} MB",
                    {"memory_mb": memory_usage_mb},
                )
            else:
                self.health_status.add_check(
                    "memory",
                    "healthy",
                    f"Memory usage: {memory_usage_mb:.1f} MB",
                    {"memory_mb": memory_usage_mb},
                )

        except Exception as e:
            self.health_status.add_check(
                "memory", "unhealthy", f"Memory check failed: {e}"
            )

        if get_config().cache_health_checks:
            try:
                # Check cache status
                cache_metrics = get_cache_metrics()
                hit_rate = cache_metrics.get("hit_rate", 0)

                if hit_rate < 0.5:  # 50% hit rate threshold
                    self.health_status.add_check(
                        "cache",
                        "degraded",
                        f"Low cache hit rate: {hit_rate:.1%}",
                        cache_metrics,
                    )
                else:
                    self.health_status.add_check(
                        "cache",
                        "healthy",
                        f"Cache hit rate: {hit_rate:.1%}",
                        cache_metrics,
                    )

            except Exception as e:
                self.health_status.add_check(
                    "cache", "unhealthy", f"Cache check failed: {e}"
                )

        # Add basic connectivity check
        self.health_status.add_check(
            "server",
            "healthy",
            "HTTP endpoints responding",
            {"timestamp": datetime.utcnow().isoformat()},
        )

    def _send_json_response(self, data: Any, status_code: int = 200) -> None:
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode("utf-8"))

    def _send_text_response(
        self, data: str, status_code: int = 200, content_type: str = "text/plain"
    ) -> None:
        """Send text response."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        self.wfile.write(data.encode("utf-8"))

    def _send_error_response(self, status_code: int, message: str) -> None:
        """Send error response."""
        error_data = {
            "error": message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._send_json_response(error_data, status_code)


class HTTPEndpointsServer:
    """HTTP server for health and metrics endpoints."""

    def __init__(self) -> None:
        self.config = get_config()
        self.server: HTTPServer | None = None
        self.server_thread: Thread | None = None
        self.running = False

    def start(self) -> None:
        """Start the HTTP server."""
        if not self.config.enable_http_endpoint:
            logger.info("HTTP endpoints disabled via configuration")
            return

        if self.running:
            logger.warning("HTTP server is already running")
            return

        if self.config.http_host not in _LOOPBACK_HOSTS:
            if not self.config.http_endpoint_auth_token:
                raise ConfigurationError(
                    f"Refusing to bind the health/metrics endpoint to "
                    f"non-loopback HTTP_HOST={self.config.http_host!r} without "
                    "HTTP_ENDPOINT_AUTH_TOKEN set — /health, /ready, /metrics, "
                    "and /thresholds would otherwise be reachable by anyone who "
                    "can reach this port with no authentication. Set a bearer "
                    "token, or bind HTTP_HOST to 127.0.0.1/localhost for "
                    "same-host-only access.",
                    subcategory="http_endpoint_auth_required",
                )
            logger.info(
                f"Health/metrics endpoint bound to non-loopback "
                f"HTTP_HOST={self.config.http_host!r}, protected by "
                "HTTP_ENDPOINT_AUTH_TOKEN. Loopback callers (e.g. the "
                "container's own liveness probe) remain trusted without it."
            )

        try:
            self.server = HTTPServer(
                (self.config.http_host, self.config.http_port), HTTPEndpointsHandler
            )

            # Start server in background thread
            self.server_thread = Thread(
                target=self._run_server, name="http-endpoints-server", daemon=True
            )
            self.server_thread.start()
            self.running = True

            logger.info(
                f"HTTP endpoints started on http://{self.config.http_host}:{self.config.http_port}",
                extra={
                    "health_path": self.config.http_health_path,
                    "ready_path": self.config.http_ready_path,
                    "metrics_path": self.config.http_metrics_path,
                },
            )

            # Mark HTTP server as ready
            HTTPEndpointsHandler.readiness_checker.set_component_ready(
                "http_server", True
            )

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            raise

    def stop(self) -> None:
        """Stop the HTTP server."""
        if not self.running or not self.server:
            return

        logger.info("Stopping HTTP endpoints server")

        try:
            self.server.shutdown()
            self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5.0)

            self.running = False
            HTTPEndpointsHandler.readiness_checker.set_component_ready(
                "http_server", False
            )

            logger.info("HTTP endpoints server stopped")

        except Exception as e:
            logger.error(f"Error stopping HTTP server: {e}")

    def _run_server(self) -> None:
        """Run the HTTP server (internal method for thread)."""
        try:
            logger.info("HTTP endpoints server thread started")
            self.server.serve_forever()
        except Exception as e:
            if self.running:  # Only log if we didn't intentionally stop
                logger.error(f"HTTP server error: {e}")
        finally:
            logger.info("HTTP endpoints server thread stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running

    def get_server_info(self) -> dict[str, Any]:
        """Get information about the HTTP server."""
        if not self.running:
            return {"running": False}

        return {
            "running": True,
            "host": self.config.http_host,
            "port": self.config.http_port,
            "endpoints": {
                "health": self.config.http_health_path,
                "ready": self.config.http_ready_path,
                "metrics": self.config.http_metrics_path,
            },
        }


# Global HTTP server instance
_http_server: HTTPEndpointsServer | None = None


def get_http_server() -> HTTPEndpointsServer:
    """Get global HTTP server instance."""
    global _http_server
    if _http_server is None:
        _http_server = HTTPEndpointsServer()
    return _http_server


def start_http_endpoints() -> None:
    """Start HTTP endpoints server."""
    server = get_http_server()
    server.start()


def stop_http_endpoints() -> None:
    """Stop HTTP endpoints server."""
    server = get_http_server()
    server.stop()


def set_component_ready(component: str, ready: bool = True) -> None:
    """Mark a component as ready or not ready."""
    HTTPEndpointsHandler.readiness_checker.set_component_ready(component, ready)


def add_health_check(
    name: str, status: str, message: str = "", details: dict[str, Any] | None = None
) -> None:
    """Add a health check result."""
    HTTPEndpointsHandler.health_status.add_check(name, status, message, details)


def add_metric(name: str, value: Any, labels: dict[str, str] | None = None) -> None:
    """Add a custom metric."""
    HTTPEndpointsHandler.metrics_collector.add_metric(name, value, labels)
