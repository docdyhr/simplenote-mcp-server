"""Tests for the MCP HTTP transport security controls added in server.py:
loopback detection, the bearer-token check, the DNS-rebinding-protection
TransportSecuritySettings builder, and run_http()'s fail-closed startup
guard for non-loopback binds without a configured token.
"""

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.transport_security import TransportSecuritySettings

import simplenote_mcp.server.server as srv
from simplenote_mcp.server.errors import ConfigurationError


class TestIsLoopbackHost:
    @pytest.mark.parametrize(
        "host,expected",
        [
            ("127.0.0.1", True),
            ("localhost", True),
            ("::1", True),
            ("0.0.0.0", False),  # noqa: S104
            ("192.168.1.5", False),
            ("example.com", False),
        ],
    )
    def test_loopback_detection(self, host, expected):
        assert srv._is_loopback_host(host) is expected


class TestBearerTokenValid:
    def _scope(self, auth_header: bytes | None) -> dict:
        headers = [] if auth_header is None else [(b"authorization", auth_header)]
        return {"headers": headers}

    def test_correct_token_is_valid(self):
        scope = self._scope(b"Bearer s3cret")
        assert srv._bearer_token_valid(scope, "s3cret") is True

    def test_wrong_token_is_invalid(self):
        scope = self._scope(b"Bearer wrong-token")
        assert srv._bearer_token_valid(scope, "s3cret") is False

    def test_missing_header_is_invalid(self):
        scope = self._scope(None)
        assert srv._bearer_token_valid(scope, "s3cret") is False

    def test_non_bearer_scheme_is_invalid(self):
        scope = self._scope(b"Basic dXNlcjpwYXNz")
        assert srv._bearer_token_valid(scope, "s3cret") is False

    def test_empty_headers_list_is_invalid(self):
        assert srv._bearer_token_valid({"headers": []}, "s3cret") is False

    def test_no_headers_key_is_invalid(self):
        assert srv._bearer_token_valid({}, "s3cret") is False


class TestBuildHttpSecuritySettings:
    def _config(self, allowed_hosts=None, allowed_origins=None):
        config = MagicMock()
        config.mcp_http_allowed_hosts = allowed_hosts or []
        config.mcp_http_allowed_origins = allowed_origins or []
        return config

    def test_explicit_allowed_hosts_enables_protection(self):
        config = self._config(allowed_hosts=["example.com"])
        settings = srv._build_http_security_settings(config, host="0.0.0.0")  # noqa: S104
        assert isinstance(settings, TransportSecuritySettings)
        assert settings.enable_dns_rebinding_protection is True
        assert settings.allowed_hosts == ["example.com"]

    def test_loopback_host_gets_safe_default_allowlist(self):
        config = self._config()
        settings = srv._build_http_security_settings(config, host="127.0.0.1")
        assert settings.enable_dns_rebinding_protection is True
        assert "127.0.0.1:*" in settings.allowed_hosts
        assert "localhost:*" in settings.allowed_hosts

    def test_non_loopback_without_allowlist_disables_protection_with_warning(
        self, caplog
    ):
        import logging

        config = self._config()
        with caplog.at_level(logging.WARNING, logger="simplenote_mcp"):
            settings = srv._build_http_security_settings(config, host="0.0.0.0")  # noqa: S104
        assert settings.enable_dns_rebinding_protection is False
        assert any(
            "DNS rebinding protection disabled" in r.message for r in caplog.records
        )


class TestRunHttpFailClosedGuard:
    """run_http() must refuse to start on a non-loopback host without a
    configured bearer token, and must not do so for loopback binds or
    non-loopback binds that do have a token configured.
    """

    def _config(self, token=None):
        config = MagicMock()
        config.mcp_http_auth_token = token
        config.mcp_http_allowed_hosts = []
        config.mcp_http_allowed_origins = []
        return config

    @pytest.mark.asyncio
    async def test_non_loopback_without_token_raises_before_any_transport_setup(self):
        config = self._config(token=None)
        unreachable_transport = MagicMock(
            side_effect=AssertionError(
                "transport must not be constructed when the guard rejects startup"
            )
        )
        with (
            patch("simplenote_mcp.server.server.get_config", return_value=config),
            patch(
                "mcp.server.streamable_http.StreamableHTTPServerTransport",
                unreachable_transport,
            ),
            pytest.raises(ConfigurationError, match="MCP_HTTP_AUTH_TOKEN"),
        ):
            await srv.run_http(host="0.0.0.0", port=8000, path="/mcp")  # noqa: S104

    class _PastGuardSentinel(Exception):
        """Raised by the fake transport's connect() to prove control flow
        reached transport construction — i.e. the guard did not block it."""

    class _FakeConnectCM:
        async def __aenter__(self):
            raise TestRunHttpFailClosedGuard._PastGuardSentinel

        async def __aexit__(self, *exc_info):
            return False

    class _FakeTransport:
        def connect(self):
            return TestRunHttpFailClosedGuard._FakeConnectCM()

    @pytest.mark.asyncio
    async def test_loopback_without_token_passes_the_guard(self):
        config = self._config(token=None)
        with (
            patch("simplenote_mcp.server.server.get_config", return_value=config),
            patch(
                "mcp.server.streamable_http.StreamableHTTPServerTransport",
                return_value=self._FakeTransport(),
            ),
            pytest.raises(self._PastGuardSentinel),
        ):
            await srv.run_http(host="127.0.0.1", port=8000, path="/mcp")

    @pytest.mark.asyncio
    async def test_non_loopback_with_token_passes_the_guard(self):
        config = self._config(token="s3cret")  # noqa: S106
        with (
            patch("simplenote_mcp.server.server.get_config", return_value=config),
            patch(
                "mcp.server.streamable_http.StreamableHTTPServerTransport",
                return_value=self._FakeTransport(),
            ),
            pytest.raises(self._PastGuardSentinel),
        ):
            await srv.run_http(host="0.0.0.0", port=8000, path="/mcp")  # noqa: S104
