"""Fixtures for handling flaky tests with retry logic."""

import asyncio
import functools
from typing import Any, Callable

import pytest


def async_retry(max_attempts: int = 3, delay: float = 0.1):
    """Decorator to retry async tests that may fail due to timing issues.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay in seconds between attempts
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except (AssertionError, Exception) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise
            if last_exception:
                raise last_exception
            return None  # unreachable when max_attempts >= 1

        return wrapper

    return decorator


@pytest.fixture
def retry_on_failure():
    """Fixture that provides retry functionality for flaky tests."""
    return async_retry


# Mark for flaky tests
pytest.mark.flaky = pytest.mark.usefixtures("retry_on_failure")
