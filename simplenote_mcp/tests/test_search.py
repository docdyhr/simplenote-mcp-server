#!/usr/bin/env python
# test_search.py - Test script for the Simplenote MCP server search functionality

import asyncio
import os
import sys
import time

# Add the parent directory to the Python path so we can import the server module
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Set project root path as a string for system path
PROJECT_ROOT_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_PATH))

from simplenote_mcp.server import get_simplenote_client  # noqa: E402
from simplenote_mcp.server.cache import NoteCache  # noqa: E402
from simplenote_mcp.server.search.engine import SearchEngine  # noqa: E402


class PerformanceTimer:
    """Simple timer for performance measurements."""

    def __init__(self):
        self.start_time = 0
        self.end_time = 0

    def start(self):
        """Start the timer."""
        self.start_time = time.time()

    def stop(self):
        """Stop the timer and return elapsed time."""
        self.end_time = time.time()
        return self.end_time - self.start_time


async def test_direct_search(query: str = "markdown") -> dict:
    """Test searching using the SearchEngine directly.

    Returns:
        Dictionary with search results and performance metrics.
    """
    print(f"\nTesting direct search for '{query}'...")
    timer = PerformanceTimer()

    try:
        # Get the client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return {"success": False, "time": 0, "count": 0}

        # Start timing API and search operations
        timer.start()

        # Get notes directly from Simplenote API
        notes, status = client.get_note_list()
        if status != 0:
            print(f"Failed to get notes from Simplenote API (status: {status})")
            return {"success": False, "time": 0, "count": 0}

        api_time = timer.stop()
        print(
            f"Retrieved {len(notes)} notes from Simplenote API in {api_time:.4f} seconds"
        )

        # Convert to the format expected by SearchEngine
        notes_dict = {note["key"]: note for note in notes}

        # Create search engine
        engine = SearchEngine()

        # Perform search with timing
        timer.start()
        results = engine.search(notes_dict, query=query)
        search_time = timer.stop()

        # Print results
        print(
            f"Found {len(results)} notes containing '{query}' in {search_time:.4f} seconds"
        )
        for i, note in enumerate(results[:5]):  # Show first 5 results
            title = note.get("content", "").splitlines()[0][:50]
            note_id = note.get("key", "unknown")
            print(f"{i + 1}. {title}... (ID: {note_id})")

        # Total time for the operation
        total_time = api_time + search_time
        print(
            f"Total time: {total_time:.4f} seconds (API: {api_time:.4f}s, Search: {search_time:.4f}s)"
        )

        return {
            "success": len(results) > 0,
            "time": total_time,
            "api_time": api_time,
            "search_time": search_time,
            "count": len(results),
        }
    except Exception as e:
        print(f"Error during search: {e}")
        return {"success": False, "time": 0, "count": 0}


async def test_cache_search(query: str = "markdown") -> dict:
    """Test searching using the NoteCache.

    Returns:
        Dictionary with search results and performance metrics.
    """
    print(f"\nTesting cache-based search for '{query}'...")
    timer = PerformanceTimer()

    try:
        # Get the client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return {"success": False, "time": 0, "count": 0}

        # Create a cache
        cache = NoteCache(client)

        # Initialize cache (this might take a while for first run)
        print("Initializing cache (this might take a while)...")
        timer.start()
        await cache.initialize()
        init_time = timer.stop()
        print(
            f"Cache initialized in {init_time:.4f} seconds with {len(cache._notes)} notes"
        )

        # First search - should be uncached
        print("\nRunning first search (uncached)...")
        timer.start()
        results1 = cache.search_notes(query=query)
        first_search_time = timer.stop()
        print(f"First search completed in {first_search_time:.4f} seconds")

        # Second search - should use cache
        print("\nRunning second search (should use cache)...")
        timer.start()
        results2 = cache.search_notes(query=query)
        second_search_time = timer.stop()
        print(f"Second search completed in {second_search_time:.4f} seconds")

        # Calculate speed improvement
        if first_search_time > 0:
            speedup = first_search_time / second_search_time
            print(f"Cache speedup factor: {speedup:.2f}x faster")

        # Print results
        print(f"Found {len(results2)} notes containing '{query}'")
        for i, note in enumerate(results2[:5]):  # Show first 5 results
            title = note.get("content", "").splitlines()[0][:50]
            note_id = note.get("key", "unknown")
            print(f"{i + 1}. {title}... (ID: {note_id})")

        return {
            "success": len(results2) > 0,
            "time": second_search_time,
            "init_time": init_time,
            "first_search_time": first_search_time,
            "second_search_time": second_search_time,
            "speedup": speedup if first_search_time > 0 else 0,
            "count": len(results2),
        }
    except Exception as e:
        print(f"Error during cache search: {e}")
        return {"success": False, "time": 0, "count": 0}


async def test_cached_pagination(query: str = "the") -> dict:
    """Test pagination with cached search results."""
    print(f"\nTesting pagination with cached search results for '{query}'...")
    timer = PerformanceTimer()

    try:
        # Get the client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return {"success": False}

        # Create a cache
        cache = NoteCache(client)

        # Initialize cache
        print("Initializing cache...")
        await cache.initialize()

        # Get total results first
        print("Getting total results...")
        all_results = cache.search_notes(query=query)
        total_count = len(all_results)
        print(f"Total notes matching '{query}': {total_count}")

        if total_count < 10:
            print("Not enough results for pagination test")
            return {"success": False}

        # Test pagination
        page_size = 5

        # Get first page
        print(f"\nGetting first page (offset=0, limit={page_size})...")
        timer.start()
        page1 = cache.search_notes(query=query, offset=0, limit=page_size)
        page1_time = timer.stop()
        print(f"First page retrieved in {page1_time:.4f} seconds, {len(page1)} results")

        # Get second page
        print(f"\nGetting second page (offset={page_size}, limit={page_size})...")
        timer.start()
        page2 = cache.search_notes(query=query, offset=page_size, limit=page_size)
        page2_time = timer.stop()
        print(
            f"Second page retrieved in {page2_time:.4f} seconds, {len(page2)} results"
        )

        # Verify no overlap
        page1_ids = {note.get("key") for note in page1}
        page2_ids = {note.get("key") for note in page2}
        no_overlap = len(page1_ids.intersection(page2_ids)) == 0
        print(f"Pages have no overlap: {no_overlap}")

        return {
            "success": True,
            "total": total_count,
            "page1_time": page1_time,
            "page2_time": page2_time,
            "no_overlap": no_overlap,
        }

    except Exception as e:
        print(f"Error during pagination test: {e}")
        return {"success": False}


async def main() -> bool:
    """Run the tests."""
    print("=" * 50)
    print("SIMPLENOTE MCP SERVER SEARCH TEST")
    print("=" * 50)

    # Check environment variables
    username = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get(
        "SIMPLENOTE_USERNAME"
    )
    password = os.environ.get("SIMPLENOTE_PASSWORD")

    if not username or not password:
        print("ERROR: Missing environment variables.")
        print("Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD.")
        return False

    print(f"Using credentials for: {username[:3]}***")

    # Get the search query from command-line arguments
    query = sys.argv[1] if len(sys.argv) > 1 else "markdown"

    # Run tests
    direct_result = await test_direct_search(query)
    cache_result = await test_cache_search(query)
    pagination_result = await test_cached_pagination(
        "the"
    )  # Common word for pagination test

    tests = [
        ("Direct search", direct_result["success"]),
        ("Cache-based search", cache_result["success"]),
        ("Pagination with cache", pagination_result["success"]),
    ]

    # Calculate performance comparison if both tests succeeded
    if direct_result["success"] and cache_result["success"]:
        speedup = (
            direct_result["time"] / cache_result["time"]
            if cache_result["time"] > 0
            else 0
        )
        print(f"\nPerformance comparison:")
        print(f"  Direct search: {direct_result['time']:.4f} seconds")
        print(f"  Cached search: {cache_result['time']:.4f} seconds")
        print(f"  Cache speedup: {speedup:.2f}x faster")

        # Compare cached vs uncached search within cache
        first_vs_second = (
            cache_result["first_search_time"] / cache_result["second_search_time"]
            if cache_result["second_search_time"] > 0
            else 0
        )
        print(f"\nCache internal speedup:")
        print(f"  First search: {cache_result['first_search_time']:.4f} seconds")
        print(f"  Second search: {cache_result['second_search_time']:.4f} seconds")
        print(f"  Speedup: {first_vs_second:.2f}x faster")

    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, result in tests:
        status = "PASSED" if result else "FAILED"
        status_colored = (
            f"\033[92m{status}\033[0m" if result else f"\033[91m{status}\033[0m"
        )
        print(f"{name}: {status_colored}")
        all_passed = all_passed and result

    print("\nOverall status:", "PASSED" if all_passed else "FAILED")
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
