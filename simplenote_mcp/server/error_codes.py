# simplenote_mcp/server/error_codes.py
"""Error code definitions for the Simplenote MCP Server.

This module contains definitions of error codes used throughout the server.
Error codes are structured to provide information about the error category,
subcategory, and specific error.

Format: {PREFIX}_{SUBCAT}_{IDENTIFIER}
- PREFIX: 2-6 letter code representing the error category (e.g., AUTH for authentication)
- SUBCAT: 2-3 letter code representing the error subcategory (e.g., REQ for required)
- IDENTIFIER: Unique identifier for the specific error (usually a 4-character UUID)

Example: AUTH_CRD_a1b2 - Authentication error with credentials subcategory
"""

from typing import Dict, Optional

# Category prefixes mapping from enum values to code prefixes
CATEGORY_PREFIXES = {
    "authentication": "AUTH",
    "configuration": "CONFIG",
    "network": "NET",
    "not_found": "NF",
    "permission": "PERM",
    "validation": "VAL",
    "internal": "INT",
    "rate_limit": "RATE",
    "timeout": "TIMEOUT",
    "data": "DATA",
    "synchronization": "SYNC",
    "unknown": "UNK",
}

# Reverse mapping for display purposes
CATEGORY_DISPLAY_NAMES = {
    "AUTH": "Authentication",
    "CONFIG": "Configuration",
    "NET": "Network",
    "NF": "Not Found",
    "PERM": "Permission",
    "VAL": "Validation",
    "INT": "Internal",
    "RATE": "Rate Limit",
    "TIMEOUT": "Timeout",
    "DATA": "Data",
    "SYNC": "Synchronization",
    "UNK": "Unknown",
}

# Subcategory codes - must match subcategories in ErrorCategory.get_subcategories()
SUBCATEGORY_CODES = {
    # Authentication subcategories
    "AUTH_CRD": "Missing or invalid credentials",
    "AUTH_EXP": "Authentication expired",
    "AUTH_TOK": "Invalid authentication token",
    "AUTH_UNA": "Unauthorized access attempt",
    "AUTH_MFA": "Multi-factor authentication required",
    # Configuration subcategories
    "CONFIG_MIS": "Missing configuration",
    "CONFIG_INV": "Invalid configuration",
    "CONFIG_ENV": "Environment configuration error",
    "CONFIG_FIL": "Configuration file error",
    "CONFIG_INC": "Incompatible configuration",
    # Network subcategories
    "NET_CON": "Connection error",
    "NET_DNS": "DNS resolution error",
    "NET_API": "API error",
    "NET_REQ": "Request error",
    "NET_RES": "Response error",
    "NET_SSL": "SSL/TLS error",
    "NET_UNA": "Service unavailable",
    # Not Found subcategories
    "NF_NOTE": "Note not found",
    "NF_RES": "Resource not found",
    "NF_TAG": "Tag not found",
    "NF_USER": "User not found",
    "NF_FILE": "File not found",
    "NF_PATH": "Path not found",
    # Permission subcategories
    "PERM_READ": "Read permission denied",
    "PERM_WRIT": "Write permission denied",
    "PERM_DEL": "Delete permission denied",
    "PERM_ACC": "Access denied",
    "PERM_INS": "Insufficient permissions",
    # Validation subcategories
    "VAL_REQ": "Required field missing",
    "VAL_FMT": "Invalid format",
    "VAL_TYP": "Invalid type",
    "VAL_RNG": "Value out of range",
    "VAL_LEN": "Invalid length",
    "VAL_PAT": "Invalid pattern",
    "VAL_CON": "Constraint violation",
    # Internal subcategories
    "INT_SRV": "Server error",
    "INT_DB": "Database error",
    "INT_MEM": "Memory error",
    "INT_STA": "Invalid state",
    "INT_DEP": "Dependency error",
    "INT_UNH": "Unhandled error",
    # Rate Limit subcategories
    "RATE_API": "API rate limit exceeded",
    "RATE_USR": "User rate limit exceeded",
    "RATE_IP": "IP rate limit exceeded",
    "RATE_THR": "Request throttled",
    # Timeout subcategories
    "TIMEOUT_CON": "Connection timeout",
    "TIMEOUT_READ": "Read timeout",
    "TIMEOUT_WRIT": "Write timeout",
    "TIMEOUT_EXEC": "Execution timeout",
    "TIMEOUT_SYNC": "Synchronization timeout",
    # Data subcategories
    "DATA_PAR": "Data parsing error",
    "DATA_SER": "Data serialization error",
    "DATA_COR": "Data corruption",
    "DATA_INT": "Data integrity error",
    "DATA_SCH": "Schema validation error",
    # Sync subcategories
    "SYNC_CON": "Sync conflict",
    "SYNC_MRG": "Merge conflict",
    "SYNC_VER": "Version mismatch",
    "SYNC_STL": "Stale data",
    "SYNC_INC": "Incomplete sync",
    # Unknown subcategories
    "UNK_GEN": "General error",
    "UNK_UNE": "Unexpected error",
    "UNK_EXT": "External service error",
}

# Common errors that may be used across the codebase
COMMON_ERRORS = {
    # Authentication errors
    "AUTH_CRD_MISSING": "Missing authentication credentials",
    "AUTH_CRD_INVALID": "Invalid authentication credentials",
    "AUTH_TOK_EXPIRED": "Authentication token has expired",
    # Configuration errors
    "CONFIG_MIS_ENV": "Missing required environment variables",
    "CONFIG_INV_SYNC": "Invalid sync interval configuration",
    "CONFIG_INV_LIMIT": "Invalid resource limit configuration",
    # Network errors
    "NET_API_UNAVAIL": "Simplenote API is unavailable",
    "NET_CON_REFUSED": "Connection refused by remote server",
    "NET_CON_RESET": "Connection reset by remote server",
    # Not Found errors
    "NF_NOTE_ID": "Note with specified ID not found",
    "NF_TAG_NAME": "Tag with specified name not found",
    "NF_RES_URI": "Resource with specified URI not found",
    # Validation errors
    "VAL_REQ_CONTENT": "Note content is required",
    "VAL_REQ_ID": "Note ID is required",
    "VAL_REQ_TAGS": "Tags are required",
    "VAL_REQ_QUERY": "Search query is required",
    "VAL_INV_URI": "Invalid Simplenote URI format",
    # Cache errors
    "INT_STA_UNINITIALIZED": "Cache not initialized",
    "INT_STA_ALREADY_RUNNING": "Background sync task is already running",
}


def parse_error_code(code: str) -> Optional[Dict[str, str]]:
    """Parse an error code into its components.

    Args:
        code: The error code to parse

    Returns:
        Dictionary with category, subcategory, and specific information,
        or None if the code doesn't match the expected format
    """
    parts = code.split("_")
    if len(parts) < 3:
        return None

    category_prefix = parts[0]
    subcategory = f"{category_prefix}_{parts[1]}"
    identifier = parts[2]

    if (
        category_prefix not in CATEGORY_DISPLAY_NAMES
        or subcategory not in SUBCATEGORY_CODES
    ):
        return None

    return {
        "category": CATEGORY_DISPLAY_NAMES[category_prefix],
        "subcategory": SUBCATEGORY_CODES[subcategory],
        "identifier": identifier,
        "full_code": code,
    }


def get_error_description(code: str) -> Optional[str]:
    """Get the description for a common error code.

    Args:
        code: The error code to look up

    Returns:
        Error description or None if not found in common errors
    """
    return COMMON_ERRORS.get(code)


def format_error_code(category_prefix: str, subcategory: str, identifier: str) -> str:
    """Format components into a standard error code.

    Args:
        category_prefix: The category prefix (e.g., 'AUTH')
        subcategory: The subcategory code (e.g., 'CRD')
        identifier: Unique identifier

    Returns:
        Formatted error code
    """
    return f"{category_prefix}_{subcategory}_{identifier}"
