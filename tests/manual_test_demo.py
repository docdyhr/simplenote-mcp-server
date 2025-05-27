#!/usr/bin/env python3
"""Manual test script to demonstrate Simplenote MCP server functionality.

This script demonstrates:
1. Creating notes with specific titles
2. Searching for notes by title content
3. Boolean search operations
4. Tag-based filtering
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any

from simplenote_mcp.server.server import get_simplenote_client
from simplenote_mcp.tests.test_helpers import handle_call_tool


async def create_demo_notes() -> list[dict[str, Any]]:
    """Create demonstration notes with various titles and content."""
    print("\n=== Creating Demo Notes ===")

    demo_notes = [
        {
            "content": "Project Management Guidelines\nBest practices for managing software projects effectively.\n\nKey points:\n- Clear communication\n- Regular updates\n- Risk assessment",
            "tags": ["project", "management", "guidelines"],
            "description": "Project management guide",
        },
        {
            "content": "Meeting Notes: Sprint Planning\nDate: "
            + datetime.now().strftime("%Y-%m-%d")
            + "\n\nDiscussed:\n- Sprint goals\n- Task allocation\n- Timeline",
            "tags": ["meeting", "sprint", "planning"],
            "description": "Sprint planning meeting",
        },
        {
            "content": "Technical Documentation: API Design\nREST API endpoints for user management:\n\nGET /api/users\nPOST /api/users\nPUT /api/users/:id\nDELETE /api/users/:id",
            "tags": ["technical", "api", "documentation"],
            "description": "API documentation",
        },
        {
            "content": "TODO List for This Week\n- Review project proposals\n- Update documentation\n- Prepare presentation\n- Code review",
            "tags": ["todo", "tasks", "weekly"],
            "description": "Weekly TODO list",
        },
        {
            "content": "project ideas brainstorming\nSome interesting project ideas:\n- Mobile app for habit tracking\n- Web dashboard for analytics\n- CLI tool for productivity",
            "tags": ["ideas", "brainstorming", "project"],
            "description": "Project brainstorming (lowercase title)",
        },
    ]

    created_notes = []

    for i, note_data in enumerate(demo_notes):
        print(f"\nCreating note {i + 1}/{len(demo_notes)}: {note_data['description']}")

        result = await handle_call_tool(
            "create_note", {"content": note_data["content"], "tags": note_data["tags"]}
        )

        result_data = json.loads(result[0].text)

        if "error" in result_data:
            print(f"  ❌ Error: {result_data['error']}")
            continue

        note_id = result_data.get("key") or result_data.get("note_id")
        first_line = result_data.get("first_line", "")

        print(f"  ✅ Created: {first_line}")
        print(f"  📝 Note ID: {note_id}")
        print(f"  🏷️  Tags: {', '.join(note_data['tags'])}")

        created_notes.append(
            {
                "id": note_id,
                "title": first_line,
                "tags": note_data["tags"],
                "description": note_data["description"],
            }
        )

        # Small delay between creations
        await asyncio.sleep(0.5)

    return created_notes


async def demonstrate_search_functionality(created_notes: list[dict[str, Any]]):
    """Demonstrate various search capabilities."""
    print("\n\n=== Demonstrating Search Functionality ===")

    # Wait a bit for notes to be indexed
    print("\nWaiting for notes to be indexed...")
    await asyncio.sleep(3)

    search_demos = [
        {
            "query": "Project",
            "description": "Search for all notes with 'Project' in title or content",
        },
        {"query": "project", "description": "Case-insensitive search (lowercase)"},
        {"query": "Meeting Notes", "description": "Multi-word search"},
        {"query": "TODO", "description": "Search for TODO items"},
        {
            "query": "Project AND Management",
            "description": "Boolean AND - notes with both words",
        },
        {
            "query": "Project OR API",
            "description": "Boolean OR - notes with either word",
        },
        {
            "query": "Project NOT Meeting",
            "description": "Boolean NOT - Project notes excluding meetings",
        },
        {
            "query": "Technical",
            "tags": "documentation",
            "description": "Search with tag filter",
        },
        {
            "query": ".",
            "tags": "project",
            "description": "All notes with 'project' tag",
        },
    ]

    for demo in search_demos:
        print(f"\n{'=' * 60}")
        print(f"🔍 {demo['description']}")
        print(f"Query: '{demo['query']}'")

        if "tags" in demo:
            print(f"Tag filter: {demo['tags']}")

        search_params = {"query": demo["query"]}
        if "tags" in demo:
            search_params["tags"] = demo["tags"]

        result = await handle_call_tool("search_notes", search_params)
        result_data = json.loads(result[0].text)

        if "error" in result_data:
            print(f"❌ Error: {result_data['error']}")
            continue

        results = result_data.get("results", [])
        total = result_data.get("total", len(results))

        print(f"\n📊 Found {len(results)} results (total: {total})")

        if results:
            print("\nResults:")
            for i, note in enumerate(results[:5]):  # Show first 5 results
                title = note.get("title", "No title")
                snippet = note.get("snippet", "")[:60] + "..."
                tags = note.get("tags", [])

                print(f"\n  {i + 1}. {title}")
                print(f"     {snippet}")
                if tags:
                    print(f"     Tags: {', '.join(tags)}")

        # Small delay between searches
        await asyncio.sleep(0.5)


async def cleanup_demo_notes(created_notes: list[dict[str, Any]]):
    """Clean up the demo notes."""
    print("\n\n=== Cleaning Up Demo Notes ===")

    client = get_simplenote_client()
    cleaned = 0

    for note in created_notes:
        try:
            client.trash_note(note["id"])
            cleaned += 1
            print(f"🗑️  Deleted: {note['title']}")
        except Exception as e:
            print(f"❌ Failed to delete {note['id']}: {e}")

    print(f"\n✅ Cleaned up {cleaned}/{len(created_notes)} demo notes")


async def main():
    """Main demonstration function."""
    print("🚀 Simplenote MCP Server - Search and Creation Demo")
    print("=" * 60)

    # Check if we have credentials
    try:
        client = get_simplenote_client()
        notes, status = client.get_note_list()
        if status != 0:
            print("❌ Failed to connect to Simplenote. Please check your credentials.")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease ensure SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD are set.")
        return

    print("✅ Connected to Simplenote successfully!")

    created_notes = []

    try:
        # Create demo notes
        created_notes = await create_demo_notes()

        if not created_notes:
            print("\n❌ No notes were created. Exiting.")
            return

        # Demonstrate search functionality
        await demonstrate_search_functionality(created_notes)

        # Ask if user wants to keep the notes
        print("\n" + "=" * 60)
        response = (
            input("\n🤔 Do you want to keep these demo notes? (y/N): ").strip().lower()
        )

        if response != "y":
            await cleanup_demo_notes(created_notes)
        else:
            print("\n✅ Demo notes kept in your account.")
            print("\nCreated note IDs for reference:")
            for note in created_notes:
                print(f"  - {note['id']}: {note['title']}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        if created_notes:
            print("Cleaning up created notes...")
            await cleanup_demo_notes(created_notes)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if created_notes:
            print("Attempting to clean up created notes...")
            await cleanup_demo_notes(created_notes)

    print("\n✨ Demo completed!")


if __name__ == "__main__":
    # Ensure we have the event loop for Windows compatibility
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
