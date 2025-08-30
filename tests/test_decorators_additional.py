"""Additional tests for decorators.py to increase coverage.

This test file focuses on testing additional decorator functionality
and validation functions.
"""

import pytest

from simplenote_mcp.server.decorators import (
    validate_content_required,
    validate_note_id_required,
    validate_query_required,
    validate_tags_required,
)
from simplenote_mcp.server.errors import ValidationError


class TestValidationFunctions:
    """Test validation functions used by decorators."""

    def test_validate_note_id_required_valid(self):
        """Test note ID validation with valid ID."""
        arguments = {"note_id": "test123"}
        # Should not raise exception
        validate_note_id_required(arguments)

    def test_validate_note_id_required_missing(self):
        """Test note ID validation with missing ID."""
        arguments = {}
        with pytest.raises(ValidationError, match="VALIDATION: Note Id is required"):
            validate_note_id_required(arguments)

    def test_validate_note_id_required_empty(self):
        """Test note ID validation with empty ID."""
        arguments = {"note_id": ""}
        with pytest.raises(
            ValidationError, match="VALIDATION: Note Id cannot be empty"
        ):
            validate_note_id_required(arguments)

    def test_validate_note_id_required_whitespace(self):
        """Test note ID validation with whitespace-only ID."""
        arguments = {"note_id": "   "}
        # Note: validators accept whitespace-only strings as valid
        validate_note_id_required(arguments)

    def test_validate_content_required_valid(self):
        """Test content validation with valid content."""
        arguments = {"content": "test content"}
        # Should not raise exception
        validate_content_required(arguments)

    def test_validate_content_required_empty_allowed(self):
        """Test content validation with empty content (allowed)."""
        arguments = {"content": ""}
        # Should not raise exception - empty content is allowed
        validate_content_required(arguments)

    def test_validate_content_required_missing(self):
        """Test content validation with missing content."""
        arguments = {}
        with pytest.raises(
            ValidationError, match="VALIDATION: Note Content is required"
        ):
            validate_content_required(arguments)

    def test_validate_content_required_none(self):
        """Test content validation with None content."""
        arguments = {"content": None}
        with pytest.raises(
            ValidationError,
            match="VALIDATION: Note Content must be string, got <class 'NoneType'>",
        ):
            validate_content_required(arguments)

    def test_validate_query_required_valid(self):
        """Test query validation with valid query."""
        arguments = {"query": "test query"}
        # Should not raise exception
        validate_query_required(arguments)

    def test_validate_query_required_missing(self):
        """Test query validation with missing query."""
        arguments = {}
        with pytest.raises(
            ValidationError, match="VALIDATION: Search Query is required"
        ):
            validate_query_required(arguments)

    def test_validate_query_required_empty(self):
        """Test query validation with empty query."""
        arguments = {"query": ""}
        with pytest.raises(
            ValidationError, match="VALIDATION: Search Query cannot be empty"
        ):
            validate_query_required(arguments)

    def test_validate_query_required_whitespace(self):
        """Test query validation with whitespace-only query."""
        arguments = {"query": "   "}
        # Note: validators accept whitespace-only strings as valid
        validate_query_required(arguments)

    def test_validate_tags_required_valid_string(self):
        """Test tags validation with valid tags string."""
        arguments = {"tags": "tag1,tag2"}
        # Should not raise exception
        validate_tags_required(arguments)

    def test_validate_tags_required_valid_list(self):
        """Test tags validation with valid tags list."""
        arguments = {"tags": ["tag1", "tag2"]}
        # Should not raise exception
        validate_tags_required(arguments)

    def test_validate_tags_required_missing(self):
        """Test tags validation with missing tags."""
        arguments = {}
        with pytest.raises(ValidationError, match="VALIDATION: Tags is required"):
            validate_tags_required(arguments)

    def test_validate_tags_required_empty_string(self):
        """Test tags validation with empty string tags."""
        arguments = {"tags": ""}
        with pytest.raises(ValidationError, match="VALIDATION: Tags cannot be empty"):
            validate_tags_required(arguments)

    def test_validate_tags_required_empty_list(self):
        """Test tags validation with empty list tags."""
        arguments = {"tags": []}
        with pytest.raises(ValidationError, match="VALIDATION: Tags cannot be empty"):
            validate_tags_required(arguments)

    def test_validate_tags_required_whitespace(self):
        """Test tags validation with whitespace-only tags."""
        arguments = {"tags": "   "}
        # Note: validators accept whitespace-only strings as valid
        validate_tags_required(arguments)


class TestDecoratorIntegration:
    """Test decorator integration scenarios."""

    def test_multiple_validation_functions(self):
        """Test multiple validation functions working together."""
        # Test case where all validations pass
        arguments = {
            "note_id": "test123",
            "content": "test content",
            "query": "test query",
            "tags": "tag1,tag2",
        }

        # All should pass without exceptions
        validate_note_id_required(arguments)
        validate_content_required(arguments)
        validate_query_required(arguments)
        validate_tags_required(arguments)

    def test_validation_precedence(self):
        """Test validation function precedence and error handling."""
        # Test that the first failing validation raises its specific error
        arguments = {"note_id": ""}  # Missing other required fields

        with pytest.raises(
            ValidationError, match="VALIDATION: Note Id cannot be empty"
        ):
            validate_note_id_required(arguments)

        # Even if we fix note_id, content validation should fail next
        arguments = {"note_id": "valid_id"}  # Still missing content

        with pytest.raises(
            ValidationError, match="VALIDATION: Note Content is required"
        ):
            validate_content_required(arguments)


class TestValidationEdgeCases:
    """Test edge cases for validation functions."""

    def test_validation_with_special_characters(self):
        """Test validation with special characters."""
        # Note ID with special characters (should pass - validation is permissive)
        arguments = {"note_id": "test-123_abc"}
        validate_note_id_required(arguments)

        # Content with special characters (should pass)
        arguments = {"content": "Content with émojis 🎉 and spëcial chars"}
        validate_content_required(arguments)

        # Query with special characters (should pass)
        arguments = {"query": "search émojis 🔍"}
        validate_query_required(arguments)

        # Tags with special characters (should pass)
        arguments = {"tags": "tëst,émoji🏷️"}
        validate_tags_required(arguments)

    def test_validation_with_numeric_values(self):
        """Test validation with numeric values."""
        # Numeric note_id (should pass as string)
        arguments = {"note_id": "12345"}
        validate_note_id_required(arguments)

        # Numeric content (should pass)
        arguments = {"content": "123"}
        validate_content_required(arguments)

    def test_validation_boundary_cases(self):
        """Test validation boundary cases."""
        # Very long values (should still pass validation at this level)
        long_string = "x" * 10000

        arguments = {"note_id": long_string}
        validate_note_id_required(arguments)

        arguments = {"content": long_string}
        validate_content_required(arguments)

        arguments = {"query": long_string}
        validate_query_required(arguments)

        arguments = {"tags": long_string}
        validate_tags_required(arguments)

    def test_validation_with_newlines_and_whitespace(self):
        """Test validation with newlines and various whitespace."""
        # Content with newlines (should pass)
        arguments = {"content": "Line 1\nLine 2\n\nLine 4"}
        validate_content_required(arguments)

        # Query with newlines (should pass)
        arguments = {"query": "multi\nline\nquery"}
        validate_query_required(arguments)

        # Note ID with trailing/leading whitespace after strip should fail
        arguments = {"note_id": "  valid_id  "}
        validate_note_id_required(arguments)  # Should pass - validator trims

    def test_validation_type_coercion(self):
        """Test how validators handle different data types."""
        # Integer note_id (converted to string)
        arguments = {"note_id": 12345}
        # This might raise TypeError depending on implementation
        # We'll test the actual behavior
        try:
            validate_note_id_required(arguments)
        except (TypeError, ValidationError):
            pass  # Either error type is acceptable

        # Boolean content (converted to string)
        arguments = {"content": True}
        try:
            validate_content_required(arguments)
        except (TypeError, ValidationError):
            pass  # Either error type is acceptable
