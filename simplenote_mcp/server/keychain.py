"""macOS keychain access for Simperium auth tokens.

The Simplenote macOS app stores its Simperium token in the keychain under
service 'chalk-bump-f49' (the Simperium app ID for Simplenote).  When the
auth.simperium.com password-auth endpoint is unreachable we can read this
cached token directly and skip the broken authenticate() call entirely.
"""

import subprocess
import sys

_SIMPERIUM_APP_ID = "chalk-bump-f49"


def get_simperium_token(email: str) -> str | None:
    """Return the Simplenote Simperium token from the macOS keychain, or None.

    Only attempts the lookup on macOS; returns None silently on other platforms
    or when the keychain entry does not exist.

    Args:
        email: The Simplenote account email used as the keychain account name.

    Returns:
        The raw token string, or None if unavailable.
    """
    if sys.platform != "darwin":
        return None

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
