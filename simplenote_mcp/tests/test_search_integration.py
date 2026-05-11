"""Real-engine integration tests for NoteCache.search_notes.

These tests bypass live Simplenote credentials by constructing a NoteCache
directly with in-memory notes.  They exercise the full async executor path
that was broken in the production regression described in the P0 handover
(2026-05-10): `await self.note_cache.search_notes(...)` raised
`TypeError: object list can't be used in 'await' expression` when the cache
held a synchronous version of search_notes while the handler already used
`await`.

Regression guarded: commit 9683398 made search_notes async + executor-wrapped.
These tests confirm the real call path works without mocks.
"""

import json
import time
from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.tool_handlers import (
    AppendToDailyNoteHandler,
    GetOrCreateNoteHandler,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_note(
    key: str,
    content: str,
    tags: list[str] | None = None,
    create_delta_days: float = 0,
    modify_delta_days: float = 0,
) -> dict[str, Any]:
    now = time.time()
    return {
        "key": key,
        "content": content,
        "tags": tags or [],
        "systemtags": [],
        "deleted": False,
        "createdate": str(now - create_delta_days * 86400),
        "modifydate": str(now - modify_delta_days * 86400),
        "version": 1,
    }


def _build_cache(notes: list[dict[str, Any]]) -> NoteCache:
    """Create a fully-indexed in-memory NoteCache without hitting the API."""
    mock_client = MagicMock()
    cache = NoteCache(mock_client)
    cache._notes = {n["key"]: n for n in notes}
    cache._initialized = True
    cache._last_sync = time.time()
    cache._build_all_indexes()
    return cache


# ---------------------------------------------------------------------------
# Fixture: ~50 diverse notes covering several test scenarios
# ---------------------------------------------------------------------------


@pytest.fixture()
def rich_cache() -> NoteCache:
    notes = [
        _make_note(
            "py1", "python programming language notes", tags=["programming", "python"]
        ),
        _make_note(
            "py2", "advanced python testing with pytest", tags=["python", "testing"]
        ),
        _make_note(
            "py3", "python and testing best practices guide", tags=["python", "testing"]
        ),
        _make_note("py4", "pythonic code style", tags=["python"]),
        _make_note(
            "py5", "python data science and pandas tutorial", tags=["python", "data"]
        ),
        _make_note("ts1", "testing strategies for modern software", tags=["testing"]),
        _make_note("ts2", "unit testing frameworks comparison", tags=["testing"]),
        _make_note("ts3", "tested approach to software quality", tags=["testing"]),
        _make_note("ts4", "test driven development tdd", tags=["testing"]),
        _make_note("go1", "go programming language tour", tags=["programming", "go"]),
        _make_note("go2", "go testing with go test command", tags=["go", "testing"]),
        _make_note(
            "rs1", "rust ownership and borrowing concepts", tags=["programming", "rust"]
        ),
        _make_note("db1", "database design patterns", tags=["database"]),
        _make_note("db2", "sql and postgresql tips", tags=["database", "sql"]),
        _make_note("db3", "nosql mongodb introduction", tags=["database", "nosql"]),
        _make_note("web1", "web development with flask", tags=["web", "python"]),
        _make_note(
            "web2", "fastapi python rest api guide", tags=["web", "python", "api"]
        ),
        _make_note(
            "web3", "javascript frontend development", tags=["web", "javascript"]
        ),
        _make_note(
            "ai1", "machine learning with python scikit learn", tags=["ai", "python"]
        ),
        _make_note("ai2", "deep learning neural networks", tags=["ai"]),
        _make_note("ai3", "natural language processing nlp", tags=["ai", "nlp"]),
        _make_note("devops1", "docker containerization basics", tags=["devops"]),
        _make_note("devops2", "kubernetes orchestration guide", tags=["devops"]),
        _make_note(
            "devops3", "ci cd pipeline configuration", tags=["devops", "testing"]
        ),
        _make_note("sec1", "security best practices", tags=["security"]),
        _make_note(
            "sec2", "authentication and authorisation patterns", tags=["security"]
        ),
        _make_note(
            "arch1", "microservices architecture patterns", tags=["architecture"]
        ),
        _make_note(
            "arch2", "monolith vs microservices comparison", tags=["architecture"]
        ),
        _make_note(
            "perf1", "performance optimisation techniques", tags=["performance"]
        ),
        _make_note(
            "perf2", "profiling python code for speed", tags=["performance", "python"]
        ),
        _make_note("log1", "structured logging best practices", tags=["logging"]),
        _make_note("log2", "log analysis and monitoring", tags=["logging", "devops"]),
        _make_note("doc1", "documentation writing guide", tags=["documentation"]),
        _make_note(
            "doc2", "api documentation with openapi", tags=["documentation", "api"]
        ),
        _make_note("git1", "git workflow and branching strategy", tags=["git"]),
        _make_note("git2", "git rebase vs merge discussion", tags=["git"]),
        _make_note("algo1", "sorting algorithms comparison", tags=["algorithms"]),
        _make_note("algo2", "dynamic programming patterns", tags=["algorithms"]),
        _make_note("ds1", "data structures linked list", tags=["data-structures"]),
        _make_note("ds2", "hash tables and dictionaries", tags=["data-structures"]),
        _make_note("net1", "networking tcp ip fundamentals", tags=["networking"]),
        _make_note("net2", "http protocol and rest", tags=["networking", "api"]),
        _make_note("os1", "operating system process management", tags=["os"]),
        _make_note("os2", "linux command line essentials", tags=["os", "linux"]),
        _make_note("misc1", "random thoughts on productivity", tags=["misc"]),
        _make_note("misc2", "reading list books and articles", tags=["misc"]),
        _make_note(
            "old1",
            "very old note about c programming",
            tags=["programming"],
            create_delta_days=365,
            modify_delta_days=365,
        ),
        _make_note(
            "old2",
            "old testing notes from last year",
            tags=["testing"],
            create_delta_days=400,
            modify_delta_days=400,
        ),
        _make_note(
            "recent1",
            "recently added machine learning notes",
            tags=["ai"],
            modify_delta_days=1,
        ),
        _make_note(
            "recent2",
            "latest python tips and tricks",
            tags=["python"],
            modify_delta_days=0.5,
        ),
    ]
    return _build_cache(notes)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_single_word_returns_results(rich_cache: NoteCache) -> None:
    """search_notes with a single keyword returns matching notes without error.

    This is the primary regression guard: before the fix, the call raised
    TypeError because search_notes was synchronous and the caller used await.
    """
    results = await rich_cache.search_notes(query="python")

    assert isinstance(results, list), "search_notes must return a list"
    assert len(results) > 0, "Should find notes containing 'python'"
    keys = {n["key"] for n in results}
    assert "py1" in keys, "Note explicitly about python must be in results"
    assert "py2" in keys, "Note about python testing must be in results"


@pytest.mark.asyncio
async def test_search_boolean_and_returns_intersection(rich_cache: NoteCache) -> None:
    """Boolean AND query returns only notes that match both terms."""
    results = await rich_cache.search_notes(query="python AND testing")

    assert isinstance(results, list)
    assert len(results) > 0, "AND query should find notes containing both words"
    for note in results:
        content = note.get("content", "").lower()
        assert "python" in content, f"Note {note['key']} lacks 'python'"
        assert "test" in content, (
            f"Note {note['key']} lacks 'test*' — substring match expected"
        )


@pytest.mark.asyncio
async def test_search_boolean_or_returns_union(rich_cache: NoteCache) -> None:
    """Boolean OR returns notes matching either term — superset of each alone."""
    only_python = await rich_cache.search_notes(query="python")
    only_rust = await rich_cache.search_notes(query="rust")
    combined = await rich_cache.search_notes(query="python OR rust")

    keys_python = {n["key"] for n in only_python}
    keys_rust = {n["key"] for n in only_rust}
    keys_combined = {n["key"] for n in combined}

    assert keys_python.issubset(keys_combined), "python results must be in OR results"
    assert keys_rust.issubset(keys_combined), "rust results must be in OR results"
    assert len(keys_combined) >= len(keys_python), (
        "OR result must be at least as large as individual"
    )


@pytest.mark.asyncio
async def test_search_returns_within_5_seconds(rich_cache: NoteCache) -> None:
    """Boolean AND query must complete in under 5 s (guards the original deadlock)."""
    import time

    start = time.monotonic()
    results = await rich_cache.search_notes(query="python AND testing")
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"search_notes took {elapsed:.2f}s — deadlock regression?"
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_substring_pre_filter_matches_inflections(rich_cache: NoteCache) -> None:
    """Pre-filter with substring matching returns notes with inflected forms.

    Before the Bug-2 fix the pre-filter used exact-token lookup:
      word_index['test'] would miss notes whose content has 'testing', 'tested'.
    After the fix the pre-filter uses substring matching (t in indexed_word),
    so 'test' matches words like 'testing', 'tested', 'tester', etc.
    """
    results = await rich_cache.search_notes(query="test")

    assert isinstance(results, list)
    keys = {n["key"] for n in results}

    # Notes with exact "test"
    assert "ts4" in keys, "'test driven development' note should match 'test'"
    # Notes with inflected forms
    assert "ts1" in keys, "'testing strategies' should match 'test' via substring"
    assert "ts2" in keys, "'unit testing' should match 'test' via substring"
    assert "ts3" in keys, "'tested approach' should match 'test' via substring"

    # Minimum: at least 4 distinct notes (direct + inflected)
    test_related = {k for k in keys if k.startswith("ts") or k.startswith("py")}
    assert len(test_related) >= 4, (
        f"Expected ≥4 test-related notes, got {len(test_related)}: {test_related}"
    )


@pytest.mark.asyncio
async def test_search_repeated_calls_are_stable(rich_cache: NoteCache) -> None:
    """Two identical searches return the same result set (cache consistency)."""
    results1 = await rich_cache.search_notes(query="python")
    results2 = await rich_cache.search_notes(query="python")

    keys1 = {n["key"] for n in results1}
    keys2 = {n["key"] for n in results2}
    assert keys1 == keys2, "Repeated searches must return the same notes"


# ---------------------------------------------------------------------------
# Downstream handler smoke tests — get_or_create_note & append_to_daily_note
# ---------------------------------------------------------------------------


def _make_sn_client(add_note_result: dict | None = None) -> MagicMock:
    """Return a mock Simplenote client for handler tests."""
    client = MagicMock()
    result = add_note_result or {"key": "new-note-1", "content": "# My Note\n"}
    client.add_note.return_value = (result, 0)
    client.update_note.return_value = (result, 0)
    return client


@pytest.mark.asyncio
async def test_get_or_create_note_finds_existing(rich_cache: NoteCache) -> None:
    """get_or_create_note returns an existing note via search without creating one.

    Smoke-tests that `await self.note_cache.search_notes(query=title)` completes
    without TypeError inside the handler.
    """
    client = _make_sn_client()
    handler = GetOrCreateNoteHandler(client, rich_cache)

    # "python programming language notes" is the first line of note py1
    result = await handler.handle({"title": "python programming language notes"})

    assert result, "Handler must return a non-empty response"
    payload = json.loads(result[0].text)
    assert payload.get("success") is True, f"Unexpected error: {payload}"
    assert payload.get("created") is False, (
        "Note already exists — should not be created"
    )
    assert payload.get("note_id") == "py1"
    client.add_note.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_note_creates_missing(rich_cache: NoteCache) -> None:
    """get_or_create_note creates a new note when the title is not found.

    The search (via async executor) must succeed before the handler falls through
    to add_note — confirming the full search + create path works.
    """
    new_note = {"key": "brand-new-1", "content": "# Totally New Note\n"}
    client = _make_sn_client(add_note_result=new_note)
    handler = GetOrCreateNoteHandler(client, rich_cache)

    result = await handler.handle(
        {"title": "Totally New Note", "content": "# Totally New Note\n"}
    )

    assert result
    payload = json.loads(result[0].text)
    assert payload.get("success") is True, f"Unexpected error: {payload}"
    assert payload.get("created") is True, "Title not in cache — note should be created"
    client.add_note.assert_called_once()


@pytest.mark.asyncio
async def test_append_to_daily_note_creates_when_absent(rich_cache: NoteCache) -> None:
    """append_to_daily_note creates today's note if it doesn't exist yet.

    Today's date string won't be in the rich_cache fixture, so the handler must
    complete the search (via async executor) and then call add_note.
    """
    new_note = {
        "key": "daily-1",
        "content": f"# {date.today().isoformat()}\n07:00 standup",
    }
    client = _make_sn_client(add_note_result=new_note)
    handler = AppendToDailyNoteHandler(client, rich_cache)

    result = await handler.handle({"text": "standup"})

    assert result
    payload = json.loads(result[0].text)
    assert payload.get("success") is True, f"Unexpected error: {payload}"
    assert payload.get("created") is True, (
        "No daily note in fixture — should be created"
    )
    client.add_note.assert_called_once()


@pytest.mark.asyncio
async def test_append_to_daily_note_appends_when_present() -> None:
    """append_to_daily_note appends to an existing daily note found via search."""
    today = date.today().isoformat()
    daily_note = _make_note(
        "daily-existing",
        f"# {today}\n08:00 morning coffee",
        tags=["daily"],
    )
    cache = _build_cache([daily_note])

    updated_note = {
        "key": "daily-existing",
        "content": f"# {today}\n08:00 morning coffee\n09:00 standup",
    }
    client = _make_sn_client(add_note_result=updated_note)
    client.update_note.return_value = (updated_note, 0)
    handler = AppendToDailyNoteHandler(client, cache)

    result = await handler.handle({"text": "standup"})

    assert result
    payload = json.loads(result[0].text)
    assert payload.get("success") is True, f"Unexpected error: {payload}"
    assert payload.get("created") is False, (
        "Daily note exists — should append, not create"
    )
    client.update_note.assert_called_once()
    client.add_note.assert_not_called()
