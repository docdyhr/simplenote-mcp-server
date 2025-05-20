#!/usr/bin/env python
"""
Benchmark script for comparing cache performance.

This script measures performance of different cache operations
and compares the optimized cache with different configurations.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Import project modules
from simplenote_mcp.server import get_simplenote_client  # noqa: E402
from simplenote_mcp.server.cache import NoteCache  # noqa: E402
from simplenote_mcp.server.logging import get_logger, initialize_logging  # noqa: E402

# Configure logging
initialize_logging()
logger = get_logger(__name__)

# Set output colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
ENDC = "\033[0m"
BOLD = "\033[1m"


class BenchmarkResult:
    """Class for storing benchmark results."""

    def __init__(self, name: str, description: str = ""):
        """Initialize the benchmark result.

        Args:
            name: Name of the benchmark
            description: Optional description
        """
        self.name = name
        self.description = description
        self.timings: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {}
        self.start_time = datetime.now()

    def add_timing(self, operation: str, seconds: float) -> None:
        """Add a timing measurement.

        Args:
            operation: Name of the operation
            seconds: Time in seconds
        """
        self.timings[operation] = seconds

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata about the benchmark.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation of the result
        """
        return {
            "name": self.name,
            "description": self.description,
            "timestamp": self.start_time.isoformat(),
            "timings": self.timings,
            "metadata": self.metadata,
        }

    def save_to_file(self, filename: str) -> None:
        """Save results to a JSON file.

        Args:
            filename: Path to output file
        """
        with open(filename, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class Timer:
    """Context manager for timing operations."""

    def __init__(self, name: str, result: BenchmarkResult):
        """Initialize the timer.

        Args:
            name: Name of the operation being timed
            result: BenchmarkResult to store the timing in
        """
        self.name = name
        self.result = result
        self.start_time = 0.0

    def __enter__(self):
        """Start the timer when entering the context."""
        print(f"{BLUE}Starting: {self.name}{ENDC}")
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer when exiting the context."""
        duration = time.time() - self.start_time
        self.result.add_timing(self.name, duration)
        print(f"{GREEN}Completed: {self.name} in {duration:.4f} seconds{ENDC}")


async def benchmark_initialization(client, result: BenchmarkResult) -> NoteCache:
    """Benchmark cache initialization performance.

    Args:
        client: Simplenote client
        result: BenchmarkResult to store timings

    Returns:
        Initialized NoteCache
    """
    print(f"\n{BOLD}Benchmarking cache initialization...{ENDC}")

    # Create cache
    cache = NoteCache(client)

    # Initialize cache and time it
    with Timer("cache_initialization", result):
        note_count = await cache.initialize()

    # Record metadata
    result.add_metadata("note_count", note_count)
    result.add_metadata("tag_count", cache.tags_count)

    return cache


async def benchmark_tag_filtering(cache: NoteCache, result: BenchmarkResult) -> None:
    """Benchmark tag filtering performance.

    Args:
        cache: Initialized cache
        result: BenchmarkResult to store timings
    """
    print(f"\n{BOLD}Benchmarking tag filtering...{ENDC}")

    # Get all available tags
    all_tags = list(cache.all_tags)

    if not all_tags:
        print(f"{YELLOW}No tags available for testing{ENDC}")
        return

    # Select a tag for testing
    test_tag = all_tags[0]
    result.add_metadata("test_tag", test_tag)

    # First filtering - index might need to be built
    with Timer("tag_filter_first", result):
        notes_with_tag = cache.get_all_notes(tag_filter=test_tag)

    # Second filtering - should use index
    with Timer("tag_filter_second", result):
        cache.get_all_notes(tag_filter=test_tag)

    # Record how many notes have this tag
    result.add_metadata("notes_with_tag", len(notes_with_tag))


async def benchmark_search(cache: NoteCache, result: BenchmarkResult) -> None:
    """Benchmark search performance.

    Args:
        cache: Initialized cache
        result: BenchmarkResult to store timings
    """
    print(f"\n{BOLD}Benchmarking search performance...{ENDC}")

    # Test with a simple term likely to be found in most notes
    simple_query = "the"

    # Test with a more complex query using boolean operators
    complex_query = "project AND meeting"

    # First search - simple query
    with Timer("search_simple_first", result):
        simple_results = cache.search_notes(query=simple_query)

    # Second search - simple query, should use cache
    with Timer("search_simple_second", result):
        cache.search_notes(query=simple_query)

    # First search - complex query
    with Timer("search_complex_first", result):
        complex_results = cache.search_notes(query=complex_query)

    # Second search - complex query, should use cache
    with Timer("search_complex_second", result):
        cache.search_notes(query=complex_query)

    # Record result counts
    result.add_metadata("simple_query_results", len(simple_results))
    result.add_metadata("complex_query_results", len(complex_results))

    # Test search with tag filters
    tags = list(cache.all_tags)
    if tags:
        test_tag = tags[0]
        with Timer("search_with_tag_filter", result):
            tag_search_results = cache.search_notes(
                query=simple_query, tag_filters=[test_tag]
            )

        result.add_metadata("tag_search_results", len(tag_search_results))


async def benchmark_pagination(cache: NoteCache, result: BenchmarkResult) -> None:
    """Benchmark pagination performance.

    Args:
        cache: Initialized cache
        result: BenchmarkResult to store timings
    """
    print(f"\n{BOLD}Benchmarking pagination performance...{ENDC}")

    total_notes = cache.notes_count
    page_size = 10

    # Get first page of all notes
    with Timer("pagination_all_notes_page1", result):
        cache.get_all_notes(limit=page_size, offset=0)

    # Get second page of all notes
    with Timer("pagination_all_notes_page2", result):
        cache.get_all_notes(limit=page_size, offset=page_size)

    # Get last page of all notes
    last_page_offset = (total_notes // page_size) * page_size
    with Timer("pagination_all_notes_last_page", result):
        cache.get_all_notes(limit=page_size, offset=last_page_offset)

    # Search with pagination
    query = "the"  # Common word likely to give results

    # Get first page of search results
    with Timer("pagination_search_page1", result):
        search_page1 = cache.search_notes(query=query, limit=page_size, offset=0)

    # Get second page of search results
    with Timer("pagination_search_page2", result):
        search_page2 = cache.search_notes(
            query=query, limit=page_size, offset=page_size
        )

    # Record metadata
    result.add_metadata("pagination_size", page_size)
    result.add_metadata("search_results_page1", len(search_page1))
    result.add_metadata("search_results_page2", len(search_page2))


async def benchmark_sorting(cache: NoteCache, result: BenchmarkResult) -> None:
    """Benchmark sort performance.

    Args:
        cache: Initialized cache
        result: BenchmarkResult to store timings
    """
    print(f"\n{BOLD}Benchmarking sort performance...{ENDC}")

    # Sort by modification date descending (newest first)
    with Timer("sort_by_modifydate_desc", result):
        cache.get_all_notes(sort_by="modifydate", sort_direction="desc")

    # Sort by modification date ascending (oldest first)
    with Timer("sort_by_modifydate_asc", result):
        cache.get_all_notes(sort_by="modifydate", sort_direction="asc")

    # Sort by title
    with Timer("sort_by_title", result):
        cache.get_all_notes(sort_by="title", sort_direction="asc")


async def run_benchmarks() -> None:
    """Run all benchmarks and save results."""
    print(f"\n{BOLD}{GREEN}SIMPLENOTE MCP SERVER CACHE BENCHMARK{ENDC}")
    print("=" * 60)

    # Check environment variables
    username = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get(
        "SIMPLENOTE_USERNAME"
    )
    password = os.environ.get("SIMPLENOTE_PASSWORD")

    if not username or not password:
        print(f"{RED}ERROR: Missing environment variables.{ENDC}")
        print("Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD.")
        return

    print(f"Using credentials for: {username[:3]}***")

    try:
        # Create benchmark result
        result = BenchmarkResult(
            "cache_optimization_benchmark", "Benchmark of optimized cache performance"
        )

        # Get the Simplenote client
        client = get_simplenote_client()
        if not client:
            print(f"{RED}Failed to get Simplenote client{ENDC}")
            return

        # Run benchmarks
        cache = await benchmark_initialization(client, result)
        await benchmark_tag_filtering(cache, result)
        await benchmark_search(cache, result)
        await benchmark_pagination(cache, result)
        await benchmark_sorting(cache, result)

        # Calculate cache hit rates
        cache_hit_rate = result.timings.get(
            "search_simple_first", 0
        ) / result.timings.get("search_simple_second", 1)
        result.add_metadata("cache_hit_speedup", cache_hit_rate)

        # Calculate pagination efficiency
        page1_time = result.timings.get("pagination_all_notes_page1", 0)
        page2_time = result.timings.get("pagination_all_notes_page2", 0)
        pagination_efficiency = page1_time / page2_time if page2_time > 0 else 1.0
        result.add_metadata("pagination_efficiency", pagination_efficiency)

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"cache_benchmark_{timestamp}.json"
        result.save_to_file(output_file)

        print(f"\n{GREEN}Benchmark completed! Results saved to {output_file}{ENDC}")

        # Print summary
        print("\nPERFORMANCE SUMMARY:")
        print("=" * 60)
        for op, time_value in result.timings.items():
            print(f"{op}: {time_value:.4f}s")

        # Print important metrics
        if (
            "search_simple_first" in result.timings
            and "search_simple_second" in result.timings
        ):
            first_search = result.timings["search_simple_first"]
            second_search = result.timings["search_simple_second"]
            speedup = first_search / second_search if second_search > 0 else 0
            print(f"\n{BOLD}Query cache speedup: {speedup:.2f}x{ENDC}")

        print(f"{BOLD}Total notes: {result.metadata.get('note_count', 0)}{ENDC}")

    except Exception as e:
        print(f"{RED}Error during benchmark: {e}{ENDC}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
