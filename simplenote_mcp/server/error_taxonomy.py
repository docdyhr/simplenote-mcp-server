"""Enhanced error taxonomy and user-friendly message system.

This module provides comprehensive error categorization, user-friendly message
generation, and context-aware error handling to improve the user experience
and maintainability of error reporting throughout the Simplenote MCP server.
"""

from enum import Enum
from typing import Any

from .error_codes import ErrorCategory


class ErrorSubcategory(Enum):
    """Enhanced subcategories for more granular error classification."""

    # Authentication subcategories
    INVALID_CREDENTIALS = "invalid_credentials"
    EXPIRED_SESSION = "expired_session"
    MISSING_AUTH = "missing_auth"
    TOKEN_INVALID = "token_invalid"  # noqa: S105
    PERMISSION_DENIED = "permission_denied"

    # Configuration subcategories
    MISSING_CONFIG = "missing_config"
    INVALID_CONFIG = "invalid_config"
    ENV_VAR_MISSING = "env_var_missing"
    CONFIG_FILE_ERROR = "config_file_error"

    # Network subcategories
    CONNECTION_FAILED = "connection_failed"
    API_UNAVAILABLE = "api_unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    DNS_ERROR = "dns_error"

    # Validation subcategories
    REQUIRED_FIELD = "required_field"
    INVALID_FORMAT = "invalid_format"
    TYPE_ERROR = "type_error"
    RANGE_ERROR = "range_error"
    LENGTH_ERROR = "length_error"

    # Resource subcategories
    NOTE_NOT_FOUND = "note_not_found"
    TAG_NOT_FOUND = "tag_not_found"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_LOCKED = "resource_locked"

    # Security subcategories
    INJECTION_ATTEMPT = "injection_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"

    # Internal subcategories
    DATABASE_ERROR = "database_error"
    CACHE_ERROR = "cache_error"
    SERVER_OVERLOAD = "server_overload"
    UNHANDLED_EXCEPTION = "unhandled_exception"

    # Session subcategories
    SESSION_EXPIRED = "session_expired"
    SESSION_INVALID = "session_invalid"
    CONCURRENT_SESSION = "concurrent_session"

    # General subcategories
    UNKNOWN = "unknown"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"

    # Vault (opt-in client-side note encryption) subcategories
    DECRYPTION_FAILED = "decryption_failed"
    VAULT_KEY_UNAVAILABLE = "vault_key_unavailable"
    VAULT_ENCRYPTED_NOTE = "vault_encrypted_note"


class ContextualMessageGenerator:
    """Generates context-aware, user-friendly error messages."""

    # Context-aware message templates
    MESSAGE_TEMPLATES = {
        # Authentication messages
        (ErrorCategory.AUTHENTICATION, ErrorSubcategory.INVALID_CREDENTIALS): {
            "message": "Your Simplenote credentials are incorrect.",
            "action": "Please check your username and password, then try again.",
            "details": "Make sure your SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables are set correctly.",
        },
        (ErrorCategory.AUTHENTICATION, ErrorSubcategory.EXPIRED_SESSION): {
            "message": "Your session has expired.",
            "action": "Please log in again to continue.",
            "details": "Sessions automatically expire after a period of inactivity for security.",
        },
        (ErrorCategory.AUTHENTICATION, ErrorSubcategory.MISSING_AUTH): {
            "message": "Authentication is required for this operation.",
            "action": "Please provide your Simplenote credentials.",
            "details": "Set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables.",
        },
        # Configuration messages
        (ErrorCategory.CONFIGURATION, ErrorSubcategory.MISSING_CONFIG): {
            "message": "Required configuration is missing.",
            "action": "Please check your configuration settings.",
            "details": "Ensure all required environment variables are set.",
        },
        (ErrorCategory.CONFIGURATION, ErrorSubcategory.ENV_VAR_MISSING): {
            "message": "Required environment variable is not set.",
            "action": "Please set the required environment variables.",
            "details": "Check the documentation for required configuration.",
        },
        (ErrorCategory.CONFIGURATION, ErrorSubcategory.VAULT_KEY_UNAVAILABLE): {
            "message": "No Vault encryption key is available.",
            "action": "Set SIMPLENOTE_VAULT_KEY_FILE to a writable path, or ensure an OS keychain/secret-service backend is available.",
            "details": "The Vault key is generated automatically on first use once a storage location is available.",
        },
        # Network messages
        (ErrorCategory.NETWORK, ErrorSubcategory.CONNECTION_FAILED): {
            "message": "Unable to connect to Simplenote servers.",
            "action": "Please check your internet connection and try again.",
            "details": "If the problem persists, Simplenote services may be temporarily unavailable.",
        },
        (ErrorCategory.NETWORK, ErrorSubcategory.API_UNAVAILABLE): {
            "message": "Simplenote API is currently unavailable.",
            "action": "Please try again in a few minutes.",
            "details": "This is usually a temporary issue. Check https://status.simplenote.com for updates.",
        },
        (ErrorCategory.NETWORK, ErrorSubcategory.TIMEOUT): {
            "message": "The operation timed out.",
            "action": "Please try again. If this persists, try a smaller request.",
            "details": "Network timeouts can occur with large operations or slow connections.",
        },
        (ErrorCategory.NETWORK, ErrorSubcategory.RATE_LIMITED): {
            "message": "Too many requests. Please slow down.",
            "action": "Wait a moment before trying again.",
            "details": "Rate limiting prevents server overload and ensures fair usage.",
        },
        # Validation messages
        (ErrorCategory.VALIDATION, ErrorSubcategory.REQUIRED_FIELD): {
            "message": "A required field is missing.",
            "action": "Please provide all required information.",
            "details": "Check the request parameters and ensure all required fields are included.",
        },
        (ErrorCategory.VALIDATION, ErrorSubcategory.INVALID_FORMAT): {
            "message": "The provided data format is incorrect.",
            "action": "Please check the format of your input and try again.",
            "details": "Ensure dates, IDs, and other formatted fields match the expected format.",
        },
        (ErrorCategory.VALIDATION, ErrorSubcategory.TYPE_ERROR): {
            "message": "The provided data type is incorrect.",
            "action": "Please check that you're providing the right type of data.",
            "details": "For example, numbers should be numeric, not text.",
        },
        (ErrorCategory.VALIDATION, ErrorSubcategory.VAULT_ENCRYPTED_NOTE): {
            "message": "This note is Vault-encrypted and can't be edited directly.",
            "action": "Call decrypt_note first, make your edit, then encrypt_note again — or pass encrypt=true to update_note to replace and re-encrypt in one step.",
            "details": "Appending or replacing content directly on encrypted note bodies would corrupt the encryption envelope.",
        },
        # Resource messages
        (ErrorCategory.NOT_FOUND, ErrorSubcategory.NOTE_NOT_FOUND): {
            "message": "The requested note could not be found.",
            "action": "Please check the note ID and try again.",
            "details": "The note may have been deleted or the ID may be incorrect.",
        },
        (ErrorCategory.NOT_FOUND, ErrorSubcategory.TAG_NOT_FOUND): {
            "message": "The requested tag could not be found.",
            "action": "Please check the tag name and try again.",
            "details": "Make sure the tag exists and is spelled correctly.",
        },
        (ErrorCategory.NOT_FOUND, ErrorSubcategory.RESOURCE_DELETED): {
            "message": "This resource has been deleted.",
            "action": "The resource is no longer available.",
            "details": "Deleted resources cannot be recovered unless restored from backup.",
        },
        # Security messages
        (ErrorCategory.SECURITY, ErrorSubcategory.RATE_LIMIT_EXCEEDED): {
            "message": "Security rate limit exceeded.",
            "action": "Please wait before trying again.",
            "details": "Multiple failed attempts trigger security protections.",
        },
        (ErrorCategory.SECURITY, ErrorSubcategory.SUSPICIOUS_ACTIVITY): {
            "message": "Suspicious activity detected.",
            "action": "Your request has been blocked for security reasons.",
            "details": "Contact support if you believe this is an error.",
        },
        (ErrorCategory.SECURITY, ErrorSubcategory.INJECTION_ATTEMPT): {
            "message": "Invalid input detected.",
            "action": "Please check your input and try again.",
            "details": "Input that appears to be malicious is automatically blocked.",
        },
        (ErrorCategory.SECURITY, ErrorSubcategory.DECRYPTION_FAILED): {
            "message": "Decryption failed.",
            "action": "This usually means the wrong Vault key is active, or the note's encrypted content has been corrupted or tampered with.",
            "details": "Vault-encrypted notes can only be decrypted on a machine holding the matching key — see vault_status to check the active key provider.",
        },
        # Internal messages
        (ErrorCategory.INTERNAL, ErrorSubcategory.SERVER_OVERLOAD): {
            "message": "The server is currently overloaded.",
            "action": "Please try again in a few minutes.",
            "details": "High server load can cause temporary performance issues.",
        },
        (ErrorCategory.INTERNAL, ErrorSubcategory.DATABASE_ERROR): {
            "message": "A database error occurred.",
            "action": "Please try again. If the problem persists, contact support.",
            "details": "This is usually a temporary issue that resolves automatically.",
        },
        (ErrorCategory.INTERNAL, ErrorSubcategory.CACHE_ERROR): {
            "message": "A cache error occurred.",
            "action": "Your request may take longer than usual. Please try again.",
            "details": "Cache issues can slow down responses but don't prevent operations.",
        },
        # Session messages
        (ErrorCategory.SESSION, ErrorSubcategory.SESSION_EXPIRED): {
            "message": "Your session has expired.",
            "action": "Please restart the server to create a new session.",
            "details": "Sessions expire automatically after a period of inactivity.",
        },
        (ErrorCategory.SESSION, ErrorSubcategory.SESSION_INVALID): {
            "message": "Your session is invalid.",
            "action": "Please restart the server to create a new session.",
            "details": "This can happen if session data becomes corrupted.",
        },
        # Default messages for each category
        ErrorCategory.AUTHENTICATION: {
            "message": "Authentication failed.",
            "action": "Please check your credentials and try again.",
            "details": "Ensure your Simplenote username and password are correct.",
        },
        ErrorCategory.CONFIGURATION: {
            "message": "Configuration error.",
            "action": "Please check your server configuration.",
            "details": "Review environment variables and configuration files.",
        },
        ErrorCategory.NETWORK: {
            "message": "Network error.",
            "action": "Please check your internet connection and try again.",
            "details": "This could be a temporary connectivity issue.",
        },
        ErrorCategory.NOT_FOUND: {
            "message": "The requested resource was not found.",
            "action": "Please check the resource identifier and try again.",
            "details": "Make sure the ID is correct and the resource exists.",
        },
        ErrorCategory.VALIDATION: {
            "message": "Invalid input provided.",
            "action": "Please check your input and try again.",
            "details": "Ensure all required fields are provided and properly formatted.",
        },
        ErrorCategory.SECURITY: {
            "message": "Security error.",
            "action": "Your request was blocked for security reasons.",
            "details": "Contact support if you believe this is an error.",
        },
        ErrorCategory.INTERNAL: {
            "message": "An internal server error occurred.",
            "action": "Please try again later.",
            "details": "If the problem persists, contact support.",
        },
        ErrorCategory.SESSION: {
            "message": "Session error.",
            "action": "Please restart the server to create a new session.",
            "details": "Session issues are usually resolved by restarting.",
        },
        ErrorCategory.UNKNOWN: {
            "message": "An unexpected error occurred.",
            "action": "Please try again.",
            "details": "If the problem persists, contact support with the error details.",
        },
    }

    @classmethod
    def generate_user_message(
        cls,
        category: ErrorCategory,
        subcategory: ErrorSubcategory | None = None,
        context: dict[str, Any] | None = None,
        include_details: bool = False,
    ) -> str:
        """Generate a context-aware user-friendly message.

        Args:
            category: Error category
            subcategory: Optional error subcategory
            context: Optional context dictionary with error details
            include_details: Whether to include technical details

        Returns:
            User-friendly error message
        """
        context = context or {}

        # Try to find specific message template
        template = None
        if subcategory:
            template = cls.MESSAGE_TEMPLATES.get((category, subcategory))

        # Fallback to category default
        if not template:
            template = cls.MESSAGE_TEMPLATES.get(category)

        # Ultimate fallback
        if not template:
            template = cls.MESSAGE_TEMPLATES[ErrorCategory.UNKNOWN]

        # Build message
        message = template["message"]

        # Add context-specific information
        if context:
            message = cls._add_context_to_message(message, context)

        # Add action if present
        if "action" in template and template["action"]:
            message += f" {template['action']}"

        # Add details if requested
        if include_details and "details" in template and template["details"]:
            message += f" ({template['details']})"

        return message

    @classmethod
    def _add_context_to_message(cls, message: str, context: dict[str, Any]) -> str:
        """Add context-specific information to the message.

        Args:
            message: Base message
            context: Context dictionary

        Returns:
            Enhanced message with context
        """
        # Add resource information if available
        if "resource_id" in context:
            if "note" in message.lower():
                message = message.replace("note", f"note '{context['resource_id']}'")
            elif "tag" in message.lower():
                message = message.replace("tag", f"tag '{context['resource_id']}'")
            elif "resource" in message.lower():
                message = message.replace(
                    "resource", f"resource '{context['resource_id']}'"
                )

        # Add field information for validation errors
        if "field" in context:
            field_name = context["field"].replace("_", " ").title()
            if "field" in message.lower():
                message = message.replace("field", f"field '{field_name}'")
            else:
                message = f"{field_name}: {message}"

        # Add operation context
        if "operation" in context and context["operation"]:
            message += f" (during {context['operation']})"

        return message

    @classmethod
    def get_resolution_steps(
        cls,
        category: ErrorCategory,
        subcategory: ErrorSubcategory | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Get context-aware resolution steps.

        Args:
            category: Error category
            subcategory: Optional error subcategory
            context: Optional context dictionary (reserved for future use)

        Returns:
            List of resolution steps
        """
        # Parameter reserved for future context-aware resolution steps
        del context  # Explicitly mark as unused to silence CodeQL warning

        # Base resolution steps from the category
        # Import from error_codes to avoid circular import with errors.py
        from .error_codes import DEFAULT_RESOLUTION_STEPS

        base_steps = DEFAULT_RESOLUTION_STEPS.get(
            category, DEFAULT_RESOLUTION_STEPS[ErrorCategory.UNKNOWN]
        )

        # Enhanced steps based on subcategory
        enhanced_steps = []

        if subcategory == ErrorSubcategory.INVALID_CREDENTIALS:
            enhanced_steps = [
                "Verify your Simplenote username and password are correct",
                "Check that SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables are set",
                "Try logging into Simplenote directly to verify your credentials",
                "Restart the server after updating credentials",
            ]
        elif subcategory == ErrorSubcategory.CONNECTION_FAILED:
            enhanced_steps = [
                "Check your internet connection",
                "Verify firewall settings allow outbound HTTPS connections",
                "Try accessing https://app.simplenote.com in a web browser",
                "Check if you're behind a proxy that may be blocking the connection",
            ]
        elif subcategory == ErrorSubcategory.RATE_LIMITED:
            enhanced_steps = [
                "Wait at least 1 minute before trying again",
                "Reduce the frequency of your requests",
                "Implement exponential backoff in your retry logic",
                "Contact support if you need higher rate limits",
            ]
        elif subcategory == ErrorSubcategory.NOTE_NOT_FOUND:
            enhanced_steps = [
                "Verify the note ID is correct and hasn't been mistyped",
                "Check that the note hasn't been deleted",
                "Try refreshing your note list to get the latest data",
                "Ensure you have access to the note (it's in your account)",
            ]

        # Use enhanced steps if available, otherwise use base steps
        return enhanced_steps if enhanced_steps else base_steps


class ErrorTaxonomyMapper:
    """Maps error conditions to standardized taxonomy."""

    # Mapping from error patterns to subcategories
    PATTERN_TO_SUBCATEGORY = {
        # Authentication patterns
        r"invalid.*(credential|password|username|email)": ErrorSubcategory.INVALID_CREDENTIALS,
        r"(expired|timeout).*session": ErrorSubcategory.EXPIRED_SESSION,
        r"missing.*(auth|credential)": ErrorSubcategory.MISSING_AUTH,
        r"(invalid|expired).*token": ErrorSubcategory.TOKEN_INVALID,
        r"permission.*(denied|refused)": ErrorSubcategory.PERMISSION_DENIED,
        # Configuration patterns
        r"missing.*(config|setting|variable)": ErrorSubcategory.MISSING_CONFIG,
        r"invalid.*(config|setting)": ErrorSubcategory.INVALID_CONFIG,
        r"environment.*variable": ErrorSubcategory.ENV_VAR_MISSING,
        r"config.*file": ErrorSubcategory.CONFIG_FILE_ERROR,
        # Network patterns
        r"connection.*(failed|refused|error)": ErrorSubcategory.CONNECTION_FAILED,
        r"api.*(unavailable|down|error)": ErrorSubcategory.API_UNAVAILABLE,
        r"(timeout|timed out)": ErrorSubcategory.TIMEOUT,
        r"rate.*(limit|exceeded)": ErrorSubcategory.RATE_LIMITED,
        r"dns.*(error|failed)": ErrorSubcategory.DNS_ERROR,
        # Validation patterns
        r"required.*field": ErrorSubcategory.REQUIRED_FIELD,
        r"invalid.*format": ErrorSubcategory.INVALID_FORMAT,
        r"(type|must be)": ErrorSubcategory.TYPE_ERROR,
        r"(range|between|too (large|small))": ErrorSubcategory.RANGE_ERROR,
        r"(length|too (long|short))": ErrorSubcategory.LENGTH_ERROR,
        # Resource patterns
        r"note.*(not found|missing)": ErrorSubcategory.NOTE_NOT_FOUND,
        r"tag.*(not found|missing)": ErrorSubcategory.TAG_NOT_FOUND,
        r"(deleted|removed)": ErrorSubcategory.RESOURCE_DELETED,
        r"(locked|busy|in use)": ErrorSubcategory.RESOURCE_LOCKED,
        # Security patterns
        r"injection.*(attempt|detected)": ErrorSubcategory.INJECTION_ATTEMPT,
        r"suspicious.*(activity|pattern)": ErrorSubcategory.SUSPICIOUS_ACTIVITY,
        r"security.*(violation|error)": ErrorSubcategory.SECURITY_VIOLATION,
        # Internal patterns
        r"database.*(error|failed)": ErrorSubcategory.DATABASE_ERROR,
        r"cache.*(error|failed)": ErrorSubcategory.CACHE_ERROR,
        r"server.*(overload|busy)": ErrorSubcategory.SERVER_OVERLOAD,
        r"unhandled.*exception": ErrorSubcategory.UNHANDLED_EXCEPTION,
        # Session patterns
        r"session.*(expired|timeout)": ErrorSubcategory.SESSION_EXPIRED,
        r"session.*(invalid|corrupted)": ErrorSubcategory.SESSION_INVALID,
        r"concurrent.*session": ErrorSubcategory.CONCURRENT_SESSION,
    }

    @classmethod
    def classify_error(
        cls,
        message: str,
        category: ErrorCategory,
        existing_subcategory: str | None = None,
    ) -> ErrorSubcategory:
        """Classify an error message into a specific subcategory.

        Args:
            message: Error message to classify
            category: Known error category
            existing_subcategory: Existing subcategory if any

        Returns:
            Appropriate error subcategory
        """
        import re

        # If we already have a specific subcategory, try to map it
        if existing_subcategory:
            try:
                return ErrorSubcategory(existing_subcategory)
            except ValueError:
                pass

        # Try pattern matching
        message_lower = message.lower()
        for pattern, subcategory in cls.PATTERN_TO_SUBCATEGORY.items():
            if re.search(pattern, message_lower):
                return subcategory

        # Fallback based on category
        category_defaults = {
            ErrorCategory.AUTHENTICATION: ErrorSubcategory.INVALID_CREDENTIALS,
            ErrorCategory.CONFIGURATION: ErrorSubcategory.INVALID_CONFIG,
            ErrorCategory.NETWORK: ErrorSubcategory.CONNECTION_FAILED,
            ErrorCategory.NOT_FOUND: ErrorSubcategory.NOTE_NOT_FOUND,
            ErrorCategory.VALIDATION: ErrorSubcategory.INVALID_FORMAT,
            ErrorCategory.SECURITY: ErrorSubcategory.SECURITY_VIOLATION,
            ErrorCategory.INTERNAL: ErrorSubcategory.UNHANDLED_EXCEPTION,
            ErrorCategory.SESSION: ErrorSubcategory.SESSION_EXPIRED,
        }

        return category_defaults.get(category, ErrorSubcategory.UNKNOWN)


# Enhanced subcategory code mapping for error codes
ENHANCED_SUBCATEGORY_CODES = {
    # Authentication codes
    ErrorSubcategory.INVALID_CREDENTIALS: "CRD",
    ErrorSubcategory.EXPIRED_SESSION: "EXP",
    ErrorSubcategory.MISSING_AUTH: "MISS",
    ErrorSubcategory.TOKEN_INVALID: "TOK",
    ErrorSubcategory.PERMISSION_DENIED: "PERM",
    # Configuration codes
    ErrorSubcategory.MISSING_CONFIG: "MISS",
    ErrorSubcategory.INVALID_CONFIG: "INV",
    ErrorSubcategory.ENV_VAR_MISSING: "ENV",
    ErrorSubcategory.CONFIG_FILE_ERROR: "FILE",
    # Network codes
    ErrorSubcategory.CONNECTION_FAILED: "CON",
    ErrorSubcategory.API_UNAVAILABLE: "API",
    ErrorSubcategory.TIMEOUT: "TIM",
    ErrorSubcategory.RATE_LIMITED: "RATE",
    ErrorSubcategory.DNS_ERROR: "DNS",
    # Validation codes
    ErrorSubcategory.REQUIRED_FIELD: "REQ",
    ErrorSubcategory.INVALID_FORMAT: "FMT",
    ErrorSubcategory.TYPE_ERROR: "TYPE",
    ErrorSubcategory.RANGE_ERROR: "RANG",
    ErrorSubcategory.LENGTH_ERROR: "LEN",
    # Resource codes
    ErrorSubcategory.NOTE_NOT_FOUND: "NOTE",
    ErrorSubcategory.TAG_NOT_FOUND: "TAG",
    ErrorSubcategory.RESOURCE_DELETED: "DEL",
    ErrorSubcategory.RESOURCE_LOCKED: "LOCK",
    # Security codes
    ErrorSubcategory.INJECTION_ATTEMPT: "INJ",
    ErrorSubcategory.RATE_LIMIT_EXCEEDED: "RATE",
    ErrorSubcategory.SUSPICIOUS_ACTIVITY: "SUSP",
    ErrorSubcategory.SECURITY_VIOLATION: "SEC",
    # Internal codes
    ErrorSubcategory.DATABASE_ERROR: "DB",
    ErrorSubcategory.CACHE_ERROR: "CACH",
    ErrorSubcategory.SERVER_OVERLOAD: "LOAD",
    ErrorSubcategory.UNHANDLED_EXCEPTION: "UNH",
    # Session codes
    ErrorSubcategory.SESSION_EXPIRED: "EXP",
    ErrorSubcategory.SESSION_INVALID: "INV",
    ErrorSubcategory.CONCURRENT_SESSION: "CONC",
    # Default codes
    ErrorSubcategory.UNKNOWN: "UNK",
    ErrorSubcategory.TEMPORARY: "TEMP",
    ErrorSubcategory.PERMANENT: "PERM",
    # Vault codes
    ErrorSubcategory.DECRYPTION_FAILED: "DECR",
    ErrorSubcategory.VAULT_KEY_UNAVAILABLE: "VKEY",
    ErrorSubcategory.VAULT_ENCRYPTED_NOTE: "VENC",
}
