#!/usr/bin/env python
# test_search.py - Test script for the Simplenote MCP server search functionality

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import the server module
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simplenote_mcp.server import get_simplenote_client  # noqa: E402
from simplenote_mcp.server.cache import NoteCache  # noqa: E402
from simplenote_mcp.server.search.engine import SearchEngine  # noqa: E402


async def test_direct_search(query="markdown"):
    """Test searching using the SearchEngine directly."""
    print(f"\nTesting direct search for '{query}'...")
    try:
        # Get the client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return False

        # Get notes directly from Simplenote API
        notes, status = client.get_note_list()
        if status != 0:
            print(f"Failed to get notes from Simplenote API (status: {status})")
            return False

        print(f"Retrieved {len(notes)} notes from Simplenote API")

        # Convert to the format expected by SearchEngine
        notes_dict = {note['key']: note for note in notes}

        # Create search engine
        engine = SearchEngine()

        # Perform search
        results = engine.search(notes_dict, query=query)

        # Print results
        print(f"Found {len(results)} notes containing '{query}'")
        for i, note in enumerate(results[:5]):  # Show first 5 results
            title = note.get('content', '').splitlines()[0][:50]
            note_id = note.get('key', 'unknown')
            print(f"{i+1}. {title}... (ID: {note_id})")

        return len(results) > 0
    except Exception as e:
        print(f"Error during search: {e}")
        return False

async def test_cache_search(query="markdown"):
    """Test searching using the NoteCache."""
    print(f"\nTesting cache-based search for '{query}'...")
    try:
        # Get the client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return False

        # Create a cache
        cache = NoteCache(client)

        # Initialize cache (this might take a while for first run)
        print("Initializing cache (this might take a while)...")
        await cache.initialize()

        # Search for the query
        results = cache.search_notes(query=query)

        # Print results
        print(f"Found {len(results)} notes containing '{query}'")
        for i, note in enumerate(results[:5]):  # Show first 5 results
            title = note.get('content', '').splitlines()[0][:50]
            note_id = note.get('key', 'unknown')
            print(f"{i+1}. {title}... (ID: {note_id})")

        return len(results) > 0
    except Exception as e:
        print(f"Error during cache search: {e}")
        return False

async def main():
    """Run the tests."""
    print("=" * 50)
    print("SIMPLENOTE MCP SERVER SEARCH TEST")
    print("=" * 50)

    # Check environment variables
    username = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get("SIMPLENOTE_USERNAME")
    password = os.environ.get("SIMPLENOTE_PASSWORD")

    if not username or not password:
        print("ERROR: Missing environment variables.")
        print("Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD.")
        return False

    print(f"Using credentials for: {username[:3]}***")

    # Get the search query from command-line arguments
    query = sys.argv[1] if len(sys.argv) > 1 else "markdown"

    # Run tests
    tests = [
        ("Direct search", await test_direct_search(query)),
        ("Cache-based search", await test_cache_search(query)),
    ]

    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, result in tests:
        status = "PASSED" if result else "FAILED"
        status_colored = f"\033[92m{status}\033[0m" if result else f"\033[91m{status}\033[0m"
        print(f"{name}: {status_colored}")
        all_passed = all_passed and result

    print("\nOverall status:", "PASSED" if all_passed else "FAILED")
    return all_passed

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
