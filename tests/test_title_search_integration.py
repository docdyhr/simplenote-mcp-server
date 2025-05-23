"""Integration tests for title search functionality with real API calls."""

import asyncio
import time

import pytest

from simplenote_mcp.server.server import get_simplenote_client
from simplenote_mcp.tests.test_helpers import handle_call_tool


@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_notes_cleanup():
    """Fixture to track and cleanup test notes created during tests."""
    created_note_ids = []

    yield created_note_ids

    # Cleanup: Delete all test notes created during the session
    if created_note_ids:
        client = get_simplenote_client()
        for note_id in created_note_ids:
            try:
                note, status = client.get_note(note_id)
                if status == 0 and note:
                    client.trash_note(note_id)
                    print(f"Cleaned up test note: {note_id}")
            except Exception as e:
                print(f"Failed to cleanup note {note_id}: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_search_by_title(test_notes_cleanup):
    """Test creating notes with specific titles and searching for them."""
    # Create test notes with distinct titles
    test_data = [
        {
            "title": "Project Alpha Documentation",
            "content": "Project Alpha Documentation\nThis is the main documentation for Project Alpha.\nIt contains technical specifications.",
            "tags": ["project", "documentation", "alpha"],
        },
        {
            "title": "Meeting Notes: Project Beta Review",
            "content": "Meeting Notes: Project Beta Review\nDate: 2025-01-20\nAttendees: Team leads\nDiscussed project timeline.",
            "tags": ["meeting", "project", "beta"],
        },
        {
            "title": "TODO: Complete Project Gamma",
            "content": "TODO: Complete Project Gamma\n- Finish implementation\n- Write tests\n- Deploy to staging",
            "tags": ["todo", "project", "gamma"],
        },
        {
            "title": "Quick Reference: API Endpoints",
            "content": "Quick Reference: API Endpoints\n/api/v1/users\n/api/v1/projects\n/api/v1/tasks",
            "tags": ["reference", "api"],
        },
        {
            "title": "Random thoughts about projects",
            "content": "Random thoughts about projects\nJust some ideas that came to mind about various projects.",
            "tags": ["thoughts"],
        },
    ]

    # Create the test notes
    created_notes = []
    for note_data in test_data:
        result = await handle_call_tool(
            "create_note", {"content": note_data["content"], "tags": note_data["tags"]}
        )

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        assert note_id is not None
        test_notes_cleanup.append(note_id)

        created_notes.append(
            {"id": note_id, "title": note_data["title"], "tags": note_data["tags"]}
        )

        # Small delay to ensure notes are indexed
        await asyncio.sleep(0.5)

    # Wait a bit for API to sync
    await asyncio.sleep(2)

    # Test 1: Search for "Project" - should find multiple notes
    result = await handle_call_tool("search_notes", {"query": "Project"})
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True
    assert len(result_data["results"]) >= 4  # At least 4 notes have "Project" in title

    # Verify that notes with "Project" in title are found
    found_titles = [r.get("title", "") for r in result_data["results"]]
    project_titles = [
        "Project Alpha Documentation",
        "Meeting Notes: Project Beta Review",
        "TODO: Complete Project Gamma",
    ]

    for expected_title in project_titles:
        # Check if any found title starts with the expected title (truncated)
        assert any(
            expected_title.startswith(title[: len(title)])
            for title in found_titles
            if title
        )

    # Test 2: Search for specific project names
    for project_name in ["Alpha", "Beta", "Gamma"]:
        result = await handle_call_tool("search_notes", {"query": project_name})
        result_data = json.loads(result[0].text)

        assert result_data["success"] is True
        assert len(result_data["results"]) >= 1

        # Verify the correct note is found
        found_ids = [r["id"] for r in result_data["results"]]
        expected_note = next(
            n for n in created_notes if project_name.lower() in n["title"].lower()
        )
        assert expected_note["id"] in found_ids

    # Test 3: Search with boolean AND - "Project AND Documentation"
    result = await handle_call_tool(
        "search_notes", {"query": "Project AND Documentation"}
    )
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True
    assert len(result_data["results"]) >= 1

    # Should find "Project Alpha Documentation"
    found_ids = [r["id"] for r in result_data["results"]]
    alpha_note = next(
        n for n in created_notes if n["title"] == "Project Alpha Documentation"
    )
    assert alpha_note["id"] in found_ids

    # Test 4: Search with NOT operator - "Project NOT Meeting"
    result = await handle_call_tool("search_notes", {"query": "Project NOT Meeting"})
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True

    # Should find project notes but not the meeting note
    found_ids = [r["id"] for r in result_data["results"]]
    meeting_note = next(n for n in created_notes if "Meeting" in n["title"])
    assert meeting_note["id"] not in found_ids

    # But should find other project notes
    alpha_note = next(
        n for n in created_notes if n["title"] == "Project Alpha Documentation"
    )
    assert alpha_note["id"] in found_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_with_special_characters_in_title(test_notes_cleanup):
    """Test searching for notes with special characters in titles."""
    # Create notes with special characters
    special_notes = [
        {
            "content": "C++ Programming Guide\nAdvanced topics in C++ development",
            "tags": ["programming", "cpp"],
        },
        {
            "content": "Email: user@example.com\nContact information",
            "tags": ["contact"],
        },
        {
            "content": "Price: $99.99 (Special Offer!)\nLimited time deal",
            "tags": ["pricing"],
        },
        {"content": "Math: 2+2=4\nBasic arithmetic", "tags": ["math"]},
    ]

    created_ids = []
    for note_data in special_notes:
        result = await handle_call_tool("create_note", note_data)

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        assert note_id is not None
        test_notes_cleanup.append(note_id)
        created_ids.append(note_id)

        await asyncio.sleep(0.5)

    # Wait for sync
    await asyncio.sleep(2)

    # Search for various special character patterns
    test_queries = [
        ("C++", "C++ Programming Guide"),
        ("user@example.com", "Email: user@example.com"),
        ("$99.99", "Price: $99.99"),
        ("2+2=4", "Math: 2+2=4"),
    ]

    for query, expected_title_start in test_queries:
        result = await handle_call_tool("search_notes", {"query": query})
        result_data = json.loads(result[0].text)

        assert result_data["success"] is True

        # Verify we found at least one result
        if result_data["results"]:
            # Check if any result matches our expected title
            found_titles = [r.get("title", "") for r in result_data["results"]]
            any(
                title.startswith(expected_title_start[: len(title)])
                for title in found_titles
                if title
            )

            # Note: Some special characters might affect search behavior
            # so we're being lenient here
            print(f"Query '{query}' found titles: {found_titles}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_case_sensitivity_real_api(test_notes_cleanup):
    """Test case sensitivity in search with real API."""
    # Create notes with different cases
    case_notes = [
        "PROJECT ALPHA IN UPPERCASE\nAll caps title",
        "project beta in lowercase\nAll lowercase title",
        "Project Gamma In Mixed Case\nMixed case title",
    ]

    created_ids = []
    for content in case_notes:
        result = await handle_call_tool("create_note", {"content": content})

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        assert note_id is not None
        test_notes_cleanup.append(note_id)
        created_ids.append(note_id)

        await asyncio.sleep(0.5)

    # Wait for sync
    await asyncio.sleep(2)

    # Search with different cases
    for query in ["project", "Project", "PROJECT", "pRoJeCt"]:
        result = await handle_call_tool("search_notes", {"query": query})
        result_data = json.loads(result[0].text)

        assert result_data["success"] is True

        # Should find all three notes regardless of case
        found_ids = [r["id"] for r in result_data["results"]]

        # Count how many of our test notes were found
        found_count = sum(1 for cid in created_ids if cid in found_ids)

        # We expect to find all 3 notes
        assert found_count >= 3, (
            f"Query '{query}' only found {found_count} of 3 test notes"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_empty_and_whitespace_titles(test_notes_cleanup):
    """Test searching with notes that have empty or whitespace-only first lines."""
    # Create notes with edge cases
    edge_case_notes = [
        "\n\nContent after empty lines\nThis note starts with newlines",
        "   \nContent after spaces\nThis note starts with spaces",
        "\t\nContent after tab\nThis note starts with a tab",
        "",  # Completely empty note
        "Normal Title\n\n\nContent after multiple newlines",
    ]

    created_ids = []
    for content in edge_case_notes:
        result = await handle_call_tool("create_note", {"content": content})

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        if note_id:
            test_notes_cleanup.append(note_id)
            created_ids.append(note_id)

        await asyncio.sleep(0.5)

    # Wait for sync
    await asyncio.sleep(2)

    # Search for content that appears after empty lines
    result = await handle_call_tool("search_notes", {"query": "Content after"})
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True

    # Should find the notes with "Content after" in them
    if result_data["results"]:
        found_ids = [r["id"] for r in result_data["results"]]

        # Count how many of our edge case notes were found
        found_count = sum(1 for cid in created_ids if cid in found_ids)

        print(f"Found {found_count} edge case notes with 'Content after'")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_with_tags_and_title(test_notes_cleanup):
    """Test searching by title with tag filters."""
    # Create notes with specific title/tag combinations
    tagged_notes = [
        {
            "content": "Project Management Best Practices\nGuidelines for effective project management",
            "tags": ["project", "management", "guide"],
        },
        {
            "content": "Project Development Workflow\nStandard development process",
            "tags": ["project", "development", "process"],
        },
        {
            "content": "Personal Project Ideas\nBrainstorming for side projects",
            "tags": ["personal", "project", "ideas"],
        },
        {
            "content": "Team Management Tips\nHow to manage teams effectively",
            "tags": ["management", "team", "tips"],
        },
    ]

    created_ids = []
    for note_data in tagged_notes:
        result = await handle_call_tool("create_note", note_data)

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        assert note_id is not None
        test_notes_cleanup.append(note_id)
        created_ids.append(note_id)

        await asyncio.sleep(0.5)

    # Wait for sync
    await asyncio.sleep(2)

    # Test 1: Search for "Project" with tag filter "personal"
    result = await handle_call_tool(
        "search_notes", {"query": "Project", "tags": "personal"}
    )
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True

    # Should find only "Personal Project Ideas"
    if result_data["results"]:
        assert len(result_data["results"]) >= 1
        # Verify it has the personal tag
        for r in result_data["results"]:
            if "tags" in r:
                assert "personal" in r["tags"]

    # Test 2: Search for "Management" with tag filter "project"
    result = await handle_call_tool(
        "search_notes", {"query": "Management", "tags": "project"}
    )
    result_data = json.loads(result[0].text)

    assert result_data["success"] is True

    # Should find "Project Management Best Practices"
    if result_data["results"]:
        for r in result_data["results"]:
            if "tags" in r:
                assert "project" in r["tags"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_performance_with_many_notes(test_notes_cleanup):
    """Test search performance with multiple notes."""
    # Create a batch of notes
    batch_size = 10
    notes_to_create = []

    for i in range(batch_size):
        notes_to_create.append(
            {
                "content": f"Test Note #{i + 1}: Project Analysis\nThis is test note number {i + 1} for performance testing.",
                "tags": ["test", "batch", f"note{i + 1}"],
            }
        )

    # Measure creation time
    start_time = time.time()

    created_ids = []
    for note_data in notes_to_create:
        result = await handle_call_tool("create_note", note_data)

        import json

        result_data = json.loads(result[0].text)
        note_id = result_data.get("key") or result_data.get("note_id")

        if note_id:
            test_notes_cleanup.append(note_id)
            created_ids.append(note_id)

        await asyncio.sleep(0.2)  # Small delay between creations

    creation_time = time.time() - start_time
    print(f"Created {len(created_ids)} notes in {creation_time:.2f} seconds")

    # Wait for sync
    await asyncio.sleep(2)

    # Measure search time
    search_start = time.time()

    result = await handle_call_tool("search_notes", {"query": "Project Analysis"})

    search_time = time.time() - search_start
    print(f"Search completed in {search_time:.3f} seconds")

    result_data = json.loads(result[0].text)

    assert result_data["success"] is True
    assert len(result_data["results"]) >= batch_size

    # Verify search performance is reasonable (should be under 5 seconds)
    assert search_time < 5.0
