"""macOS keychain access for Simperium auth tokens.

The Simplenote macOS app stores its Simperium token in the keychain under
service 'chalk-bump-f49' (the Simperium app ID for Simplenote).  When the
auth.simperium.com password-auth endpoint is unreachable we can read this
cached token directly and skip the broken authenticate() call entirely.

To avoid the per-start keychain approval dialog (macOS enforces ACLs when a
different application reads an item it did not create), we maintain our own
keychain entry under service 'simplenote-mcp-server'.  The security CLI can
read back items it created without prompting, so subsequent starts are
prompt-free.  The Desktop entry is only consulted when our own cache is empty
(first run or after invalidation), resulting in at most one approval dialog.
"""

import subprocess
import sys

_SIMPERIUM_APP_ID = "chalk-bump-f49"
_MCP_SERVICE = "simplenote-mcp-server"


def _get_token_from_service(service: str, email: str) -> str | None:
    """Read a generic-password entry from the macOS keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", email, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            return token if token else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _cache_token(email: str, token: str) -> None:
    """Persist token in the MCP server's own keychain entry.

    Uses -U so the call is idempotent (creates or updates).
    """
    try:
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s",
                _MCP_SERVICE,
                "-a",
                email,
                "-w",
                token,
                "-U",
            ],
            capture_output=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


def invalidate_cached_token(email: str) -> None:
    """Delete the MCP server's cached token entry.

    Call this when the cached token is rejected by the API so the next
    startup re-reads a fresh token from the Simplenote Desktop entry.
    No-op on non-macOS or when no entry exists.
    """
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            [
                "security",
                "delete-generic-password",
                "-s",
                _MCP_SERVICE,
                "-a",
                email,
            ],
            capture_output=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


def get_simperium_token(email: str) -> str | None:
    """Return the Simplenote Simperium token from the macOS keychain, or None.

    Lookup order (darwin only):
    1. MCP server's own keychain entry — created by the security CLI, readable
       without ACL prompts on every restart.
    2. Simplenote Desktop's entry (service 'chalk-bump-f49') — may trigger a
       one-time approval dialog; the result is immediately written to step 1 so
       subsequent starts are prompt-free.

    Args:
        email: The Simplenote account email used as the keychain account name.

    Returns:
        The raw token string, or None if unavailable.
    """
    if sys.platform != "darwin":
        return None

    # Our own entry — security CLI can read it without an ACL prompt.
    cached = _get_token_from_service(_MCP_SERVICE, email)
    if cached:
        return cached

    # Simplenote Desktop's entry — may prompt once; cache immediately after.
    desktop_token = _get_token_from_service(_SIMPERIUM_APP_ID, email)
    if desktop_token:
        _cache_token(email, desktop_token)
        return desktop_token

    return None
