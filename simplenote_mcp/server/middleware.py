"""Middleware for request processing and security in Simplenote MCP server.

This module provides middleware components for:
- Rate limiting
- Request validation
- Security monitoring
- Authentication checks
- Request/response logging
"""

import hashlib
import hmac
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable

from .error_helpers import (
    empty_field_error,
    range_validation_error,
    type_validation_error,
)
from .errors import AuthenticationError, SecurityError, ValidationError
from .logging import logger


class RateLimiter:
    """Advanced rate limiting with multiple strategies."""

    def __init__(self):
        """Initialize rate limiter with sliding window algorithm."""
        from .config import get_config

        # Get rate limit configuration
        config = get_config()
        self.default_max_requests = config.rate_limit_requests
        self.default_window_seconds = config.rate_limit_window_seconds
        self.default_burst_limit = config.rate_limit_burst

        # Sliding window counters: {identifier: deque of timestamps}
        self.sliding_windows = defaultdict(lambda: deque())

        # Token bucket counters: {identifier: (tokens, last_refill_time)}
        self.token_buckets = defaultdict(lambda: (0, time.time()))

        # Failed attempts tracking
        self.failed_attempts = defaultdict(list)

        # Temporary blocks: {identifier: block_until_timestamp}
        self.blocked_until = defaultdict(float)

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        strategy: str = "sliding_window",
        burst_limit: int | None = None,
    ) -> None:
        """Check if request is within rate limits.

        Args:
            identifier: Unique identifier for the requester
            max_requests: Maximum requests allowed (uses config default if None)
            window_seconds: Time window in seconds (uses config default if None)
            strategy: Rate limiting strategy ('sliding_window' or 'token_bucket')
            burst_limit: Maximum burst requests (uses config default if None)

        Raises:
            SecurityError: If rate limit is exceeded
        """
        from .config import get_config

        # Use configured defaults if not specified
        if max_requests is None:
            max_requests = self.default_max_requests
        if window_seconds is None:
            window_seconds = self.default_window_seconds
        if burst_limit is None:
            burst_limit = self.default_burst_limit

        # Skip rate limiting in offline/test mode
        if get_config().offline_mode:
            return

        now = time.time()

        # Check if temporarily blocked
        if identifier in self.blocked_until and now < self.blocked_until[identifier]:
            remaining = int(self.blocked_until[identifier] - now)
            raise SecurityError(
                f"Temporarily blocked for {remaining} seconds due to rate limit violations"
            )

        if strategy == "sliding_window":
            self._check_sliding_window(identifier, max_requests, window_seconds, now)
        elif strategy == "token_bucket":
            self._check_token_bucket(
                identifier,
                max_requests,
                window_seconds,
                burst_limit or max_requests,
                now,
            )
        else:
            raise ValueError(f"Unknown rate limiting strategy: {strategy}")

    def _check_sliding_window(
        self, identifier: str, max_requests: int, window_seconds: int, now: float
    ) -> None:
        """Check sliding window rate limit."""
        window = self.sliding_windows[identifier]
        cutoff_time = now - window_seconds

        # Remove old entries
        while window and window[0] < cutoff_time:
            window.popleft()

        # Check current count
        if len(window) >= max_requests:
            self._handle_rate_limit_violation(identifier)
            oldest_request = window[0]
            wait_time = int(oldest_request + window_seconds - now)
            raise SecurityError(
                f"Rate limit exceeded. Try again in {wait_time} seconds"
            )

        # Add current request
        window.append(now)

    def _check_token_bucket(
        self,
        identifier: str,
        max_tokens: int,
        refill_period: int,
        burst_limit: int,
        now: float,
    ) -> None:
        """Check token bucket rate limit."""
        tokens, last_refill = self.token_buckets[identifier]

        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_refill
        tokens_to_add = (time_elapsed / refill_period) * max_tokens
        tokens = min(burst_limit, tokens + tokens_to_add)

        # Check if we have tokens available
        if tokens < 1:
            self._handle_rate_limit_violation(identifier)
            wait_time = int((1 - tokens) * (refill_period / max_tokens))
            raise SecurityError(
                f"Rate limit exceeded. Try again in {wait_time} seconds"
            )

        # Consume one token
        tokens -= 1
        self.token_buckets[identifier] = (tokens, now)

    def _handle_rate_limit_violation(self, identifier: str) -> None:
        """Handle rate limit violations with progressive penalties."""
        now = time.time()
        recent_cutoff = now - 3600  # Last hour

        # Trigger security alert for rate limit violation
        self._trigger_rate_limit_alert(identifier)

        # Clean old failed attempts
        self.failed_attempts[identifier] = [
            timestamp
            for timestamp in self.failed_attempts[identifier]
            if timestamp > recent_cutoff
        ]

        # Add current violation
        self.failed_attempts[identifier].append(now)
        violation_count = len(self.failed_attempts[identifier])

        # Progressive blocking: 1min, 5min, 15min, 1hour
        if violation_count >= 5:
            block_duration = 3600  # 1 hour
        elif violation_count >= 3:
            block_duration = 900  # 15 minutes
        elif violation_count >= 2:
            block_duration = 300  # 5 minutes
        else:
            block_duration = 60  # 1 minute

        self.blocked_until[identifier] = now + block_duration

        logger.warning(
            f"Rate limit violation #{violation_count} for {identifier}. "
            f"Blocked for {block_duration} seconds"
        )

    def get_rate_limit_info(
        self, identifier: str, window_seconds: int = 900
    ) -> dict[str, Any]:
        """Get current rate limit status for an identifier."""
        now = time.time()
        window = self.sliding_windows[identifier]
        cutoff_time = now - window_seconds

        # Count current requests in window
        current_requests = sum(1 for timestamp in window if timestamp > cutoff_time)

        # Check if blocked
        is_blocked = (
            identifier in self.blocked_until and now < self.blocked_until[identifier]
        )
        block_remaining = max(0, self.blocked_until.get(identifier, 0) - now)

        return {
            "current_requests": current_requests,
            "is_blocked": is_blocked,
            "block_remaining_seconds": int(block_remaining),
            "failed_attempts_last_hour": len(self.failed_attempts[identifier]),
        }

    def _trigger_rate_limit_alert(self, identifier: str) -> None:
        """Trigger security alert for rate limit violation.

        Args:
            identifier: The identifier that violated rate limits
        """
        try:
            # Lazy import to avoid circular dependency
            import asyncio

            from .alerting import alert_rate_limit_violation

            # Get current rate limit info
            info = self.get_rate_limit_info(identifier)

            # Schedule or run the alert depending on whether a loop is already running.
            try:
                asyncio.get_running_loop()
                asyncio.create_task(
                    alert_rate_limit_violation(
                        identifier,
                        info["current_requests"],
                        100,  # Default limit
                        {"rate_limit_info": info},
                    )
                )
            except RuntimeError:
                asyncio.run(
                    alert_rate_limit_violation(
                        identifier,
                        info["current_requests"],
                        100,  # Default limit
                        {"rate_limit_info": info},
                    )
                )

        except Exception as e:
            # Don't let alerting failures break rate limiting
            logger.warning(f"Failed to trigger rate limit alert: {e}")


def sanitize_arguments_for_logging(arguments: dict[str, Any]) -> dict[str, Any]:
    """Redact/truncate tool arguments so they're safe to log.

    Redacts fields whose name suggests a secret (password/token/secret/key)
    and truncates long string values (note content, search queries) rather
    than logging them in full.
    """
    sanitized = {}
    for key, value in arguments.items():
        if key.lower() in ["password", "token", "secret", "key"]:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:100] + "... [TRUNCATED]"
        else:
            sanitized[key] = value
    return sanitized


class RequestValidator:
    """Comprehensive request validation middleware."""

    def __init__(self, security_validator=None):
        """Initialize request validator."""
        if security_validator is None:
            # Import here to avoid circular imports
            from .security import SecurityValidator

            security_validator = SecurityValidator()
        self.security_validator = security_validator
        self.request_history = defaultdict(list)

    def validate_request(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Validate incoming request.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments
            context: Additional context (client info, etc.)

        Returns:
            Validated arguments

        Raises:
            ValidationError: If request is invalid
            SecurityError: If request poses security risk
        """
        context = context or {}

        # Basic request structure validation
        self._validate_request_structure(tool_name, arguments)

        # Security validation
        validated_args = self.security_validator.validate_arguments(
            arguments, tool_name
        )

        # Check for suspicious patterns
        self._check_suspicious_patterns(tool_name, validated_args, context)

        # Log request for monitoring
        self._log_request(tool_name, validated_args, context)

        return validated_args

    def _validate_request_structure(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> None:
        """Validate basic request structure."""
        if not isinstance(tool_name, str):
            raise type_validation_error("tool_name", "string", tool_name)
        if not tool_name:
            raise empty_field_error("tool_name")

        if not isinstance(arguments, dict):
            raise type_validation_error("arguments", "dictionary", arguments)

        # Check for excessively large requests
        request_size = len(str(arguments))
        if request_size > 1024 * 1024:  # 1MB
            raise range_validation_error(
                "request_size", max_value=1024 * 1024, actual_value=request_size
            )

    def _check_suspicious_patterns(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """Check for suspicious request patterns."""
        client_id = context.get("client_id", "unknown")
        now = time.time()

        # Track request history
        self.request_history[client_id].append(
            {
                "tool_name": tool_name,
                "timestamp": now,
                "arguments": arguments,
            }
        )

        # Keep only recent history (last hour)
        cutoff = now - 3600
        self.request_history[client_id] = [
            req for req in self.request_history[client_id] if req["timestamp"] > cutoff
        ]

        recent_requests = self.request_history[client_id]

        # Check for suspicious patterns
        self._check_rapid_identical_requests(recent_requests, client_id)
        self._check_enumeration_attacks(recent_requests, client_id)
        self._check_unusual_parameter_patterns(arguments, client_id)

    def _check_rapid_identical_requests(
        self, requests: list[dict], client_id: str
    ) -> None:
        """Check for rapid identical requests (potential replay attack)."""
        if len(requests) < 5:
            return

        # Check last 5 requests
        recent_5 = requests[-5:]
        if len({str(req["arguments"]) for req in recent_5}) == 1:
            # All 5 requests are identical
            time_span = recent_5[-1]["timestamp"] - recent_5[0]["timestamp"]
            if time_span < 10:  # Within 10 seconds
                logger.warning(f"Potential replay attack detected from {client_id}")
                raise SecurityError("Suspicious request pattern detected")

    def _check_enumeration_attacks(self, requests: list[dict], client_id: str) -> None:
        """Check for enumeration attacks."""
        if len(requests) < 10:
            return

        # Look for patterns like sequential note IDs
        note_ids = []
        for req in requests[-10:]:
            if req["tool_name"] in ["get_note", "update_note", "delete_note"]:
                note_id = req["arguments"].get("note_id")
                if note_id and note_id.isdigit():
                    note_ids.append(int(note_id))

        if len(note_ids) >= 5:
            # Check if they're sequential
            note_ids.sort()
            sequential_count = 0
            for i in range(len(note_ids) - 1):
                if note_ids[i + 1] - note_ids[i] == 1:
                    sequential_count += 1

            if sequential_count >= 4:  # 5 sequential IDs
                logger.warning(
                    f"Potential enumeration attack detected from {client_id}"
                )
                raise SecurityError("Enumeration attack pattern detected")

    def _check_unusual_parameter_patterns(
        self, arguments: dict[str, Any], client_id: str
    ) -> None:
        """Check for unusual parameter patterns."""
        # Check for excessively long parameter values
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 50000:  # 50KB per parameter
                logger.warning(f"Unusually large parameter '{key}' from {client_id}")

        # Check for unusual parameter counts
        if len(arguments) > 20:  # Too many parameters
            logger.warning(
                f"Unusual parameter count ({len(arguments)}) from {client_id}"
            )

    def _log_request(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """Log request for security monitoring."""
        client_id = context.get("client_id", "unknown")
        sanitized_args = self._sanitize_arguments(arguments)

        logger.info(
            f"Request validated: tool={tool_name}, client={client_id}, "
            f"args_count={len(arguments)}"
        )
        logger.debug(f"Request details: {sanitized_args}")

    def _sanitize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Sanitize arguments for logging (remove sensitive data)."""
        return sanitize_arguments_for_logging(arguments)


class AuthenticationMiddleware:
    """Authentication and session management middleware."""

    # Class-level flag to warn only once about missing SESSION_SECRET_KEY
    _session_key_warning_logged = False

    def __init__(self):
        """Initialize authentication middleware."""
        self.session_store = {}
        self.failed_auth_attempts = defaultdict(list)
        self.session_timeout = 3600  # 1 hour default

    def validate_session(self, session_token: str, client_id: str) -> dict[str, Any]:
        """Validate session token.

        Args:
            session_token: Session token to validate
            client_id: Client identifier

        Returns:
            Session information

        Raises:
            AuthenticationError: If session is invalid
        """
        if not session_token:
            self._record_auth_failure(client_id, "Missing session token")
            raise AuthenticationError("Session token required")

        session = self.session_store.get(session_token)
        if not session:
            self._record_auth_failure(client_id, "Invalid session token")
            raise AuthenticationError("Invalid session token")

        # Check session expiry
        now = time.time()
        if now > session["expires_at"]:
            self._cleanup_expired_session(session_token)
            self._record_auth_failure(client_id, "Expired session token")
            raise AuthenticationError("Session expired")

        # Check client ID match
        if session["client_id"] != client_id:
            self._record_auth_failure(client_id, "Client ID mismatch")
            raise AuthenticationError("Session client mismatch")

        # Update last activity
        session["last_activity"] = now

        return session

    def create_session(
        self, user_id: str, client_id: str, timeout: int | None = None
    ) -> str:
        """Create new session.

        Args:
            user_id: User identifier
            client_id: Client identifier
            timeout: Session timeout in seconds

        Returns:
            Session token
        """
        now = time.time()
        timeout = timeout or self.session_timeout

        # Generate secure session token
        session_token = self._generate_session_token(user_id, client_id, now)

        session = {
            "user_id": user_id,
            "client_id": client_id,
            "created_at": now,
            "last_activity": now,
            "expires_at": now + timeout,
        }

        self.session_store[session_token] = session

        logger.info(f"Session created for user {user_id}, client {client_id}")
        return session_token

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        now = time.time()
        expired_tokens = [
            token
            for token, session in self.session_store.items()
            if now > session["expires_at"]
        ]

        for token in expired_tokens:
            self._cleanup_expired_session(token)

        return len(expired_tokens)

    def _generate_session_token(
        self, user_id: str, client_id: str, timestamp: float
    ) -> str:
        """Generate secure session token."""
        import os
        import secrets

        # Use HMAC for secure token generation
        # Get secret key from environment or generate ephemeral key for dev
        secret_key = os.environ.get("SESSION_SECRET_KEY")
        if not secret_key:
            if not AuthenticationMiddleware._session_key_warning_logged:
                logger.warning(
                    "SESSION_SECRET_KEY not set - generating ephemeral key. "
                    "Sessions will not persist across server restarts. "
                    "Set SESSION_SECRET_KEY environment variable for production use."
                )
                AuthenticationMiddleware._session_key_warning_logged = True
            secret_key = secrets.token_hex(32)

        data = f"{user_id}:{client_id}:{timestamp}".encode()
        signature = hmac.new(secret_key.encode(), data, hashlib.sha256).hexdigest()
        return f"{timestamp}:{signature}"

    def _cleanup_expired_session(self, session_token: str) -> None:
        """Clean up expired session."""
        if session_token in self.session_store:
            session = self.session_store[session_token]
            logger.debug(f"Cleaning up expired session for user {session['user_id']}")
            del self.session_store[session_token]

    def _record_auth_failure(self, client_id: str, reason: str) -> None:
        """Record authentication failure."""
        now = time.time()
        self.failed_auth_attempts[client_id].append(
            {
                "timestamp": now,
                "reason": reason,
            }
        )

        # Clean old failures (keep last 24 hours)
        cutoff = now - 86400
        self.failed_auth_attempts[client_id] = [
            failure
            for failure in self.failed_auth_attempts[client_id]
            if failure["timestamp"] > cutoff
        ]

        # Check for excessive failures
        recent_failures = [
            failure
            for failure in self.failed_auth_attempts[client_id]
            if failure["timestamp"] > now - 3600  # Last hour
        ]

        if len(recent_failures) >= 10:
            logger.warning(f"Excessive authentication failures from {client_id}")

        logger.warning(f"Authentication failure from {client_id}: {reason}")


# Global middleware instances
rate_limiter = RateLimiter()
request_validator = RequestValidator()
auth_middleware = AuthenticationMiddleware()


def with_rate_limiting(
    max_requests: int = 100,
    window_seconds: int = 900,
    strategy: str = "sliding_window",
    identifier_func: Callable | None = None,
):
    """Decorator for rate limiting."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get client identifier
            if identifier_func:
                client_id = identifier_func(*args, **kwargs)
            else:
                client_id = kwargs.get("client_id", "default")

            # Check rate limit
            rate_limiter.check_rate_limit(
                client_id, max_requests, window_seconds, strategy
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_request_validation(require_auth: bool = False):
    """Decorator for request validation."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract tool name and arguments from both positional and keyword args
            if len(args) >= 2:
                # Called with positional arguments: handle_call_tool(name, arguments)
                tool_name = args[0]
                arguments = args[1]
                context = kwargs.get("context", {})
            else:
                # Called with keyword arguments
                tool_name = kwargs.get("tool_name", "unknown")
                arguments = kwargs.get("arguments", {})
                context = kwargs.get("context", {})

            # Validate request
            validated_args = request_validator.validate_request(
                tool_name, arguments, context
            )

            # Update arguments with validated ones
            if len(args) >= 2:
                # Called with positional arguments - update the args tuple
                args = (args[0], validated_args) + args[2:]
            else:
                # Called with keyword arguments
                kwargs["arguments"] = validated_args

            # Authentication check if required
            if require_auth:
                session_token = context.get("session_token")
                client_id = context.get("client_id", "unknown")
                session = auth_middleware.validate_session(session_token, client_id)
                kwargs["session"] = session

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def with_security_monitoring():
    """Decorator for security monitoring."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Log successful operation
                duration = time.time() - start_time
                logger.debug(f"Operation {func.__name__} completed in {duration:.3f}s")

                return result

            except (SecurityError, ValidationError, AuthenticationError) as e:
                # Log security-related errors
                logger.warning(f"Security error in {func.__name__}: {str(e)}")
                raise

            except Exception as e:
                # Log unexpected errors
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True
                )
                raise

        return wrapper

    return decorator
