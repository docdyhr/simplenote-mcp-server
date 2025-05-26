# Monitoring Integration Guide for Simplenote MCP Server

This guide explains how to integrate performance monitoring throughout the Simplenote MCP Server codebase to track metrics and improve observability.

## Overview

The monitoring system provides functionality to track:
- API call performance (response times, success rates)
- Cache performance (hit/miss rates, size)
- Tool usage (call frequencies, execution times)
- System resources (CPU, memory, disk usage)

## Metrics Collector

The `MetricsCollector` class provides a singleton instance that collects metrics throughout the application. The system automatically saves metrics to a JSON file at regular intervals and provides functions to record various events.

## Quick Start

### 1. Import the Required Functions

```python
from simplenote_mcp.server.monitoring.metrics import (
    start_metrics_collection,
    record_api_call,
    record_response_time, 
    record_cache_hit,
    record_cache_miss,
    record_tool_call,
    record_tool_execution_time,
    update_cache_size,
)
```

### 2. Initialize Metrics Collection

Add this to your server startup code (in the `run()` function):

```python
# Start performance monitoring
logger.info("Starting performance monitoring")
start_metrics_collection(interval=60)  # Collect metrics every minute
```

### 3. Track API Calls

When making API calls:

```python
try:
    # Record API call start
    api_start_time = time.time()
    
    # Make the API call
    result = api_client.some_method()
    
    # Record successful API call
    record_api_call("some_method", success=True)
    record_response_time("some_method", time.time() - api_start_time)
    
    return result
except Exception as e:
    # Record failed API call
    record_api_call("some_method", success=False, error_type=type(e).__name__)
    raise
```

### 4. Track Cache Performance

When accessing the cache:

```python
def get_from_cache(key):
    if key in cache:
        record_cache_hit()
        return cache[key]
    else:
        record_cache_miss()
        return None
```

Periodically update the cache size metrics:

```python
update_cache_size(len(cache), cache.max_size)
```

### 5. Track Tool Calls

When handling tool calls:

```python
def handle_tool_call(name, arguments):
    # Record tool call
    record_tool_call(name)
    start_time = time.time()
    
    try:
        # Execute the tool
        result = execute_tool(name, arguments)
        
        # Record tool execution time
        record_tool_execution_time(name, time.time() - start_time)
        return result
    except Exception as e:
        # Record tool execution time even on error
        record_tool_execution_time(name, time.time() - start_time)
        raise
```

## Integration Points

### Server Initialization

Add monitoring initialization to the `run()` function in `server.py`:

```python
async def run() -> None:
    # ... existing code ...
    
    # Start performance monitoring
    logger.info("Starting performance monitoring")
    start_metrics_collection(interval=60)  # Collect metrics every minute
    
    # ... rest of the function ...
```

### API Client Interactions

Instrument the `get_simplenote_client()` function:

```python
def get_simplenote_client():
    api_start_time = time.time()
    try:
        client = Simplenote(config.simplenote_email, config.simplenote_password)
        record_api_call("get_simplenote_client", success=True)
        record_response_time("get_simplenote_client", time.time() - api_start_time)
        return client
    except Exception as e:
        record_api_call("get_simplenote_client", success=False, error_type=type(e).__name__)
        raise
```

### Tool Handling

Add monitoring to the `handle_call_tool()` function:

```python
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    logger.info(f"Tool call: {name} with arguments: {json.dumps(arguments)}")
    
    # Record tool call for performance monitoring
    record_tool_call(name)
    start_time = time.time()
    
    try:
        # ... existing code ...
        
        # Record tool execution time
        record_tool_execution_time(name, time.time() - start_time)
        return result
    except Exception as e:
        # Record tool execution time even on error
        record_tool_execution_time(name, time.time() - start_time)
        raise
```

### Cache Operations

Add monitoring to cache operations in the `NoteCache` class:

```python
def get_note(self, note_id):
    if note_id in self.notes:
        record_cache_hit()
        return self.notes[note_id]
    else:
        record_cache_miss()
        return None
```

## Accessing Metrics

Metrics are automatically saved to `simplenote_mcp/logs/metrics/performance_metrics.json` and can be accessed programmatically:

```python
from simplenote_mcp.server.monitoring.metrics import get_metrics

# Get current metrics
metrics = get_metrics()
print(f"Cache hit rate: {metrics['cache']['hit_rate']}%")
print(f"API success rate: {metrics['api']['success_rate']}%")
```

## Extending the Monitoring System

To add new metrics:

1. Add new metric fields to the appropriate class in `metrics.py`
2. Add methods to record those metrics
3. Add the metrics to the serialization functions

## Dashboard Visualization

For future enhancement, the metrics JSON can be used with visualization tools:

1. **Grafana**: Configure a JSON data source pointing to the metrics file
2. **Custom Dashboard**: Build a simple web dashboard that reads and displays the metrics
3. **Monitoring Service**: Send metrics to a monitoring service for alerting

## Testing

Run the tests to verify monitoring is working correctly:

```bash
pytest simplenote_mcp/tests/test_performance_monitoring.py
```
