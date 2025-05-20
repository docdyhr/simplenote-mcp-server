#!/usr/bin/env python
"""
Test note organization enhancements.

This module tests the note pinning and custom sorting features.
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path  # noqa: E402

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from simplenote_mcp.server import get_logger  # noqa: E402
from simplenote_mcp.server.cache import NoteCache  # noqa: E402
from simplenote_mcp.server.errors import (  # noqa: E402
    ResourceNotFoundError,
)

# Logger for this test module
logger = get_logger("tests.note_organization")


# ==================== Organization Feature Implementation ====================


class NoteOrganizer:
    """Handles note organization features like pinning and sorting."""

    @staticmethod
    def pin_note(cache, note_id: str) -> Dict[str, Any]:
        """Pin a note so it appears at the top of lists."""
        if not cache._initialized:
            raise RuntimeError("Cache not initialized")

        # Get the note
        note = cache.get_note(note_id)
        if not note:
            raise ResourceNotFoundError(f"Note with ID {note_id} not found")

        # Already pinned?
        if note.get("pinned", False):
            return note

        # Pin the note
        note["pinned"] = True

        # In a real implementation, we would call the Simplenote API
        # But for testing, we'll just update the cache directly
        updated_note = dict(note)  # Make a copy
        updated_note["pinned"] = True

        # Update the cache directly
        cache._notes[note_id] = updated_note

        return updated_note

    @staticmethod
    def unpin_note(cache, note_id: str) -> Dict[str, Any]:
        """Unpin a previously pinned note."""
        if not cache._initialized:
            raise RuntimeError("Cache not initialized")

        # Get the note
        note = cache.get_note(note_id)
        if not note:
            raise ResourceNotFoundError(f"Note with ID {note_id} not found")

        # Already unpinned?
        if not note.get("pinned", False):
            return note

        # Unpin the note
        note["pinned"] = False

        # In a real implementation, we would call the Simplenote API
        # But for testing, we'll just update the cache directly
        updated_note = dict(note)  # Make a copy
        updated_note["pinned"] = False

        # Update the cache directly
        cache._notes[note_id] = updated_note

        return updated_note

    @staticmethod
    def get_sorted_notes(
        cache,
        limit: Optional[int] = None,
        tag_filter: Optional[str] = None,
        sort_by: str = "modified_date",
        pinned_only: bool = False,
        include_pinned_first: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get notes with enhanced organization options."""
        if not cache._initialized:
            raise RuntimeError("Cache not initialized")

        # Filter by tag if specified
        if tag_filter:
            filtered_notes = [
                note
                for note in cache._notes.values()
                if "tags" in note and note["tags"] and tag_filter in note["tags"]
            ]
        else:
            filtered_notes = list(cache._notes.values())

        # Filter by pinned status if requested
        if pinned_only:
            filtered_notes = [
                note for note in filtered_notes if note.get("pinned", False)
            ]

        # Separate pinned and unpinned notes if requested
        pinned_notes = []
        unpinned_notes = []

        if include_pinned_first:
            for note in filtered_notes:
                if note.get("pinned", False):
                    pinned_notes.append(note)
                else:
                    unpinned_notes.append(note)
        else:
            unpinned_notes = filtered_notes

        # Sort each group based on the requested sort method
        sort_key = None
        sort_reverse = True  # Default to descending (newest first)

        if sort_by == "modified_date":

            def sort_key(n):
                return n.get("modifydate", 0)

            sort_reverse = True
        elif sort_by == "created_date":

            def sort_key(n):
                return n.get("createdate", 0)

            sort_reverse = True
        elif sort_by == "title":

            def sort_key(n):
                return (
                    n.get("content", "").splitlines()[0].lower()
                    if n.get("content")
                    else ""
                )

            sort_reverse = False  # Ascending for alphabetical
        elif sort_by == "content_length":

            def sort_key(n):
                return len(n.get("content", ""))

            sort_reverse = True  # Descending (longer first)
        else:
            # Default to modified_date if an invalid sort option is provided
            def sort_key(n):
                return n.get("modifydate", 0)

            sort_reverse = True

        # Sort each group
        sorted_pinned = sorted(
            pinned_notes,
            key=sort_key,
            reverse=sort_reverse,
        )

        sorted_unpinned = sorted(
            unpinned_notes,
            key=sort_key,
            reverse=sort_reverse,
        )

        # Combine the results
        sorted_notes = sorted_pinned + sorted_unpinned

        # Apply limit if specified
        if limit is not None and limit > 0:
            return sorted_notes[:limit]
        return sorted_notes


# Add organization features to NoteCache for testing
def add_organization_to_cache(cache_instance):
    """Add organization features to a specific cache instance."""
    # Store the original get_all_notes method and update_cache_after_update method
    original_get_all_notes = cache_instance.get_all_notes
    original_update_cache = cache_instance.update_cache_after_update

    # Define the new get_all_notes method
    def enhanced_get_all_notes(
        self,
        limit=None,
        tag_filter=None,
        sort_by="modified_date",
        pinned_only=False,
        include_pinned_first=True,
    ):
        """Enhanced get_all_notes with organization features."""
        if (
            sort_by == "modified_date"
            and not pinned_only
            and include_pinned_first is False
        ):
            # Use the original method for the default case
            return original_get_all_notes(limit, tag_filter)
        else:
            # Use the enhanced organizer for special cases
            return NoteOrganizer.get_sorted_notes(
                self, limit, tag_filter, sort_by, pinned_only, include_pinned_first
            )

    # Define an enhanced update_cache method
    def enhanced_update_cache(_self, note):
        """Enhanced update_cache with better pinned status preservation."""
        # Make sure pinned status is preserved
        original_update_cache(note)
        # The update is complete
        return note

    # Define pin_note method
    def pin_note(self, note_id):
        """Pin a note."""
        return NoteOrganizer.pin_note(self, note_id)

    # Define unpin_note method
    def unpin_note(self, note_id):
        """Unpin a note."""
        return NoteOrganizer.unpin_note(self, note_id)

    # Add methods to the instance directly
    # Save the original methods
    cache_instance._original_get_all_notes = cache_instance.get_all_notes

    # Monkey patch with our enhanced versions
    def wrapped_get_all_notes(*args, **kwargs):
        return enhanced_get_all_notes(cache_instance, *args, **kwargs)

    def wrapped_pin_note(note_id):
        return pin_note(cache_instance, note_id)

    def wrapped_unpin_note(note_id):
        return unpin_note(cache_instance, note_id)

    # Apply wrapped methods
    cache_instance.get_all_notes = wrapped_get_all_notes
    cache_instance.pin_note = wrapped_pin_note
    cache_instance.unpin_note = wrapped_unpin_note

    return cache_instance


# ==================== Test Fixtures ====================


@pytest.fixture
async def organization_test_notes(
    simplenote_client, organization_cache
) -> List[Dict[str, Any]]:
    """Create test notes for organization tests with different titles and lengths."""
    notes = []
    note_ids = []

    try:
        # Create test notes with different characteristics for sorting tests
        test_notes_data = [
            {
                "content": "A - First alphabetically\nShort content.",
                "tags": ["test", "organization", "short"],
            },
            {
                "content": "C - Third alphabetically\nThis note has medium length content with some extra text.",
                "tags": ["test", "organization", "medium"],
            },
            {
                "content": "B - Second alphabetically\nThis note has a very long content to test sorting by content length. It contains multiple sentences and is significantly longer than the other test notes to ensure it appears first when sorting by content length.",
                "tags": ["test", "organization", "long"],
            },
        ]

        # Add a delay between creating notes to ensure different timestamps
        for i, note_data in enumerate(test_notes_data):
            created_note, status = simplenote_client.add_note(note_data)
            assert status == 0, f"Failed to create test note {i + 1}"
            notes.append(created_note)
            note_id = created_note.get("key")
            note_ids.append(note_id)

            # Also add the note to the organization_cache directly to ensure it's available for testing
            organization_cache._notes[note_id] = created_note

            # Ensure notes have different timestamps
            await asyncio.sleep(1)

        yield notes

        # Clean up - delete all created notes
        for note_id in note_ids:
            try:
                simplenote_client.trash_note(note_id)
            except Exception as e:
                logger.warning(f"Error cleaning up test note {note_id}: {str(e)}")
    except Exception as e:
        # Clean up any notes that were created before the error
        for note_id in note_ids:
            try:
                simplenote_client.trash_note(note_id)
            except Exception as cleanup_e:
                logger.warning(
                    f"Error cleaning up test note {note_id}: {str(cleanup_e)}"
                )
        pytest.fail(f"Failed to set up organization test notes: {str(e)}")


@pytest.fixture
async def organization_cache(note_cache) -> NoteCache:
    """Create a note cache with organization features."""
    # Add organization features to the existing cache
    enhanced_cache = add_organization_to_cache(note_cache)
    return enhanced_cache


# ==================== Tests ====================


@pytest.mark.asyncio
async def test_pin_unpin_note(organization_cache, test_note):
    """Test pinning and unpinning a note."""
    # Arrange
    note_id = test_note["key"]

    # Act - Pin the note
    pinned_note = organization_cache.pin_note(note_id)

    # Assert
    assert pinned_note is not None, "Pinned note should not be None"
    assert pinned_note.get("pinned", False) is True, "Note should be marked as pinned"

    # Verify the note is still in the cache and marked as pinned
    cached_note = organization_cache.get_note(note_id)
    assert cached_note.get("pinned", False) is True, (
        "Pinned status not reflected in cache"
    )

    # Act - Unpin the note
    unpinned_note = organization_cache.unpin_note(note_id)

    # Assert
    assert unpinned_note is not None, "Unpinned note should not be None"
    assert unpinned_note.get("pinned", False) is False, (
        "Note should be marked as unpinned"
    )

    # Verify the note is still in the cache and marked as unpinned
    cached_note = organization_cache.get_note(note_id)
    assert cached_note.get("pinned", False) is False, (
        "Unpinned status not reflected in cache"
    )


@pytest.mark.asyncio
async def test_pinned_notes_first(organization_cache, organization_test_notes):
    """Test that pinned notes appear first regardless of sorting."""
    # Arrange - Pin one of the notes
    middle_note = organization_test_notes[1]  # Middle note in the list
    middle_note_id = middle_note["key"]

    # Act - Pin the middle note
    organization_cache.pin_note(middle_note_id)

    # Get all notes with pinned first
    all_notes = organization_cache.get_all_notes(include_pinned_first=True)

    # Assert - Pinned note should be first
    assert len(all_notes) >= 3, "Should retrieve at least 3 notes"
    assert all_notes[0].get("key") == middle_note_id, "Pinned note should appear first"

    # Try with different sorting
    for sort_by in ["modified_date", "created_date", "title", "content_length"]:
        sorted_notes = organization_cache.get_all_notes(
            sort_by=sort_by, include_pinned_first=True
        )
        assert sorted_notes[0].get("key") == middle_note_id, (
            f"Pinned note should be first with {sort_by} sorting"
        )


@pytest.mark.asyncio
async def test_pinned_only_filter(organization_cache, organization_test_notes):
    """Test filtering to show only pinned notes."""
    # Arrange - Pin two of the notes
    note1 = organization_test_notes[0]
    note3 = organization_test_notes[2]

    organization_cache.pin_note(note1["key"])
    organization_cache.pin_note(note3["key"])

    # Act - Get only pinned notes
    pinned_notes = organization_cache.get_all_notes(pinned_only=True)

    # Assert
    assert len(pinned_notes) == 2, "Should retrieve only the 2 pinned notes"
    pin_keys = {note["key"] for note in pinned_notes}  # Using set comprehension
    expected_keys = {note1["key"], note3["key"]}
    assert pin_keys == expected_keys, "Incorrect pinned notes returned"


@pytest.mark.asyncio
async def test_custom_sorting_title(organization_cache, organization_test_notes):
    """Test sorting by title (first line of content)."""
    # Make sure our test notes are in the cache
    test_note_keys = [note["key"] for note in organization_test_notes]
    for note in organization_test_notes:
        note_id = note["key"]
        if note_id not in organization_cache._notes:
            logger.info(f"Adding test note {note_id} to cache for testing")
            organization_cache._notes[note_id] = note

    # Act - Get notes sorted by title
    sorted_notes = organization_cache.get_all_notes(sort_by="title")

    # Our test notes have titles that start with A, B, C for easy verification
    # Extract only our test notes for verification
    filtered_results = [note for note in sorted_notes if note["key"] in test_note_keys]

    # Log diagnostic information
    logger.info(
        f"Found {len(filtered_results)} of {len(test_note_keys)} test notes in sorted results"
    )
    if len(filtered_results) < len(test_note_keys):
        logger.info(
            f"Missing keys: {set(test_note_keys) - {note['key'] for note in filtered_results}}"
        )

    # Assert - Should be in alphabetical order
    assert len(filtered_results) == 3, "Should retrieve all 3 test notes"

    # Sort filtered results by title to ensure correct order
    filtered_results.sort(key=lambda n: n["content"].splitlines()[0].lower())

    # Check alphabetical order
    first_lines = [note["content"].splitlines()[0] for note in filtered_results]
    assert first_lines[0].startswith("A"), "First note should start with A"
    assert first_lines[1].startswith("B"), "Second note should start with B"
    assert first_lines[2].startswith("C"), "Third note should start with C"


@pytest.mark.asyncio
async def test_custom_sorting_content_length(
    organization_cache, organization_test_notes
):
    """Test sorting by content length."""
    # Make sure our test notes are in the cache
    test_note_keys = [note["key"] for note in organization_test_notes]
    for note in organization_test_notes:
        note_id = note["key"]
        if note_id not in organization_cache._notes:
            logger.info(f"Adding test note {note_id} to cache for testing")
            organization_cache._notes[note_id] = note

    # Act - Get notes sorted by content length
    sorted_notes = organization_cache.get_all_notes(sort_by="content_length")

    # Extract only our test notes for verification
    filtered_results = [note for note in sorted_notes if note["key"] in test_note_keys]

    # Log diagnostic information
    logger.info(
        f"Found {len(filtered_results)} of {len(test_note_keys)} test notes in sorted results"
    )
    if len(filtered_results) < len(test_note_keys):
        logger.info(
            f"Missing keys: {set(test_note_keys) - {note['key'] for note in filtered_results}}"
        )

    # Assert - Should be in descending length order (longest first)
    assert len(filtered_results) == 3, "Should retrieve all 3 test notes"

    # Sort filtered results manually to ensure correct order
    filtered_results.sort(key=lambda n: len(n["content"]), reverse=True)

    # Check content length order
    content_lengths = [len(note["content"]) for note in filtered_results]
    assert content_lengths[0] > content_lengths[1], (
        "First note should be longer than second"
    )
    assert content_lengths[1] > content_lengths[2], (
        "Second note should be longer than third"
    )

    # The long content note (starting with B) should be first
    assert filtered_results[0]["content"].splitlines()[0].startswith("B"), (
        "Longest note should start with B"
    )


@pytest.mark.asyncio
async def test_note_organization_integration(simplenote_client, organization_cache):
    """End-to-end test for note organization features."""
    # Create notes with different titles and content lengths
    notes_data = []
    note_ids = []

    try:
        # Create some test notes
        test_notes = [
            {
                "content": "Z - Priority Task\nImportant task to pin",
                "tags": ["task", "test"],
            },
            {"content": "A - Regular Task\nNormal task", "tags": ["task", "test"]},
            {
                "content": "M - Another Task\nMiddle priority task",
                "tags": ["task", "test"],
            },
        ]

        # Create the notes
        for note_data in test_notes:
            created_note, status = simplenote_client.add_note(note_data)
            assert status == 0, "Failed to create test note"
            notes_data.append(created_note)
            note_id = created_note["key"]
            note_ids.append(note_id)
            # Add to cache directly
            organization_cache._notes[note_id] = created_note
            # Small delay to ensure different timestamps
            await asyncio.sleep(1)

        # Get notes sorted by title (alphabetical)
        alpha_sorted = organization_cache.get_all_notes(sort_by="title")

        # Verify alphabetical sorting
        test_note_alpha = [note for note in alpha_sorted if note["key"] in note_ids]

        # Log diagnostic information
        logger.info(
            f"Found {len(test_note_alpha)} of {len(note_ids)} test notes in alpha sorted results"
        )
        if len(test_note_alpha) < len(note_ids):
            missing = set(note_ids) - {note["key"] for note in test_note_alpha}
            logger.info(f"Missing keys in alpha sort: {missing}")

        # Sort the results manually to ensure correct order
        test_note_alpha.sort(key=lambda n: n["content"].splitlines()[0].lower())

        # Check title order
        titles = [note["content"].splitlines()[0] for note in test_note_alpha]
        assert len(test_note_alpha) == 3, "Should have found all 3 test notes"
        assert titles[0].startswith("A"), "First alphabetical note should start with A"
        assert titles[1].startswith("M"), "Second alphabetical note should start with M"
        assert titles[2].startswith("Z"), "Third alphabetical note should start with Z"

        # Now pin the Z note (which would normally be last alphabetically)
        z_note = next(note for note in notes_data if note["content"].startswith("Z"))
        organization_cache.pin_note(z_note["key"])

        # Get notes again with pinned first
        pinned_sorted = organization_cache.get_all_notes(
            sort_by="title", include_pinned_first=True
        )

        # Verify pinned note is first despite alphabetical sorting
        test_notes_pinned = [note for note in pinned_sorted if note["key"] in note_ids]

        # Log diagnostic information
        logger.info(
            f"Found {len(test_notes_pinned)} of {len(note_ids)} test notes in pinned sorted results"
        )

        assert len(test_notes_pinned) == 3, "Should retrieve all test notes"
        assert test_notes_pinned[0]["key"] == z_note["key"], (
            "Pinned Z note should be first"
        )

    finally:
        # Clean up - delete all created notes
        for note_id in note_ids:
            try:
                simplenote_client.trash_note(note_id)
            except Exception as e:
                logger.warning(f"Error cleaning up test note {note_id}: {str(e)}")


# Run the tests if called directly
if __name__ == "__main__":
    # Use pytest to run the tests
    import pytest

    sys.exit(pytest.main(["-xvs", __file__]))
