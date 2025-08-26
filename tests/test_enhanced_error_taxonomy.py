"""Tests for the enhanced error taxonomy and user-facing messages system."""

import pytest

from simplenote_mcp.server.error_helpers import (
    required_field_error,
    resource_not_found_error,
    type_validation_error,
)
from simplenote_mcp.server.error_taxonomy import (
    ENHANCED_SUBCATEGORY_CODES,
    ContextualMessageGenerator,
    ErrorSubcategory,
    ErrorTaxonomyMapper,
)
from simplenote_mcp.server.errors import (
    AuthenticationError,
    ErrorCategory,
    NetworkError,
    ResourceNotFoundError,
    ValidationError,
)


class TestErrorSubcategory:
    """Test the ErrorSubcategory enum."""

    def test_subcategory_values(self):
        """Test that subcategories have correct string values."""
        assert ErrorSubcategory.INVALID_CREDENTIALS.value == "invalid_credentials"
        assert ErrorSubcategory.NOTE_NOT_FOUND.value == "note_not_found"
        assert ErrorSubcategory.REQUIRED_FIELD.value == "required_field"

    def test_subcategory_completeness(self):
        """Test that all subcategories have codes."""
        for subcategory in ErrorSubcategory:
            assert subcategory in ENHANCED_SUBCATEGORY_CODES, (
                f"Missing code mapping for {subcategory}"
            )

    def test_unique_subcategory_codes(self):
        """Test that subcategory codes are reasonably unique."""
        codes = list(ENHANCED_SUBCATEGORY_CODES.values())
        # Some duplication is expected (e.g., PERM used for multiple permission-related errors)
        unique_codes = set(codes)
        assert len(unique_codes) >= len(codes) * 0.8, (
            "Too many duplicate subcategory codes"
        )


class TestContextualMessageGenerator:
    """Test the contextual message generation system."""

    def test_basic_message_generation(self):
        """Test basic message generation without context."""
        message = ContextualMessageGenerator.generate_user_message(
            category=ErrorCategory.AUTHENTICATION,
            subcategory=ErrorSubcategory.INVALID_CREDENTIALS,
        )
        assert isinstance(message, str)
        assert len(message) > 0
        assert "credentials" in message.lower()

    def test_message_with_context(self):
        """Test message generation with context."""
        context = {"field": "note_id", "operation": "update_note"}
        message = ContextualMessageGenerator.generate_user_message(
            category=ErrorCategory.VALIDATION,
            subcategory=ErrorSubcategory.REQUIRED_FIELD,
            context=context,
        )
        assert isinstance(message, str)
        assert "Note Id" in message or "note_id" in message

    def test_message_with_resource_context(self):
        """Test message generation with resource context."""
        context = {"resource_id": "abc123", "operation": "retrieval"}
        message = ContextualMessageGenerator.generate_user_message(
            category=ErrorCategory.NOT_FOUND,
            subcategory=ErrorSubcategory.NOTE_NOT_FOUND,
            context=context,
        )
        assert isinstance(message, str)
        assert "abc123" in message

    def test_fallback_to_category_default(self):
        """Test fallback when subcategory is not found."""
        message = ContextualMessageGenerator.generate_user_message(
            category=ErrorCategory.NETWORK,
            subcategory=None,  # Should use category default
        )
        assert isinstance(message, str)
        assert len(message) > 0

    def test_unknown_category_fallback(self):
        """Test fallback for unknown categories."""
        message = ContextualMessageGenerator.generate_user_message(
            category=ErrorCategory.UNKNOWN
        )
        assert isinstance(message, str)
        assert "unexpected" in message.lower()

    def test_resolution_steps_generation(self):
        """Test resolution steps generation."""
        steps = ContextualMessageGenerator.get_resolution_steps(
            category=ErrorCategory.AUTHENTICATION,
            subcategory=ErrorSubcategory.INVALID_CREDENTIALS,
        )
        assert isinstance(steps, list)
        assert len(steps) > 0
        assert any("credential" in step.lower() for step in steps)

    def test_resolution_steps_with_context(self):
        """Test resolution steps with context."""
        context = {"operation": "note_creation"}
        steps = ContextualMessageGenerator.get_resolution_steps(
            category=ErrorCategory.VALIDATION,
            subcategory=ErrorSubcategory.REQUIRED_FIELD,
            context=context,
        )
        assert isinstance(steps, list)
        assert len(steps) > 0


class TestErrorTaxonomyMapper:
    """Test the error taxonomy classification system."""

    def test_classify_authentication_errors(self):
        """Test classification of authentication errors."""
        test_cases = [
            ("invalid credentials provided", ErrorSubcategory.INVALID_CREDENTIALS),
            (
                "session has expired",
                ErrorSubcategory.SESSION_EXPIRED,
            ),  # This pattern matches session_expired
            ("missing authentication token", ErrorSubcategory.MISSING_AUTH),
            ("permission denied for user", ErrorSubcategory.PERMISSION_DENIED),
        ]

        for message, expected in test_cases:
            result = ErrorTaxonomyMapper.classify_error(
                message, ErrorCategory.AUTHENTICATION
            )
            assert result == expected, f"Failed to classify: {message}"

    def test_classify_network_errors(self):
        """Test classification of network errors."""
        test_cases = [
            ("connection failed to server", ErrorSubcategory.CONNECTION_FAILED),
            ("API is currently unavailable", ErrorSubcategory.API_UNAVAILABLE),
            ("request timed out", ErrorSubcategory.TIMEOUT),
            ("rate limit exceeded", ErrorSubcategory.RATE_LIMITED),
        ]

        for message, expected in test_cases:
            result = ErrorTaxonomyMapper.classify_error(message, ErrorCategory.NETWORK)
            assert result == expected, f"Failed to classify: {message}"

    def test_classify_validation_errors(self):
        """Test classification of validation errors."""
        test_cases = [
            ("required field is missing", ErrorSubcategory.REQUIRED_FIELD),
            ("invalid format provided", ErrorSubcategory.INVALID_FORMAT),
            ("must be a string type", ErrorSubcategory.TYPE_ERROR),
            ("value too large for range", ErrorSubcategory.RANGE_ERROR),
        ]

        for message, expected in test_cases:
            result = ErrorTaxonomyMapper.classify_error(
                message, ErrorCategory.VALIDATION
            )
            assert result == expected, f"Failed to classify: {message}"

    def test_classify_resource_errors(self):
        """Test classification of resource errors."""
        test_cases = [
            ("note with ID abc123 not found", ErrorSubcategory.NOTE_NOT_FOUND),
            ("tag 'work' not found", ErrorSubcategory.TAG_NOT_FOUND),
            ("resource has been deleted", ErrorSubcategory.RESOURCE_DELETED),
            ("resource is currently locked", ErrorSubcategory.RESOURCE_LOCKED),
        ]

        for message, expected in test_cases:
            result = ErrorTaxonomyMapper.classify_error(
                message, ErrorCategory.NOT_FOUND
            )
            assert result == expected, f"Failed to classify: {message}"

    def test_fallback_classification(self):
        """Test fallback classification for unmatched patterns."""
        result = ErrorTaxonomyMapper.classify_error(
            "completely unrelated error message", ErrorCategory.INTERNAL
        )
        # Should fallback to category default
        assert result == ErrorSubcategory.UNHANDLED_EXCEPTION

    def test_existing_subcategory_mapping(self):
        """Test that existing subcategories are preserved if valid."""
        result = ErrorTaxonomyMapper.classify_error(
            "some error message",
            ErrorCategory.VALIDATION,
            existing_subcategory="required_field",
        )
        assert result == ErrorSubcategory.REQUIRED_FIELD


class TestEnhancedErrorHelpers:
    """Test the enhanced error helper functions."""

    def test_type_validation_error_enhanced(self):
        """Test enhanced type validation error."""
        error = type_validation_error("note_id", "string", 123)

        assert isinstance(error, ValidationError)
        assert error.subcategory == ErrorSubcategory.TYPE_ERROR.value
        assert error.user_message is not None
        assert len(error.user_message) > 0
        assert "field" in error.details
        assert error.details["field"] == "note_id"

    def test_required_field_error_enhanced(self):
        """Test enhanced required field error."""
        error = required_field_error("email")

        assert isinstance(error, ValidationError)
        assert error.subcategory == ErrorSubcategory.REQUIRED_FIELD.value
        assert error.user_message is not None
        assert len(error.user_message) > 0
        assert "field" in error.details
        assert error.details["field"] == "email"

    def test_resource_not_found_error_enhanced(self):
        """Test enhanced resource not found error."""
        error = resource_not_found_error("note", "abc123")

        assert isinstance(error, ResourceNotFoundError)
        assert error.subcategory == ErrorSubcategory.NOTE_NOT_FOUND.value
        assert error.user_message is not None
        assert len(error.user_message) > 0
        assert error.resource_id == "abc123"
        assert "abc123" in error.user_message

    def test_tag_not_found_classification(self):
        """Test that tag resources are classified correctly."""
        error = resource_not_found_error("tag", "work")

        assert isinstance(error, ResourceNotFoundError)
        assert error.subcategory == ErrorSubcategory.TAG_NOT_FOUND.value
        assert error.resource_id == "work"


class TestIntegratedErrorHandling:
    """Test the integrated error handling with enhanced taxonomy."""

    def test_server_error_user_message_enhancement(self):
        """Test that ServerError uses enhanced user messages."""
        error = ValidationError(
            "Note ID is required",
            subcategory=ErrorSubcategory.REQUIRED_FIELD.value,
            details={"field": "note_id"},
        )

        user_message = error.get_user_message()
        assert isinstance(user_message, str)
        assert len(user_message) > 0

    def test_server_error_resolution_steps_enhancement(self):
        """Test that ServerError uses enhanced resolution steps."""
        error = AuthenticationError(
            "Invalid credentials",
            subcategory=ErrorSubcategory.INVALID_CREDENTIALS.value,
        )

        steps = error.resolution_steps
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_error_code_generation_with_enhanced_subcategories(self):
        """Test error code generation with enhanced subcategories."""
        error = NetworkError(
            "Connection failed", subcategory=ErrorSubcategory.CONNECTION_FAILED.value
        )

        # Error code format uses underscores, not dashes
        assert error.error_code.startswith("NET_CON_")

    def test_backward_compatibility(self):
        """Test that the enhanced system maintains backward compatibility."""
        # Old-style error creation should still work
        error = ValidationError("Old style error", subcategory="old_subcategory")

        # Should not crash and should provide reasonable defaults
        user_message = error.get_user_message()
        assert isinstance(user_message, str)
        assert len(user_message) > 0

        steps = error.resolution_steps
        assert isinstance(steps, list)
        assert len(steps) > 0


class TestMessageQuality:
    """Test the quality and consistency of generated messages."""

    def test_message_actionability(self):
        """Test that messages provide actionable guidance."""
        error = AuthenticationError(
            "Credentials invalid",
            subcategory=ErrorSubcategory.INVALID_CREDENTIALS.value,
        )

        message = error.get_user_message()
        steps = error.resolution_steps

        # Message should be user-friendly
        assert not any(
            word in message.lower() for word in ["exception", "traceback", "stack"]
        )

        # Steps should be actionable
        assert any(
            action_word in " ".join(steps).lower()
            for action_word in ["check", "verify", "try", "restart", "contact"]
        )

    def test_message_consistency(self):
        """Test that similar errors produce consistent messages."""
        error1 = ValidationError(
            "Note ID required",
            subcategory=ErrorSubcategory.REQUIRED_FIELD.value,
            details={"field": "note_id"},
        )

        error2 = ValidationError(
            "Email required",
            subcategory=ErrorSubcategory.REQUIRED_FIELD.value,
            details={"field": "email"},
        )

        message1 = error1.get_user_message()
        message2 = error2.get_user_message()

        # Should have similar structure
        assert "required" in message1.lower() or "provide" in message1.lower()
        assert "required" in message2.lower() or "provide" in message2.lower()

    def test_message_length_appropriateness(self):
        """Test that messages are appropriately sized."""
        error = NetworkError(
            "Connection timeout", subcategory=ErrorSubcategory.TIMEOUT.value
        )

        message = error.get_user_message()
        steps = error.resolution_steps

        # Message should be concise but informative
        assert 10 < len(message) < 200, f"Message length inappropriate: {len(message)}"

        # Steps should be detailed enough to be helpful
        for step in steps:
            assert 5 < len(step) < 150, f"Step length inappropriate: {len(step)}"


if __name__ == "__main__":
    pytest.main([__file__])
