"""Focused tests for server.py handler functions.

Covers the paths left untested after the legacy disabled test files were
retired:  get_simplenote_client, write/cleanup_pid_file, setup_signal_handlers,
handle_list_tools exception fallback, handle_call_tool unknown-tool and
ServerError paths, handle_list_prompts, handle_get_prompt (all three branches),
and handle_read_resource invalid-URI / not-found paths.
"""

import json
import os
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_client():
    """Reset the global simplenote_client singleton between tests."""
    import simplenote_mcp.server.server as srv

    srv.simplenote_client = None


# ---------------------------------------------------------------------------
# get_simplenote_client
# ---------------------------------------------------------------------------


class TestGetSimplenoteClient:
    """Tests for the get_simplenote_client() factory."""

    def setup_method(self):
        _clear_client()

    def teardown_method(self):
        _clear_client()

    def test_offline_mode_returns_mock(self):
        """In offline mode a MagicMock is returned without touching Simplenote."""
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.offline_mode = True

        with patch("simplenote_mcp.server.server.get_config", return_value=mock_config):
            client = srv.get_simplenote_client()

        assert client is not None
        # Mock has the expected methods configured by the factory
        assert hasattr(client, "get_note_list")

    def test_offline_mode_client_cached(self):
        """A second call in offline mode reuses the cached mock."""
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.offline_mode = True

        with patch("simplenote_mcp.server.server.get_config", return_value=mock_config):
            c1 = srv.get_simplenote_client()
            c2 = srv.get_simplenote_client()

        assert c1 is c2

    def test_missing_credentials_raises_auth_error(self):
        """Without credentials an AuthenticationError is raised."""
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = False

        with (
            patch("simplenote_mcp.server.server.get_config", return_value=mock_config),
            pytest.raises(AuthenticationError),
        ):
            srv.get_simplenote_client()

    def test_with_credentials_creates_simplenote_instance(self):
        """Valid credentials lead to a Simplenote instance being created."""
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "user@example.com"
        mock_config.simplenote_password = "secret"

        mock_sn = MagicMock()
        with (
            patch("simplenote_mcp.server.server.get_config", return_value=mock_config),
            patch("simplenote_mcp.server.server.Simplenote", return_value=mock_sn),
        ):
            client = srv.get_simplenote_client()

        assert client is mock_sn

    def test_non_server_error_wrapped_and_reraised(self):
        """A generic exception during init is wrapped into a ServerError."""
        import simplenote_mcp.server.server as srv
        from simplenote_mcp.server.errors import ServerError

        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.has_credentials = True
        mock_config.simplenote_email = "u@x.com"
        mock_config.simplenote_password = "p"

        with (
            patch("simplenote_mcp.server.server.get_config", return_value=mock_config),
            patch(
                "simplenote_mcp.server.server.Simplenote",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(ServerError),
        ):
            srv.get_simplenote_client()

    def test_clear_client_cache(self):
        """clear_client_cache() resets the global singleton."""
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.offline_mode = True

        with patch("simplenote_mcp.server.server.get_config", return_value=mock_config):
            srv.get_simplenote_client()  # populate the cache

        assert srv.simplenote_client is not None
        srv.clear_client_cache()
        assert srv.simplenote_client is None


# ---------------------------------------------------------------------------
# write_pid_file / cleanup_pid_file
# ---------------------------------------------------------------------------


class TestPidFileManagement:
    """Tests for PID file write and cleanup helpers."""

    def test_write_pid_file_creates_file(self, tmp_path):
        """write_pid_file() creates the PID file with the current PID."""
        import simplenote_mcp.server.server as srv

        pid_path = tmp_path / "server.pid"
        alt_path = tmp_path / "server_alt.pid"

        with (
            patch.object(srv, "PID_FILE_PATH", pid_path),
            patch.object(srv, "ALT_PID_FILE_PATH", alt_path),
        ):
            srv.write_pid_file()

        assert pid_path.exists()
        assert pid_path.read_text() == str(os.getpid())

    def test_cleanup_pid_file_removes_file(self, tmp_path):
        """cleanup_pid_file() removes PID files that exist."""
        import simplenote_mcp.server.server as srv

        pid_path = tmp_path / "server.pid"
        alt_path = tmp_path / "server_alt.pid"
        pid_path.write_text("12345")
        alt_path.write_text("12345")

        with (
            patch.object(srv, "PID_FILE_PATH", pid_path),
            patch.object(srv, "ALT_PID_FILE_PATH", alt_path),
        ):
            srv.cleanup_pid_file()

        assert not pid_path.exists()
        assert not alt_path.exists()

    def test_cleanup_pid_file_tolerates_missing(self, tmp_path):
        """cleanup_pid_file() does not raise if files don't exist."""
        import simplenote_mcp.server.server as srv

        pid_path = tmp_path / "no_such.pid"
        alt_path = tmp_path / "no_such_alt.pid"

        with (
            patch.object(srv, "PID_FILE_PATH", pid_path),
            patch.object(srv, "ALT_PID_FILE_PATH", alt_path),
        ):
            srv.cleanup_pid_file()  # should not raise


# ---------------------------------------------------------------------------
# setup_signal_handlers
# ---------------------------------------------------------------------------


class TestSetupSignalHandlers:
    """Tests for setup_signal_handlers()."""

    def test_signal_handlers_registered(self):
        """After setup_signal_handlers the SIGINT and SIGTERM handlers are callable."""
        import simplenote_mcp.server.server as srv

        srv.setup_signal_handlers()
        # Both signals should now point to our custom handler
        assert signal.getsignal(signal.SIGINT) is not signal.SIG_DFL
        assert signal.getsignal(signal.SIGTERM) is not signal.SIG_DFL


# ---------------------------------------------------------------------------
# handle_list_tools
# ---------------------------------------------------------------------------


class TestHandleListTools:
    """Tests for the list_tools handler."""

    @pytest.mark.asyncio
    async def test_returns_tool_list_normally(self):
        """handle_list_tools returns read-only tools without write_mode."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_list_tools()

        assert isinstance(result, list)
        assert len(result) >= 2
        names = [t.name for t in result]
        # Read-only tools are always present
        assert "search_notes" in names
        assert "list_notes" in names
        assert "get_note" in names
        # Write tools are absent when write_mode is off (the default)
        assert "create_note" not in names

    @pytest.mark.asyncio
    async def test_returns_write_tools_when_write_mode_enabled(self):
        """handle_list_tools includes write tools when SIMPLENOTE_WRITE_MODE=true."""
        import simplenote_mcp.server.config as _cfg
        import simplenote_mcp.server.server as srv

        _cfg._config = None
        try:
            with patch.dict("os.environ", {"SIMPLENOTE_WRITE_MODE": "true"}):
                result = await srv.handle_list_tools()
        finally:
            _cfg._config = None

        names = [t.name for t in result]
        assert "create_note" in names
        assert "update_note" in names
        assert "search_notes" in names

    @pytest.mark.asyncio
    async def test_exception_falls_back_to_core_tools(self):
        """When an unexpected error occurs only the fallback tool is returned."""
        import simplenote_mcp.server.server as srv

        # Patch the logger.info used at the start of the try-block to raise
        with patch.object(
            srv.logger, "info", side_effect=[RuntimeError("oops"), None, None, None]
        ):
            result = await srv.handle_list_tools()

        names = [t.name for t in result]
        assert "search_notes" in names


# ---------------------------------------------------------------------------
# handle_call_tool — unknown tool and ServerError paths
# ---------------------------------------------------------------------------


def _reset_note_cache():
    """Reset the global note_cache singleton between tests."""
    import simplenote_mcp.server.server as srv

    srv.note_cache = None


class TestHandleCallTool:
    """Tests for handle_call_tool edge cases."""

    def setup_method(self):
        _clear_client()
        _reset_note_cache()

    def teardown_method(self):
        _clear_client()
        _reset_note_cache()

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_json(self):
        """Calling an unknown tool returns a TextContent with an error JSON."""
        import simplenote_mcp.server.server as srv

        mock_sn = MagicMock()
        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_sn,
            ),
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
        ):
            result = await srv.handle_call_tool("nonexistent_tool", {})

        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        payload = json.loads(result.content[0].text)
        assert (
            "error" in payload or "message" in payload or "Unknown tool" in str(payload)
        )

    @pytest.mark.asyncio
    async def test_server_error_returns_error_json(self):
        """A ServerError raised inside the handler is returned as JSON, not re-raised."""
        import simplenote_mcp.server.server as srv
        from simplenote_mcp.server.errors import ErrorCategory, ServerError

        mock_sn = MagicMock()
        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        mock_handler = AsyncMock(
            side_effect=ServerError("API failure", ErrorCategory.INTERNAL)
        )

        mock_registry = MagicMock()
        mock_registry.get_handler.return_value = MagicMock(handle=mock_handler)

        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_sn,
            ),
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
            patch(
                "simplenote_mcp.server.tool_handlers.ToolHandlerRegistry",
                return_value=mock_registry,
            ),
        ):
            result = await srv.handle_call_tool("search_notes", {"query": "test"})

        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        payload = json.loads(result.content[0].text)
        # ServerError.to_dict() always has an "error" key
        assert "error" in payload

    @pytest.mark.asyncio
    async def test_invalid_arguments_type_raises_validation_error(self):
        """Non-dict arguments cause a ValidationError."""
        import simplenote_mcp.server.server as srv

        with pytest.raises(ValidationError):
            await srv.handle_call_tool("create_note", "not-a-dict")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_tool_call_does_not_log_plaintext_at_info(self, caplog):
        """Note content must never appear in INFO-or-above logs.

        Regression test: handle_call_tool used to dump the full, unsanitized
        arguments dict (including note content) via logger.info() on every
        call. A sanitized/truncated form at DEBUG is fine and expected.
        """
        import logging

        import simplenote_mcp.server.server as srv

        marker = "UNIQUE-PLAINTEXT-MARKER-89f3c2"

        mock_sn = MagicMock()
        mock_cache = MagicMock()
        mock_cache.is_initialized = True

        with (
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_sn,
            ),
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
            caplog.at_level(logging.DEBUG, logger="simplenote_mcp"),
        ):
            # Write mode is disabled by default, so this is rejected before
            # touching the network — the logging call under test runs before
            # that gate either way, so it still exercises the fixed code path.
            await srv.handle_call_tool("create_note", {"content": marker})

        for record in caplog.records:
            if record.levelno >= logging.INFO:
                assert marker not in record.getMessage()


# ---------------------------------------------------------------------------
# handle_list_prompts
# ---------------------------------------------------------------------------


class TestHandleListPrompts:
    """Tests for handle_list_prompts."""

    @pytest.mark.asyncio
    async def test_returns_three_prompts(self):
        """handle_list_prompts returns exactly three prompts."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_list_prompts()

        assert len(result) == 3
        names = [p.name for p in result]
        assert "create_note_prompt" in names
        assert "search_notes_prompt" in names
        assert "session_handoff_prompt" in names

    @pytest.mark.asyncio
    async def test_session_handoff_prompt_has_required_project_arg(self):
        """session_handoff_prompt declares a required 'project' argument."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_list_prompts()
        handoff_prompt = next(p for p in result if p.name == "session_handoff_prompt")

        required_args = [a for a in handoff_prompt.arguments if a.required]
        names = [a.name for a in required_args]
        assert names == ["project"]

    @pytest.mark.asyncio
    async def test_create_note_prompt_has_required_content_arg(self):
        """create_note_prompt declares a required 'content' argument."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_list_prompts()
        create_prompt = next(p for p in result if p.name == "create_note_prompt")

        required_args = [a for a in create_prompt.arguments if a.required]
        names = [a.name for a in required_args]
        assert "content" in names

    @pytest.mark.asyncio
    async def test_search_notes_prompt_has_required_query_arg(self):
        """search_notes_prompt declares a required 'query' argument."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_list_prompts()
        search_prompt = next(p for p in result if p.name == "search_notes_prompt")

        required_args = [a for a in search_prompt.arguments if a.required]
        assert any(a.name == "query" for a in required_args)


# ---------------------------------------------------------------------------
# handle_get_prompt
# ---------------------------------------------------------------------------


class TestHandleGetPrompt:
    """Tests for all four branches of handle_get_prompt."""

    @pytest.mark.asyncio
    async def test_create_note_prompt_returns_two_messages(self):
        """create_note_prompt returns a result with two PromptMessage items."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_get_prompt(
            "create_note_prompt", {"content": "hello", "tags": "work"}
        )

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 2
        # Second message should contain the content
        assert "hello" in result.messages[1].content.text
        assert "work" in result.messages[1].content.text

    @pytest.mark.asyncio
    async def test_create_note_prompt_with_no_arguments(self):
        """create_note_prompt works when arguments is None."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_get_prompt("create_note_prompt", None)

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 2

    @pytest.mark.asyncio
    async def test_search_notes_prompt_contains_query(self):
        """search_notes_prompt embeds the query in the second message."""
        import simplenote_mcp.server.server as srv

        result = await srv.handle_get_prompt(
            "search_notes_prompt", {"query": "project ideas"}
        )

        assert isinstance(result, types.GetPromptResult)
        assert "project ideas" in result.messages[1].content.text

    @pytest.mark.asyncio
    async def test_unknown_prompt_raises_validation_error(self):
        """An unknown prompt name raises ValidationError."""
        import simplenote_mcp.server.server as srv

        with pytest.raises(ValidationError):
            await srv.handle_get_prompt("no_such_prompt", {})


# ---------------------------------------------------------------------------
# handle_read_resource
# ---------------------------------------------------------------------------


class TestHandleReadResource:
    """Tests for handle_read_resource."""

    def setup_method(self):
        _clear_client()
        _reset_note_cache()

    def teardown_method(self):
        _clear_client()
        _reset_note_cache()

    @pytest.mark.asyncio
    async def test_invalid_uri_raises_validation_error(self):
        """A URI that does not start with 'simplenote://note/' raises ValidationError."""
        from pydantic import AnyUrl

        import simplenote_mcp.server.server as srv

        bad_uri = AnyUrl("https://example.com/not-a-note")
        with pytest.raises(ValidationError):
            await srv.handle_read_resource(bad_uri)

    @pytest.mark.asyncio
    async def test_note_found_in_cache_is_returned(self):
        """When the cache has the note it is returned directly."""
        from pydantic import AnyUrl

        import simplenote_mcp.server.server as srv

        note_id = "abc123"
        fake_note = {
            "key": note_id,
            "content": "cached content",
            "tags": ["work"],
        }

        mock_cache = MagicMock()
        mock_cache.is_initialized = True
        mock_cache.get_note.return_value = fake_note

        with patch(
            "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
            return_value=mock_cache,
        ):
            uri = AnyUrl(f"simplenote://note/{note_id}")
            result = list(await srv.handle_read_resource(uri))

        # handle_read_resource must return Iterable[ReadResourceContents] —
        # the @server.read_resource() decorator wraps this into
        # ReadResourceResult itself. Returning a pre-built ReadResourceResult
        # here would be silently misinterpreted as that Iterable (pydantic
        # BaseModel defines __iter__), yielding (field_name, value) tuples
        # instead of resource contents and crashing the real wire protocol.
        assert len(result) == 1
        assert result[0].content == "cached content"
        assert result[0].meta == {
            "tags": ["work"],
            "modifydate": "",
            "createdate": "",
        }

    @pytest.mark.asyncio
    async def test_note_not_in_cache_fetched_from_api(self):
        """Cache miss triggers an API call and the result is returned."""
        from pydantic import AnyUrl

        import simplenote_mcp.server.server as srv

        note_id = "xyz789"
        fake_note = {"key": note_id, "content": "api content", "tags": []}

        mock_cache = MagicMock()
        mock_cache.is_initialized = True
        mock_cache.get_note.side_effect = ResourceNotFoundError("not in cache")
        mock_cache.update_cache_after_update = MagicMock()

        mock_sn = MagicMock()
        mock_sn.get_note.return_value = (fake_note, 0)

        with (
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_sn,
            ),
        ):
            uri = AnyUrl(f"simplenote://note/{note_id}")
            result = list(await srv.handle_read_resource(uri))

        assert result[0].content == "api content"

    @pytest.mark.asyncio
    async def test_api_failure_raises_resource_not_found(self):
        """When the API returns a bad status, ResourceNotFoundError is raised."""
        from pydantic import AnyUrl

        import simplenote_mcp.server.server as srv

        note_id = "missing99"

        mock_cache = MagicMock()
        mock_cache.is_initialized = True
        mock_cache.get_note.side_effect = ResourceNotFoundError("not in cache")

        mock_sn = MagicMock()
        mock_sn.get_note.return_value = (None, 1)  # status != 0

        with (
            patch(
                "simplenote_mcp.server.cache_utils.get_cache_or_create_minimal",
                return_value=mock_cache,
            ),
            patch(
                "simplenote_mcp.server.server.get_simplenote_client",
                return_value=mock_sn,
            ),
        ):
            uri = AnyUrl(f"simplenote://note/{note_id}")
            with pytest.raises(ResourceNotFoundError):
                await srv.handle_read_resource(uri)


# ---------------------------------------------------------------------------
# utils/common.py — cover uncovered branches
# ---------------------------------------------------------------------------


class TestSafeGet:
    """Tests for safe_get covering None / non-dict guard."""

    def test_none_data_returns_default(self):
        from simplenote_mcp.server.utils.common import safe_get

        assert safe_get(None, "key", "default") == "default"

    def test_non_dict_returns_default(self):
        from simplenote_mcp.server.utils.common import safe_get

        assert safe_get("not a dict", "key", 42) == 42  # type: ignore[arg-type]

    def test_missing_key_returns_default(self):
        from simplenote_mcp.server.utils.common import safe_get

        assert safe_get({}, "missing") is None


class TestSafeSet:
    """Tests for safe_set covering non-dict guard (line 34-35)."""

    def test_non_dict_is_ignored(self):
        from simplenote_mcp.server.utils.common import safe_set

        # Should not raise even for non-dict — just silently does nothing
        safe_set("not a dict", "key", "value")  # type: ignore[arg-type]

    def test_dict_sets_value(self):
        from simplenote_mcp.server.utils.common import safe_set

        d: dict = {}
        safe_set(d, "key", "value")
        assert d["key"] == "value"


class TestSafeSplit:
    """Tests for safe_split covering non-string and max_splits paths."""

    def test_non_string_returns_empty(self):
        from simplenote_mcp.server.utils.common import safe_split

        assert safe_split(123) == []  # type: ignore[arg-type]

    def test_unlimited_split(self):
        from simplenote_mcp.server.utils.common import safe_split

        result = safe_split("a b c", " ")
        assert result == ["a", "b", "c"]

    def test_max_splits(self):
        from simplenote_mcp.server.utils.common import safe_split

        result = safe_split("a b c", " ", 1)
        assert result == ["a", "b c"]


class TestExtractTitleFromContent:
    """Tests for extract_title_from_content covering all branches."""

    def test_empty_content_returns_none(self):
        from simplenote_mcp.server.utils.common import extract_title_from_content

        assert extract_title_from_content("") is None

    def test_whitespace_only_returns_none(self):
        from simplenote_mcp.server.utils.common import extract_title_from_content

        assert extract_title_from_content("   \n   ") is None

    def test_first_non_empty_line_is_title(self):
        from simplenote_mcp.server.utils.common import extract_title_from_content

        assert extract_title_from_content("\n\nHello World\nMore text") == "Hello World"

    def test_title_truncated_at_100_chars(self):
        from simplenote_mcp.server.utils.common import extract_title_from_content

        long_line = "x" * 150
        result = extract_title_from_content(long_line)
        assert result == "x" * 100


# ---------------------------------------------------------------------------
# error_codes.py — cover parse_error_code and get_error_description
# ---------------------------------------------------------------------------


class TestErrorCodeHelpers:
    """Tests for parse_error_code and get_error_description."""

    def test_parse_error_code_too_short_returns_none(self):
        from simplenote_mcp.server.error_codes import parse_error_code

        assert parse_error_code("AUTH") is None
        assert parse_error_code("AUTH_CRD") is None

    def test_parse_error_code_unknown_prefix_returns_none(self):
        from simplenote_mcp.server.error_codes import parse_error_code

        assert parse_error_code("UNKNOWN_XX_001") is None

    def test_get_error_description_missing_code_returns_none(self):
        from simplenote_mcp.server.error_codes import get_error_description

        assert get_error_description("NONEXISTENT_CODE_XYZ") is None


# ---------------------------------------------------------------------------
# run_main — Config.validate() must run first and fail closed
# ---------------------------------------------------------------------------


class TestRunMainConfigValidation:
    """run_main() must validate config and fail fast — before PID file
    creation, signal handler setup, or any attempt to start the server.
    Regression test: Config.validate() existed but was never called on any
    production startup path, so invalid config (e.g. missing credentials
    outside offline mode) only surfaced later, less clearly, deep inside
    client/cache initialization.
    """

    def setup_method(self):
        _reset_note_cache()

    def teardown_method(self):
        _reset_note_cache()

    def test_invalid_config_exits_before_any_side_effects(self):
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.log_level = srv.LogLevel.INFO
        mock_config.validate.side_effect = ValueError(
            "SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables must be set"
        )

        with (
            patch("simplenote_mcp.server.server.get_config", return_value=mock_config),
            patch("simplenote_mcp.server.server.write_pid_file") as mock_write_pid,
            patch("simplenote_mcp.server.server.setup_signal_handlers") as mock_signals,
            patch("simplenote_mcp.server.server.cleanup_pid_file") as mock_cleanup,
            patch("simplenote_mcp.server.server.asyncio.run") as mock_asyncio_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            srv.run_main()

        assert exc_info.value.code == 1
        mock_config.validate.assert_called_once()
        mock_write_pid.assert_not_called()
        mock_signals.assert_not_called()
        mock_asyncio_run.assert_not_called()
        mock_cleanup.assert_called_once()

    def test_valid_config_proceeds_past_validation(self):
        import simplenote_mcp.server.server as srv

        mock_config = MagicMock()
        mock_config.log_level = srv.LogLevel.INFO
        mock_config.mcp_transport = "stdio"
        mock_config.simplenote_email = None
        mock_config.simplenote_password = None
        mock_config.validate.return_value = None

        with (
            patch("simplenote_mcp.server.server.get_config", return_value=mock_config),
            patch("simplenote_mcp.server.server.write_pid_file") as mock_write_pid,
            patch("simplenote_mcp.server.server.setup_signal_handlers") as mock_signals,
            # Mock run() itself too, not just asyncio.run — otherwise the
            # real `run()` coroutine object still gets constructed (just
            # never awaited, since asyncio.run is mocked), which logs a
            # harmless but noisy "coroutine was never awaited" warning.
            patch("simplenote_mcp.server.server.run", new=AsyncMock()),
            patch("simplenote_mcp.server.server.asyncio.run") as mock_asyncio_run,
            patch("simplenote_mcp.server.server.cleanup_pid_file"),
        ):
            srv.run_main()

        mock_config.validate.assert_called_once()
        mock_write_pid.assert_called_once()
        mock_signals.assert_called_once()
        mock_asyncio_run.assert_called_once()
