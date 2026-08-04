"""Simperium token resolution for the Simplenote MCP server.

Token acquisition order (see get_simperium_token):
1. Local file cache — ~/.config/simplenote-mcp/<email>.token (mode 0600).
   No keychain interaction, no dialogs, works on every platform.
2. Simplenote Desktop's macOS keychain entry (service 'chalk-bump-f49').
   May trigger a one-time approval dialog; result is written to the file
   cache so subsequent starts are completely prompt-free.

Previous versions stored the cache in a keychain entry ('simplenote-mcp-server').
Those entries are now unused; they can be removed via Keychain Access if desired.
"""

import os
import subprocess
import sys
from pathlib import Path

_SIMPERIUM_APP_ID = "chalk-bump-f49"
_CACHE_DIR = Path.home() / ".config" / "simplenote-mcp"


# ---------------------------------------------------------------------------
# File cache helpers
# ---------------------------------------------------------------------------


def _cache_path(email: str) -> Path:
    safe = email.replace("@", "_at_").replace("/", "_")
    return _CACHE_DIR / f"{safe}.token"


def _read_file_cache(email: str) -> str | None:
    try:
        token = _cache_path(email).read_text().strip()
        return token if token else None
    except OSError:
        return None


def _write_file_cache(email: str, token: str) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _cache_path(email)
        # Create with 0600 atomically via os.open — writing then chmod'ing
        # afterward leaves a window where the token file has default (often
        # world-readable) permissions before being restricted.
        fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(token)
    except OSError:
        pass


def _delete_file_cache(email: str) -> None:
    try:
        _cache_path(email).unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Simplenote Desktop keychain read (macOS, one-time prompt)
# ---------------------------------------------------------------------------


def _read_desktop_token(email: str) -> str | None:
    """Read token from Simplenote Desktop's keychain entry via the security CLI.

    This may trigger a one-time approval dialog the first time it runs.
    After the token is cached locally the keychain is never consulted again.
    """
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                _SIMPERIUM_APP_ID,
                "-a",
                email,
                "-w",
            ],
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


def cache_token(email: str, token: str) -> None:
    """Persist token to the local file cache.

    Call this after any successful authentication to ensure subsequent starts
    are prompt-free regardless of which auth path was used.
    """
    _write_file_cache(email, token)


def invalidate_cached_token(email: str) -> None:
    """Delete the local token cache so the next startup re-reads from the Desktop keychain.

    Call this when the cached token is rejected by the Simperium API.
    No-op if no cache file exists.
    """
    _delete_file_cache(email)


def get_simperium_token(email: str) -> str | None:
    """Return the Simplenote Simperium token, or None if unavailable.

    Lookup order:
    1. Local file cache (~/.config/simplenote-mcp/<email>.token, mode 0600).
       No keychain access, no dialogs, platform-agnostic.
    2. Simplenote Desktop's macOS keychain entry — may trigger a one-time
       approval dialog.  On success the token is written to the file cache
       so all subsequent starts are prompt-free.

    Args:
        email: Simplenote account email, used as the cache key.

    Returns:
        The raw token string, or None if unavailable.
    """
    cached = _read_file_cache(email)
    if cached:
        return cached

    if sys.platform == "darwin":
        desktop_token = _read_desktop_token(email)
        if desktop_token:
            _write_file_cache(email, desktop_token)
            return desktop_token

    return None
