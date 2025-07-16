"""Tests for MCP types compatibility module."""

from simplenote_mcp.server.mcp_types_compat import (
    Context,
    GetNoteRequest,
    ListResourcesRequest,
    ReadResourceRequest,
)


class TestContext:
    """Test the Context class."""

    def test_context_creation_default(self):
        """Test creating Context with default values."""
        context = Context()
        assert context.request_id is None

    def test_context_creation_with_id(self):
        """Test creating Context with request ID."""
        context = Context(request_id="test-123")
        assert context.request_id == "test-123"


class TestListResourcesRequest:
    """Test the ListResourcesRequest class."""

    def test_default_creation(self):
        """Test creating ListResourcesRequest with defaults."""
        request = ListResourcesRequest()

        assert request.tag is None
        assert request.limit is None
        assert request.offset == 0
        assert request.sort_by is None
        assert request.sort_direction is None

    def test_creation_with_parameters(self):
        """Test creating ListResourcesRequest with parameters."""
        request = ListResourcesRequest(
            tag="work", limit=50, offset=10, sort_by="modified", sort_direction="desc"
        )

        assert request.tag == "work"
        assert request.limit == 50
        assert request.offset == 10
        assert request.sort_by == "modified"
        assert request.sort_direction == "desc"


class TestReadResourceRequest:
    """Test the ReadResourceRequest class."""

    def test_default_creation(self):
        """Test creating ReadResourceRequest with defaults."""
        request = ReadResourceRequest()
        assert request.uri is None

    def test_creation_with_uri(self):
        """Test creating ReadResourceRequest with URI."""
        request = ReadResourceRequest(uri="simplenote://note/123")
        assert request.uri == "simplenote://note/123"


class TestGetNoteRequest:
    """Test the GetNoteRequest class."""

    def test_default_creation(self):
        """Test creating GetNoteRequest with defaults."""
        request = GetNoteRequest()
        assert request.note_id is None

    def test_creation_with_note_id(self):
        """Test creating GetNoteRequest with note ID."""
        request = GetNoteRequest(note_id="note-123")
        assert request.note_id == "note-123"
