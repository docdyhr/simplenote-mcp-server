# Cache Module Test Coverage Improvement Plan

**Current Coverage:** 83% (significantly improved from 14%)  
**Target Coverage:** 90%+  
**Priority:** Medium  
**Owner:** Core development team  
**Last Updated:** 2025-10-20

---

## 📊 Current State Analysis

### Coverage Breakdown (as of 2025-10-19)

| Module | Coverage | Status | Priority |
|--------|----------|--------|----------|
| `cache.py` | 83% | ✅ Good | Maintain |
| Background sync | ~70% | ⚠️ Needs work | High |
| Error handling | ~75% | ⚠️ Needs work | High |
| Edge cases | ~60% | ❌ Gaps | High |

### Recent Improvements

- ✅ Basic cache operations: 100% covered
- ✅ TTL expiration: Well tested
- ✅ LRU eviction: Comprehensive tests
- ✅ Thread safety: Validated
- ✅ Concurrent access: Load tested

### Remaining Gaps

1. **Edge Cases** (~15% of uncovered code)
   - Race conditions in expiry checking
   - Negative/zero TTL handling
   - Concurrent eviction scenarios
   - Cache size boundary conditions

2. **Error Recovery** (~8% of uncovered code)
   - Background sync failures
   - Network timeout handling
   - Invalid data recovery
   - Corrupted cache state

3. **Performance Scenarios** (~7% of uncovered code)
   - High-load stress testing
   - Memory pressure conditions
   - Slow backend responses
   - Cache stampede prevention

---

## 🎯 Improvement Strategy

### Phase 1: Critical Edge Cases (Week 1)

**Goal:** Add 5% coverage focusing on race conditions and boundary cases

#### 1.1 Race Condition Tests

```python
# Test: Expiry race condition
async def test_cache_expiry_race_condition():
    """Test concurrent access during TTL expiration."""
    cache = NoteCache(ttl=0.1)
    
    # Set item with short TTL
    cache.set("key1", "value1")
    
    # Wait until just before expiry
    await asyncio.sleep(0.09)
    
    # Start multiple concurrent gets
    tasks = [cache.get("key1") for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify consistent behavior (all hit or all miss)
    assert all(r == results[0] for r in results)
```

```python
# Test: Concurrent eviction
async def test_concurrent_eviction_race():
    """Test LRU eviction during concurrent access."""
    cache = NoteCache(max_size=5)
    
    # Fill cache to capacity
    for i in range(5):
        cache.set(f"key{i}", f"value{i}")
    
    # Trigger eviction with concurrent sets
    async def set_item(key, value):
        cache.set(key, value)
        await asyncio.sleep(0.001)
    
    tasks = [set_item(f"new{i}", f"val{i}") for i in range(3)]
    await asyncio.gather(*tasks)
    
    # Verify cache size never exceeds max
    assert cache.size() <= 5
```

#### 1.2 Boundary Condition Tests

```python
# Test: Negative TTL
def test_negative_ttl_handling():
    """Test cache behavior with negative TTL."""
    cache = NoteCache(ttl=-1)
    
    cache.set("key", "value")
    
    # Should either reject or treat as no expiry
    result = cache.get("key")
    assert result is not None or cache.ttl == 0
```

```python
# Test: Zero TTL
def test_zero_ttl_immediate_expiry():
    """Test that zero TTL causes immediate expiry."""
    cache = NoteCache(ttl=0)
    
    cache.set("key", "value")
    
    # Should be immediately expired
    result = cache.get("key")
    assert result is None
```

```python
# Test: Max size boundary
def test_cache_at_max_capacity():
    """Test behavior exactly at max capacity."""
    cache = NoteCache(max_size=10)
    
    # Fill to exact capacity
    for i in range(10):
        cache.set(f"key{i}", f"value{i}")
    
    assert cache.size() == 10
    assert not cache.has_space()
    
    # Adding one more should evict oldest
    cache.set("key10", "value10")
    assert cache.size() == 10
    assert "key0" not in cache
```

### Phase 2: Error Recovery (Week 2)

**Goal:** Add 4% coverage focusing on failure scenarios

#### 2.1 Background Sync Failures

```python
# Test: Sync with network timeout
@pytest.mark.asyncio
async def test_background_sync_network_timeout():
    """Test background sync handling of network timeouts."""
    cache = NoteCache(sync_interval=1)

    with patch("simplenote.Simplenote.get_note_list") as mock_sync:
        mock_sync.side_effect = TimeoutError("Network timeout")

        sync_manager = BackgroundSync(cache, sync_interval=0.1)
        sync_manager.start()

        await asyncio.sleep(0.2)

        # Verify cache remains operational
        cache.set("key", "value")
        assert cache.get("key") == "value"

        # Verify error was logged
        assert "Network timeout" in captured_logs
```

```python
# Test: Sync with invalid data
@pytest.mark.asyncio
async def test_background_sync_invalid_data():
    """Test background sync handling of corrupted data."""
    cache = NoteCache()

    with patch("simplenote.Simplenote.get_note_list") as mock_sync:
        # Return malformed data
        mock_sync.return_value = [None, {"invalid": "structure"}]

        sync_manager = BackgroundSync(cache, sync_interval=0.1)
        result = await sync_manager.sync_once()

        # Should handle gracefully
        assert result is False or result is None

        # Cache should still be usable
        cache.set("key", "value")
        assert cache.get("key") == "value"
```

#### 2.2 Cache State Recovery

```python
# Test: Recovery from corrupted state
def test_cache_recovery_from_corruption():
    """Test cache can recover from internal state corruption."""
    cache = NoteCache()
    
    # Populate cache
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    # Simulate state corruption
    cache._cache["key1"] = None  # Invalid entry
    
    # Cache should handle gracefully
    result = cache.get("key1")
    assert result is None
    
    # Other entries still work
    assert cache.get("key2") == "value2"
    
    # Can overwrite corrupted entry
    cache.set("key1", "new_value")
    assert cache.get("key1") == "new_value"
```

### Phase 3: Performance Scenarios (Week 3)

**Goal:** Add 3% coverage with stress and load tests

#### 3.1 High Load Tests

```python
# Test: Cache under high load
@pytest.mark.perf
async def test_cache_high_load_performance():
    """Test cache performance under high concurrent load."""
    cache = NoteCache(max_size=1000)
    
    async def worker(worker_id: int):
        for i in range(100):
            key = f"worker{worker_id}_key{i}"
            cache.set(key, f"value{i}")
            await asyncio.sleep(0.001)
            retrieved = cache.get(key)
            assert retrieved == f"value{i}"
    
    # Run 50 concurrent workers
    tasks = [worker(i) for i in range(50)]
    await asyncio.gather(*tasks)
    
    # Verify cache integrity
    assert cache.size() <= 1000
```

```python
# Test: Memory pressure
@pytest.mark.perf
def test_cache_memory_pressure():
    """Test cache behavior under memory pressure."""
    cache = NoteCache(max_size=1000)
    
    # Fill with large objects
    large_value = "x" * 1024 * 100  # 100KB per entry
    
    for i in range(1000):
        cache.set(f"key{i}", large_value)
    
    # Verify eviction is working
    assert cache.size() <= 1000
    
    # Verify cache is still responsive
    cache.set("test", "small")
    assert cache.get("test") == "small"
```

#### 3.2 Cache Stampede Prevention

```python
# Test: Cache stampede scenario
@pytest.mark.asyncio
async def test_cache_stampede_prevention():
    """Test that cache handles stampede scenarios gracefully."""
    cache = NoteCache(ttl=1)
    
    # Simulate popular key expiring
    cache.set("popular_key", "value")
    await asyncio.sleep(1.1)  # Let it expire
    
    # Simulate many concurrent requests for same expired key
    request_count = 0
    
    async def fetch_with_fallback(key):
        nonlocal request_count
        result = cache.get(key)
        if result is None:
            # Simulate expensive backend call
            await asyncio.sleep(0.1)
            request_count += 1
            result = f"backend_value_{request_count}"
            cache.set(key, result)
        return result
    
    # 100 concurrent requests
    tasks = [fetch_with_fallback("popular_key") for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    # With proper stampede prevention, should have few backend calls
    # Without it, would have ~100 backend calls
    print(f"Backend calls: {request_count}")
    assert request_count < 50  # Should be much lower with proper handling
```

---

## 📋 Test Implementation Checklist

### Edge Cases
- [ ] Race condition during expiry check
- [ ] Concurrent eviction scenarios
- [ ] Negative TTL handling
- [ ] Zero TTL immediate expiry
- [ ] Max size boundary conditions
- [ ] Empty cache operations
- [ ] Single-item cache operations
- [ ] Duplicate key handling

### Error Scenarios
- [ ] Background sync network timeout
- [ ] Background sync invalid data
- [ ] Background sync rate limiting
- [ ] Corrupted cache state recovery
- [ ] Out of memory handling
- [ ] Thread safety violations
- [ ] Lock acquisition failures

### Performance Tests
- [ ] High concurrent load (50+ workers)
- [ ] Memory pressure with large objects
- [ ] Cache stampede prevention
- [ ] Slow backend simulation
- [ ] Rapid eviction cycles
- [ ] Long-running sync operations
- [ ] Cache warm-up performance

---

## 🧪 Test Quality Standards

### Test Requirements

1. **Isolation**
   - Each test must be fully independent
   - Clean up resources in teardown
   - Reset global state between tests

2. **Determinism**
   - Tests must pass consistently
   - No flaky tests due to timing
   - Use controlled async delays

3. **Performance**
   - Mark slow tests with `@pytest.mark.perf`
   - Keep unit tests under 100ms
   - Performance tests under 5s

4. **Documentation**
   - Clear docstrings explaining what is tested
   - Document expected behavior
   - Include rationale for edge case tests

### Example Test Structure

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_specific_scenario():
    """Test cache behavior in specific scenario.
    
    This test verifies that the cache correctly handles [scenario]
    when [condition]. This is important because [rationale].
    
    Expected behavior:
    - [Expected outcome 1]
    - [Expected outcome 2]
    """
    # Arrange
    cache = NoteCache(max_size=10, ttl=60)
    
    # Act
    cache.set("key", "value")
    result = cache.get("key")
    
    # Assert
    assert result == "value"
    assert cache.size() == 1
```

---

## 📊 Success Metrics

### Coverage Targets

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Overall cache.py | 83% | 90%+ | Week 3 |
| Edge cases | ~60% | 95%+ | Week 1 |
| Error handling | ~75% | 90%+ | Week 2 |
| Performance paths | ~70% | 85%+ | Week 3 |

### Quality Metrics

| Metric | Target |
|--------|--------|
| Test pass rate | 100% |
| Flaky test rate | 0% |
| Test execution time | < 30s total |
| Lines of test code | ~1500+ |

---

## 🔄 Continuous Improvement

### Monitoring

```bash
# Run coverage report
pytest tests/test_cache*.py --cov=simplenote_mcp/server/cache --cov-report=term-missing

# Identify uncovered lines
pytest tests/test_cache*.py --cov=simplenote_mcp/server/cache --cov-report=html
open htmlcov/index.html
```

### Review Process

1. **Weekly Review**
   - Check coverage progress
   - Identify new gaps
   - Adjust priorities

2. **Test Code Review**
   - Peer review all new tests
   - Verify quality standards
   - Check for duplicates

3. **Performance Tracking**
   - Monitor test execution time
   - Identify slow tests
   - Optimize where needed

---

## 🛠️ Tools and Resources

### Testing Tools

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-timeout pytest-mock

# Run cache tests
pytest tests/test_cache*.py -v

# Run with coverage
pytest tests/test_cache*.py --cov=simplenote_mcp/server/cache

# Run only fast tests (exclude perf)
pytest tests/test_cache*.py -m "not perf"

# Run only edge case tests
pytest tests/test_cache*.py -k "edge_case or boundary"
```

### Coverage Analysis

```python
# scripts/analyze_cache_coverage.py
import coverage
import json


def analyze_missing_coverage():
    """Analyze which cache.py lines are not covered."""
    cov = coverage.Coverage()
    cov.load()

    analysis = cov.analysis("simplenote_mcp/server/cache.py")
    missing_lines = analysis[2]  # Lines not covered

    print(f"Missing coverage on {len(missing_lines)} lines:")
    for line in missing_lines:
        print(f"  Line {line}")
```

---

## 📚 References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio guide](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [Python asyncio testing patterns](https://docs.python.org/3/library/asyncio-task.html)
- [Cache testing best practices](https://martinfowler.com/bliki/TestCoverage.html)

---

## 📝 Notes

### Known Challenges

1. **Timing-dependent tests**
   - Use controlled delays instead of random sleep
   - Consider using `pytest-timeout` for safety
   - Mock time where possible

2. **Concurrency testing**
   - Ensure proper test isolation
   - Use locks/semaphores carefully
   - Verify thread safety explicitly

3. **Performance test stability**
   - Mark with `@pytest.mark.perf`
   - Exclude from default test runs
   - Set realistic thresholds

### Future Enhancements

- [ ] Add property-based testing with Hypothesis
- [ ] Implement fuzzing for cache operations
- [ ] Add chaos engineering tests
- [ ] Create performance regression tracking
- [ ] Add cache behavior visualization

---

**Status:** 🟢 In Progress  
**Next Review:** 2025-10-27  
**Owner:** Core Development Team
