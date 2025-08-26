"""Security validation and protection for Simplenote MCP server.

This module provides comprehensive security validation for all MCP tools and operations,
including input sanitization, rate limiting, authentication checks, and security logging.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from .error_helpers import (
    range_validation_error,
    security_violation_error,
    validate_list_or_string,
    validate_not_empty,
    validate_string_type,
)
from .errors import SecurityError, ValidationError
from .logging import logger


class SecurityValidator:
    """Comprehensive security validation for MCP tools."""

    # Security patterns and limits
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    MAX_TAG_LENGTH = 100
    MAX_TAGS_COUNT = 50
    MAX_NOTE_ID_LENGTH = 100
    MAX_QUERY_LENGTH = 1000

    # Dangerous patterns to detect - refined to reduce false positives while maintaining security
    DANGEROUS_PATTERNS = [
        # SQL injection patterns - keep both broad and specific patterns for comprehensive protection
        r"(\b(union\s+select|drop\s+table|insert\s+into|delete\s+from)\b)",
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE)\s+(FROM|INTO|TABLE|DATABASE|WHERE)\b)",
        r"(\b(SELECT|DROP|INSERT|UPDATE|DELETE)\s+\*?\s*(FROM|TABLE|INTO)?\s+\w+)",
        r'([\'"];\s*(DROP|DELETE|UPDATE|INSERT))',
        r"(\bOR\s+\d+\s*=\s*\d+\b)",
        r"(\'\s*OR\s*\'\w*\'\s*=\s*\')",
        # XSS patterns
        r"(<script[^>]*>.*?</script>)",
        r"(javascript:)",
        r"(on\w+\s*=\s*['\"]?[^'\">]*['\">])",
        r"(on\w+\s*=)",
        r"(<iframe[^>]*>)",
        r"(eval\s*\()",
        # Path traversal
        r"(\.\./|\.\.\\)",
        r"(/etc/passwd|/etc/shadow|/proc/)",
        # Command injection - balance between security and false positives
        r"(;\s*(rm|cat|ls|chmod|wget|curl|bash|sh|whoami|id)(\s+|$))",
        r"(\$\w+;\s*(rm|cat|ls|chmod|wget|curl|bash|sh))",
        r"(\$\([^)]*\))",
        r"(`(rm|cat|ls|chmod|wget|curl|bash|sh|whoami|id|echo|pwd)[^`]*`)",  # Backticks with dangerous commands
        r"(\|\s*(rm|cat|ls|chmod|wget|curl|bash|sh|whoami|id)(\s+|$))",
        r"(&&\s*(rm|cat|ls|chmod|wget|curl|bash|sh)(\s+|$))",
        r"(&\s+(rm|cat|ls|chmod|wget|curl|bash|sh|whoami|id)(\s+|$))",
        # LDAP injection
        r"(\*\)|(\)\(|\(\*))",
        # Code injection
        r"(__import__|exec\(|eval\()",
    ]

    # Compile patterns for performance
    COMPILED_PATTERNS = [
        re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS
    ]

    def __init__(self):
        """Initialize security validator."""
        self.failed_validation_attempts = defaultdict(list)
        self.rate_limit_attempts = defaultdict(list)

    def validate_note_content(
        self, content: str, context: str = "note content"
    ) -> None:
        """Validate note content for security issues.

        Args:
            content: The note content to validate
            context: Context for logging/error messages

        Raises:
            ValidationError: If content fails validation
            SecurityError: If content contains security threats
        """
        validate_string_type("content", content)

        # Length validation
        if len(content) > self.MAX_CONTENT_LENGTH:
            self._log_security_event(
                "content_length_exceeded",
                f"Content length {len(content)} exceeds maximum {self.MAX_CONTENT_LENGTH}",
                context,
            )
            raise ValidationError(
                f"Content too long (max {self.MAX_CONTENT_LENGTH} characters)"
            )

        # Security pattern detection
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(content):
                self._log_security_event(
                    "dangerous_pattern_detected",
                    f"Potentially dangerous pattern found in {context}",
                    context,
                    severity="HIGH",
                )
                raise SecurityError(
                    f"Potentially dangerous content detected in {context}"
                )

    def validate_note_id(self, note_id: str, context: str = "note ID") -> None:
        """Validate note ID for security and format.

        Args:
            note_id: The note ID to validate
            context: Context for logging/error messages

        Raises:
            ValidationError: If note_id fails validation
        """
        validate_string_type("note_id", note_id)

        validate_not_empty("note_id", note_id)

        if len(note_id) > self.MAX_NOTE_ID_LENGTH:
            raise ValidationError(
                f"Note ID too long (max {self.MAX_NOTE_ID_LENGTH} characters)",
                field="note_id",
                subcategory="length",
            )

        # Note IDs should be alphanumeric with hyphens/underscores only
        if not re.match(r"^[a-zA-Z0-9\-_]+$", note_id):
            self._log_security_event(
                "invalid_note_id_format", f"Invalid note ID format: {note_id}", context
            )
            raise ValidationError("Note ID contains invalid characters")

    def validate_tags(self, tags: str | list[str], context: str = "tags") -> list[str]:
        """Validate and sanitize tags.

        Args:
            tags: Tags as string or list
            context: Context for logging/error messages

        Returns:
            List of validated tags

        Raises:
            ValidationError: If tags fail validation
        """
        if isinstance(tags, str):
            if not tags.strip():
                return []
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            tag_list = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            validate_list_or_string("tags", tags)

        if len(tag_list) > self.MAX_TAGS_COUNT:
            raise range_validation_error(
                "tag_count", max_value=self.MAX_TAGS_COUNT, actual_value=len(tag_list)
            )

        validated_tags = []
        for tag in tag_list:
            if len(tag) > self.MAX_TAG_LENGTH:
                raise ValidationError(
                    f"Tag too long: '{tag}' (max {self.MAX_TAG_LENGTH} characters)"
                )

            # Tags should not contain dangerous characters
            if not re.match(r"^[a-zA-Z0-9\s\-_#@.]+$", tag):
                self._log_security_event(
                    "invalid_tag_format", f"Invalid tag format: {tag}", context
                )
                raise ValidationError(
                    f"Tag contains invalid characters: '{tag}'",
                    field="tag",
                    subcategory="format",
                    details={"tag": tag, "allowed_pattern": r"a-zA-Z0-9\s\-_#@."},
                )

            validated_tags.append(tag)

        return validated_tags

    def validate_search_query(self, query: str, context: str = "search query") -> None:
        """Validate search query for security issues.

        Args:
            query: The search query to validate
            context: Context for logging/error messages

        Raises:
            ValidationError: If query fails validation
            SecurityError: If query contains security threats
        """
        validate_string_type("search_query", query)

        validate_not_empty("search_query", query)

        if len(query) > self.MAX_QUERY_LENGTH:
            raise ValidationError(
                f"Search query too long (max {self.MAX_QUERY_LENGTH} characters)",
                field="search_query",
                subcategory="length",
            )

        # Check for injection patterns
        for pattern in self.COMPILED_PATTERNS:
            if pattern.search(query):
                self._log_security_event(
                    "dangerous_search_pattern",
                    "Potentially dangerous pattern in search query",
                    context,
                    severity="HIGH",
                )
                raise security_violation_error(
                    "Dangerous search query pattern",
                    "Query contains potentially malicious patterns",
                )

    def validate_pagination_params(
        self, limit: Any = None, offset: Any = None
    ) -> tuple[int | None, int | None]:
        """Validate pagination parameters.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (validated_limit, validated_offset)

        Raises:
            ValidationError: If parameters are invalid
        """
        validated_limit = None
        validated_offset = None

        if limit is not None:
            try:
                validated_limit = int(limit)
                if validated_limit < 0:
                    raise ValidationError("Limit must be non-negative")
                if validated_limit > 1000:  # Reasonable upper bound
                    raise ValidationError("Limit too large (max 1000)")
            except (ValueError, TypeError) as e:
                raise ValidationError("Limit must be a valid integer") from e

        if offset is not None:
            try:
                validated_offset = int(offset)
                if validated_offset < 0:
                    raise ValidationError("Offset must be non-negative")
            except (ValueError, TypeError) as e:
                raise ValidationError("Offset must be a valid integer") from e

        return validated_limit, validated_offset

    def validate_date_range(
        self, from_date: Any = None, to_date: Any = None
    ) -> tuple[datetime | None, datetime | None]:
        """Validate date range parameters.

        Args:
            from_date: Start date (ISO format string or datetime)
            to_date: End date (ISO format string or datetime)

        Returns:
            Tuple of (validated_from_date, validated_to_date)

        Raises:
            ValidationError: If dates are invalid
        """
        validated_from = None
        validated_to = None

        if from_date is not None:
            if isinstance(from_date, str):
                try:
                    validated_from = datetime.fromisoformat(
                        from_date.replace("Z", "+00:00")
                    )
                except ValueError as e:
                    raise ValidationError(
                        f"Invalid from_date format: {from_date}"
                    ) from e
            elif isinstance(from_date, datetime):
                validated_from = from_date
            else:
                raise ValidationError("from_date must be a string or datetime")

        if to_date is not None:
            if isinstance(to_date, str):
                try:
                    validated_to = datetime.fromisoformat(
                        to_date.replace("Z", "+00:00")
                    )
                except ValueError as e:
                    raise ValidationError(f"Invalid to_date format: {to_date}") from e
            elif isinstance(to_date, datetime):
                validated_to = to_date
            else:
                raise ValidationError("to_date must be a string or datetime")

        # Validate date range logic
        if validated_from and validated_to:
            if validated_from > validated_to:
                raise ValidationError("from_date must be before to_date")

            # Prevent extremely large date ranges (potential DoS)
            if (validated_to - validated_from).days > 3650:  # 10 years
                raise ValidationError("Date range too large (max 10 years)")

        return validated_from, validated_to

    def validate_uri(self, uri: str, allowed_schemes: list[str] = None) -> None:
        """Validate URI for security issues.

        Args:
            uri: URI to validate
            allowed_schemes: List of allowed URI schemes

        Raises:
            ValidationError: If URI is invalid
            SecurityError: If URI contains security threats
        """
        if not isinstance(uri, str):
            raise ValidationError(f"URI must be a string, got {type(uri)}")

        if not uri.strip():
            raise ValidationError("URI cannot be empty")

        try:
            parsed = urlparse(uri)
        except Exception as e:
            raise ValidationError("Invalid URI format") from e

        # Check allowed schemes
        if allowed_schemes is None:
            allowed_schemes = ["simplenote", "https", "http"]

        if parsed.scheme and parsed.scheme.lower() not in allowed_schemes:
            self._log_security_event(
                "disallowed_uri_scheme",
                f"Disallowed URI scheme: {parsed.scheme}",
                "URI validation",
            )
            raise SecurityError(f"URI scheme '{parsed.scheme}' not allowed")

    def check_rate_limit(
        self, identifier: str, max_requests: int = 100, window_minutes: int = 15
    ) -> None:
        """Check rate limiting for requests.

        Args:
            identifier: Unique identifier for the requester
            max_requests: Maximum requests allowed in window
            window_minutes: Time window in minutes

        Raises:
            SecurityError: If rate limit is exceeded
        """
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        # Clean old entries
        self.rate_limit_attempts[identifier] = [
            timestamp
            for timestamp in self.rate_limit_attempts[identifier]
            if timestamp > window_start
        ]

        # Check current count
        current_count = len(self.rate_limit_attempts[identifier])
        if current_count >= max_requests:
            self._log_security_event(
                "rate_limit_exceeded",
                f"Rate limit exceeded for {identifier}: {current_count}/{max_requests}",
                "rate limiting",
                severity="HIGH",
            )
            raise SecurityError(
                f"Rate limit exceeded: {max_requests} requests per {window_minutes} minutes"
            )

        # Record this attempt
        self.rate_limit_attempts[identifier].append(now)

    def sanitize_output(self, output: str) -> str:
        """Sanitize output to prevent information leakage.

        Args:
            output: Output string to sanitize

        Returns:
            Sanitized output string
        """
        if not isinstance(output, str):
            return str(output)

        # Remove potential sensitive patterns
        sensitive_patterns = [
            (r"password[s]?\s*[:=]\s*[^\s]+", "password: [REDACTED]"),
            (r"token[s]?\s*[:=]\s*[^\s]+", "token: [REDACTED]"),
            (r"key[s]?\s*[:=]\s*[^\s]+", "key: [REDACTED]"),
            (r"secret[s]?\s*[:=]\s*[^\s]+", "secret: [REDACTED]"),
        ]

        sanitized = output
        for pattern, replacement in sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def validate_arguments(
        self, arguments: dict[str, Any], tool_name: str
    ) -> dict[str, Any]:
        """Comprehensive validation of tool arguments.

        Args:
            arguments: Dictionary of tool arguments
            tool_name: Name of the tool being called

        Returns:
            Dictionary of validated and sanitized arguments

        Raises:
            ValidationError: If arguments fail validation
            SecurityError: If arguments contain security threats
        """
        if not isinstance(arguments, dict):
            raise ValidationError("Arguments must be a dictionary")

        validated_args = {}

        # Tool-specific validation
        if tool_name in ["create_note", "update_note"]:
            if "content" in arguments:
                self.validate_note_content(arguments["content"], f"{tool_name} content")
                validated_args["content"] = arguments["content"]

            if "tags" in arguments:
                validated_args["tags"] = self.validate_tags(
                    arguments["tags"], f"{tool_name} tags"
                )

        if tool_name in [
            "update_note",
            "delete_note",
            "get_note",
            "add_tags",
            "remove_tags",
            "replace_tags",
        ]:
            if "note_id" in arguments:
                self.validate_note_id(arguments["note_id"], f"{tool_name} note_id")
                validated_args["note_id"] = arguments["note_id"]

        if tool_name == "search_notes":
            if "query" in arguments:
                self.validate_search_query(arguments["query"], f"{tool_name} query")
                validated_args["query"] = arguments["query"]

            if "limit" in arguments or "offset" in arguments:
                limit, offset = self.validate_pagination_params(
                    arguments.get("limit"), arguments.get("offset")
                )
                if limit is not None:
                    validated_args["limit"] = limit
                if offset is not None:
                    validated_args["offset"] = offset

            if "from_date" in arguments or "to_date" in arguments:
                from_date, to_date = self.validate_date_range(
                    arguments.get("from_date"), arguments.get("to_date")
                )
                if from_date is not None:
                    validated_args["from_date"] = from_date
                if to_date is not None:
                    validated_args["to_date"] = to_date

            if "tags" in arguments:
                validated_args["tags"] = self.validate_tags(
                    arguments["tags"], f"{tool_name} tag filters"
                )

        # Copy other arguments after basic validation
        for key, value in arguments.items():
            if key not in validated_args:
                # Basic type and length validation for unknown parameters
                if isinstance(value, str) and len(value) > 10000:
                    raise ValidationError(f"Parameter '{key}' too long")
                validated_args[key] = value

        return validated_args

    def _log_security_event(
        self, event_type: str, message: str, context: str, severity: str = "MEDIUM"
    ) -> None:
        """Log security events for monitoring and analysis.

        Args:
            event_type: Type of security event
            message: Detailed message
            context: Context where event occurred
            severity: Event severity (LOW, MEDIUM, HIGH)
        """
        timestamp = datetime.now().isoformat()

        security_log = {
            "timestamp": timestamp,
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "context": context,
        }

        # Log with appropriate level
        if severity == "HIGH":
            logger.error(
                f"SECURITY ALERT [{event_type}]: {message} (context: {context})"
            )
        elif severity == "MEDIUM":
            logger.warning(
                f"SECURITY WARNING [{event_type}]: {message} (context: {context})"
            )
        else:
            logger.info(f"SECURITY INFO [{event_type}]: {message} (context: {context})")

        # Store for analysis (in a real system, this might go to a security database)
        self.failed_validation_attempts[event_type].append(security_log)

        # Trigger alerting for high-severity events
        if severity == "HIGH":
            self._trigger_security_alert(event_type, message, context)

    def _trigger_security_alert(
        self, event_type: str, message: str, context: str
    ) -> None:
        """Trigger security alert for high-severity events.

        Args:
            event_type: Type of security event
            message: Detailed message
            context: Context where event occurred
        """
        try:
            # Lazy import to avoid circular dependency
            import asyncio

            from .alerting import AlertSeverity, AlertType, get_alerter

            # Map event types to alert types
            alert_type_mapping = {
                "dangerous_pattern_detected": AlertType.DANGEROUS_INPUT,
                "dangerous_search_pattern": AlertType.DANGEROUS_INPUT,
                "rate_limit_exceeded": AlertType.RATE_LIMIT_VIOLATION,
                "repeated_failures": AlertType.REPEATED_FAILURES,
                "authentication_failure": AlertType.AUTHENTICATION_FAILURE,
            }

            alert_type = alert_type_mapping.get(
                event_type, AlertType.SUSPICIOUS_PATTERN
            )

            # Create alert asynchronously
            alerter = get_alerter()

            # Try to get the current event loop, create one if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the coroutine to run
                    asyncio.create_task(
                        alerter.create_alert(
                            alert_type,
                            AlertSeverity.HIGH,
                            message,
                            {"event_type": event_type, "context": context},
                        )
                    )
                else:
                    # Run in the current loop
                    loop.run_until_complete(
                        alerter.create_alert(
                            alert_type,
                            AlertSeverity.HIGH,
                            message,
                            {"event_type": event_type, "context": context},
                        )
                    )
            except RuntimeError:
                # No event loop, create a new one
                asyncio.run(
                    alerter.create_alert(
                        alert_type,
                        AlertSeverity.HIGH,
                        message,
                        {"event_type": event_type, "context": context},
                    )
                )

        except Exception as e:
            # Don't let alerting failures break security validation
            logger.warning(f"Failed to trigger security alert: {e}")


# Global security validator instance
security_validator = SecurityValidator()


def validate_tool_security(tool_name: str):
    """Decorator for comprehensive tool security validation.

    Args:
        tool_name: Name of the tool being decorated
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract arguments (assume second parameter is arguments dict)
            arguments = (
                args[1]
                if len(args) > 1 and isinstance(args[1], dict)
                else kwargs.get("arguments", {})
            )

            # Perform comprehensive security validation
            try:
                validated_args = security_validator.validate_arguments(
                    arguments, tool_name
                )

                # Replace original arguments with validated ones
                if len(args) > 1:
                    args = list(args)
                    args[1] = validated_args
                    args = tuple(args)
                else:
                    kwargs["arguments"] = validated_args

            except (ValidationError, SecurityError) as e:
                logger.error(f"Security validation failed for {tool_name}: {str(e)}")
                # Re-raise to be handled by standard error handling
                raise

            return await func(*args, **kwargs)

        return wrapper

    return decorator
