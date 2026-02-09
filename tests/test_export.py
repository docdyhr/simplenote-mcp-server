"""Tests for note export functionality."""

import json

import pytest

from simplenote_mcp.server.export import NoteExporter


@pytest.fixture
def exporter():
    """Create a NoteExporter instance."""
    return NoteExporter()


@pytest.fixture
def sample_note():
    """Create a sample note for testing."""
    return {
        "key": "abc123",
        "content": "# My Note Title\n\nThis is the body of the note.\nWith multiple lines.",
        "tags": ["work", "important"],
        "createdate": 1700000000.0,
        "modifydate": 1700100000.0,
    }


@pytest.fixture
def sample_note_minimal():
    """Create a minimal note with no metadata."""
    return {
        "key": "def456",
        "content": "Simple note content",
        "tags": [],
    }


@pytest.mark.unit
class TestExportMarkdown:
    """Tests for Markdown export."""

    def test_basic_export(self, exporter, sample_note):
        """Test basic Markdown export with metadata."""
        result = exporter.export_markdown(sample_note, include_metadata=True)
        assert result.startswith("---\n")
        assert "id: abc123" in result
        assert "title:" in result
        assert "tags: [work, important]" in result
        assert "created:" in result
        assert "modified:" in result
        assert "# My Note Title" in result
        assert "This is the body of the note." in result

    def test_export_without_metadata(self, exporter, sample_note):
        """Test Markdown export without YAML front matter."""
        result = exporter.export_markdown(sample_note, include_metadata=False)
        assert not result.startswith("---")
        assert "# My Note Title" in result
        assert "This is the body of the note." in result

    def test_export_empty_tags(self, exporter, sample_note_minimal):
        """Test export with empty tags."""
        result = exporter.export_markdown(sample_note_minimal, include_metadata=True)
        assert "tags: []" in result

    def test_export_empty_content(self, exporter):
        """Test export with empty content."""
        note = {"key": "test", "content": "", "tags": []}
        result = exporter.export_markdown(note, include_metadata=True)
        assert "---" in result
        assert 'title: ""' in result

    def test_yaml_escaping(self, exporter):
        """Test YAML special characters are escaped."""
        note = {
            "key": "test",
            "content": 'Title with "quotes" and \\backslash',
            "tags": [],
        }
        result = exporter.export_markdown(note, include_metadata=True)
        assert '\\"quotes\\"' in result


@pytest.mark.unit
class TestExportJson:
    """Tests for JSON export."""

    def test_basic_export(self, exporter, sample_note):
        """Test basic JSON export."""
        result = exporter.export_json(sample_note, include_metadata=True)
        assert result["id"] == "abc123"
        assert result["title"] == "# My Note Title"
        assert "This is the body" in result["content"]
        assert result["tags"] == ["work", "important"]
        assert result["createdate"] is not None
        assert result["modifydate"] is not None

    def test_export_without_metadata(self, exporter, sample_note):
        """Test JSON export without metadata."""
        result = exporter.export_json(sample_note, include_metadata=False)
        assert result["id"] == "abc123"
        assert result["content"] is not None
        assert "createdate" not in result
        assert "modifydate" not in result

    def test_empty_note(self, exporter):
        """Test JSON export of empty note."""
        note = {"key": "", "content": "", "tags": []}
        result = exporter.export_json(note)
        assert result["id"] == ""
        assert result["title"] == ""
        assert result["content"] == ""
        assert result["tags"] == []


@pytest.mark.unit
class TestExportBatch:
    """Tests for batch export."""

    def test_batch_markdown(self, exporter, sample_note, sample_note_minimal):
        """Test batch Markdown export."""
        notes = [sample_note, sample_note_minimal]
        result = exporter.export_batch(notes, fmt="markdown", include_metadata=True)
        assert "---" in result
        assert "abc123" in result
        assert "def456" in result
        # Should have separator between notes
        parts = result.split("\n---\n")
        assert len(parts) >= 2

    def test_batch_json(self, exporter, sample_note, sample_note_minimal):
        """Test batch JSON export."""
        notes = [sample_note, sample_note_minimal]
        result = exporter.export_batch(notes, fmt="json", include_metadata=True)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["id"] == "abc123"
        assert parsed[1]["id"] == "def456"

    def test_batch_single_note(self, exporter, sample_note):
        """Test batch with single note."""
        result = exporter.export_batch([sample_note], fmt="markdown")
        assert "abc123" in result

    def test_batch_empty_list(self, exporter):
        """Test batch with empty list."""
        result = exporter.export_batch([], fmt="json")
        assert json.loads(result) == []


@pytest.mark.unit
class TestFormatDate:
    """Tests for date formatting helper."""

    def test_timestamp_float(self, exporter):
        """Test float timestamp formatting."""
        result = NoteExporter._format_date(1700000000.0)
        assert result is not None
        assert "2023" in result

    def test_timestamp_int(self, exporter):
        """Test integer timestamp formatting."""
        result = NoteExporter._format_date(1700000000)
        assert result is not None

    def test_string_passthrough(self, exporter):
        """Test string date passes through unchanged."""
        result = NoteExporter._format_date("2023-11-14T12:00:00")
        assert result == "2023-11-14T12:00:00"

    def test_none_returns_none(self, exporter):
        """Test None returns None."""
        assert NoteExporter._format_date(None) is None

    def test_zero_returns_none(self, exporter):
        """Test 0 returns None."""
        assert NoteExporter._format_date(0) is None

    def test_string_value_passthrough(self, exporter):
        """Test string values are passed through as-is (assumed valid)."""
        assert NoteExporter._format_date("invalid") == "invalid"


@pytest.mark.unit
class TestExportNotesHandler:
    """Tests for the ExportNotesHandler tool handler."""

    @pytest.fixture
    def mock_client(self):
        from unittest.mock import MagicMock

        client = MagicMock()
        return client

    @pytest.fixture
    def mock_cache(self):
        from unittest.mock import MagicMock

        cache = MagicMock()
        cache.is_initialized = True
        cache.get_note.return_value = {
            "key": "test123",
            "content": "Test note content",
            "tags": ["test"],
            "createdate": 1700000000.0,
            "modifydate": 1700100000.0,
        }
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import ExportNotesHandler

        return ExportNotesHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_export_single_note_markdown(self, handler):
        """Test exporting a single note as markdown."""
        arguments = {"note_ids": "test123", "format": "markdown"}
        result = await handler.handle(arguments)
        assert len(result) == 1
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["format"] == "markdown"
        assert response["count"] == 1

    @pytest.mark.asyncio
    async def test_export_single_note_json(self, handler):
        """Test exporting a single note as JSON."""
        arguments = {"note_ids": "test123", "format": "json"}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["format"] == "json"

    @pytest.mark.asyncio
    async def test_export_missing_note_ids(self, handler):
        """Test export with missing note_ids raises error."""
        from simplenote_mcp.server.errors import ServerError

        arguments = {"format": "markdown"}
        with pytest.raises(ServerError):
            await handler.handle(arguments)
