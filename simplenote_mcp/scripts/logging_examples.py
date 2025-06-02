#!/usr/bin/env python3
# simplenote_mcp/scripts/logging_examples.py
"""Examples of how to use structured logging in the Simplenote MCP Server."""

import asyncio

# Add parent directory to path for running the script directly
import os
import random
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from simplenote_mcp.server import get_logger, get_request_logger, logger

# Configure logging for the examples
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["LOG_FORMAT"] = "json"


def example_basic_logging() -> None:
    """Basic logging examples."""
    print("\n=== Basic Logging Examples ===")

    # Using the global logger
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Using logger with exception information
    try:
        _ = 1 / 0  # Assign to _ to avoid B018 warning
    except Exception:
        logger.error("An error occurred", exc_info=True)

    # Using logger with extra fields
    logger.info(
        "User action", extra={"user_id": "123", "action": "login", "ip": "192.168.1.1"}
    )


def example_contextual_logging() -> None:
    """Examples of logging with context."""
    print("\n=== Contextual Logging Examples ===")

    # Get logger for a specific component
    cache_logger = get_logger("cache", component="cache", subsystem="storage")
    cache_logger.info("Cache initialized")

    # Add context for a specific operation
    op_logger = cache_logger.with_context(operation="sync", target="notes")
    op_logger.info("Starting sync operation")

    # Log with dynamic context
    for i in range(3):
        op_logger.with_context(
            iteration=i,
            items_processed=random.randint(10, 100),  # noqa: S311
            duration_ms=random.randint(50, 200),  # noqa: S311
        ).info("Sync batch completed")

    op_logger.info("Sync operation completed")


def example_request_tracing() -> None:
    """Examples of request tracing with structured logging."""
    print("\n=== Request Tracing Examples ===")

    # Simulate handling multiple requests
    def handle_request(request_id: str, user_id: str, action: str) -> None:
        # Create a logger with request context
        req_logger = get_request_logger(request_id, user_id=user_id, action=action)

        req_logger.info("Request started")

        # Simulate some processing stages
        req_logger.debug("Authenticating user")
        time.sleep(0.1)

        # Add more context as the request progresses
        req_logger.with_context(auth_status="success").info("User authenticated")

        # Simulate an operation
        try:
            if random.random() < 0.3:  # 30% chance of error  # noqa: S311
                raise ValueError("Random processing error")

            time.sleep(0.2)
            req_logger.with_context(
                result="success",
                processing_time_ms=random.randint(100, 500),  # noqa: S311
            ).info("Request processed successfully")

        except Exception as e:
            req_logger.with_context(
                error=str(e), error_type=e.__class__.__name__
            ).error("Error processing request", exc_info=True)

        req_logger.info("Request completed")

    # Process multiple requests in parallel
    requests = [
        {"id": str(uuid.uuid4()), "user_id": "user123", "action": "get_notes"},
        {"id": str(uuid.uuid4()), "user_id": "user456", "action": "create_note"},
        {"id": str(uuid.uuid4()), "user_id": "user789", "action": "update_note"},
    ]

    for req in requests:
        handle_request(req["id"], req["user_id"], req["action"])


async def example_async_logging() -> None:
    """Examples of logging in async functions."""
    print("\n=== Async Logging Examples ===")

    async def process_item(item_id: str, logger) -> None:
        logger.debug(f"Processing item {item_id}")
        await asyncio.sleep(0.1)  # Simulate async work
        logger.info(f"Item {item_id} processed")

    # Create a logger for this task
    task_logger = get_logger("async_task", task_id="background-sync")

    # Create multiple tasks
    tasks = []
    for i in range(5):
        item_logger = task_logger.with_context(item_id=f"item-{i}")
        tasks.append(process_item(i, item_logger))

    task_logger.info(f"Starting batch processing of {len(tasks)} items")
    await asyncio.gather(*tasks)
    task_logger.info("Batch processing completed")


def example_performance_logging() -> None:
    """Examples of logging performance metrics."""
    print("\n=== Performance Logging Examples ===")

    # Create a logger for performance monitoring
    perf_logger = get_logger("performance")

    # Simple timing function
    def timed_operation(name, logger=None):
        _logger = logger or perf_logger
        start_time = time.time()

        def end_timer(**additional_context):
            duration = (time.time() - start_time) * 1000  # ms
            context = {"operation": name, "duration_ms": duration}
            context.update(additional_context)
            _logger.with_context(**context).info(f"Operation '{name}' completed")
            return duration

        return end_timer

    # Example usage
    timer = timed_operation("database_query")
    # Simulate work
    time.sleep(0.3)
    timer(rows_returned=42, cache_hit=False)

    # Another example with more complex operations
    for i in range(3):
        timer = timed_operation(f"batch_process_{i}")
        # Simulate variable work
        time.sleep(0.1 * random.randint(1, 5))  # noqa: S311
        timer(items_processed=random.randint(10, 100), errors=random.randint(0, 3))  # noqa: S311


async def main() -> None:
    """Run all examples."""
    example_basic_logging()
    example_contextual_logging()
    example_request_tracing()
    await example_async_logging()
    example_performance_logging()

    print("\nCheck the log files for the structured output!")


if __name__ == "__main__":
    asyncio.run(main())
