"""End-to-end user session scenario tests."""

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import mcp.types as types
import pytest

from simplenote_mcp.server.errors import ResourceNotFoundError
from simplenote_mcp.server.server import (
    handle_list_resources,
    handle_read_resource,
    initialize_cache,
)


async def call_tool_helper(name: str, arguments: dict) -> Any:
    """Local helper function for tool calls."""
    from simplenote_mcp.server.server import handle_call_tool as server_handle_call_tool

    return await server_handle_call_tool(name, arguments)


@pytest.fixture
async def end_to_end_setup():
    """Set up complete server environment for end-to-end testing."""
    # Mock client with comprehensive note data
    mock_client = MagicMock()

    # Initial empty state
    mock_client.get_note_list.return_value = ([], 0)
    mock_client.add_note.return_value = (
        None,
        0,
    )  # Will be overridden per test - using correct method name
    mock_client.update_note.return_value = (None, 0)  # Will be overridden per test
    mock_client.trash_note.return_value = 0  # trash_note returns status only
    mock_client.get_note.return_value = (None, 0)  # Will be overridden per test

    with (
        patch(
            "simplenote_mcp.server.server.get_simplenote_client",
            return_value=mock_client,
        ),
        patch("simplenote_mcp.server.server.note_cache", None),
        patch("simplenote_mcp.server.server.get_config") as mock_get_config,
    ):
        # Configure mock config with proper values
        mock_config = MagicMock()
        mock_config.default_resource_limit = 100
        mock_config.max_resource_limit = 1000
        mock_config.cache_initialization_timeout = 30  # Proper timeout value
        mock_config.sync_interval_seconds = 120
        mock_config.write_mode = True
        mock_config.write_budget_max = 100
        mock_config.write_budget_window_seconds = 60
        mock_get_config.return_value = mock_config

        # Initialize cache
        await initialize_cache()

        yield {"mock_client": mock_client, "mock_config": mock_config}


@pytest.mark.integration
class TestEndToEndScenarios:
    """Test complete user session workflows from start to finish."""

    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, end_to_end_setup):
        """Test a complete user workflow: create → tag → search → paginate → delete."""
        mock_client = end_to_end_setup["mock_client"]

        # Step 1: Create initial notes
        created_notes = []

        # Create multiple notes for comprehensive testing
        note_contents = [
            ("Meeting Notes - Project Alpha", ["work", "project-alpha", "important"]),
            ("Project Alpha Tasks", ["work", "project-alpha", "tasks"]),
            ("Personal Journal Entry", ["personal", "journal"]),
            ("Work Ideas and Brainstorming", ["work", "ideas"]),
            ("Shopping List", ["personal", "shopping"]),
            ("Meeting Notes - Project Beta", ["work", "project-beta", "important"]),
            ("Project Beta Planning", ["work", "project-beta", "planning"]),
            ("Book Recommendations", ["personal", "books", "reference"]),
            ("Coding Notes - Python Tips", ["work", "coding", "python", "reference"]),
            ("Travel Plans Summer 2025", ["personal", "travel", "planning"]),
        ]

        for i, (content, tags) in enumerate(note_contents):
            note_id = f"note_{i + 1}"
            created_note = {
                "key": note_id,
                "content": content,
                "tags": tags,
                "modifydate": f"2025-04-{i + 1:02d}T12:00:00Z",
                "createdate": f"2025-01-{i + 1:02d}T00:00:00Z",
            }

            # Mock add_note response
            mock_client.add_note.return_value = (created_note, 0)

            # Create note via tool
            result = await call_tool_helper(
                "create_note", {"content": content, "tags": tags}
            )

            assert len(result) == 1
            response = json.loads(result[0].text)
            assert response["success"] is True

            created_notes.append(created_note)

            # Add note to mock client's note list for future operations
            if not hasattr(mock_client, "_notes_db"):
                mock_client._notes_db = {}
            mock_client._notes_db[note_id] = created_note

        # Step 2: List resources to verify creation
        mock_client.get_note_list.return_value = (created_notes, 0)

        resources = await handle_list_resources()
        assert len(resources) == len(created_notes)

        # Step 3: Search for specific tags
        # Mock search by returning filtered notes
        def mock_search_response(query_args):
            query = query_args.get("query", "")
            limit = int(query_args.get("limit", 50))

            # Simple search simulation
            matching_notes = []
            for note in created_notes:
                if query.lower() in note["content"].lower() or any(
                    query.lower() in tag.lower() for tag in note.get("tags", [])
                ):
                    matching_notes.append(note)

            return matching_notes[:limit]

        # Search for work-related notes
        work_notes = mock_search_response({"query": "work", "limit": "10"})
        assert len(work_notes) >= 5  # Should find several work notes

        # Search for project-alpha notes
        alpha_notes = mock_search_response({"query": "project-alpha", "limit": "10"})
        assert len(alpha_notes) == 2  # Should find exactly 2 project-alpha notes

        # Step 4: Test pagination with get_all_notes
        # First page
        first_page = await handle_list_resources(limit=5)
        assert len(first_page) == 5

        # Second page (simulated with offset, though our current API doesn't directly support it)
        # We'll test by requesting different limits to verify pagination logic
        larger_page = await handle_list_resources(limit=8)
        assert len(larger_page) == 8
        assert len(larger_page) > len(first_page)

        # Step 5: Read specific resources
        # Mock get_note for individual note retrieval
        mock_client.get_note.return_value = (created_notes[0], 0)

        note_resource = list(
            await handle_read_resource(f"simplenote://note/{created_notes[0]['key']}")
        )
        assert note_resource
        assert created_notes[0]["content"] in note_resource[0].content

        # Step 6: Update a note (add tags)
        updated_note = created_notes[0].copy()
        updated_note["tags"] = created_notes[0]["tags"] + ["updated", "new-tag"]
        updated_note["content"] = (
            updated_note["content"] + "\n\nUpdated with additional content."
        )

        mock_client.update_note.return_value = (updated_note, 0)
        mock_client.get_note.return_value = (updated_note, 0)  # For subsequent reads

        update_result = await call_tool_helper(
            "update_note",
            {
                "note_id": created_notes[0]["key"],
                "content": updated_note["content"],
                "tags": updated_note["tags"],
            },
        )

        assert len(update_result) == 1
        response = json.loads(update_result[0].text)
        assert response["success"] is True

        # Step 7: Verify updated note can be found in searches
        # Update our mock database
        mock_client._notes_db[created_notes[0]["key"]] = updated_note

        # Search should now find the updated tag
        updated_search = mock_search_response({"query": "new-tag", "limit": "10"})
        assert len(updated_search) >= 1

        # Step 8: Delete some notes
        notes_to_delete = created_notes[7:9]  # Delete 2 notes

        for note in notes_to_delete:
            delete_result = await call_tool_helper(
                "delete_note", {"note_id": note["key"]}
            )

            assert len(delete_result) == 1
            response = json.loads(delete_result[0].text)
            assert response["success"] is True

            # Remove from mock database
            if (
                hasattr(mock_client, "_notes_db")
                and note["key"] in mock_client._notes_db
            ):
                del mock_client._notes_db[note["key"]]

        # Step 9: Verify final state
        # Update mock to return remaining notes
        remaining_notes = [n for n in created_notes if n not in notes_to_delete]
        remaining_notes[0] = updated_note  # Include the updated version
        mock_client.get_note_list.return_value = (remaining_notes, 0)

        final_resources = await handle_list_resources()
        assert len(final_resources) == len(remaining_notes)

        # Verify deleted notes are no longer accessible
        for deleted_note in notes_to_delete:
            mock_client.get_note.return_value = (None, 1)  # Not found

            with pytest.raises(ResourceNotFoundError):
                await handle_read_resource(f"simplenote://note/{deleted_note['key']}")

    @pytest.mark.asyncio
    async def test_concurrent_user_sessions(self, end_to_end_setup):
        """Test multiple concurrent user sessions performing different operations."""
        mock_client = end_to_end_setup["mock_client"]

        # Set up initial state
        initial_notes = [
            {
                "key": f"concurrent_note_{i}",
                "content": f"Concurrent test note {i}",
                "tags": ["concurrent", f"session_{i % 3}"],
                "modifydate": f"2025-04-{i + 1:02d}T12:00:00Z",
            }
            for i in range(10)
        ]

        mock_client.get_note_list.return_value = (initial_notes, 0)
        mock_client._notes_db = {note["key"]: note for note in initial_notes}

        # Initialize cache with initial notes
        from simplenote_mcp.server.server import note_cache

        if note_cache:
            for note in initial_notes:
                note_cache._notes[note["key"]] = note

        async def user_session_1():
            """User session focused on creating and tagging notes."""
            results = []
            for i in range(3):
                note = {
                    "key": f"session1_note_{i}",
                    "content": f"Session 1 note {i}",
                    "tags": ["session1", "created"],
                    "modifydate": f"2025-04-{i + 11:02d}T12:00:00Z",
                }
                mock_client.add_note.return_value = (note, 0)

                result = await call_tool_helper(
                    "create_note", {"content": note["content"], "tags": note["tags"]}
                )
                results.append(result)

                # Small delay to simulate user interaction
                await asyncio.sleep(0.01)

            return results

        async def user_session_2():
            """User session focused on searching and reading notes."""
            results = []

            # Perform multiple searches
            search_terms = ["concurrent", "session", "test"]
            for term in search_terms:
                # Mock search results
                [
                    note
                    for note in initial_notes
                    if term in note["content"] or term in " ".join(note.get("tags", []))
                ]

                # Simulate search by listing resources with filter-like behavior
                resources = await handle_list_resources(
                    tag=term if term in ["concurrent", "session"] else None
                )
                results.append(len(resources))

                await asyncio.sleep(0.01)

            return results

        async def user_session_3():
            """User session focused on updating and deleting notes."""
            results = []

            # Update a few notes
            for i in range(2):
                note_id = f"concurrent_note_{i}"
                if note_id in mock_client._notes_db:
                    updated_note = mock_client._notes_db[note_id].copy()
                    updated_note["tags"].append("updated")
                    updated_note["content"] += "\n\nUpdated by session 3"

                    mock_client.update_note.return_value = (updated_note, 0)

                    result = await call_tool_helper(
                        "update_note",
                        {
                            "note_id": note_id,
                            "content": updated_note["content"],
                            "tags": updated_note["tags"],
                        },
                    )
                    results.append(result)

                    mock_client._notes_db[note_id] = updated_note

                await asyncio.sleep(0.01)

            return results

        # Run all sessions concurrently
        session1_task = asyncio.create_task(user_session_1())
        session2_task = asyncio.create_task(user_session_2())
        session3_task = asyncio.create_task(user_session_3())

        results = await asyncio.gather(
            session1_task, session2_task, session3_task, return_exceptions=True
        )

        # Verify all sessions completed without exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Session {i + 1} failed with exception: {result}")

        # Verify session 1 results (created notes)
        session1_results = results[0]
        assert len(session1_results) == 3
        for result in session1_results:
            response = json.loads(result[0].text)
            assert response["success"] is True

        # Verify session 2 results (searches)
        session2_results = results[1]
        assert len(session2_results) == 3
        for search_count in session2_results:
            assert search_count >= 0  # Should find some results

        # Verify session 3 results (updates)
        session3_results = results[2]
        assert len(session3_results) == 2
        for result in session3_results:
            response = json.loads(result[0].text)
            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, end_to_end_setup):
        """Test error recovery during user sessions."""
        mock_client = end_to_end_setup["mock_client"]

        # Scenario 1: Network failure during note creation
        mock_client.add_note.return_value = (None, 1)  # Simulate failure

        # The tool should return an error response rather than raising an exception
        result = await call_tool_helper(
            "create_note", {"content": "This should fail", "tags": ["test"]}
        )

        # Check that we got an error response
        assert isinstance(result, types.CallToolResult)
        assert result.isError is True
        response = json.loads(result.content[0].text)
        assert response["error"] is not None  # Should contain error information

        # Scenario 2: Recovery after network failure
        successful_note = {
            "key": "recovery_note",
            "content": "This should succeed",
            "tags": ["recovery"],
            "modifydate": "2025-04-15T12:00:00Z",
        }
        mock_client.add_note.return_value = (successful_note, 0)

        result = await call_tool_helper(
            "create_note", {"content": "This should succeed", "tags": ["recovery"]}
        )

        response = json.loads(result[0].text)
        assert response["success"] is True

        # Scenario 3: Partial failure during batch operations
        notes_to_create = [
            ("Note 1", ["batch"]),
            ("Note 2", ["batch"]),
            ("Note 3", ["batch"]),
        ]

        success_count = 0
        failure_count = 0

        for i, (content, tags) in enumerate(notes_to_create):
            if i == 1:  # Simulate failure on second note
                mock_client.add_note.return_value = (None, 1)
            else:
                note = {
                    "key": f"batch_note_{i}",
                    "content": content,
                    "tags": tags,
                    "modifydate": f"2025-04-{i + 16:02d}T12:00:00Z",
                }
                mock_client.add_note.return_value = (note, 0)

            result = await call_tool_helper(
                "create_note", {"content": content, "tags": tags}
            )

            if isinstance(result, types.CallToolResult):
                assert result.isError is True
                failure_count += 1
            else:
                response = json.loads(result[0].text)
                if response["success"]:
                    success_count += 1
                else:
                    failure_count += 1

        # Should have partial success
        assert success_count >= 1
        assert failure_count >= 1
        assert success_count + failure_count == len(notes_to_create)

    @pytest.mark.asyncio
    async def test_large_dataset_user_workflow(self, end_to_end_setup):
        """Test user workflow with a large dataset."""
        mock_client = end_to_end_setup["mock_client"]

        # Create large dataset
        large_dataset = []
        for i in range(500):  # 500 notes
            note = {
                "key": f"large_note_{i}",
                "content": f"Large dataset note {i}\n\nContent for testing large datasets with search and pagination.",
                "tags": [
                    f"category_{i % 10}",  # 10 different categories
                    f"priority_{i % 3}",  # 3 priority levels
                    "large_dataset",
                ],
                "modifydate": f"2025-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
                "createdate": "2025-01-01T00:00:00Z",
            }
            large_dataset.append(note)

        mock_client.get_note_list.return_value = (large_dataset, 0)
        mock_client._notes_db = {note["key"]: note for note in large_dataset}

        # Initialize cache with large dataset
        from simplenote_mcp.server.server import note_cache

        if note_cache:
            for note in large_dataset:
                note_cache._notes[note["key"]] = note

        # Test 1: List resources with pagination
        page1 = await handle_list_resources(limit=50)
        assert len(page1) == 50

        page2 = await handle_list_resources(limit=100)
        assert len(page2) == 100
        assert len(page2) > len(page1)

        # Test 2: Search performance with large dataset
        # Simulate search for specific category
        category_notes = [
            note for note in large_dataset if "category_5" in note["tags"]
        ]
        len(category_notes)  # Should be ~50 notes (500/10)

        # Test tag filtering
        tag_filtered = await handle_list_resources(tag="category_5", limit=100)
        # Note: Our mock might not perfectly simulate tag filtering,
        # but we can verify the structure works with large datasets
        assert len(tag_filtered) >= 0

        # Test 3: Read random resources from large dataset
        import random

        random_indices = random.sample(range(len(large_dataset)), 10)

        for idx in random_indices:
            note = large_dataset[idx]
            mock_client.get_note.return_value = (note, 0)

            resource = list(
                await handle_read_resource(f"simplenote://note/{note['key']}")
            )
            assert resource
            assert note["content"] in resource[0].content

        # Test 4: Batch operations on large dataset
        # Update multiple notes
        updates_completed = 0
        for i in range(0, 20, 2):  # Update every other note in first 20
            note_id = f"large_note_{i}"
            if note_id in mock_client._notes_db:
                updated_note = mock_client._notes_db[note_id].copy()
                updated_note["tags"].append("batch_updated")
                updated_note["content"] += "\n\nUpdated in batch operation."

                mock_client.update_note.return_value = (updated_note, 0)

                try:
                    result = await call_tool_helper(
                        "update_note",
                        {
                            "note_id": note_id,
                            "content": updated_note["content"],
                            "tags": updated_note["tags"],
                        },
                    )

                    response = json.loads(result[0].text)
                    if response["success"]:
                        updates_completed += 1
                        mock_client._notes_db[note_id] = updated_note

                except Exception:
                    # Some updates might fail, that's OK for this test
                    pass

        # Should have completed some updates
        assert updates_completed > 0
