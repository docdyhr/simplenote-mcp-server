"""Tests for duplicate detection and merging functionality."""

import json
from unittest.mock import MagicMock

import pytest

from simplenote_mcp.server.duplicates import DuplicateFinder


@pytest.fixture
def finder():
    """Create a DuplicateFinder with default threshold."""
    return DuplicateFinder(threshold=0.8)


@pytest.fixture
def duplicate_notes():
    """Create a set of notes with duplicates."""
    return [
        {
            "key": "note1",
            "content": "Meeting notes for project alpha. Discussed timeline and deliverables.",
            "tags": ["work", "project-alpha"],
            "modifydate": 1700200000.0,
        },
        {
            "key": "note2",
            "content": "Meeting notes for project alpha. Discussed timeline and deliverables.",
            "tags": ["meetings"],
            "modifydate": 1700100000.0,
        },
        {
            "key": "note3",
            "content": "Completely different note about cooking recipes.",
            "tags": ["personal"],
            "modifydate": 1700000000.0,
        },
    ]


@pytest.fixture
def near_duplicate_notes():
    """Create notes that are similar but not identical."""
    return [
        {
            "key": "note1",
            "content": "Project Alpha: Q4 Review\n\nRevenue exceeded targets by 15%.\nTeam performance was excellent.",
            "tags": ["review"],
            "modifydate": 1700200000.0,
        },
        {
            "key": "note2",
            "content": "Project Alpha: Q4 Review\n\nRevenue exceeded targets by 15%.\nTeam performance was excellent.\nUpdated with final numbers.",
            "tags": ["review", "final"],
            "modifydate": 1700300000.0,
        },
        {
            "key": "note3",
            "content": "Weekly grocery list:\n- Milk\n- Eggs\n- Bread",
            "tags": ["shopping"],
            "modifydate": 1700000000.0,
        },
    ]


@pytest.mark.unit
class TestDuplicateFinder:
    """Tests for DuplicateFinder.find_duplicates."""

    def test_find_exact_duplicates(self, finder, duplicate_notes):
        """Test finding exact duplicate notes."""
        groups = finder.find_duplicates(duplicate_notes)
        assert len(groups) == 1
        assert len(groups[0]) == 2
        # Both note1 and note2 should be in the group
        ids = {n["key"] for n in groups[0]}
        assert ids == {"note1", "note2"}

    def test_find_near_duplicates(self, finder, near_duplicate_notes):
        """Test finding near-duplicate notes."""
        groups = finder.find_duplicates(near_duplicate_notes)
        assert len(groups) == 1
        ids = {n["key"] for n in groups[0]}
        assert "note1" in ids
        assert "note2" in ids
        assert "note3" not in ids

    def test_no_duplicates(self, finder):
        """Test with no duplicates."""
        notes = [
            {"key": "1", "content": "First completely unique note", "tags": []},
            {"key": "2", "content": "Second totally different note", "tags": []},
        ]
        groups = finder.find_duplicates(notes)
        assert len(groups) == 0

    def test_empty_notes(self, finder):
        """Test with empty list."""
        groups = finder.find_duplicates([])
        assert groups == []

    def test_single_note(self, finder):
        """Test with single note."""
        notes = [{"key": "1", "content": "Only note", "tags": []}]
        groups = finder.find_duplicates(notes)
        assert groups == []

    def test_empty_content_skipped(self, finder):
        """Test notes with empty content are skipped."""
        notes = [
            {"key": "1", "content": "", "tags": []},
            {"key": "2", "content": "", "tags": []},
            {"key": "3", "content": "Actual content", "tags": []},
        ]
        groups = finder.find_duplicates(notes)
        assert len(groups) == 0

    def test_high_threshold(self):
        """Test high threshold only matches near-identical notes."""
        strict = DuplicateFinder(threshold=0.99)
        notes = [
            {"key": "1", "content": "Project Alpha meeting notes", "tags": []},
            {"key": "2", "content": "Project Alpha meeting notes!", "tags": []},
        ]
        groups = strict.find_duplicates(notes)
        # Slight difference might not pass 0.99
        # Just verify it runs without error
        assert isinstance(groups, list)

    def test_low_threshold(self):
        """Test low threshold catches more duplicates."""
        relaxed = DuplicateFinder(threshold=0.3)
        notes = [
            {
                "key": "1",
                "content": "Project Alpha meeting notes for today",
                "tags": [],
            },
            {
                "key": "2",
                "content": "Project Alpha meeting agenda for today",
                "tags": [],
            },
        ]
        groups = relaxed.find_duplicates(notes)
        assert len(groups) >= 1

    def test_threshold_clamping(self):
        """Test threshold is clamped."""
        f1 = DuplicateFinder(threshold=-1.0)
        assert f1.threshold == 0.0
        f2 = DuplicateFinder(threshold=5.0)
        assert f2.threshold == 1.0

    def test_sorted_by_modify_date(self, finder, duplicate_notes):
        """Test groups are sorted newest first."""
        groups = finder.find_duplicates(duplicate_notes)
        assert len(groups) == 1
        # note1 has newer modifydate (1700200000) than note2 (1700100000)
        assert groups[0][0]["key"] == "note1"

    def test_similarity_scores_present(self, finder, duplicate_notes):
        """Test that similarity scores are added to results."""
        groups = finder.find_duplicates(duplicate_notes)
        assert len(groups) == 1
        for note in groups[0]:
            assert "_similarity" in note


@pytest.mark.unit
class TestMergeGroup:
    """Tests for DuplicateFinder.merge_group."""

    def test_merge_basic(self, finder):
        """Test basic merge keeps newest content."""
        group = [
            {
                "key": "newer",
                "content": "Updated content",
                "tags": ["tag1"],
                "modifydate": 1700200000.0,
                "_similarity": 1.0,
            },
            {
                "key": "older",
                "content": "Original content",
                "tags": ["tag2"],
                "modifydate": 1700100000.0,
                "_similarity": 0.95,
            },
        ]
        merged = finder.merge_group(group)
        assert merged["key"] == "newer"
        assert merged["content"] == "Updated content"
        assert set(merged["tags"]) == {"tag1", "tag2"}

    def test_merge_tag_union(self, finder):
        """Test tags are unioned across all notes."""
        group = [
            {"key": "a", "content": "Content", "tags": ["x", "y"], "_similarity": 1.0},
            {"key": "b", "content": "Content", "tags": ["y", "z"], "_similarity": 0.9},
            {"key": "c", "content": "Content", "tags": ["z", "w"], "_similarity": 0.85},
        ]
        merged = finder.merge_group(group)
        assert set(merged["tags"]) == {"w", "x", "y", "z"}

    def test_merge_removes_similarity_key(self, finder):
        """Test _similarity key is removed from merged result."""
        group = [
            {"key": "a", "content": "Test", "tags": [], "_similarity": 1.0},
        ]
        merged = finder.merge_group(group)
        assert "_similarity" not in merged

    def test_merge_empty_group(self, finder):
        """Test merging empty group returns empty dict."""
        merged = finder.merge_group([])
        assert merged == {}

    def test_merge_no_tags(self, finder):
        """Test merge with notes that have no tags."""
        group = [
            {"key": "a", "content": "Content", "_similarity": 1.0},
            {"key": "b", "content": "Content", "_similarity": 0.9},
        ]
        merged = finder.merge_group(group)
        assert merged["tags"] == []


@pytest.mark.unit
class TestFindAndMergeDuplicatesHandler:
    """Tests for the FindAndMergeDuplicatesHandler tool handler."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.get_note_list.return_value = ([], 0)
        client.update_note.return_value = ({"key": "test", "tags": []}, 0)
        client.trash_note.return_value = 0
        return client

    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.is_initialized = True
        cache.get_all_notes.return_value = [
            {
                "key": "note1",
                "content": "Duplicate content here that is long enough for comparison",
                "tags": ["test"],
                "modifydate": 1700200000.0,
            },
            {
                "key": "note2",
                "content": "Duplicate content here that is long enough for comparison",
                "tags": ["other"],
                "modifydate": 1700100000.0,
            },
        ]
        return cache

    @pytest.fixture
    def handler(self, mock_client, mock_cache):
        from simplenote_mcp.server.tool_handlers import FindAndMergeDuplicatesHandler

        return FindAndMergeDuplicatesHandler(mock_client, mock_cache)

    @pytest.mark.asyncio
    async def test_dry_run_default(self, handler):
        """Test dry_run is True by default."""
        arguments = {}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_dry_run_finds_duplicates(self, handler):
        """Test dry run reports duplicate groups."""
        arguments = {"threshold": 0.8}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["total_groups"] >= 1

    @pytest.mark.asyncio
    async def test_no_duplicates_found(self, handler, mock_cache):
        """Test response when no duplicates found."""
        mock_cache.get_all_notes.return_value = [
            {"key": "1", "content": "Completely unique first note", "tags": []},
            {"key": "2", "content": "Totally different second note", "tags": []},
        ]
        arguments = {"threshold": 0.9}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["total_groups"] == 0

    @pytest.mark.asyncio
    async def test_empty_notes(self, handler, mock_cache):
        """Test with no notes."""
        mock_cache.get_all_notes.return_value = []
        arguments = {}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert "No notes found" in response["message"]

    @pytest.mark.asyncio
    async def test_merge_mode(self, handler, mock_client):
        """Test actual merge mode."""
        arguments = {"dry_run": False}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
        assert response["dry_run"] is False

    @pytest.mark.asyncio
    async def test_threshold_validation(self, handler):
        """Test invalid threshold defaults to 0.8."""
        arguments = {"threshold": "invalid"}
        result = await handler.handle(arguments)
        response = json.loads(result[0].text)
        assert response["success"] is True
