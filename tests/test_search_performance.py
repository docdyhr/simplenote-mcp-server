"""Performance tests for the search functionality."""

import random
import string
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytest

from simplenote_mcp.server.search.engine import SearchEngine


def generate_random_text(min_words=50, max_words=200):
    """Generate random text with a specified number of words."""
    words = []
    word_count = random.randint(min_words, max_words)

    for _ in range(word_count):
        # Generate a random word length between 3 and 10 characters
        word_length = random.randint(3, 10)
        word = "".join(
            random.choice(string.ascii_lowercase) for _ in range(word_length)
        )
        words.append(word)

    # Insert some specific keywords for searching
    keywords = [
        "project",
        "meeting",
        "report",
        "important",
        "todo",
        "deadline",
        "client",
    ]
    for _ in range(random.randint(3, 8)):  # Insert 3-8 keywords
        position = random.randint(0, len(words) - 1)
        keyword = random.choice(keywords)
        words[position] = keyword

    return " ".join(words)


@pytest.fixture
def large_note_collection():
    """Generate a large collection of notes for performance testing."""
    notes = {}
    now = datetime.now()

    # Generate 500 notes
    for i in range(500):
        # Create a random date within the last year
        days_ago = random.randint(0, 365)
        note_date = now - timedelta(days=days_ago)

        # Select random tags
        all_tags = [
            "work",
            "personal",
            "project",
            "meeting",
            "important",
            "todo",
            "idea",
        ]
        note_tags = random.sample(all_tags, random.randint(0, 3))

        # Generate note content
        note_content = generate_random_text()

        # Create the note
        notes[f"note{i}"] = {
            "key": f"note{i}",
            "content": note_content,
            "tags": note_tags,
            "modifydate": note_date.isoformat(),
        }

    return notes


class TestSearchPerformance:
    """Test search performance with large datasets."""

    def test_simple_term_search_performance(self, large_note_collection):
        """Test performance of simple term search."""
        engine = SearchEngine()

        # Time a simple search
        start_time = time.time()
        results = engine.search(large_note_collection, "project")
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Simple search 'project' over 500 notes took {elapsed_time:.4f} seconds")
        print(f"Found {len(results)} matching notes")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 0.5, "Simple search should complete quickly"

    def test_boolean_search_performance(self, large_note_collection):
        """Test performance of boolean search expressions."""
        engine = SearchEngine()

        # Time a complex boolean search
        start_time = time.time()
        results = engine.search(
            large_note_collection, "project AND meeting AND NOT todo"
        )
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Boolean search over 500 notes took {elapsed_time:.4f} seconds")
        print(f"Found {len(results)} matching notes")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 1.0, "Boolean search should complete in reasonable time"

    def test_tag_filter_performance(self, large_note_collection):
        """Test performance of tag filtering."""
        engine = SearchEngine()

        # Time a tag filter search
        start_time = time.time()
        results = engine.search(
            large_note_collection, "", tag_filters=["work", "important"]
        )
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Tag filter search over 500 notes took {elapsed_time:.4f} seconds")
        print(f"Found {len(results)} matching notes")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 0.5, "Tag filter search should complete quickly"

    def test_date_filter_performance(self, large_note_collection):
        """Test performance of date filtering."""
        engine = SearchEngine()

        # Get dates for a 30-day period
        now = datetime.now()
        month_ago = now - timedelta(days=30)

        # Time a date filter search
        start_time = time.time()
        results = engine.search(large_note_collection, "", date_range=(month_ago, now))
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Date filter search over 500 notes took {elapsed_time:.4f} seconds")
        print(f"Found {len(results)} matching notes")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 0.5, "Date filter search should complete quickly"

    def test_complex_query_performance(self, large_note_collection):
        """Test performance of a complex query with multiple components."""
        engine = SearchEngine()

        # Get dates for a 90-day period
        now = datetime.now()
        three_months_ago = now - timedelta(days=90)

        # Time a complex search with multiple filters
        start_time = time.time()
        results = engine.search(
            large_note_collection,
            "project AND (report OR meeting) AND NOT deadline",
            tag_filters=["work"],
            date_range=(three_months_ago, now),
        )
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Complex search over 500 notes took {elapsed_time:.4f} seconds")
        print(f"Found {len(results)} matching notes")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 1.0, "Complex search should complete in reasonable time"


class TestSearchStress:
    """Stress test the search functionality with extreme cases."""

    @pytest.fixture
    def very_large_note(self):
        """Generate a very large note for stress testing."""
        # Generate a note with 10,000 words
        content = generate_random_text(min_words=10000, max_words=10000)

        return {
            "large_note": {
                "key": "large_note",
                "content": content,
                "tags": ["test", "large"],
                "modifydate": datetime.now().isoformat(),
            }
        }

    @pytest.fixture
    def many_small_notes(self):
        """Generate many small notes for stress testing."""
        notes = {}

        # Generate 1000 small notes
        for i in range(1000):
            content = generate_random_text(min_words=10, max_words=30)

            notes[f"note{i}"] = {
                "key": f"note{i}",
                "content": content,
                "tags": ["test"],
                "modifydate": datetime.now().isoformat(),
            }

        return notes

    def test_very_large_note_search(self, very_large_note):
        """Test search performance with a very large note."""
        engine = SearchEngine()

        # Time search in a very large note
        start_time = time.time()
        _ = engine.search(
            very_large_note, "project"
        )  # Result ignored; we're testing timing
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Search in a 10,000-word note took {elapsed_time:.4f} seconds")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 0.5, "Search in large note should complete quickly"

    def test_many_small_notes_search(self, many_small_notes):
        """Test search performance with many small notes."""
        engine = SearchEngine()

        # Time search across many small notes
        start_time = time.time()
        _ = engine.search(
            many_small_notes, "project"
        )  # Result ignored; we're testing timing
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Search across 1000 small notes took {elapsed_time:.4f} seconds")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 1.0, (
            "Search across many notes should complete in reasonable time"
        )

    def test_complex_query_on_many_notes(self, many_small_notes):
        """Test complex query performance on many notes."""
        engine = SearchEngine()

        # Time complex search across many notes
        start_time = time.time()
        _ = engine.search(
            many_small_notes,
            "(project OR meeting) AND (report OR todo) AND NOT deadline",
        )  # Result ignored; we're testing timing
        end_time = time.time()

        # Print performance info
        elapsed_time = end_time - start_time
        print(f"Complex search across 1000 notes took {elapsed_time:.4f} seconds")

        # Assert the search completes in a reasonable time
        assert elapsed_time < 1.5, (
            "Complex search on many notes should complete in reasonable time"
        )

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, many_small_notes):
        """Test performance with multiple concurrent searches."""
        import asyncio

        async def run_search(search_term):
            """Run a search asynchronously."""
            engine = SearchEngine()
            start_time = time.time()
            results = engine.search(many_small_notes, search_term)
            end_time = time.time()
            elapsed = end_time - start_time
            return search_term, len(results), elapsed

        # Define different search queries to run concurrently
        search_terms = [
            "project",
            "meeting",
            "report",
            "todo",
            "deadline",
            "project AND meeting",
            "report OR todo",
            "project AND NOT deadline",
        ]

        # Run searches concurrently
        overall_start = time.time()
        tasks = [run_search(term) for term in search_terms]
        results = await asyncio.gather(*tasks)
        overall_end = time.time()

        # Print performance metrics
        print("\nConcurrent search performance results:")
        print(
            f"Total time for {len(search_terms)} concurrent searches: {overall_end - overall_start:.4f} seconds"
        )

        for term, count, elapsed in results:
            print(f"  Search '{term}': found {count} results in {elapsed:.4f} seconds")

        # Calculate average time and throughput
        avg_time = sum(elapsed for _, _, elapsed in results) / len(results)
        throughput = len(results) / (overall_end - overall_start)

        print(f"Average search time: {avg_time:.4f} seconds")
        print(f"Search throughput: {throughput:.2f} searches/second")

        # Check that concurrent searches don't take too long
        assert (overall_end - overall_start) < 3.0, (
            "Concurrent searches should complete in a reasonable time"
        )

        # Individual searches should still be reasonably fast
        for _, _, elapsed in results:
            assert elapsed < 1.5, (
                "Individual concurrent searches should complete in a reasonable time"
            )

    @pytest.mark.skip(reason="Only run manually for benchmark purposes")
    def test_search_benchmark(self, many_small_notes: dict) -> None:
        """Benchmark search performance with different query types."""
        engine = SearchEngine()

        # Define a list of benchmark cases with proper typing
        benchmark_cases: List[Tuple[str, str, Optional[List[str]]]] = [
            ("Simple term", "project", None),
            ("Multiple terms", "project meeting report", None),
            ("Boolean AND", "project AND meeting", None),
            ("Boolean OR", "project OR meeting", None),
            ("Boolean NOT", "project NOT meeting", None),
            (
                "Complex boolean",
                "(project OR meeting) AND (report OR todo) AND NOT deadline",
                None,
            ),
            ("Tag filter only", "", ["work"]),
            ("Term with tag filter", "project", ["work"]),
        ]

        results: Dict[str, Dict[str, Any]] = {}

        # Run each benchmark case multiple times
        runs = 5
        for name, query, tag_filters in benchmark_cases:
            total_time: float = 0.0
            for _ in range(runs):
                start_time = time.time()
                if tag_filters:
                    _ = engine.search(
                        many_small_notes, query, tag_filters=tag_filters
                    )  # Result ignored; just timing
                else:
                    _ = engine.search(
                        many_small_notes, query
                    )  # Result ignored; just timing
                elapsed = time.time() - start_time
                total_time += elapsed

            avg_time = total_time / runs
            results[name] = {
                "avg_time": avg_time,
                "query": query,
                "tag_filters": tag_filters,
            }

        # Print benchmark results
        print("\nSearch Performance Benchmark Results:")
        print("-" * 80)
        print(f"{'Query Type':<30} | {'Avg Time (sec)':<15} | {'Query':<35}")
        print("-" * 80)

        for name, data in results.items():
            query_display = data["query"] if data["query"] else "(empty query)"
            if data["tag_filters"]:
                query_display += f" tags:{data['tag_filters']}"
            print(f"{name:<30} | {data['avg_time']:<15.4f} | {query_display:<35}")

        # No assertions - this is purely informational
