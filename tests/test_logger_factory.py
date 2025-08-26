"""Tests for logger factory and standardized logging schema.

This module tests the logger factory system that creates loggers with
standardized schemas and contextual fields for consistent logging.
"""

from simplenote_mcp.server.logger_factory import (
    LogCategory,
    LogContext,
    LoggerFactory,
    create_contextual_logger,
    get_auth_logger,
    get_cache_logger,
    get_error_logger,
    get_logger_factory,
    get_performance_logger,
    get_request_logger,
    get_security_logger,
    get_simplenote_logger,
    get_tool_logger,
    with_logging_context,
)
from simplenote_mcp.server.logging import StructuredLogAdapter


class TestLogCategory:
    """Test log category enumeration."""

    def test_all_categories_present(self):
        """Test that all expected categories are defined."""
        expected_categories = [
            "authentication",
            "authorization",
            "cache",
            "configuration",
            "database",
            "error_handling",
            "metrics",
            "network",
            "performance",
            "request",
            "response",
            "security",
            "server",
            "simplenote_api",
            "tool",
            "validation",
            "general",
        ]

        actual_categories = [cat.value for cat in LogCategory]

        for expected in expected_categories:
            assert expected in actual_categories

    def test_category_values(self):
        """Test specific category values."""
        assert LogCategory.AUTHENTICATION.value == "authentication"
        assert LogCategory.SECURITY.value == "security"
        assert LogCategory.PERFORMANCE.value == "performance"
        assert LogCategory.TOOL.value == "tool"


class TestLogContext:
    """Test log context functionality."""

    def test_basic_initialization(self):
        """Test basic context initialization."""
        context = LogContext(
            user_id="test_user",
            operation="test_operation",
            category=LogCategory.AUTHENTICATION,
        )

        assert context.user_id == "test_user"
        assert context.operation == "test_operation"
        assert context.category == LogCategory.AUTHENTICATION
        assert context.request_id is not None
        assert context.trace_id is not None
        assert context.timestamp is not None

    def test_auto_component_detection(self):
        """Test automatic component name detection."""
        context = LogContext()

        # Should detect component from calling module
        assert context.component is not None
        # In test context, might be 'test_logger_factory' or similar
        assert isinstance(context.component, str)

    def test_context_to_dict(self):
        """Test conversion of context to dictionary."""
        context = LogContext(
            user_id="test_user",
            session_id="test_session",
            operation="test_op",
            category=LogCategory.SECURITY,
            extra={"custom_field": "custom_value"},
        )

        context_dict = context.to_dict()

        assert context_dict["user_id"] == "test_user"
        assert context_dict["session_id"] == "test_session"
        assert context_dict["operation"] == "test_op"
        assert context_dict["category"] == "security"
        assert context_dict["custom_field"] == "custom_value"
        assert "request_id" in context_dict
        assert "trace_id" in context_dict
        assert "timestamp" in context_dict

    def test_context_with_operation(self):
        """Test creating new context with updated operation."""
        original = LogContext(user_id="test_user", operation="original_op")
        updated = original.with_operation("new_operation")

        assert original.operation == "original_op"
        assert updated.operation == "new_operation"
        assert updated.user_id == "test_user"
        assert updated.request_id == original.request_id

    def test_context_with_user(self):
        """Test creating new context with user information."""
        original = LogContext(operation="test_op")
        updated = original.with_user("new_user")

        assert original.user_id is None
        assert updated.user_id == "new_user"
        assert updated.operation == "test_op"

    def test_context_with_extra(self):
        """Test creating new context with additional fields."""
        original = LogContext(user_id="test_user")
        updated = original.with_extra(custom_field="custom_value", another_field=123)

        assert updated.user_id == "test_user"
        assert updated.extra["custom_field"] == "custom_value"
        assert updated.extra["another_field"] == 123
        assert len(original.extra) == 0  # Original unchanged

    def test_context_optional_fields(self):
        """Test that optional fields are handled correctly."""
        context = LogContext()
        context_dict = context.to_dict()

        # Optional fields should not be included if None
        assert "user_id" not in context_dict
        assert "session_id" not in context_dict
        assert "operation" not in context_dict

        # Required fields should always be present
        assert "request_id" in context_dict
        assert "trace_id" in context_dict
        assert "category" in context_dict
        assert "timestamp" in context_dict


class TestLoggerFactory:
    """Test logger factory functionality."""

    def test_factory_initialization(self):
        """Test factory initialization."""
        factory = LoggerFactory()
        assert factory._default_context is not None
        assert isinstance(factory._default_context, LogContext)

    def test_create_basic_logger(self):
        """Test creating a basic logger."""
        factory = LoggerFactory()
        logger = factory.create_logger("test")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.logger.name == "simplenote_mcp.test"

    def test_create_logger_with_context(self):
        """Test creating logger with context object."""
        factory = LoggerFactory()
        context = LogContext(
            user_id="test_user",
            operation="test_operation",
            category=LogCategory.AUTHENTICATION,
        )

        logger = factory.create_logger("auth", context)

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "test_user"
        assert logger.extra["operation"] == "test_operation"
        assert logger.extra["category"] == "authentication"

    def test_create_logger_with_kwargs(self):
        """Test creating logger with keyword arguments."""
        factory = LoggerFactory()
        logger = factory.create_logger("test", user_id="test_user", operation="test_op")

        assert logger.extra["user_id"] == "test_user"
        assert logger.extra["operation"] == "test_op"

    def test_authentication_logger(self):
        """Test creating authentication logger."""
        factory = LoggerFactory()
        logger = factory.create_authentication_logger(
            user_id="auth_user", operation="login", client_ip="192.168.1.1"
        )

        assert logger.extra["user_id"] == "auth_user"
        assert logger.extra["operation"] == "login"
        assert logger.extra["category"] == "authentication"
        assert logger.extra["component"] == "auth"
        assert logger.extra["client_ip"] == "192.168.1.1"

    def test_request_logger(self):
        """Test creating request logger."""
        factory = LoggerFactory()
        logger = factory.create_request_logger(
            request_id="req_123", user_id="request_user", operation="create_note"
        )

        assert logger.extra["request_id"] == "req_123"
        assert logger.extra["user_id"] == "request_user"
        assert logger.extra["operation"] == "create_note"
        assert logger.extra["category"] == "request"
        assert logger.extra["component"] == "request_handler"

    def test_security_logger(self):
        """Test creating security logger."""
        factory = LoggerFactory()
        logger = factory.create_security_logger(
            user_id="security_user",
            operation="failed_login",
            threat_level="high",
            attack_type="brute_force",
        )

        assert logger.extra["user_id"] == "security_user"
        assert logger.extra["operation"] == "failed_login"
        assert logger.extra["category"] == "security"
        assert logger.extra["component"] == "security"
        assert logger.extra["threat_level"] == "high"
        assert logger.extra["attack_type"] == "brute_force"

    def test_performance_logger(self):
        """Test creating performance logger."""
        factory = LoggerFactory()
        logger = factory.create_performance_logger(
            operation="search_notes", duration=0.25, memory_usage=1024
        )

        assert logger.extra["operation"] == "search_notes"
        assert logger.extra["category"] == "performance"
        assert logger.extra["component"] == "metrics"
        assert logger.extra["duration_seconds"] == 0.25
        assert logger.extra["memory_usage"] == 1024

    def test_tool_logger(self):
        """Test creating tool logger."""
        factory = LoggerFactory()
        logger = factory.create_tool_logger(
            tool_name="create_note",
            user_id="tool_user",
            operation="execute",
            tool_version="1.0",
        )

        assert logger.extra["tool_name"] == "create_note"
        assert logger.extra["user_id"] == "tool_user"
        assert logger.extra["operation"] == "execute"
        assert logger.extra["category"] == "tool"
        assert logger.extra["component"] == "tool_handler"
        assert logger.extra["tool_version"] == "1.0"

    def test_simplenote_logger(self):
        """Test creating Simplenote API logger."""
        factory = LoggerFactory()
        logger = factory.create_simplenote_logger(
            operation="get_note", note_id="note_123", api_version="v2"
        )

        assert logger.extra["operation"] == "get_note"
        assert logger.extra["note_id"] == "note_123"
        assert logger.extra["category"] == "simplenote_api"
        assert logger.extra["component"] == "simplenote_client"
        assert logger.extra["api_version"] == "v2"

    def test_cache_logger(self):
        """Test creating cache logger."""
        factory = LoggerFactory()
        logger = factory.create_cache_logger(
            operation="cache_hit",
            cache_key="notes:user_123",
            hit_rate=0.85,
            cache_size=1000,
        )

        assert logger.extra["operation"] == "cache_hit"
        assert logger.extra["cache_key"] == "notes:user_123"
        assert logger.extra["category"] == "cache"
        assert logger.extra["component"] == "cache"
        assert logger.extra["hit_rate"] == 0.85
        assert logger.extra["cache_size"] == 1000

    def test_error_logger(self):
        """Test creating error logger."""
        factory = LoggerFactory()
        logger = factory.create_error_logger(
            error_type="ValidationError",
            error_code="VAL_001",
            user_id="error_user",
            operation="validate_input",
            stack_trace="line 1\nline 2",
        )

        assert logger.extra["error_type"] == "ValidationError"
        assert logger.extra["error_code"] == "VAL_001"
        assert logger.extra["user_id"] == "error_user"
        assert logger.extra["operation"] == "validate_input"
        assert logger.extra["category"] == "error_handling"
        assert logger.extra["component"] == "error_handler"
        assert logger.extra["stack_trace"] == "line 1\nline 2"

    def test_set_get_default_context(self):
        """Test setting and getting default context."""
        factory = LoggerFactory()
        default_context = LogContext(user_id="default_user", operation="default_op")

        factory.set_default_context(default_context)
        retrieved_context = factory.get_default_context()

        assert retrieved_context == default_context
        assert retrieved_context.user_id == "default_user"
        assert retrieved_context.operation == "default_op"


class TestGlobalFactoryFunctions:
    """Test global factory convenience functions."""

    def test_get_logger_factory_singleton(self):
        """Test that get_logger_factory returns singleton."""
        factory1 = get_logger_factory()
        factory2 = get_logger_factory()

        assert factory1 is factory2
        assert isinstance(factory1, LoggerFactory)

    def test_get_auth_logger(self):
        """Test convenience auth logger function."""
        logger = get_auth_logger(user_id="auth_test", operation="logout")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "auth_test"
        assert logger.extra["operation"] == "logout"
        assert logger.extra["category"] == "authentication"

    def test_get_request_logger(self):
        """Test convenience request logger function."""
        logger = get_request_logger(user_id="req_test", operation="search")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "req_test"
        assert logger.extra["operation"] == "search"
        assert logger.extra["category"] == "request"

    def test_get_security_logger(self):
        """Test convenience security logger function."""
        logger = get_security_logger(
            user_id="sec_test", operation="block_request", threat_level="critical"
        )

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "sec_test"
        assert logger.extra["threat_level"] == "critical"
        assert logger.extra["category"] == "security"

    def test_get_performance_logger(self):
        """Test convenience performance logger function."""
        logger = get_performance_logger(operation="query", duration=1.5)

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["operation"] == "query"
        assert logger.extra["duration_seconds"] == 1.5
        assert logger.extra["category"] == "performance"

    def test_get_tool_logger(self):
        """Test convenience tool logger function."""
        logger = get_tool_logger("search_notes", user_id="tool_test")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["tool_name"] == "search_notes"
        assert logger.extra["user_id"] == "tool_test"
        assert logger.extra["category"] == "tool"

    def test_get_simplenote_logger(self):
        """Test convenience Simplenote logger function."""
        logger = get_simplenote_logger(operation="sync", note_id="note_456")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["operation"] == "sync"
        assert logger.extra["note_id"] == "note_456"
        assert logger.extra["category"] == "simplenote_api"

    def test_get_cache_logger(self):
        """Test convenience cache logger function."""
        logger = get_cache_logger(operation="evict", cache_key="expired_key")

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["operation"] == "evict"
        assert logger.extra["cache_key"] == "expired_key"
        assert logger.extra["category"] == "cache"

    def test_get_error_logger(self):
        """Test convenience error logger function."""
        logger = get_error_logger(
            error_type="NetworkError", error_code="NET_001", operation="api_call"
        )

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["error_type"] == "NetworkError"
        assert logger.extra["error_code"] == "NET_001"
        assert logger.extra["operation"] == "api_call"
        assert logger.extra["category"] == "error_handling"


class TestContextualLogging:
    """Test contextual logging functionality."""

    def test_create_contextual_logger_with_context_object(self):
        """Test creating contextual logger with LogContext object."""
        context = LogContext(
            user_id="contextual_user",
            operation="contextual_op",
            category=LogCategory.VALIDATION,
        )

        logger = create_contextual_logger("contextual", context)

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "contextual_user"
        assert logger.extra["operation"] == "contextual_op"
        assert logger.extra["category"] == "validation"

    def test_create_contextual_logger_with_dict(self):
        """Test creating contextual logger with dictionary context."""
        context_dict = {
            "user_id": "dict_user",
            "operation": "dict_op",
            "category": LogCategory.NETWORK,
        }

        logger = create_contextual_logger("contextual", context_dict)

        assert isinstance(logger, StructuredLogAdapter)
        assert logger.extra["user_id"] == "dict_user"
        assert logger.extra["operation"] == "dict_op"
        assert logger.extra["category"] == "network"

    def test_create_contextual_logger_with_extra_kwargs(self):
        """Test creating contextual logger with extra keyword arguments."""
        context = LogContext(user_id="base_user")

        logger = create_contextual_logger(
            "contextual", context, extra_field="extra_value", another_field=42
        )

        assert logger.extra["user_id"] == "base_user"
        assert logger.extra["extra_field"] == "extra_value"
        assert logger.extra["another_field"] == 42

    def test_with_logging_context_decorator(self):
        """Test logging context decorator."""

        @with_logging_context(category=LogCategory.TOOL, operation="decorated_function")
        def test_function(x, y, logger=None):
            assert logger is not None
            assert isinstance(logger, StructuredLogAdapter)
            assert logger.extra["category"] == "tool"
            assert logger.extra["operation"] == "decorated_function"
            return x + y

        result = test_function(2, 3)
        assert result == 5

    def test_with_logging_context_decorator_custom_logger(self):
        """Test logging context decorator with custom logger."""
        custom_logger = get_auth_logger(user_id="custom_user")

        @with_logging_context(category=LogCategory.AUTHENTICATION)
        def test_function(logger=custom_logger):
            # Should use provided logger, not create new one
            assert logger == custom_logger
            return "success"

        result = test_function()
        assert result == "success"


class TestLogSchemaConsistency:
    """Test logging schema consistency across different logger types."""

    def test_all_loggers_have_required_fields(self):
        """Test that all logger types include required fields."""
        factory = get_logger_factory()

        # Test all logger creation methods
        loggers = [
            factory.create_authentication_logger(user_id="test"),
            factory.create_request_logger(user_id="test"),
            factory.create_security_logger(user_id="test"),
            factory.create_performance_logger(operation="test"),
            factory.create_tool_logger("test_tool"),
            factory.create_simplenote_logger(operation="test"),
            factory.create_cache_logger(operation="test"),
            factory.create_error_logger(error_type="TestError"),
        ]

        required_fields = ["request_id", "trace_id", "category", "timestamp"]

        for logger in loggers:
            for field in required_fields:
                assert field in logger.extra, (
                    f"Missing {field} in {type(logger)} logger"
                )

    def test_category_consistency(self):
        """Test that each logger type has correct category."""
        factory = get_logger_factory()

        logger_categories = [
            (factory.create_authentication_logger(), "authentication"),
            (factory.create_request_logger(), "request"),
            (factory.create_security_logger(), "security"),
            (factory.create_performance_logger(), "performance"),
            (factory.create_tool_logger("test"), "tool"),
            (factory.create_simplenote_logger(), "simplenote_api"),
            (factory.create_cache_logger(), "cache"),
            (factory.create_error_logger(), "error_handling"),
        ]

        for logger, expected_category in logger_categories:
            assert logger.extra["category"] == expected_category

    def test_component_consistency(self):
        """Test that each logger type has expected component."""
        factory = get_logger_factory()

        logger_components = [
            (factory.create_authentication_logger(), "auth"),
            (factory.create_request_logger(), "request_handler"),
            (factory.create_security_logger(), "security"),
            (factory.create_performance_logger(), "metrics"),
            (factory.create_tool_logger("test"), "tool_handler"),
            (factory.create_simplenote_logger(), "simplenote_client"),
            (factory.create_cache_logger(), "cache"),
            (factory.create_error_logger(), "error_handler"),
        ]

        for logger, expected_component in logger_components:
            assert logger.extra["component"] == expected_component

    def test_trace_id_consistency(self):
        """Test that trace IDs are properly propagated."""
        context = LogContext(trace_id="test_trace_123")
        factory = get_logger_factory()

        logger = factory.create_logger("test", context)
        assert logger.extra["trace_id"] == "test_trace_123"

        # Create derived logger with same context
        derived_logger = factory.create_authentication_logger(
            user_id="test", **context.to_dict()
        )

        # Should have same trace ID
        assert derived_logger.extra["trace_id"] == "test_trace_123"

    def test_timestamp_format(self):
        """Test that timestamps are in consistent format."""
        import re

        context = LogContext()
        # ISO 8601 format pattern
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$"

        assert re.match(iso_pattern, context.timestamp)

        factory = get_logger_factory()
        logger = factory.create_logger("test", context)

        assert re.match(iso_pattern, logger.extra["timestamp"])
