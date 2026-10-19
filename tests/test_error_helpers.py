"""Tests for the error-construction helpers in ``simplenote_mcp.server.error_helpers``.

``tests/test_enhanced_error_taxonomy.py`` already covers the basic taxonomy
wiring of ``type_validation_error``, ``required_field_error`` and
``resource_not_found_error``. This module covers message variants, detail and
``resource_id``/``operation`` propagation, ``create_error_from_exception`` and
the ``validate_*`` convenience checks.
"""

import pytest

from simplenote_mcp.server import error_helpers as eh
from simplenote_mcp.server.errors import (
    AuthenticationError,
    ConfigurationError,
    ErrorCategory,
    InternalError,
    NetworkError,
    ResourceNotFoundError,
    SecurityError,
    ServerError,
    ValidationError,
)

pytestmark = pytest.mark.unit


class TestTypeValidationError:
    def test_long_values_are_truncated_in_details(self):
        error = eh.type_validation_error("content", "string", "x" * 500)

        assert error.details["actual_value"] == "x" * 100
        assert error.details["actual_type"] == "<class 'str'>"

    def test_operation_reaches_error_details_and_user_message(self):
        error = eh.type_validation_error("note_id", "string", 42, operation="get_note")

        assert error.operation == "get_note"
        assert error.details["operation"] == "get_note"
        assert error.user_message.endswith(
            "(during get_note) Please check that you're providing the right "
            "type of data."
        )

    def test_default_operation_is_validation(self):
        error = eh.type_validation_error("limit", "integer", "ten")

        assert error.message == "Limit must be integer, got <class 'str'>"
        assert error.operation is None
        assert error.details["operation"] == "validation"


class TestRangeValidationError:
    @pytest.mark.parametrize(
        ("min_value", "max_value", "expected"),
        [
            (1024, 65535, "Port must be between 1024 and 65535 (got 80)"),
            (1024, None, "Port must be at least 1024 (got 80)"),
            (None, 79, "Port must be at most 79 (got 80)"),
            (None, None, "Port value 80 is out of range"),
        ],
    )
    def test_message_variants(self, min_value, max_value, expected):
        error = eh.range_validation_error(
            "port", min_value=min_value, max_value=max_value, actual_value=80
        )

        assert isinstance(error, ValidationError)
        assert error.message == expected
        assert error.subcategory == "range"
        assert error.details == {
            "field": "port",
            "min_value": min_value,
            "max_value": max_value,
            "actual_value": 80,
        }

    def test_extra_kwargs_are_forwarded(self):
        error = eh.range_validation_error(
            "limit", min_value=1, actual_value=0, operation="list_notes"
        )

        assert error.operation == "list_notes"


class TestSimpleValidationErrors:
    def test_required_field_error_carries_operation(self):
        error = eh.required_field_error("note_id", operation="delete_note")

        assert error.message == "Note Id is required"
        assert error.subcategory == "required_field"
        assert error.operation == "delete_note"
        assert error.details == {"field": "note_id", "operation": "delete_note"}

    def test_empty_field_error(self):
        error = eh.empty_field_error("search_query")

        assert isinstance(error, ValidationError)
        assert error.message == "Search Query cannot be empty"
        assert error.subcategory == "required"
        assert error.details == {"field": "search_query"}

    def test_format_error(self):
        error = eh.format_error("start_date", "ISO 8601 (YYYY-MM-DD)")

        assert error.message == (
            "Invalid start date format, expected ISO 8601 (YYYY-MM-DD)"
        )
        assert error.subcategory == "format"
        assert error.details == {
            "field": "start_date",
            "expected_format": "ISO 8601 (YYYY-MM-DD)",
        }


class TestResourceNotFoundError:
    def test_resource_id_propagates_everywhere(self):
        error = eh.resource_not_found_error("note", "abc123")

        assert isinstance(error, ResourceNotFoundError)
        assert error.message == "Note with ID abc123 not found"
        assert error.resource_id == "abc123"
        assert error.details["resource_id"] == "abc123"
        assert error.subcategory == "note_not_found"
        assert error.error_code.startswith("NF_NOTE_")
        assert "note 'abc123'" in error.user_message
        payload = error.to_dict()["error"]
        assert payload["resource_id"] == "abc123"
        assert payload["user_message"] == error.user_message

    @pytest.mark.parametrize("resource_type", ["tag", "TAG", "Tag"])
    def test_tag_classification_is_case_insensitive(self, resource_type):
        error = eh.resource_not_found_error(resource_type, "work")

        assert error.subcategory == "tag_not_found"
        assert "tag 'work'" in error.user_message

    @pytest.mark.parametrize("resource_type", ["user", "account", "Account"])
    def test_user_and_account_map_to_resource_deleted(self, resource_type):
        error = eh.resource_not_found_error(resource_type, "u1")

        assert error.subcategory == "resource_deleted"
        assert error.resource_id == "u1"
        assert "resource 'u1'" in error.user_message

    def test_unknown_resource_type_falls_back_to_note_subcategory(self):
        error = eh.resource_not_found_error("folder", "f1")

        assert error.message == "Folder with ID f1 not found"
        assert error.subcategory == "note_not_found"
        assert error.resource_id == "f1"

    def test_operation_kwarg_reaches_error_and_payload(self):
        error = eh.resource_not_found_error("note", "abc", operation="update_note")

        assert error.operation == "update_note"
        assert error.details["operation"] == "update_note"
        assert error.to_dict()["error"]["operation"] == "update_note"
        assert "(during update_note)" in error.user_message

    def test_default_operation_is_retrieval(self):
        error = eh.resource_not_found_error("note", "abc")

        assert error.operation is None
        assert error.details["operation"] == "retrieval"

    def test_non_string_resource_id_is_kept_as_given(self):
        error = eh.resource_not_found_error("note", 123)

        assert error.resource_id == 123
        assert error.to_dict()["error"]["resource_id"] == 123

    def test_empty_resource_id_is_omitted_from_payload(self):
        error = eh.resource_not_found_error("note", "")

        assert error.resource_id == ""
        assert "resource_id" not in error.to_dict()["error"]
        assert error.details["resource_id"] == ""


class TestAuthenticationFailedError:
    @pytest.mark.parametrize(
        ("reason", "status_code", "expected_message", "expected_details"),
        [
            (None, None, "Authentication failed", {}),
            (
                "Invalid credentials",
                None,
                "Authentication failed: Invalid credentials",
                {"reason": "Invalid credentials"},
            ),
            (None, 401, "Authentication failed (status 401)", {"status_code": 401}),
            (
                "Invalid credentials",
                401,
                "Authentication failed: Invalid credentials (status 401)",
                {"reason": "Invalid credentials", "status_code": 401},
            ),
        ],
    )
    def test_message_and_details(
        self, reason, status_code, expected_message, expected_details
    ):
        error = eh.authentication_failed_error(reason, status_code)

        assert isinstance(error, AuthenticationError)
        assert error.message == expected_message
        assert error.details == expected_details
        assert error.subcategory == "credentials"
        assert error.category is ErrorCategory.AUTHENTICATION
        assert error.recoverable is False


class TestConfigurationError:
    def test_without_suggestion(self):
        error = eh.configuration_error("database_url", "Cannot connect to database")

        assert isinstance(error, ConfigurationError)
        assert error.message == (
            "Configuration error in database_url: Cannot connect to database"
        )
        assert error.subcategory == "setting"
        assert error.details == {
            "setting": "database_url",
            "issue": "Cannot connect to database",
            "suggestion": None,
        }

    def test_with_suggestion(self):
        error = eh.configuration_error(
            "port", "Port already in use", "Try using a different port"
        )

        assert error.message == (
            "Configuration error in port: Port already in use. "
            "Try using a different port"
        )
        assert error.details["suggestion"] == "Try using a different port"


class TestNetworkError:
    @pytest.mark.parametrize(
        ("reason", "url", "suffix", "extra_details"),
        [
            (None, None, "", {}),
            (
                "Connection timeout",
                None,
                ": Connection timeout",
                {"reason": "Connection timeout"},
            ),
            (
                None,
                "https://api.example.com",
                " (https://api.example.com)",
                {"url": "https://api.example.com"},
            ),
            (
                "Connection timeout",
                "https://api.example.com",
                ": Connection timeout (https://api.example.com)",
                {"reason": "Connection timeout", "url": "https://api.example.com"},
            ),
        ],
    )
    def test_message_and_details(self, reason, url, suffix, extra_details):
        error = eh.network_error("Fetching Notes", reason, url)

        assert isinstance(error, NetworkError)
        assert error.message == f"Network error while fetching notes{suffix}"
        # The message lowercases the operation; details keep it verbatim.
        assert error.details == {"operation": "Fetching Notes", **extra_details}
        assert error.subcategory == "connection"
        assert error.recoverable is True


class TestSecurityViolationError:
    def test_without_details(self):
        error = eh.security_violation_error("Invalid URI scheme")

        assert isinstance(error, SecurityError)
        assert error.message == "Security violation: Invalid URI scheme"
        assert error.subcategory == "violation"
        assert error.details == {
            "violation_type": "Invalid URI scheme",
            "violation_details": None,
        }

    def test_with_details(self):
        error = eh.security_violation_error(
            "Rate limit exceeded", "Too many requests in 1 minute"
        )

        assert error.message == (
            "Security violation: Rate limit exceeded - Too many requests in 1 minute"
        )
        assert error.details["violation_details"] == "Too many requests in 1 minute"


class TestInternalServerError:
    def test_without_cause(self):
        error = eh.internal_server_error("Saving Note")

        assert isinstance(error, InternalError)
        assert error.message == "Internal error while saving note"
        assert error.operation == "Saving Note"
        assert error.original_error is None
        assert error.details == {"operation": "Saving Note", "cause": None}
        assert error.subcategory == "server"

    def test_with_cause_and_original_error(self):
        original = RuntimeError("socket closed")

        error = eh.internal_server_error(
            "Database query", "Connection lost", original_error=original
        )

        assert error.message == "Internal error while database query: Connection lost"
        assert error.original_error is original
        assert error.details["cause"] == "Connection lost"
        assert "caused by: RuntimeError: socket closed" in str(error)


class TestCreateErrorFromException:
    @pytest.mark.parametrize(
        ("exc", "expected_type"),
        [
            (ValueError("invalid input"), ValidationError),
            (TypeError("bad type"), ValidationError),
            (ConnectionError("refused"), NetworkError),
            (TimeoutError("slow"), NetworkError),
            (FileNotFoundError("gone"), ResourceNotFoundError),
            (RuntimeError("boom"), InternalError),
        ],
    )
    def test_maps_exception_types(self, exc, expected_type):
        error = eh.create_error_from_exception(exc, "validating data", "op")

        assert type(error) is expected_type
        assert error.original_error is exc
        assert error.operation == "op"

    def test_permission_error_becomes_permission_category(self):
        error = eh.create_error_from_exception(
            PermissionError("denied"), "reading cache"
        )

        assert type(error) is ServerError
        assert error.category is ErrorCategory.PERMISSION
        assert error.message == "Permission denied while reading cache: denied"

    def test_context_is_appended_to_message(self):
        error = eh.create_error_from_exception(
            ValueError("invalid input"), "validating user data"
        )

        assert error.message == "invalid input while validating user data"

    def test_kwargs_are_merged_into_details(self):
        error = eh.create_error_from_exception(
            ConnectionError("refused"), "connecting", "fetch_notes", host="api", retry=2
        )

        assert error.details["host"] == "api"
        assert error.details["retry"] == 2

    def test_resource_id_is_extracted_from_message(self):
        exc = FileNotFoundError("Note with ID abc123 not found")

        error = eh.create_error_from_exception(exc, operation="get_note")

        assert isinstance(error, ResourceNotFoundError)
        assert error.resource_id == "abc123"
        assert error.to_dict()["error"]["resource_id"] == "abc123"

    def test_message_without_id_has_no_resource_id(self):
        error = eh.create_error_from_exception(ValueError("bad input"))

        assert error.resource_id is None
        assert "resource_id" not in error.to_dict()["error"]

    def test_resource_id_kwarg_only_lands_in_details(self):
        # **kwargs are merged into .details, not passed to the constructor, so a
        # caller-supplied resource_id never reaches error.resource_id.
        error = eh.create_error_from_exception(
            FileNotFoundError("missing"), resource_id="abc123"
        )

        assert error.details["resource_id"] == "abc123"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Bug in errors.py:479-491 (handle_exception, used by "
            "create_error_from_exception): the r'note (\\w+)' pattern captures the "
            "next word, so 'note not found' yields resource_id 'not'."
        ),
    )
    def test_not_found_message_without_id_has_no_resource_id(self):
        error = eh.create_error_from_exception(FileNotFoundError("note not found"))

        assert error.resource_id is None

    def test_existing_server_error_is_returned_unchanged(self):
        original = eh.resource_not_found_error("note", "abc")

        error = eh.create_error_from_exception(
            original, "ignored context", "get_note", attempt=1
        )

        assert error is original
        assert error.message == "Note with ID abc not found"
        assert error.operation == "get_note"
        assert error.resource_id == "abc"
        assert error.details["attempt"] == 1

    def test_existing_operation_is_not_overwritten(self):
        original = ServerError("x", operation="first")

        error = eh.create_error_from_exception(original, operation="second")

        assert error.operation == "first"


class TestValidators:
    def test_validate_string_type_accepts_strings(self):
        assert eh.validate_string_type("title", "hello") is None

    def test_validate_string_type_rejects_non_strings(self):
        with pytest.raises(ValidationError) as exc_info:
            eh.validate_string_type("title", 5, operation="create_note")

        assert exc_info.value.message == "Title must be string, got <class 'int'>"
        assert exc_info.value.operation == "create_note"

    @pytest.mark.parametrize("value", ["x", "  x  "])
    def test_validate_not_empty_accepts_content(self, value):
        assert eh.validate_not_empty("query", value) is None

    @pytest.mark.parametrize("value", ["", "   ", "\n\t", None])
    def test_validate_not_empty_rejects_blank(self, value):
        with pytest.raises(ValidationError, match="Query cannot be empty"):
            eh.validate_not_empty("query", value)

    @pytest.mark.parametrize(
        ("value", "min_value", "max_value"),
        [(1, 1, 10), (10, 1, 10), (5, None, None), (-5, None, 0), (99, 0, None)],
    )
    def test_validate_integer_range_accepts_inclusive_bounds(
        self, value, min_value, max_value
    ):
        assert eh.validate_integer_range("limit", value, min_value, max_value) is None

    def test_validate_integer_range_below_min(self):
        with pytest.raises(ValidationError) as exc_info:
            eh.validate_integer_range("limit", 0, min_value=1, max_value=100)

        assert exc_info.value.message == "Limit must be at least 1 (got 0)"
        assert exc_info.value.details["actual_value"] == 0

    def test_validate_integer_range_above_max(self):
        with pytest.raises(ValidationError) as exc_info:
            eh.validate_integer_range(
                "limit", 101, min_value=1, max_value=100, operation="search"
            )

        assert exc_info.value.message == "Limit must be at most 100 (got 101)"
        assert exc_info.value.operation == "search"

    @pytest.mark.parametrize("value", ["tag", ["a", "b"], []])
    def test_validate_list_or_string_accepts(self, value):
        assert eh.validate_list_or_string("tags", value) is None

    @pytest.mark.parametrize("value", [("a",), {"a": 1}, 3, None])
    def test_validate_list_or_string_rejects(self, value):
        with pytest.raises(ValidationError, match="Tags must be string or list"):
            eh.validate_list_or_string("tags", value)
