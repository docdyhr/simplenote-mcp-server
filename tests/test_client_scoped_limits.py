"""Tests for per-client identity resolution and the per-client write budget
added to server.py: _resolve_client_id(), _check_write_budget(),
_record_write(). Covers both the stdio fallback and HTTP-transport identity
derived from server.py's own `_request_ctx_var` contextvar (mcp 2.0 removed
the SDK's `server.request_context` property; the `on_call_tool` adapter now
stashes the per-request ServerRequestContext there instead).
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import simplenote_mcp.server.server as srv
from simplenote_mcp.server.errors import ValidationError


def _fake_request_context(request):
    """Build a minimal object with a `.request` attribute, matching the
    shape _request_ctx_var holds (only `.request` is read)."""
    return SimpleNamespace(request=request)


@contextmanager
def _active_request_context(ctx):
    token = srv._request_ctx_var.set(ctx)
    try:
        yield
    finally:
        srv._request_ctx_var.reset(token)


class TestResolveClientId:
    def test_no_active_request_context_is_stdio_local(self):
        # No request context set at all — matches a direct call outside of
        # any MCP request (e.g. process startup).
        assert srv._resolve_client_id() == "stdio-local"

    def test_stdio_request_context_with_no_request_is_stdio_local(self):
        fake_ctx = _fake_request_context(request=None)
        with _active_request_context(fake_ctx):
            assert srv._resolve_client_id() == "stdio-local"

    def test_http_request_uses_peer_source_ip(self):
        fake_request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.5"))
        fake_ctx = _fake_request_context(request=fake_request)
        with _active_request_context(fake_ctx):
            assert srv._resolve_client_id() == "http:203.0.113.5"

    def test_http_request_without_client_attr_is_unknown(self):
        fake_request = SimpleNamespace(client=None)
        fake_ctx = _fake_request_context(request=fake_request)
        with _active_request_context(fake_ctx):
            assert srv._resolve_client_id() == "http:unknown"

    def test_different_peers_get_different_identifiers(self):
        for host in ("10.0.0.1", "10.0.0.2"):
            fake_request = SimpleNamespace(client=SimpleNamespace(host=host))
            fake_ctx = _fake_request_context(request=fake_request)
            with _active_request_context(fake_ctx):
                assert srv._resolve_client_id() == f"http:{host}"


class TestPerClientWriteBudget:
    @pytest.fixture(autouse=True)
    def _clean_budget_state(self):
        srv._write_timestamps.clear()
        yield
        srv._write_timestamps.clear()

    def _config(self, max_writes=3, window=60):
        config = MagicMock()
        config.write_budget_max = max_writes
        config.write_budget_window_seconds = window
        return config

    def test_budget_exhaustion_is_scoped_to_one_client(self):
        config = self._config(max_writes=2)
        with patch("simplenote_mcp.server.server.get_config", return_value=config):
            srv._check_write_budget("client-a")
            srv._record_write("client-a")
            srv._check_write_budget("client-a")
            srv._record_write("client-a")

            # client-a is now at its limit (2/2) — the third check must fail.
            with pytest.raises(ValidationError, match="Write budget exhausted"):
                srv._check_write_budget("client-a")

            # client-b has never written — its own budget is untouched.
            srv._check_write_budget("client-b")  # must not raise

    def test_recording_a_write_only_affects_that_clients_bucket(self):
        config = self._config(max_writes=100)
        with patch("simplenote_mcp.server.server.get_config", return_value=config):
            srv._record_write("client-a")
            srv._record_write("client-a")
            srv._record_write("client-b")

        assert len(srv._write_timestamps["client-a"]) == 2
        assert len(srv._write_timestamps["client-b"]) == 1
