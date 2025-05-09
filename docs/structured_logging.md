# Structured Logging in Simplenote MCP Server

This document provides a comprehensive guide to using structured logging in the Simplenote MCP Server.

## Overview

Structured logging provides a more consistent and machine-readable way to log events in the application. Instead of simple text messages, structured logs include additional context in a structured format (usually JSON), making them easier to search, filter, and analyze.

Benefits of structured logging:
- Improved searchability and filtering
- Enhanced debugging capabilities
- Better integration with log aggregation tools
- More consistent log format
- Better context for log messages

## Basic Usage

The Simplenote MCP Server provides several ways to use structured logging:

### 1. Global Logger

The simplest way to use structured logging is through the global `logger` object:

```python
from simplenote_mcp.server import logger

logger.debug("Cache initialization started")
logger.info("Successfully connected to Simplenote API")
logger.warning("Authentication token expired, getting new token")
logger.error("Failed to connect to Simplenote API")
```

### 2. Contextual Logging

To add context to your logs, use the `with_context()` method or the `extra` parameter:

```python
# Using with_context method (recommended)
logger.with_context(note_id="abc123", operation="update").info("Note updated successfully")

# Using extra parameter (compatible with standard logging)
logger.info("Note updated successfully", extra={"note_id": "abc123", "operation": "update"})
```

### 3. Component-Specific Loggers

Create loggers for specific components:

```python
from simplenote_mcp.server import get_logger

# Create a logger for the cache component
cache_logger = get_logger("cache", component="cache")
cache_logger.info("Cache initialized")

# Create a logger for the API client
api_logger = get_logger("api", component="api_client")
api_logger.info("API client created")
```

### 4. Request Tracing

For tracking operations across multiple functions:

```python
from simplenote_mcp.server import get_request_logger
import uuid

# Create a unique ID for the request
request_id = str(uuid.uuid4())

# Create a logger with request tracing
request_logger = get_request_logger(request_id, user_id="user123")
request_logger.info("Request started")

# Later in another function, you can add more context
request_logger.with_context(operation="sync").info("Sync started")
```

## Advanced Features

### Performance Logging

Track the performance of operations:

```python
import time
from simplenote_mcp.server import get_logger

perf_logger = get_logger("performance")

def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration_ms = (time.time() - start_time) * 1000
        
        perf_logger.with_context(
            function=func.__name__,
            duration_ms=duration_ms,
            args_count=len(args),
            kwargs_count=len(kwargs)
        ).info(f"Function {func.__name__} execution completed")
        
        return result
    return wrapper

@measure_execution_time
def my_function(arg1, arg2):
    # Function code...
    pass
```

### Error Logging

Log exceptions with context:

```python
try:
    # Some code that might fail
    result = api_call()
except Exception as e:
    logger.with_context(
        operation="api_call",
        error_type=type(e).__name__,
    ).error(f"API call failed: {str(e)}", exc_info=True)
```

## Configuration

### Environment Variables

Configure the logging behavior using environment variables:

- `LOG_LEVEL`: Sets the minimum log level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT`: Sets the log format (`standard` or `json`)
- `LOG_TO_FILE`: Whether to write logs to a file (`true` or `false`)
- `MCP_DEBUG`: Enables debug mode (`true` or `false`)

### JSON Format

When `LOG_FORMAT` is set to `json`, logs will be output in JSON format:

```json
{
  "timestamp": "2023-09-25T12:34:56.789012",
  "level": "INFO",
  "message": "Note updated successfully",
  "logger": "simplenote_mcp",
  "thread_id": 12345,
  "thread_name": "MainThread",
  "note_id": "abc123",
  "operation": "update",
  "caller": "server.py:handle_call_tool:256"
}
```

## Migration Guide

### Converting Existing Log Calls

To convert existing log calls to use structured logging:

#### Before:

```python
logger.info(f"Updated {notes_count} notes in cache in {elapsed:.2f}s")

logger.error(f"Failed to find note with ID {note_id}")
```

#### After:

```python
logger.with_context(
    notes_count=notes_count,
    duration_seconds=elapsed
).info("Updated notes in cache")

logger.with_context(
    note_id=note_id
).error("Failed to find note")
```

### Best Practices

1. **Keep messages simple**: Move variable data to the context instead of interpolating into the message.
2. **Use consistent message texts**: This makes it easier to search and aggregate logs.
3. **Use appropriate log levels**:
   - `DEBUG`: Detailed information for debugging.
   - `INFO`: Confirmation that things are working as expected.
   - `WARNING`: An indication that something unexpected happened, but the application can continue.
   - `ERROR`: An error occurred but the application can still function.
   - `CRITICAL`: A serious error that may prevent the application from continuing.
4. **Add context, not just messages**: Include relevant identifiers, operation names, and metrics.
5. **Use trace IDs for multi-step operations**: This helps track requests through different components.

## Examples

See the `simplenote_mcp/scripts/logging_examples.py` file for comprehensive examples of how to use structured logging in different scenarios.

To run the examples:

```bash
python -m simplenote_mcp.scripts.logging_examples
```

## Using the Logger in the MCP Server

The most common patterns for using structured logging in the MCP server:

### Server Methods

```python
async def handle_call_tool(name: str, arguments: dict) -> list[types.Content]:
    """Handle a tool call."""
    # Create a request-specific logger
    request_id = str(uuid.uuid4())
    req_logger = get_request_logger(
        request_id,
        tool_name=name,
        arguments=json.dumps(arguments)
    )
    
    req_logger.info("Tool call received")
    
    # Later in the function
    req_logger.with_context(
        result_type="success",
        note_id=result_id
    ).info("Tool call completed")
```

### Cache Operations

```python
async def sync(self) -> int:
    """Synchronize the cache with Simplenote."""
    sync_id = str(uuid.uuid4())
    sync_logger = get_request_logger(
        sync_id,
        operation="cache_sync",
        last_sync=self._last_sync
    )
    
    sync_logger.debug("Starting cache sync")
    
    # Later in the function
    sync_logger.with_context(
        changes_count=change_count,
        duration_seconds=elapsed
    ).info("Cache sync completed")
```

## Reference

### Available Functions

- `get_logger(name=None, **context)`: Get a logger with optional context
- `get_request_logger(request_id, **context)`: Get a logger with request tracing
- `logger`: The global logger instance

### StructuredLogAdapter Methods

- `debug(msg, *args, **kwargs)`: Log at DEBUG level
- `info(msg, *args, **kwargs)`: Log at INFO level
- `warning(msg, *args, **kwargs)`: Log at WARNING level
- `error(msg, *args, **kwargs)`: Log at ERROR level
- `critical(msg, *args, **kwargs)`: Log at CRITICAL level
- `with_context(**context)`: Create a new logger with additional context
- `trace(trace_id=None)`: Create a new logger with a trace ID
