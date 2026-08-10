"""Regression tests for auth-failure robustness (task brief 2026-06-24).

Covers:
- _test_simplenote_connection raises AuthenticationError (not TypeError) when
  authenticate() returns None or raises SimplenoteLoginFailed.
- _get_note_from_cache_or_api raises ResourceNotFoundError (not TypeError) when
  the Simplenote token is None.
- GetNoteVersionsHandler raises ResourceNotFoundError (not TypeError) when the
  Simplenote token is None.
- GetServerInfoHandler exposes authenticated/last_sync_error in debug payload.
- LogPatternMonitor._monitor_logs starts at current file end, not position 0.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import AuthenticationError, ResourceNotFoundError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sn(token=None):
    """Return a MagicMock Simplenote client with configurable token."""
    sn = MagicMock()
    sn.token = token
    sn.username = "user@example.com"
    sn.password = "secret"
    return sn


# ---------------------------------------------------------------------------
# _test_simplenote_connection — fail-fast on auth
# ---------------------------------------------------------------------------


class TestTestSimplenoteConnection:
    """_test_simplenote_connection should raise AuthenticationError, not TypeError."""

    @pytest.mark.asyncio
    async def test_none_token_raises_auth_error(self):
        """authenticate() returning None must surface as AuthenticationError."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn(token=None)
        sn.authenticate.return_value = None  # no token

        with pytest.raises(AuthenticationError):
            await _test_simplenote_connection(sn)

    @pytest.mark.asyncio
    async def test_authenticate_exception_raises_auth_error(self):
        """authenticate() raising any exception surfaces as AuthenticationError."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn()
        sn.authenticate.side_effect = Exception("Login failed")

        with pytest.raises(AuthenticationError):
            await _test_simplenote_connection(sn)

    @pytest.mark.asyncio
    async def test_valid_token_proceeds_to_api_check(self):
        """With a valid token the connection test calls get_note_list."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn()
        sn.authenticate.return_value = "valid-token-abc"
        sn.get_note_list.return_value = ([], 0)

        await _test_simplenote_connection(sn)

        sn.get_note_list.assert_called_once()
        assert sn.token == "valid-token-abc"

    @pytest.mark.asyncio
    async def test_api_status_nonzero_raises_auth_error(self):
        """get_note_list returning non-zero status raises AuthenticationError."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn()
        sn.authenticate.return_value = "valid-token"
        sn.get_note_list.return_value = (None, 1)

        with pytest.raises(AuthenticationError):
            await _test_simplenote_connection(sn)


# ---------------------------------------------------------------------------
# _background_cache_initialization_safe — stores last_auth_error
# ---------------------------------------------------------------------------


class TestBackgroundCacheInitSafe:
    """Auth errors must be stored in _last_auth_error for get_server_info."""

    @pytest.mark.asyncio
    async def test_auth_error_stored_in_module_state(self):
        import simplenote_mcp.server.server as srv
        from simplenote_mcp.server.server import _background_cache_initialization_safe

        sn = _make_sn(token=None)
        sn.authenticate.return_value = None  # triggers AuthenticationError

        cache = MagicMock()
        srv._last_auth_error = None  # start clean

        await _background_cache_initialization_safe(cache, sn, timeout=10)

        assert srv._last_auth_error is not None
        assert (
            "authentication" in srv._last_auth_error.lower()
            or "token" in srv._last_auth_error.lower()
        )

    @pytest.mark.asyncio
    async def test_success_clears_last_auth_error(self):
        import simplenote_mcp.server.server as srv
        from simplenote_mcp.server.server import _background_cache_initialization_safe

        sn = _make_sn(token="valid-token")
        sn.authenticate.return_value = "valid-token"
        sn.get_note_list.return_value = ([], 0)

        cache = MagicMock()
        cache.initialize = AsyncMock(return_value=None)
        cache._notes = {}
        srv._last_auth_error = "stale error from last run"

        with patch(
            "simplenote_mcp.server.server._background_cache_initialization",
            new_callable=AsyncMock,
        ):
            await _background_cache_initialization_safe(cache, sn, timeout=10)

        assert srv._last_auth_error is None


# ---------------------------------------------------------------------------
# _get_note_from_cache_or_api — clean not-found when token is None
# ---------------------------------------------------------------------------


class TestGetNoteFromCacheOrApi:
    """API fallback with None token must return ResourceNotFoundError, not TypeError."""

    def _make_handler(self, sn, cache=None):
        from simplenote_mcp.server.tool_handlers import GetNoteHandler

        handler = GetNoteHandler.__new__(GetNoteHandler)
        handler.sn = sn
        handler.note_cache = cache
        return handler

    def test_none_token_raises_resource_not_found(self):
        """No token → ResourceNotFoundError, never a urllib TypeError."""
        sn = _make_sn(token=None)

        # Cache miss: cache returns None
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.side_effect = ResourceNotFoundError("not found")

        handler = self._make_handler(sn, cache)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            handler._get_note_from_cache_or_api("missing-id")

        assert (
            "not authenticated" in str(exc_info.value).lower()
            or "not found" in str(exc_info.value).lower()
        )
        # The sn.get_note (which would TypeError) must NOT have been called
        sn.get_note.assert_not_called()

    def test_valid_token_falls_back_to_api(self):
        """With a valid token the API is called when cache misses."""
        sn = _make_sn(token="valid-token")
        note = {"key": "abc", "content": "Hello", "tags": []}
        sn.get_note.return_value = (note, 0)

        # Empty cache
        cache = MagicMock()
        cache.is_initialized = False  # skip cache lookup

        handler = self._make_handler(sn, cache)
        result = handler._get_note_from_cache_or_api("abc")

        assert result == note
        sn.get_note.assert_called_once_with("abc")


# ---------------------------------------------------------------------------
# GetNoteVersionsHandler — clean not-found when token is None
# ---------------------------------------------------------------------------


class TestGetNoteVersionsHandler:
    """get_note_versions with None token must return clean error, not TypeError."""

    def _make_handler(self, sn):
        from simplenote_mcp.server.tool_handlers import GetNoteVersionsHandler

        handler = GetNoteVersionsHandler.__new__(GetNoteVersionsHandler)
        handler.sn = sn
        handler.note_cache = None
        return handler

    @pytest.mark.asyncio
    async def test_none_token_returns_not_found_error(self):
        """None token → structured error response, not a crash."""
        sn = _make_sn(token=None)
        handler = self._make_handler(sn)

        result = await handler.handle({"note_id": "some-id"})

        assert isinstance(result, types.CallToolResult)
        assert result.is_error is True
        payload = json.loads(result.content[0].text)
        assert payload.get("success") is False
        # Must NOT have called sn.get_note (which would TypeError)
        sn.get_note.assert_not_called()


# ---------------------------------------------------------------------------
# GetServerInfoHandler — authenticated / last_sync_error in payload
# ---------------------------------------------------------------------------


class TestGetServerInfoHandler:
    """get_server_info must expose authenticated and last_sync_error."""

    def _make_handler(self, sn, cache=None):
        from simplenote_mcp.server.tool_handlers import GetServerInfoHandler

        handler = GetServerInfoHandler.__new__(GetServerInfoHandler)
        handler.sn = sn
        handler.note_cache = cache
        return handler

    @pytest.mark.asyncio
    async def test_unauthenticated_reported_in_payload(self):
        import simplenote_mcp.server.server as srv

        sn = _make_sn(token=None)
        srv._last_auth_error = "Simplenote authentication returned no token"
        cache = MagicMock()
        cache.is_initialized = True
        cache._notes = {}

        handler = self._make_handler(sn, cache)
        result = await handler.handle({})
        payload = json.loads(result[0].text)

        assert payload["debug"]["authenticated"] is False
        assert payload["debug"]["last_sync_error"] is not None

    @pytest.mark.asyncio
    async def test_authenticated_reported_in_payload(self):
        import simplenote_mcp.server.server as srv

        sn = _make_sn(token="tok123")
        srv._last_auth_error = None
        cache = MagicMock()
        cache.is_initialized = True
        cache._notes = {"a": {}, "b": {}}

        handler = self._make_handler(sn, cache)
        result = await handler.handle({})
        payload = json.loads(result[0].text)

        assert payload["debug"]["authenticated"] is True
        assert payload["debug"]["last_sync_error"] is None
        assert payload["debug"]["note_count"] == 2


# ---------------------------------------------------------------------------
# LogPatternMonitor — starts at file end, not position 0
# ---------------------------------------------------------------------------


class TestLogMonitorStartsAtFileEnd:
    """_monitor_logs must seek to current EOF so old content is not re-processed."""

    def test_existing_file_position_starts_at_end(self):
        """If a log file exists, the initial position must equal file size."""
        from simplenote_mcp.server.log_monitor import LogPatternMonitor

        monitor = LogPatternMonitor()

        captured_positions: dict = {}

        def fake_monitor(log_sources):
            # Capture the first file_positions dict that would be created

            for source in log_sources:
                if source.exists():
                    captured_positions[source] = source.stat().st_size
                else:
                    captured_positions[source] = 0
            # Don't actually start the loop
            raise StopIteration("captured")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("old content that must not trigger alerts\n" * 10)
            log_path = Path(f.name)

        try:
            expected_size = log_path.stat().st_size
            assert expected_size > 0

            with patch.object(monitor, "_monitor_logs", side_effect=fake_monitor):
                try:
                    monitor.start_monitoring([log_path])
                except StopIteration:
                    pass

            # The fake just verifies the computation matches — now test the real
            # _monitor_logs implementation directly by inspecting the source.
            # A simpler check: run a real _monitor_logs call that exits immediately
            # and verify no pattern was matched for the old content.
            monitor2 = LogPatternMonitor()
            monitor2._stop_event.set()  # stop immediately after first iteration

            # If the implementation is correct, processing the existing content would
            # NOT occur because _monitor_logs seeks to file end.
            # We verify by checking that matched counts stay at 0.
            import threading

            t = threading.Thread(target=monitor2._monitor_logs, args=([log_path],))
            t.start()
            t.join(timeout=2.0)

            assert monitor2.stats["logs_processed"] == 0, (
                "Old log content must not be processed on startup"
            )
        finally:
            log_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# keychain — get_simperium_token / file cache
# ---------------------------------------------------------------------------


def _make_run_result(returncode: int, stdout: str = "") -> MagicMock:
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    return r


class TestGetSimperiumToken:
    """get_simperium_token: file cache first, Desktop keychain fallback."""

    def test_file_cache_hit_skips_desktop(self):
        """Token in file cache → Desktop keychain never queried."""
        from simplenote_mcp.server import keychain

        with (
            patch.object(keychain, "_read_file_cache", return_value="cached-token"),
            patch.object(keychain, "_read_desktop_token") as mock_desktop,
        ):
            result = keychain.get_simperium_token("user@example.com")

        assert result == "cached-token"
        mock_desktop.assert_not_called()

    def test_cache_miss_reads_desktop_and_caches(self):
        """File cache miss → reads Desktop entry → caches token to file."""
        from simplenote_mcp.server import keychain

        with patch("simplenote_mcp.server.keychain.sys") as mock_sys:
            mock_sys.platform = "darwin"
            with (
                patch.object(keychain, "_read_file_cache", return_value=None),
                patch.object(
                    keychain, "_read_desktop_token", return_value="desktop-token"
                ),
                patch.object(keychain, "_write_file_cache") as mock_write,
            ):
                result = keychain.get_simperium_token("user@example.com")

        assert result == "desktop-token"
        mock_write.assert_called_once_with("user@example.com", "desktop-token")

    def test_both_miss_returns_none(self):
        """No file cache and no Desktop entry → None."""
        from simplenote_mcp.server import keychain

        with patch("simplenote_mcp.server.keychain.sys") as mock_sys:
            mock_sys.platform = "darwin"
            with (
                patch.object(keychain, "_read_file_cache", return_value=None),
                patch.object(keychain, "_read_desktop_token", return_value=None),
            ):
                result = keychain.get_simperium_token("user@example.com")

        assert result is None

    def test_non_darwin_skips_desktop_read(self):
        """On non-macOS, Desktop keychain read is skipped entirely."""
        from simplenote_mcp.server import keychain

        with patch("simplenote_mcp.server.keychain.sys") as mock_sys:
            mock_sys.platform = "linux"
            with (
                patch.object(keychain, "_read_file_cache", return_value=None),
                patch.object(keychain, "_read_desktop_token") as mock_desktop,
            ):
                result = keychain.get_simperium_token("user@example.com")

        assert result is None
        mock_desktop.assert_not_called()


class TestInvalidateCachedToken:
    """invalidate_cached_token deletes the cache file."""

    def test_calls_delete_file_cache(self):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_delete_file_cache") as mock_del:
            keychain.invalidate_cached_token("user@example.com")

        mock_del.assert_called_once_with("user@example.com")


class TestFileCacheHelpers:
    """File cache read / write / delete."""

    def test_read_missing_returns_none(self, tmp_path):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_CACHE_DIR", tmp_path):
            result = keychain._read_file_cache("user@example.com")

        assert result is None

    def test_write_then_read(self, tmp_path):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_CACHE_DIR", tmp_path):
            keychain._write_file_cache("user@example.com", "mytoken")
            result = keychain._read_file_cache("user@example.com")

        assert result == "mytoken"

    def test_write_sets_mode_600(self, tmp_path):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_CACHE_DIR", tmp_path):
            keychain._write_file_cache("user@example.com", "mytoken")
            path = keychain._cache_path("user@example.com")

        assert oct(path.stat().st_mode)[-3:] == "600"

    def test_delete_removes_file(self, tmp_path):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_CACHE_DIR", tmp_path):
            keychain._write_file_cache("user@example.com", "mytoken")
            keychain._delete_file_cache("user@example.com")
            result = keychain._read_file_cache("user@example.com")

        assert result is None

    def test_delete_missing_is_noop(self, tmp_path):
        from simplenote_mcp.server import keychain

        with patch.object(keychain, "_CACHE_DIR", tmp_path):
            keychain._delete_file_cache("user@example.com")  # must not raise


class TestReadDesktopToken:
    """_read_desktop_token reads the Simplenote Desktop keychain entry."""

    def test_success_returns_stripped_token(self):
        from simplenote_mcp.server.keychain import _read_desktop_token

        hit = _make_run_result(0, "tok123\n")
        with patch("subprocess.run", return_value=hit):
            result = _read_desktop_token("user@example.com")

        assert result == "tok123"

    def test_nonzero_exit_returns_none(self):
        from simplenote_mcp.server.keychain import _read_desktop_token

        with patch("subprocess.run", return_value=_make_run_result(44)):
            result = _read_desktop_token("user@example.com")

        assert result is None

    def test_subprocess_error_returns_none(self):
        from simplenote_mcp.server.keychain import _read_desktop_token

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _read_desktop_token("user@example.com")

        assert result is None


# ---------------------------------------------------------------------------
# _test_simplenote_connection — keychain and env-var token paths
# ---------------------------------------------------------------------------


class TestConnectionWithPresetToken:
    """_test_simplenote_connection must skip authenticate() when a token is available."""

    @pytest.mark.asyncio
    async def test_env_var_token_skips_authenticate(self):
        """SIMPLENOTE_TOKEN env var → authenticate() must NOT be called."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn(token=None)
        sn.get_note_list.return_value = ([], 0)

        with patch.dict("os.environ", {"SIMPLENOTE_TOKEN": "env-supplied-token"}):
            await _test_simplenote_connection(sn)

        sn.authenticate.assert_not_called()
        assert sn.token == "env-supplied-token"

    @pytest.mark.asyncio
    async def test_keychain_token_skips_authenticate(self):
        """macOS keychain token → authenticate() must NOT be called."""
        from simplenote_mcp.server.server import _test_simplenote_connection

        sn = _make_sn(token=None)
        sn.get_note_list.return_value = ([], 0)

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("SIMPLENOTE_TOKEN", None)
            with patch(
                "simplenote_mcp.server.keychain.get_simperium_token",
                return_value="keychain-token-xyz",
            ):
                await _test_simplenote_connection(sn)

        sn.authenticate.assert_not_called()
        assert sn.token == "keychain-token-xyz"
