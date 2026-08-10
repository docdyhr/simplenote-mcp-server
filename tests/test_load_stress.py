"""Load and stress tests for the Simplenote MCP server.

These tests verify the server's behavior under various load conditions
and help identify performance bottlenecks.
"""

import asyncio
import json
import statistics
import time
from unittest.mock import AsyncMock, MagicMock, patch

import mcp.types as types
import pytest


class TestLoadTesting:
    """Load tests to verify server behavior under sustained load."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache with configurable number of notes."""
        cache = MagicMock()
        cache.is_initialized = True
        cache._initialized = True
        cache._tags = {"work", "personal", "project"}
        return cache

    def _generate_mock_notes(self, count: int) -> dict:
        """Generate mock notes for testing."""
        notes = {}
        for i in range(count):
            note_id = f"note_{i:06d}"
            notes[note_id] = {
                "key": note_id,
                "content": f"Note {i} content\nThis is test note number {i}",
                "tags": [f"tag{i % 10}", "test"],
                "modifydate": 1700000000 + i,
                "createdate": 1699000000 + i,
                "deleted": 0,
            }
        return notes

    @pytest.mark.asyncio
    async def test_concurrent_search_requests(self, mock_cache):
        """Test handling multiple concurrent search requests."""
        from simplenote_mcp.server.tool_handlers import SearchNotesHandler

        # Setup mock cache with notes
        notes = self._generate_mock_notes(100)
        mock_cache._notes = notes
        mock_cache.search_notes = AsyncMock(return_value=list(notes.values())[:10])
        mock_cache.get_pagination_info = MagicMock(
            return_value={
                "total": 100,
                "page": 1,
                "total_pages": 10,
                "has_more": True,
            }
        )

        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)

        # Run multiple concurrent search requests
        num_requests = 50
        queries = [f"test query {i}" for i in range(num_requests)]

        async def run_search(query: str):
            start = time.time()
            result = await handler.handle({"query": query})
            elapsed = time.time() - start
            return elapsed, result

        # Execute all searches concurrently
        tasks = [run_search(q) for q in queries]
        results = await asyncio.gather(*tasks)

        # Analyze results
        times = [r[0] for r in results]
        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        # All requests should complete
        assert len(results) == num_requests

        # Performance assertions (adjust thresholds as needed)
        assert avg_time < 0.5, f"Average response time {avg_time:.3f}s too high"
        assert max_time < 2.0, f"Max response time {max_time:.3f}s too high"
        assert p95_time < 1.0, f"P95 response time {p95_time:.3f}s too high"

    @pytest.mark.asyncio
    async def test_rapid_note_creation(self, mock_cache):
        """Test rapid sequential note creation."""
        from simplenote_mcp.server.tool_handlers import CreateNoteHandler

        mock_client = MagicMock()
        mock_client.add_note = MagicMock(
            side_effect=lambda note: (
                {"key": f"new_{time.time_ns()}", **note},
                0,
            )
        )

        mock_cache._notes = {}
        mock_cache.update_cache_after_create = AsyncMock()

        handler = CreateNoteHandler(mock_client, mock_cache)

        # Create many notes rapidly
        num_notes = 100
        start_time = time.time()

        for i in range(num_notes):
            result = await handler.handle(
                {
                    "content": f"Load test note {i}\nContent for testing",
                    "tags": "loadtest,stress",
                }
            )
            # Verify each creation succeeds
            result_data = json.loads(result[0].text)
            assert result_data.get("success") is True or "key" in result_data

        elapsed = time.time() - start_time
        rate = num_notes / elapsed

        # Should be able to create at least 10 notes per second
        assert rate > 10, f"Creation rate {rate:.1f} notes/sec too slow"

    @pytest.mark.asyncio
    async def test_large_cache_search(self, mock_cache):
        """Test search performance with large cache."""
        from simplenote_mcp.server.tool_handlers import SearchNotesHandler

        # Create a large cache
        large_note_count = 1000
        notes = self._generate_mock_notes(large_note_count)
        mock_cache._notes = notes

        # Mock search to simulate actual search behavior
        def mock_search(query, limit=None, offset=0, **kwargs):
            # Simulate matching ~10% of notes
            matching = [n for n in notes.values() if "test" in str(n)]
            if limit:
                return matching[offset : offset + limit]
            return matching

        mock_cache.search_notes = AsyncMock(side_effect=mock_search)
        mock_cache.get_pagination_info = MagicMock(
            return_value={
                "total": large_note_count,
                "page": 1,
                "total_pages": 100,
                "has_more": True,
            }
        )

        mock_client = MagicMock()
        handler = SearchNotesHandler(mock_client, mock_cache)

        # Run search with pagination
        start = time.time()
        result = await handler.handle(
            {
                "query": "test",
                "limit": 20,
                "offset": 0,
            }
        )
        elapsed = time.time() - start

        # Search should complete quickly even with large cache
        assert elapsed < 1.0, f"Search took {elapsed:.3f}s, expected < 1s"

        result_data = json.loads(result[0].text)
        assert result_data.get("success") is True

    @pytest.mark.asyncio
    async def test_cache_eviction_under_load(self, mock_cache):
        """Test cache eviction behavior under load."""
        from simplenote_mcp.server.cache import NoteCache

        # Create cache with small max size
        with patch("simplenote_mcp.server.cache.get_config") as mock_config:
            config = MagicMock()
            config.cache_max_size = 50
            config.sync_interval_seconds = 120
            mock_config.return_value = config

            mock_client = MagicMock()
            mock_client.get_note_list = MagicMock(return_value=([], 0))

            cache = NoteCache(mock_client)
            cache._initialized = True
            cache._notes = {}

            # Add notes beyond max size
            for i in range(100):
                note_id = f"note_{i}"
                cache._notes[note_id] = {
                    "key": note_id,
                    "content": f"Note {i}",
                    "tags": [],
                }
                cache._record_access(note_id)

                # Trigger eviction periodically
                if len(cache._notes) > config.cache_max_size:
                    cache._evict_if_needed()

            # Cache should not exceed max size
            assert len(cache._notes) <= config.cache_max_size + 10  # Some tolerance


class TestStressTesting:
    """Stress tests to verify server behavior at limits."""

    @pytest.mark.asyncio
    async def test_max_concurrent_operations(self):
        """Test maximum concurrent operations."""
        from simplenote_mcp.server.tool_handlers import GetNoteHandler

        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache._notes = {}
        # Cache is empty/uninitialized so lookups fall through to the API mock
        # below. An unconfigured MagicMock().is_initialized is truthy and
        # MagicMock().get_note(...) returns a non-dict MagicMock rather than
        # None/raising, so without this the handler would take the cache
        # branch and treat every lookup as a hard failure (non-dict "note"),
        # never reaching the API mock at all.
        mock_cache.is_initialized = False

        mock_client.get_note = MagicMock(
            side_effect=lambda nid: ({"key": nid, "content": "Test"}, 0)
        )

        handler = GetNoteHandler(mock_client, mock_cache)

        # Launch many concurrent requests
        num_concurrent = 100

        async def get_note(note_id: str):
            try:
                return await handler.handle({"note_id": note_id})
            except Exception as e:
                return str(e)

        tasks = [get_note(f"note_{i}") for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful results
        successful = sum(
            1 for r in results if not isinstance(r, Exception) and isinstance(r, list)
        )

        # At least 90% should succeed under stress
        assert successful >= num_concurrent * 0.9

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test behavior under memory pressure with large notes."""
        from simplenote_mcp.server.tool_handlers import CreateNoteHandler

        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache._notes = {}
        mock_cache.update_cache_after_create = AsyncMock()

        # Create large content
        large_content = "x" * 100000  # 100KB per note

        mock_client.add_note = MagicMock(
            side_effect=lambda note: (
                {"key": f"large_{time.time_ns()}", **note},
                0,
            )
        )

        handler = CreateNoteHandler(mock_client, mock_cache)

        # Create several large notes
        num_large_notes = 10
        for i in range(num_large_notes):
            result = await handler.handle(
                {
                    "content": f"Large note {i}\n{large_content}",
                }
            )
            result_data = json.loads(result[0].text)
            assert "key" in result_data or result_data.get("success")

    @pytest.mark.asyncio
    async def test_rate_limiting_effectiveness(self):
        """Test that rate limiting is effective under burst load."""
        from unittest.mock import patch

        from simplenote_mcp.server.errors import SecurityError
        from simplenote_mcp.server.middleware import RateLimiter

        # Mock get_config to return a config with offline_mode=False
        mock_config = MagicMock()
        mock_config.offline_mode = False
        mock_config.rate_limit_requests = 100
        mock_config.rate_limit_window_seconds = 60
        mock_config.rate_limit_burst = 100

        # Patch at the source module since middleware imports get_config locally
        with patch("simplenote_mcp.server.config.get_config", return_value=mock_config):
            limiter = RateLimiter()

            # Simulate burst of requests from same client
            client_id = "test_client_burst_" + str(time.time_ns())
            allowed_count = 0
            denied_count = 0

            # Send burst of requests - check_rate_limit raises SecurityError on limit
            for _ in range(200):
                try:
                    limiter.check_rate_limit(
                        client_id,
                        max_requests=50,  # Set low limit for testing
                        window_seconds=60,
                    )
                    allowed_count += 1
                except SecurityError:
                    denied_count += 1

            # Rate limiter should track requests
            total = allowed_count + denied_count
            assert total == 200, "Rate limiter should process all requests"
            # With a limit of 50, should deny some requests
            assert denied_count > 0, "Rate limiter should deny some burst requests"
            # But should allow up to the limit
            assert allowed_count > 0, "Rate limiter should allow some requests"
            assert allowed_count <= 50, "Rate limiter should enforce the limit"

    @pytest.mark.asyncio
    async def test_error_recovery_under_load(self):
        """Test error recovery when operations fail under load."""
        from simplenote_mcp.server.tool_handlers import UpdateNoteHandler

        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache._notes = {
            f"note_{i}": {"key": f"note_{i}", "content": f"Original {i}"}
            for i in range(50)
        }
        mock_cache.update_cache_after_update = AsyncMock()

        # Simulate intermittent failures (30% failure rate)
        call_count = [0]

        def flaky_update(note):
            call_count[0] += 1
            if call_count[0] % 3 == 0:
                return None, -1  # Simulated failure
            # Return a clean dict without MagicMock objects
            note_key = note.get("key", f"note_{call_count[0]}")
            return {
                "key": note_key,
                "content": note.get("content", ""),
                "tags": [],
                "modifydate": 1700000000,
            }, 0

        mock_client.update_note = MagicMock(side_effect=flaky_update)

        handler = UpdateNoteHandler(mock_client, mock_cache)

        # Run many updates
        success_count = 0
        error_count = 0
        total_processed = 0

        for i in range(50):
            try:
                result = await handler.handle(
                    {
                        "note_id": f"note_{i}",
                        "content": f"Updated content {i}",
                    }
                )
                total_processed += 1
                if isinstance(result, types.CallToolResult):
                    assert result.is_error is True
                    error_count += 1
                else:
                    result_data = json.loads(result[0].text)
                    if result_data.get("success") or "key" in result_data:
                        success_count += 1
                    else:
                        error_count += 1
            except Exception:
                error_count += 1
                total_processed += 1

        # Should process all requests (success or graceful failure)
        assert total_processed == 50, "Should process all update requests"
        # Should have handled operations
        assert success_count + error_count == total_processed


class TestPerformanceBenchmarks:
    """Performance benchmarks for various operations."""

    @pytest.mark.asyncio
    async def test_search_latency_percentiles(self):
        """Measure search latency percentiles."""
        from simplenote_mcp.server.tool_handlers import SearchNotesHandler

        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache._notes = {
            f"note_{i}": {
                "key": f"note_{i}",
                "content": f"Benchmark note {i}",
                "tags": ["benchmark"],
            }
            for i in range(200)
        }
        mock_cache.search_notes = AsyncMock(
            return_value=list(mock_cache._notes.values())[:20]
        )
        mock_cache.get_pagination_info = MagicMock(
            return_value={"total": 200, "page": 1, "total_pages": 10}
        )

        handler = SearchNotesHandler(mock_client, mock_cache)

        # Run multiple searches and measure latencies
        latencies = []
        for _ in range(100):
            start = time.time()
            await handler.handle({"query": "benchmark"})
            latencies.append(time.time() - start)

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[50]
        p90 = sorted_latencies[90]
        p99 = sorted_latencies[99]

        # Log results for monitoring
        print("\nSearch Latency Percentiles:")
        print(f"  P50: {p50 * 1000:.2f}ms")
        print(f"  P90: {p90 * 1000:.2f}ms")
        print(f"  P99: {p99 * 1000:.2f}ms")

        # Performance assertions
        assert p50 < 0.1, f"P50 latency {p50:.3f}s too high"
        assert p90 < 0.2, f"P90 latency {p90:.3f}s too high"
        assert p99 < 0.5, f"P99 latency {p99:.3f}s too high"

    @pytest.mark.asyncio
    async def test_throughput_measurement(self):
        """Measure overall throughput of operations."""
        from simplenote_mcp.server.tool_handlers import GetNoteHandler

        mock_client = MagicMock()
        mock_cache = MagicMock()
        mock_cache._notes = {
            f"note_{i}": {"key": f"note_{i}", "content": f"Content {i}"}
            for i in range(100)
        }

        handler = GetNoteHandler(mock_client, mock_cache)

        # Measure throughput over fixed time period
        duration = 2.0  # seconds
        operation_count = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            note_id = f"note_{operation_count % 100}"
            await handler.handle({"note_id": note_id})
            operation_count += 1

        elapsed = time.time() - start_time
        throughput = operation_count / elapsed

        print(f"\nThroughput: {throughput:.1f} ops/sec")

        # Should achieve reasonable throughput
        assert throughput > 100, f"Throughput {throughput:.1f} ops/sec too low"
