#!/usr/bin/env python3
# simplenote_mcp/scripts/log_format_test.py
"""Test script for structured logging formats in the Simplenote MCP server."""

import argparse
import json
import os
import sys
import time
import uuid

# Add parent directory to path for running the script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from simplenote_mcp.server import get_logger, get_request_logger, logger
from simplenote_mcp.server.logging import (
    DEBUG_LOG_FILE,
    LOG_FILE,
    initialize_logging,
)


def setup_logging(level="DEBUG", format_type="json"):
    """Configure logging settings for the test."""
    os.environ["LOG_LEVEL"] = level
    os.environ["LOG_FORMAT"] = format_type
    os.environ["LOG_TO_FILE"] = "true"

    # Re-initialize logging with the new settings
    initialize_logging()

    print(f"Logging initialized with level={level}, format={format_type}")
    print(f"Logs will be written to: {LOG_FILE} and {DEBUG_LOG_FILE}")


def print_log_entries(log_file, count=5):
    """Print the most recent log entries from a file."""
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            print(f"\n=== Last {min(count, len(lines))} entries from {log_file} ===")
            for line in lines[-count:]:
                try:
                    if line.strip().startswith("{"):
                        # Pretty-print JSON logs
                        parsed = json.loads(line.strip())
                        print(json.dumps(parsed, indent=2))
                    else:
                        print(line.strip())
                except Exception:
                    print(line.strip())
    except Exception as e:
        print(f"Error reading log file {log_file}: {e}")


def test_basic_logging():
    """Test basic logging functionality."""
    print("\n=== Testing Basic Logging ===")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Log with exception
    try:
        x = 1 / 0
    except Exception as e:
        logger.error(f"Exception occurred: {e}", exc_info=True)


def test_contextual_logging():
    """Test contextual logging functionality."""
    print("\n=== Testing Contextual Logging ===")

    # Using with_context method
    logger.with_context(operation="test", module="logging", test_id=123).info(
        "Log message with context"
    )

    # Using extra parameter
    logger.info(
        "Another contextual log",
        extra={"method": "extra", "timestamp_ms": int(time.time() * 1000)},
    )

    # Component-specific logger
    component_logger = get_logger(
        "test_component", component="testing", purpose="demonstration"
    )
    component_logger.info("Component logger test")


def test_request_tracing():
    """Test request tracing functionality."""
    print("\n=== Testing Request Tracing ===")

    request_id = str(uuid.uuid4())
    print(f"Request ID: {request_id}")

    # Create a traced logger
    req_logger = get_request_logger(
        request_id, user="test_user", source="script", action="log_test"
    )

    # Log the request lifecycle
    req_logger.info("Request started")

    # Add more context as the request progresses
    auth_logger = req_logger.with_context(stage="authentication")
    auth_logger.debug("Authenticating user")
    time.sleep(0.1)  # Simulate some work
    auth_logger.info("Authentication successful")

    # Process request
    process_logger = req_logger.with_context(stage="processing")
    process_logger.debug("Processing request data")
    time.sleep(0.2)  # Simulate more work

    # Final result
    req_logger.with_context(
        stage="completion",
        duration_ms=300,
        result_code=200,
    ).info("Request completed successfully")


def test_performance_logging():
    """Test performance logging patterns."""
    print("\n=== Testing Performance Logging ===")

    perf_logger = get_logger("performance")

    # Measure function execution time
    def timed_function(name):
        start_time = time.time()

        # Return a function to end the timer
        def end_timer(**context):
            duration_ms = (time.time() - start_time) * 1000
            perf_logger.with_context(
                operation=name, duration_ms=duration_ms, **context
            ).info(f"Operation '{name}' completed")
            return duration_ms

        return end_timer

    # Use the timer
    timer = timed_function("database_query")
    time.sleep(0.3)  # Simulate work
    timer(rows=42, cache_hit=False)

    # Another operation
    timer = timed_function("api_request")
    time.sleep(0.2)  # Simulate work
    timer(endpoint="/api/v1/notes", status_code=200)


def test_all_formats():
    """Test both JSON and standard logging formats."""
    # Test with JSON format
    setup_logging(format_type="json")
    test_basic_logging()
    test_contextual_logging()
    test_request_tracing()
    test_performance_logging()
    print_log_entries(LOG_FILE)

    print("\n" + "=" * 50 + "\n")

    # Test with standard format
    setup_logging(format_type="standard")
    test_basic_logging()
    test_contextual_logging()
    test_request_tracing()
    test_performance_logging()
    print_log_entries(LOG_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test structured logging formats")
    parser.add_argument(
        "--format",
        choices=["json", "standard", "both"],
        default="both",
        help="Log format to test",
    )
    parser.add_argument(
        "--level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="DEBUG",
        help="Log level to use",
    )

    args = parser.parse_args()

    if args.format == "both":
        test_all_formats()
    else:
        setup_logging(level=args.level, format_type=args.format)
        test_basic_logging()
        test_contextual_logging()
        test_request_tracing()
        test_performance_logging()
        print_log_entries(LOG_FILE)

    print("\nTest complete! Check the log files for detailed output.")
