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

Security note: reads use `security find-generic-password -w` (token in stdout,
never in process arguments).  Writes use the Security framework directly via
ctypes so the token is passed as a memory buffer, not a command-line argument
visible in `ps` output.
"""

import ctypes
import ctypes.util
import subprocess
import sys

_SIMPERIUM_APP_ID = "chalk-bump-f49"
_MCP_SERVICE = "simplenote-mcp-server"
_ERR_SEC_DUPLICATE_ITEM = -25299


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

    Calls the Security framework directly via ctypes so the token is passed
    as a memory buffer rather than a command-line argument (which would be
    visible to other processes via `ps`).
    """
    if sys.platform != "darwin":
        return
    try:
        _sec = ctypes.CDLL(ctypes.util.find_library("Security") or "Security")
        _cf = ctypes.CDLL(
            ctypes.util.find_library("CoreFoundation") or "CoreFoundation"
        )

        svc = _MCP_SERVICE.encode()
        acct = email.encode()
        pwd = token.encode()
        item_ref = ctypes.c_void_p()

        status = _sec.SecKeychainAddGenericPassword(
            None,
            len(svc),
            svc,
            len(acct),
            acct,
            len(pwd),
            pwd,
            ctypes.byref(item_ref),
        )

        if status == _ERR_SEC_DUPLICATE_ITEM:
            find_ref = ctypes.c_void_p()
            ok = _sec.SecKeychainFindGenericPassword(
                None,
                len(svc),
                svc,
                len(acct),
                acct,
                None,
                None,
                ctypes.byref(find_ref),
            )
            if ok == 0 and find_ref.value:
                _sec.SecKeychainItemModifyAttributesAndData(
                    find_ref, None, len(pwd), pwd
                )
                _cf.CFRelease(find_ref)
        elif status == 0 and item_ref.value:
            _cf.CFRelease(item_ref)
    except OSError:
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
    1. MCP server's own keychain entry — created by the Security framework,
       readable without ACL prompts on every restart.
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

    # Our own entry — no ACL prompt since we created it via the Security framework.
    cached = _get_token_from_service(_MCP_SERVICE, email)
    if cached:
        return cached

    # Simplenote Desktop's entry — may prompt once; cache immediately after.
    desktop_token = _get_token_from_service(_SIMPERIUM_APP_ID, email)
    if desktop_token:
        _cache_token(email, desktop_token)
        return desktop_token

    return None
