"""Tests for PermanentDeleteNoteHandler and EmptyTrashHandler."""

import json
from unittest.mock import MagicMock

import mcp.types as types
import pytest

from simplenote_mcp.server.tool_handlers import (
    EmptyTrashHandler,
    PermanentDeleteNoteHandler,
    ToolHandlerRegistry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(key: str, deleted: bool = False, content: str = "Test note") -> dict:
    return {"key": key, "content": content, "tags": [], "deleted": deleted}


def _make_handler_fixtures(handler_class):
    """Return (client, cache, handler) mocks for a given handler class."""
    client = MagicMock()
    cache = MagicMock()
    cache.is_initialized = True
    handler = handler_class(client, cache)
    return client, cache, handler


# ---------------------------------------------------------------------------
# PermanentDeleteNoteHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPermanentDeleteNoteHandler:
    """Tests for the permanent_delete_note handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        return PermanentDeleteNoteHandler(mock_client, mock_cache)

    # --- Dry-run path ---

    @pytest.mark.asyncio
    async def test_dry_run_when_confirm_false(self, handler, mock_client):
        """confirm=False returns a dry-run response without calling delete_note."""
        mock_client.get_note.return_value = (_make_note("abc"), 0)
        # Cache miss so handler falls through to API
        handler.note_cache.is_initialized = False

        result = await handler.handle({"note_id": "abc", "confirm": False})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["dry_run"] is True
        assert "abc" in data["note_id"]
        assert "DRY RUN" in data["message"]
        mock_client.delete_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_when_confirm_omitted(self, handler, mock_client):
        """Omitting confirm also returns a dry-run response."""
        handler.note_cache.is_initialized = False
        mock_client.get_note.return_value = (_make_note("abc"), 0)

        result = await handler.handle({"note_id": "abc"})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["dry_run"] is True
        mock_client.delete_note.assert_not_called()

    # --- Success path ---

    @pytest.mark.asyncio
    async def test_permanent_delete_success(self, handler, mock_client, mock_cache):
        """confirm=True with a valid note_id permanently deletes the note."""
        note = _make_note("abc")
        mock_cache.get_note.return_value = note
        mock_client.delete_note.return_value = ({}, 0)

        result = await handler.handle({"note_id": "abc", "confirm": True})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["note_id"] == "abc"
        mock_client.delete_note.assert_called_once_with("abc")
        mock_cache.update_cache_after_delete.assert_called_once_with("abc")

    # --- Error paths ---

    @pytest.mark.asyncio
    async def test_missing_note_id_returns_error(self, handler):
        """Missing note_id returns an error response."""
        result = await handler.handle({"confirm": True})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        data = json.loads(result.content[0].text)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_note_not_found_returns_error(self, handler, mock_client, mock_cache):
        """Note not found in cache or API returns error."""
        mock_cache.get_note.side_effect = Exception("not found")
        mock_client.get_note.return_value = ({}, -1)

        result = await handler.handle({"note_id": "missing", "confirm": True})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        data = json.loads(result.content[0].text)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_api_delete_failure_returns_error(
        self, handler, mock_client, mock_cache
    ):
        """API returning status -1 on delete returns an error response."""
        note = _make_note("abc")
        mock_cache.get_note.return_value = note
        mock_client.delete_note.return_value = ("error", -1)

        result = await handler.handle({"note_id": "abc", "confirm": True})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        data = json.loads(result.content[0].text)

        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_api_delete_exception_returns_error(
        self, handler, mock_client, mock_cache
    ):
        """Exception from API on delete returns an error response."""
        note = _make_note("abc")
        mock_cache.get_note.return_value = note
        mock_client.delete_note.side_effect = RuntimeError("network error")

        result = await handler.handle({"note_id": "abc", "confirm": True})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        data = json.loads(result.content[0].text)

        assert data["success"] is False


# ---------------------------------------------------------------------------
# EmptyTrashHandler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmptyTrashHandler:
    """Tests for the empty_trash handler."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        return EmptyTrashHandler(mock_client, mock_cache)

    # --- Empty trash ---

    @pytest.mark.asyncio
    async def test_empty_trash_already_empty(self, handler, mock_cache):
        """Returns success with count 0 when no notes are trashed."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=False),
            "n2": _make_note("n2", deleted=False),
        }

        result = await handler.handle({"dry_run": True})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["trashed_count"] == 0
        assert "already empty" in data["message"].lower()

    # --- Dry-run path ---

    @pytest.mark.asyncio
    async def test_dry_run_default_lists_trashed_notes(self, handler, mock_cache):
        """Default call (dry_run=True) lists trashed notes without deleting."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True, content="Trashed note 1"),
            "n2": _make_note("n2", deleted=False, content="Active note"),
            "n3": _make_note("n3", deleted=True, content="Trashed note 2"),
        }

        result = await handler.handle({})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["dry_run"] is True
        assert data["trashed_count"] == 2
        assert data["deleted_count"] == 0
        assert "DRY RUN" in data["message"]
        assert len(data["notes"]) == 2

    @pytest.mark.asyncio
    async def test_dry_run_explicit_true_no_deletion(self, handler, mock_cache):
        """Explicit dry_run=True, confirm=True still does not delete."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
        }

        result = await handler.handle({"dry_run": True, "confirm": True})
        data = json.loads(result[0].text)

        assert data["dry_run"] is True
        assert data["deleted_count"] == 0
        handler.sn.delete_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_confirm_false_no_deletion(self, handler, mock_cache):
        """dry_run=False but confirm=False still does not delete."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
        }

        result = await handler.handle({"dry_run": False, "confirm": False})
        data = json.loads(result[0].text)

        assert data["dry_run"] is True
        assert data["deleted_count"] == 0
        handler.sn.delete_note.assert_not_called()

    # --- Execute path ---

    @pytest.mark.asyncio
    async def test_execute_deletes_all_trashed_notes(
        self, handler, mock_client, mock_cache
    ):
        """dry_run=False and confirm=True permanently deletes all trashed notes."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
            "n2": _make_note("n2", deleted=False),
            "n3": _make_note("n3", deleted=True),
        }
        mock_client.delete_note.return_value = ({}, 0)

        result = await handler.handle({"dry_run": False, "confirm": True})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["dry_run"] is False
        assert data["trashed_count"] == 2
        assert data["deleted_count"] == 2
        assert mock_client.delete_note.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_partial_failure_reported(
        self, handler, mock_client, mock_cache
    ):
        """Failed deletions are reported in failed_ids."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
            "n2": _make_note("n2", deleted=True),
        }

        def _delete_side_effect(note_id):
            if note_id == "n1":
                return ({}, 0)
            return ("error", -1)

        mock_client.delete_note.side_effect = _delete_side_effect

        result = await handler.handle({"dry_run": False, "confirm": True})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["deleted_count"] == 1
        assert "n2" in data["failed_ids"]

    @pytest.mark.asyncio
    async def test_execute_exception_during_delete_reported(
        self, handler, mock_client, mock_cache
    ):
        """Exception during deletion is caught and note_id appears in failed_ids."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
        }
        mock_client.delete_note.side_effect = RuntimeError("network error")

        result = await handler.handle({"dry_run": False, "confirm": True})
        data = json.loads(result[0].text)

        assert data["success"] is True
        assert data["deleted_count"] == 0
        assert "n1" in data["failed_ids"]

    # --- Fallback to API when cache is unavailable ---

    @pytest.mark.asyncio
    async def test_fallback_to_api_when_cache_not_initialized(
        self, handler, mock_client, mock_cache
    ):
        """When cache is not initialised, get_note_list is used as fallback."""
        mock_cache.is_initialized = False
        mock_client.get_note_list.return_value = (
            [
                _make_note("n1", deleted=True),
                _make_note("n2", deleted=False),
            ],
            0,
        )

        result = await handler.handle({"dry_run": True})
        data = json.loads(result[0].text)

        assert data["trashed_count"] == 1
        mock_client.get_note_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_failure_returns_error(self, handler, mock_client, mock_cache):
        """get_note_list API failure returns an error response."""
        mock_cache.is_initialized = False
        mock_client.get_note_list.return_value = ([], -1)

        result = await handler.handle({"dry_run": True})
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        data = json.loads(result.content[0].text)

        assert data["success"] is False

    # --- Cache update ---

    @pytest.mark.asyncio
    async def test_cache_updated_after_deletion(self, handler, mock_client, mock_cache):
        """Cache.update_cache_after_delete is called for each deleted note."""
        mock_cache._notes = {
            "n1": _make_note("n1", deleted=True),
            "n2": _make_note("n2", deleted=True),
        }
        mock_client.delete_note.return_value = ({}, 0)

        await handler.handle({"dry_run": False, "confirm": True})

        assert mock_cache.update_cache_after_delete.call_count == 2


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryIncludesNewTools:
    """The ToolHandlerRegistry must expose the two new tools."""

    def test_permanent_delete_note_registered(self):
        registry = ToolHandlerRegistry()
        assert "permanent_delete_note" in registry.list_tools()

    def test_empty_trash_registered(self):
        registry = ToolHandlerRegistry()
        assert "empty_trash" in registry.list_tools()

    def test_get_permanent_delete_handler(self):
        registry = ToolHandlerRegistry()
        client = MagicMock()
        handler = registry.get_handler("permanent_delete_note", client)
        assert isinstance(handler, PermanentDeleteNoteHandler)

    def test_get_empty_trash_handler(self):
        registry = ToolHandlerRegistry()
        client = MagicMock()
        handler = registry.get_handler("empty_trash", client)
        assert isinstance(handler, EmptyTrashHandler)
