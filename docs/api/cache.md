# Cache System

This document provides technical documentation for the Simplenote MCP Server's caching system.

## Overview

The caching system is designed to improve performance by storing frequently accessed notes in memory, reducing the number of API calls to Simplenote and providing faster response times for common operations.

## Architecture

The cache system uses a multi-layered approach:

1. **Memory Cache**: In-memory storage for frequently accessed notes
2. **Persistent Cache**: Optional disk-based cache for session persistence
3. **Smart Invalidation**: Automatic cache invalidation based on TTL and modifications

## Cache Class

::: simplenote_mcp.server.cache
    options:
      show_source: true
      heading_level: 3

## Configuration

### Environment Variables

The cache system can be configured using the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_SIZE` | `1000` | Maximum number of notes to cache in memory |
| `CACHE_TTL` | `300` | Cache time-to-live in seconds (5 minutes) |
| `CACHE_STRATEGY` | `lru` | Cache eviction strategy (`lru`, `lfu`, `fifo`) |
| `CACHE_PERSISTENT` | `false` | Enable persistent disk-based caching |
| `CACHE_CLEANUP_INTERVAL` | `60` | Cache cleanup interval in seconds |

### Programmatic Configuration

```python
from simplenote_mcp.server.cache import NoteCache

cache = NoteCache(
    max_size=1000,
    ttl=300,
    strategy="lru",
    persistent=False
)
```

## Cache Strategies

### LRU (Least Recently Used)

Default strategy that evicts the least recently accessed items when the cache is full.

```python
cache = NoteCache(strategy="lru")
```

**Advantages:**
- Good performance for temporal locality
- Simple and predictable behavior
- Low memory overhead

**Use Cases:**
- General note access patterns
- Mixed read/write workloads

### LFU (Least Frequently Used)

Evicts items that are accessed least frequently.

```python
cache = NoteCache(strategy="lfu")
```

**Advantages:**
- Better for frequency-based access patterns
- Retains popular items longer

**Use Cases:**
- Heavy read workloads
- Clear access frequency patterns

### FIFO (First In, First Out)

Evicts the oldest items in the cache first.

```python
cache = NoteCache(strategy="fifo")
```

**Advantages:**
- Simple implementation
- Predictable memory usage

**Use Cases:**
- Sequential access patterns
- Simple caching needs

## Cache Operations

### Basic Operations

#### Store a Note

```python
await cache.put(note_id, note_data)
```

#### Retrieve a Note

```python
note_data = await cache.get(note_id)
if note_data is None:
    # Cache miss - fetch from API
    note_data = await fetch_from_api(note_id)
    await cache.put(note_id, note_data)
```

#### Check Cache Status

```python
# Check if note is cached
if await cache.contains(note_id):
    print("Note is in cache")

# Get cache statistics
stats = await cache.get_stats()
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
```

#### Remove from Cache

```python
# Remove specific note
await cache.remove(note_id)

# Clear entire cache
await cache.clear()
```

### Batch Operations

#### Bulk Store

```python
notes_data = {
    "note1": {"content": "...", "tags": []},
    "note2": {"content": "...", "tags": ["work"]},
    "note3": {"content": "...", "tags": ["personal"]}
}

await cache.put_many(notes_data)
```

#### Bulk Retrieve

```python
note_ids = ["note1", "note2", "note3"]
cached_notes = await cache.get_many(note_ids)

# Returns dict with available notes
# Missing notes will not be included
```

#### Bulk Remove

```python
note_ids = ["note1", "note2", "note3"]
await cache.remove_many(note_ids)
```

## Cache Invalidation

### Time-based Invalidation (TTL)

Notes automatically expire after the configured TTL:

```python
# Configure 10-minute TTL
cache = NoteCache(ttl=600)

# Note will be automatically removed after 10 minutes
await cache.put(note_id, note_data)
```

### Manual Invalidation

```python
# Invalidate specific note
await cache.invalidate(note_id)

# Invalidate notes by tag
await cache.invalidate_by_tag("work")

# Invalidate all notes
await cache.invalidate_all()
```

### Smart Invalidation

The cache automatically invalidates notes when they are modified:

```python
# This will automatically invalidate the cached version
await update_note(note_id, new_content)
```

## Cache Events

### Event Listeners

```python
@cache.on_hit
async def on_cache_hit(note_id: str):
    """Called when a cache hit occurs."""
    print(f"Cache hit for note: {note_id}")

@cache.on_miss  
async def on_cache_miss(note_id: str):
    """Called when a cache miss occurs."""
    print(f"Cache miss for note: {note_id}")

@cache.on_eviction
async def on_cache_eviction(note_id: str, reason: str):
    """Called when a note is evicted from cache."""
    print(f"Note {note_id} evicted: {reason}")
```

### Event Types

- `hit`: Cache hit occurred
- `miss`: Cache miss occurred  
- `eviction`: Note evicted from cache
- `expiration`: Note expired due to TTL
- `update`: Cached note was updated
- `invalidation`: Note was manually invalidated

## Performance Monitoring

### Cache Statistics

```python
stats = await cache.get_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit ratio: {stats['hit_ratio']:.2%}")
print(f"Miss ratio: {stats['miss_ratio']:.2%}")
print(f"Evictions: {stats['evictions']}")
print(f"Current size: {stats['current_size']}")
print(f"Max size: {stats['max_size']}")
print(f"Memory usage: {stats['memory_usage_mb']:.2f} MB")
```

### Performance Metrics

```python
# Get detailed performance metrics
metrics = await cache.get_metrics()

print(f"Average response time: {metrics['avg_response_time_ms']:.2f} ms")
print(f"P95 response time: {metrics['p95_response_time_ms']:.2f} ms")
print(f"P99 response time: {metrics['p99_response_time_ms']:.2f} ms")
print(f"Throughput: {metrics['requests_per_second']:.2f} req/s")
```

### Cache Health Check

```python
health = await cache.health_check()

if health['status'] == 'healthy':
    print("Cache is operating normally")
else:
    print(f"Cache issues detected: {health['issues']}")
```

## Memory Management

### Memory Limits

```python
# Configure memory limits
cache = NoteCache(
    max_size=1000,              # Maximum number of items
    max_memory_mb=100,          # Maximum memory usage in MB
    max_item_size_kb=1024       # Maximum size per item in KB
)
```

### Memory Optimization

```python
# Enable compression for large notes
cache = NoteCache(
    compression=True,
    compression_threshold=1024  # Compress notes larger than 1KB
)

# Configure garbage collection
cache.configure_gc(
    gc_interval=300,            # Run GC every 5 minutes
    gc_threshold=0.8            # GC when 80% full
)
```

### Memory Monitoring

```python
# Monitor memory usage
memory_info = await cache.get_memory_info()

print(f"Total memory: {memory_info['total_mb']:.2f} MB")
print(f"Used memory: {memory_info['used_mb']:.2f} MB")
print(f"Free memory: {memory_info['free_mb']:.2f} MB")
print(f"Memory utilization: {memory_info['utilization']:.1%}")
```

## Persistent Caching

### Enable Persistent Cache

```python
cache = NoteCache(
    persistent=True,
    cache_dir="~/.simplenote-cache",
    persistence_format="json"  # or "pickle", "msgpack"
)
```

### Cache Persistence Options

```python
# Configure persistence behavior
cache.configure_persistence(
    save_interval=60,           # Save to disk every minute
    load_on_startup=True,       # Load cache on startup
    compress_files=True,        # Compress cache files
    max_file_age_days=7         # Delete files older than 7 days
)
```

### Manual Persistence Operations

```python
# Save cache to disk
await cache.save_to_disk()

# Load cache from disk
await cache.load_from_disk()

# Clear persistent cache
await cache.clear_persistent_cache()
```

## Error Handling

### Cache Errors

```python
from simplenote_mcp.cache.exceptions import (
    CacheError,
    CacheFullError,
    CacheCorruptionError,
    PersistenceError
)

try:
    await cache.put(note_id, note_data)
except CacheFullError:
    # Handle cache full condition
    await cache.clear_old_entries()
    await cache.put(note_id, note_data)
except CacheCorruptionError:
    # Handle cache corruption
    await cache.rebuild_cache()
except PersistenceError as e:
    # Handle persistence issues
    print(f"Persistence error: {e}")
```

### Error Recovery

```python
# Configure error recovery
cache.configure_error_handling(
    auto_recovery=True,         # Automatically recover from errors
    max_retries=3,              # Maximum retry attempts
    retry_delay=1.0,            # Delay between retries
    fallback_to_memory=True     # Fall back to memory-only on persistence errors
)
```

## Best Practices

### Cache Sizing

```python
# Size cache based on available memory and usage patterns
import psutil

available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
cache_memory_mb = min(available_memory_mb * 0.1, 100)  # Use max 10% of available memory

cache = NoteCache(max_memory_mb=cache_memory_mb)
```

### Cache Warming

```python
async def warm_cache():
    """Pre-populate cache with frequently accessed notes."""
    # Get most recently accessed notes
    recent_notes = await get_recent_notes(limit=100)
    
    # Pre-load into cache
    for note in recent_notes:
        await cache.put(note['id'], note)
    
    print(f"Warmed cache with {len(recent_notes)} notes")
```

### Cache Monitoring

```python
async def monitor_cache():
    """Monitor cache performance and adjust if needed."""
    stats = await cache.get_stats()
    
    if stats['hit_ratio'] < 0.7:  # Less than 70% hit ratio
        print("Cache hit ratio is low, consider increasing cache size")
    
    if stats['memory_usage_mb'] > 90:  # Using more than 90% of allocated memory
        print("Cache memory usage is high, consider cleanup")
        await cache.cleanup_expired()
```

### Cache Partitioning

```python
# Partition cache by note type or usage pattern
class PartitionedCache:
    def __init__(self):
        self.work_cache = NoteCache(max_size=500, ttl=600)
        self.personal_cache = NoteCache(max_size=300, ttl=1800)
        self.archive_cache = NoteCache(max_size=200, ttl=3600)
    
    async def get_cache(self, note_tags):
        if 'work' in note_tags:
            return self.work_cache
        elif 'personal' in note_tags:
            return self.personal_cache
        else:
            return self.archive_cache
```

## Testing

### Cache Testing Utilities

```python
from simplenote_mcp.cache.testing import CacheTestUtils

async def test_cache_behavior():
    # Create test cache
    cache = CacheTestUtils.create_test_cache()
    
    # Populate with test data
    await CacheTestUtils.populate_cache(cache, num_notes=100)
    
    # Verify cache behavior
    assert await cache.get("test_note_1") is not None
    assert cache.get_stats()['current_size'] == 100
    
    # Test eviction
    await CacheTestUtils.fill_cache_to_capacity(cache)
    stats = cache.get_stats()
    assert stats['evictions'] > 0
```

### Performance Testing

```python
async def benchmark_cache():
    """Benchmark cache performance."""
    cache = NoteCache(max_size=1000)
    
    # Benchmark write performance
    start_time = time.time()
    for i in range(1000):
        await cache.put(f"note_{i}", {"content": f"Content {i}"})
    write_time = time.time() - start_time
    
    # Benchmark read performance  
    start_time = time.time()
    for i in range(1000):
        await cache.get(f"note_{i}")
    read_time = time.time() - start_time
    
    print(f"Write performance: {1000/write_time:.2f} ops/sec")
    print(f"Read performance: {1000/read_time:.2f} ops/sec")
```

## Integration with MCP Server

The cache system is automatically integrated with the MCP server:

```python
from simplenote_mcp.server import SimplenoteServer

# Server automatically creates and configures cache
server = SimplenoteServer()

# Access server's cache instance
cache = server.cache

# Cache is used automatically for all note operations
note = await server.get_note(note_id)  # Uses cache transparently
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**: Reduce cache size or enable compression
2. **Low Hit Ratio**: Increase cache size or TTL
3. **Persistence Errors**: Check disk space and permissions
4. **Performance Issues**: Monitor cache statistics and optimize configuration

### Debug Mode

```python
# Enable cache debugging
cache = NoteCache(debug=True, log_level="DEBUG")

# This will log all cache operations
await cache.put(note_id, note_data)  # Logs: "Cache PUT: note_123"
await cache.get(note_id)             # Logs: "Cache HIT: note_123"
```

### Cache Validation

```python
# Validate cache integrity
validation_result = await cache.validate()

if not validation_result['valid']:
    print(f"Cache validation failed: {validation_result['errors']}")
    await cache.rebuild_cache()
```

## API Reference

For complete API documentation, see the source code documentation and type hints in the `simplenote_mcp.server.cache` module.

## Related Documentation

- [Server API](server.md) - Main server implementation
- [Search Engine](search.md) - Search functionality that uses caching
- [Configuration](../configuration.md) - Server configuration options
- [Performance Guide](../usage.md#performance-tips) - Performance optimization tips
