# Error Categorization in Simplenote MCP Server

This document provides an overview of the error categorization system in the Simplenote MCP Server, its components, and how to use it effectively.

## Table of Contents

- [Overview](#overview)
- [Error Structure](#error-structure)
- [Error Categories](#error-categories)
- [Error Codes](#error-codes)
- [Using the Error System](#using-the-error-system)
- [Handling Errors](#handling-errors)
- [Integration with Structured Logging](#integration-with-structured-logging)

## Overview

The Simplenote MCP Server's error categorization system provides a consistent, structured approach to error handling throughout the codebase. It offers:

1. **Detailed Error Categories** - Errors are classified into main categories and subcategories
2. **Consistent Error Codes** - Each error has a unique, parseable code
3. **Actionable Error Messages** - Separate technical and user-friendly messages
4. **Resolution Guidance** - Suggested steps to resolve each error
5. **Integration with Structured Logging** - Comprehensive error context in logs
6. **Traceability** - Unique trace IDs to track errors through the system

## Error Structure

All errors in the system derive from the `ServerError` base class and include:

- **Error Code**: Unique identifier for the error (e.g., `AUTH_CRD_a1b2`)
- **Category**: Main error category (e.g., `authentication`)
- **Subcategory**: More specific error type (e.g., `credentials`)
- **Message**: Technical description for logs and debugging
- **User Message**: Human-friendly message suitable for end-users
- **Severity**: How critical the error is (CRITICAL, ERROR, WARNING, INFO)
- **Recoverable**: Whether the system can continue after this error
- **Trace ID**: Unique identifier for tracking the error across logs
- **Resolution Steps**: Suggested actions to resolve the error
- **Context**: Additional information about where/how the error occurred
- **Original Error**: The underlying exception that caused this error (if any)

## Error Categories

The system defines the following main error categories:

| Category | Description | Example |
|----------|-------------|---------|
| Authentication | Authentication and authorization issues | Invalid credentials |
| Configuration | System configuration problems | Missing environment variable |
| Network | Network and API connectivity issues | API connection failed |
| Not Found | Resource not found errors | Note ID not found |
| Permission | Access control violations | Insufficient permissions |
| Validation | Input validation failures | Missing required field |
| Internal | Server-side errors | Unhandled exception |
| Rate Limit | Rate limiting related errors | Too many API requests |
| Timeout | Operation timeout errors | API request timed out |
| Data | Data processing/storage errors | JSON parsing failed |
| Sync | Synchronization issues | Sync conflict |
| Unknown | Uncategorized errors | Unexpected error |

Each category has further subcategories for more specific error classification.

## Error Codes

Error codes follow the format: `{PREFIX}_{SUBCAT}_{IDENTIFIER}`

- **PREFIX**: 2-6 letter code representing the error category (e.g., `AUTH` for authentication)
- **SUBCAT**: 2-3 letter code representing the error subcategory (e.g., `CRD` for credentials)
- **IDENTIFIER**: Unique identifier for the specific error (usually a 4-character UUID)

Example: `AUTH_CRD_a1b2` - Authentication error with credentials subcategory and unique identifier `a1b2`

Common error codes are defined in `error_codes.py` for standardization.

## Using the Error System

### Creating Specific Errors

```python
from simplenote_mcp.server.errors import ValidationError

# Basic error
raise ValidationError("Note content cannot be empty", field="content")

# With subcategory
raise ValidationError("Note content cannot be empty", 
                    subcategory="required", 
                    field="content")

# With detailed context
raise ValidationError(
    "Note content cannot be empty",
    subcategory="required",
    field="content",
    operation="create_note",
    resource_id="note123",
    details={"max_length": 200000}
)
```

### Handling Standard Exceptions

Use the `handle_exception` utility to convert standard exceptions to appropriate ServerError types:

```python
from simplenote_mcp.server.errors import handle_exception

try:
    # Some operation that might fail
    result = api_call()
except Exception as e:
    # Convert to appropriate ServerError type
    error = handle_exception(e, context="calling Simplenote API", operation="sync_notes")
    # Use the structured error information
    print(f"Error code: {error.error_code}")
    print(f"User message: {error.get_user_message()}")
    print(f"Resolution steps: {error.get_resolution_guidance()}")
    # Re-raise or handle as appropriate
    raise error
```

## Handling Errors

When an error occurs, you can:

1. **Log it** - The error is automatically logged with appropriate severity
2. **Return it** - Convert to a dictionary for API responses with `to_dict()`
3. **Display it** - Show user-friendly messages with `get_user_message()`
4. **Resolve it** - Suggest resolution steps with `get_resolution_guidance()`

Example API response:

```json
{
  "success": false,
  "error": {
    "code": "VAL_REQ_a1b2",
    "message": "Note content is required",
    "user_message": "The note content cannot be empty.",
    "category": "validation",
    "subcategory": "required",
    "severity": "warning",
    "recoverable": true,
    "trace_id": "f8d7e6c5-b4a3-42d1-9f0e-8d7e6c5b4a3d",
    "resolution_steps": [
      "Provide content in the note",
      "Check that the content field is not null or empty"
    ]
  }
}
```

## Integration with Structured Logging

The error system integrates with the structured logging system to provide comprehensive error information in logs:

```json
{
  "timestamp": "2023-09-25T12:34:56.789012",
  "level": "ERROR",
  "message": "[VAL_REQ_a1b2] VALIDATION/required: Note content is required",
  "logger": "simplenote_mcp.errors",
  "error_code": "VAL_REQ_a1b2",
  "category": "validation",
  "subcategory": "required",
  "recoverable": true,
  "trace_id": "f8d7e6c5-b4a3-42d1-9f0e-8d7e6c5b4a3d",
  "operation": "create_note",
  "resource_id": "note123",
  "exception_type": "ValueError",
  "details": {
    "field": "content",
    "max_length": 200000
  },
  "caller": {
    "file": "server.py",
    "function": "handle_call_tool",
    "line": 714
  }
}
```

This rich context makes it easier to:

1. **Find related logs** - Use the trace ID to find all logs related to an error
2. **Understand the context** - See where, when, and why the error occurred
3. **Fix the issue** - Get specific information needed to resolve the problem

## Best Practices

1. **Use specific error types** - Choose the most specific error type for the situation
2. **Include subcategories** - Use subcategories for more precise error classification
3. **Provide context** - Include operation, resource IDs, and other relevant context
4. **Handle exceptions appropriately** - Use `handle_exception` to convert standard exceptions
5. **Return actionable errors** - Ensure error responses include clear resolution steps

By following these guidelines, you'll create a more maintainable and user-friendly system with errors that are easier to track, understand, and resolve.
