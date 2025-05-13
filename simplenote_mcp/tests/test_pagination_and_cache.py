#!/usr/bin/env python
"""
Tests for pagination features and cache performance.

This test suite verifies the pagination functionality and measures
the performance improvements from the optimized cache implementation.
"""

import asyncio
import os
import sys
import time

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Set project root path as a string for system path
PROJECT_ROOT_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_PATH))

from simplenote_mcp.server import get_simplenote_client
from simplenote_mcp.server.cache import NoteCache
from simplenote_mcp.server.logging import get_logger

# Set up logger
logger = get_logger(__name__)


class PerformanceTest:
    """Class for measuring and reporting performance metrics."""

    def __init__(self, name: str):
        """Initialize the performance test.

        Args:
            name: The name of the test
        """
        self.name = name
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0

    def start(self) -> None:
        """Start the performance timer."""
        self.start_time = time.time()

    def stop(self) -> None:
        """Stop the performance timer."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def report(self) -> None:
        """Print the performance report."""
        print(f"{self.name}: {self.duration:.4f} seconds")

    def __enter__(self):
        """Start timer when entering context."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer when exiting context."""
        self.stop()
        self.report()


async def test_pagination_get_all_notes(cache: NoteCache) -> bool:
    """Test pagination with get_all_notes.

    Args:
        cache: Initialized NoteCache instance

    Returns:
        True if test passes, False otherwise
    """
    print("\nTesting pagination with get_all_notes...")
    try:
        # Get total notes count
        total_notes = cache.notes_count
        print(f"Total notes in cache: {total_notes}")

        # Set page size
        page_size = 10

        # Calculate number of pages
        total_pages = (total_notes + page_size - 1) // page_size
        print(
            f"Testing pagination with page size {page_size} ({total_pages} pages total)"
        )

        # Retrieve and verify first page
        with PerformanceTest("Retrieve first page"):
            page1 = cache.get_all_notes(limit=page_size, offset=0)

        assert len(page1) <= page_size, (
            f"Page 1 should have at most {page_size} notes, got {len(page1)}"
        )

        # Retrieve and verify second page
        with PerformanceTest("Retrieve second page"):
            page2 = cache.get_all_notes(limit=page_size, offset=page_size)

        assert len(page2) <= page_size, (
            f"Page 2 should have at most {page_size} notes, got {len(page2)}"
        )

        # Verify pages don't overlap
        if len(page1) > 0 and len(page2) > 0:
            page1_ids = {note.get("key") for note in page1}
            page2_ids = {note.get("key") for note in page2}
            overlap = page1_ids.intersection(page2_ids)
            assert len(overlap) == 0, (
                f"Pages should not overlap, found {len(overlap)} common notes"
            )

        # Test sorting
        print("\nTesting sorting...")

        # Sort by modification date descending (newest first)
        with PerformanceTest("Sort by modifydate desc"):
            newest_notes = cache.get_all_notes(
                limit=5, sort_by="modifydate", sort_direction="desc"
            )

        # Sort by modification date ascending (oldest first)
        with PerformanceTest("Sort by modifydate asc"):
            oldest_notes = cache.get_all_notes(
                limit=5, sort_by="modifydate", sort_direction="asc"
            )

        if newest_notes and oldest_notes:
            newest_date = newest_notes[0].get("modifydate", 0)
            oldest_date = oldest_notes[0].get("modifydate", 0)
            assert newest_date >= oldest_date, (
                "Sorting by date failed: newest should be >= oldest"
            )

        # Get pagination metadata
        if total_notes > 0:
            pagination = cache.get_pagination_info(total_notes, page_size, 0)
            assert pagination["total"] == total_notes
            assert pagination["limit"] == page_size
            assert pagination["offset"] == 0
            assert pagination["has_more"] == (total_notes > page_size)
            assert pagination["page"] == 1
            assert pagination["total_pages"] == total_pages

            if total_notes > page_size:
                assert pagination["next_offset"] == page_size
                assert (
                    pagination["prev_offset"] == 0
                )  # First page should have prev_offset=0

        return True
    except Exception as e:
        print(f"Error during pagination test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_pagination_search_notes(cache: NoteCache) -> bool:
    """Test pagination with search_notes.

    Args:
        cache: Initialized NoteCache instance

    Returns:
        True if test passes, False otherwise
    """
    print("\nTesting pagination with search_notes...")
    try:
        # Use a generic query that should match multiple notes
        query = "the"  # Common word that should appear in many notes

        # First run the search to get total results
        with PerformanceTest("Initial search"):
            all_results = cache.search_notes(query=query)

        total_results = len(all_results)
        print(f"Found {total_results} notes matching '{query}'")

        if total_results < 2:
            print("Not enough matching notes for pagination test, skipping")
            return True

        # Set page size
        page_size = min(5, total_results // 2)

        # Calculate number of pages
        total_pages = (total_results + page_size - 1) // page_size

        # Test pagination
        print(f"Testing search pagination with page size {page_size}")

        # Get first page
        with PerformanceTest("Search page 1"):
            page1 = cache.search_notes(query=query, limit=page_size, offset=0)

        assert len(page1) <= page_size, (
            f"Page 1 should have at most {page_size} notes, got {len(page1)}"
        )

        # Get second page
        with PerformanceTest("Search page 2"):
            page2 = cache.search_notes(query=query, limit=page_size, offset=page_size)

        assert len(page2) <= page_size, (
            f"Page 2 should have at most {page_size} notes, got {len(page2)}"
        )

        # Verify pages don't overlap
        page1_ids = {note.get("key") for note in page1}
        page2_ids = {note.get("key") for note in page2}
        overlap = page1_ids.intersection(page2_ids)
        assert len(overlap) == 0, (
            f"Pages should not overlap, found {len(overlap)} common notes"
        )

        return True
    except Exception as e:
        print(f"Error during search pagination test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_cache_performance(cache: NoteCache) -> bool:
    """Test cache performance with repeated searches.

    Args:
        cache: Initialized NoteCache instance

    Returns:
        True if test passes, False otherwise
    """
    print("\nTesting cache performance with repeated searches...")
    try:
        # Use a specific query that should be consistent
        query = "test"

        # First search - should be uncached
        with PerformanceTest("First search (uncached)"):
            results1 = cache.search_notes(query=query)

        # Second search with same query - should use cache
        with PerformanceTest("Second search (cached)"):
            results2 = cache.search_notes(query=query)

        # Third search with same query - should also use cache
        with PerformanceTest("Third search (cached)"):
            results3 = cache.search_notes(query=query)

        # Verify results consistency
        assert len(results1) == len(results2) == len(results3), (
            "Search results count should be consistent"
        )

        # Test with tag filtering
        print("\nTesting tag index performance...")
        tags = list(cache.all_tags)

        if tags:
            test_tag = tags[0]
            print(f"Testing tag filtering with tag '{test_tag}'")

            # First search with tag - should build index
            with PerformanceTest("First tag filter"):
                results_tag1 = cache.get_all_notes(tag_filter=test_tag)

            # Second search with same tag - should use index
            with PerformanceTest("Second tag filter (using index)"):
                results_tag2 = cache.get_all_notes(tag_filter=test_tag)

            # Verify results consistency
            assert len(results_tag1) == len(results_tag2), (
                "Tag filter results should be consistent"
            )

        return True
    except Exception as e:
        print(f"Error during cache performance test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_tag_index_performance(cache: NoteCache) -> bool:
    """Test tag index performance improvements.

    Args:
        cache: Initialized NoteCache instance

    Returns:
        True if test passes, False otherwise
    """
    print("\nTesting tag index performance...")
    try:
        # Get all available tags
        tags = list(cache.all_tags)

        if not tags:
            print("No tags available for testing")
            return True

        selected_tag = tags[0]
        print(f"Testing with tag: {selected_tag}")

        # Test tag filtering via search with tag_filters parameter
        with PerformanceTest("Search with tag filter"):
            tag_results1 = cache.search_notes(query="", tag_filters=[selected_tag])

        print(f"Found {len(tag_results1)} notes with tag '{selected_tag}'")

        # Test tag filtering via get_all_notes with tag_filter parameter
        with PerformanceTest("Get all notes with tag filter"):
            tag_results2 = cache.get_all_notes(tag_filter=selected_tag)

        print(
            f"Found {len(tag_results2)} notes with tag '{selected_tag}' via get_all_notes"
        )

        # Results should have the same count
        assert len(tag_results1) == len(tag_results2), (
            "Tag filtering should give consistent results"
        )

        return True
    except Exception as e:
        print(f"Error during tag index test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_query_cache(cache: NoteCache) -> bool:
    """Test query cache performance.

    Args:
        cache: Initialized NoteCache instance

    Returns:
        True if test passes, False otherwise
    """
    print("\nTesting query cache performance...")
    try:
        # Run a complex query multiple times
        complex_query = "project AND meeting"

        # First run - uncached
        print("Running complex query first time (uncached)...")
        with PerformanceTest("Complex query (uncached)"):
            results1 = cache.search_notes(query=complex_query)

        # Second run - should use cached result
        print("Running same query again (should use cache)...")
        with PerformanceTest("Complex query (cached)"):
            results2 = cache.search_notes(query=complex_query)

        # Third run with pagination - should use cached result but apply pagination
        print("Running same query with pagination...")
        with PerformanceTest("Complex query with pagination (cached)"):
            results3 = cache.search_notes(query=complex_query, limit=5, offset=0)

        # Results should be consistent
        assert len(results1) == len(results2), (
            "Cached query should return same number of results"
        )

        if len(results1) > 5:
            assert len(results3) == 5, "Paginated results should respect limit"

        return True
    except Exception as e:
        print(f"Error during query cache test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> bool:
    """Run all pagination and cache performance tests.

    Returns:
        True if all tests pass, False otherwise
    """
    print("=" * 70)
    print("SIMPLENOTE MCP SERVER PAGINATION AND CACHE PERFORMANCE TESTS")
    print("=" * 70)

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

    try:
        # Get the Simplenote client
        client = get_simplenote_client()
        if not client:
            print("Failed to get Simplenote client")
            return False

        # Create a cache
        cache = NoteCache(client)

        # Initialize cache
        print("\nInitializing cache (this might take a while)...")
        with PerformanceTest("Cache initialization"):
            await cache.initialize()

        print(
            f"Cache initialized with {cache.notes_count} notes and {cache.tags_count} unique tags"
        )

        # Run tests
        tests = [
            (
                "Pagination with get_all_notes",
                await test_pagination_get_all_notes(cache),
            ),
            ("Pagination with search_notes", await test_pagination_search_notes(cache)),
            (
                "Cache performance with repeated searches",
                await test_cache_performance(cache),
            ),
            ("Tag index performance", await test_tag_index_performance(cache)),
            ("Query cache performance", await test_query_cache(cache)),
        ]

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

    except Exception as e:
        print(f"Error during test execution: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
