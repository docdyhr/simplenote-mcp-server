"""macOS keychain access for Simperium auth tokens.

The Simplenote macOS app stores its Simperium token in the keychain under
service 'chalk-bump-f49' (the Simperium app ID for Simplenote).  When the
auth.simperium.com password-auth endpoint is unreachable we can read this
cached token directly and skip the broken authenticate() call entirely.

To avoid the per-start keychain approval dialog (macOS enforces ACLs per
calling application), we maintain our own keychain entry under service
'simplenote-mcp-server'.  All operations on that entry — read, write, and
delete — go through the Security framework via ctypes.  Because the same
Python process both creates and reads the entry, macOS considers it the
owner and never shows an approval dialog.

The Simplenote Desktop entry is only consulted when our cache is empty
(first run or after stale-token invalidation).  That one-time read uses
the `security` CLI, which may prompt once.  After approval the token is
written to our cache and the Desktop entry is never touched again.
"""

import ctypes
import ctypes.util
import subprocess
import sys

_SIMPERIUM_APP_ID = "chalk-bump-f49"
_MCP_SERVICE = "simplenote-mcp-server"
_ERR_SEC_DUPLICATE_ITEM = -25299


# ---------------------------------------------------------------------------
# Private helpers — ctypes Security framework operations on our own entry
# ---------------------------------------------------------------------------


def _sec_lib() -> ctypes.CDLL:
    return ctypes.CDLL(ctypes.util.find_library("Security") or "Security")


def _cf_lib() -> ctypes.CDLL:
    return ctypes.CDLL(ctypes.util.find_library("CoreFoundation") or "CoreFoundation")


def _ctypes_read_token(service: str, email: str) -> str | None:
    """Read a generic-password entry via the Security framework (no subprocess).

    Because the same Python process writes and reads our own entry, macOS
    grants access without an approval dialog.
    """
    try:
        sec = _sec_lib()
        svc = service.encode()
        acct = email.encode()
        pwd_len = ctypes.c_uint32(0)
        pwd_ptr = ctypes.c_void_p(None)

        status = sec.SecKeychainFindGenericPassword(
            None,
            len(svc),
            svc,
            len(acct),
            acct,
            ctypes.byref(pwd_len),
            ctypes.byref(pwd_ptr),
            None,
        )

        if status == 0 and pwd_ptr.value:
            raw = ctypes.string_at(pwd_ptr.value, pwd_len.value)
            sec.SecKeychainItemFreeContent(None, ctypes.c_void_p(pwd_ptr.value))
            token = raw.decode("utf-8", errors="replace").strip()
            return token if token else None
    except OSError:
        pass
    return None


def _cache_token(email: str, token: str) -> None:
    """Persist token in the MCP server's own keychain entry via ctypes.

    Token is passed as a memory buffer — never appears in process arguments.
    Uses SecKeychainAddGenericPassword; falls back to Find+Modify on duplicate.
    """
    if sys.platform != "darwin":
        return
    try:
        sec = _sec_lib()
        cf = _cf_lib()
        svc = _MCP_SERVICE.encode()
        acct = email.encode()
        pwd = token.encode()
        item_ref = ctypes.c_void_p()

        status = sec.SecKeychainAddGenericPassword(
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
            ok = sec.SecKeychainFindGenericPassword(
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
                sec.SecKeychainItemModifyAttributesAndData(
                    find_ref, None, len(pwd), pwd
                )
                cf.CFRelease(find_ref)
        elif status == 0 and item_ref.value:
            cf.CFRelease(item_ref)
    except OSError:
        pass


def _ctypes_delete_token(service: str, email: str) -> None:
    """Delete a generic-password entry via the Security framework (no subprocess)."""
    try:
        sec = _sec_lib()
        cf = _cf_lib()
        svc = service.encode()
        acct = email.encode()
        item_ref = ctypes.c_void_p()

        status = sec.SecKeychainFindGenericPassword(
            None,
            len(svc),
            svc,
            len(acct),
            acct,
            None,
            None,
            ctypes.byref(item_ref),
        )
        if status == 0 and item_ref.value:
            sec.SecKeychainDeleteItem(item_ref)
            cf.CFRelease(item_ref)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Private helper — subprocess read for the Simplenote Desktop entry
# ---------------------------------------------------------------------------


def _subprocess_read_token(service: str, email: str) -> str | None:
    """Read a generic-password entry via the `security` CLI.

    Used only for the Simplenote Desktop entry (chalk-bump-f49), which was
    created by a different application.  May trigger a one-time approval dialog;
    after that the result is cached in our own entry and this is never called
    again.
    """
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def invalidate_cached_token(email: str) -> None:
    """Delete the MCP server's cached token entry via ctypes.

    Call this when the cached token is rejected by the API so the next
    startup re-reads a fresh token from the Simplenote Desktop entry.
    No-op on non-macOS or when no entry exists.
    """
    if sys.platform != "darwin":
        return
    _ctypes_delete_token(_MCP_SERVICE, email)


def get_simperium_token(email: str) -> str | None:
    """Return the Simplenote Simperium token from the macOS keychain, or None.

    Lookup order (darwin only):
    1. MCP server's own keychain entry — read via ctypes (same process that
       wrote it), so macOS grants access without any approval dialog.
    2. Simplenote Desktop's entry (service 'chalk-bump-f49') — read via
       `security` CLI, may trigger a one-time approval dialog.  On success
       the token is cached in step 1 so subsequent starts are prompt-free.

    Args:
        email: The Simplenote account email used as the keychain account name.

    Returns:
        The raw token string, or None if unavailable.
    """
    if sys.platform != "darwin":
        return None

    # Our own entry — ctypes read, same process as writer → no ACL prompt.
    cached = _ctypes_read_token(_MCP_SERVICE, email)
    if cached:
        return cached

    # Simplenote Desktop's entry — subprocess read, may prompt once.
    desktop_token = _subprocess_read_token(_SIMPERIUM_APP_ID, email)
    if desktop_token:
        _cache_token(email, desktop_token)
        return desktop_token

    return None
