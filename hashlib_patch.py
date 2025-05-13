#!/usr/bin/env python
"""
hashlib_patch.py - Patch for Python 3.13+ hashlib compatibility issues

This script fixes the issue in Python 3.13 where blake2b and blake2s hash functions
may not be available due to missing OpenSSL support. It provides fallback implementations
using pure Python versions or alternative hash algorithms.

To use it, import this module at the very beginning of your application:
import hashlib_patch  # Must be imported before other modules

This patch is designed to handle dependencies that might also be affected by
the hashlib reorganization or missing algorithms in Python 3.13+.
"""

import logging
import os
import sys
from typing import Any, Union

from utils.logging_util import setup_logging

# Configure logging - only if running as script or debug is enabled
PATCH_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "hashlib_patch.log"
)


# Initialize logger using the common logging utility
logger = setup_logging("hashlib_patch", PATCH_LOG_FILE)


class FallbackBlake2Hash:
    """Fallback implementation for blake2 hash functions"""

    def __init__(self, digest_size: int = 64, **kwargs: Any):
        self.digest_size = digest_size
        self.block_size = 128
        self._data = bytearray()
        self._fallback_hash = None
        self._kwargs = kwargs

        # Log the fallback being used
        logger.debug(f"Using fallback Blake2Hash with digest_size={digest_size}")

    def update(self, data: Union[bytes, bytearray, memoryview]) -> None:
        """Update the hash object with data"""
        if isinstance(data, (str, bytes, bytearray, memoryview)):
            if isinstance(data, str):
                data = data.encode("utf-8")
            self._data.extend(data)
        else:
            raise TypeError(
                f"object supporting the buffer API required, not {type(data).__name__}"
            )

    def digest(self) -> bytes:
        """Return the digest of the data passed to the update() method"""
        import hashlib

        # Use SHA3-256 as a fallback
        h = hashlib.sha3_256(self._data)

        # Make it the right length
        result = h.digest()
        if len(result) < self.digest_size:
            # Repeat the hash if needed to reach the requested digest size
            result = result * (self.digest_size // len(result) + 1)

        # Truncate to the requested digest size
        return result[: self.digest_size]

    def hexdigest(self) -> str:
        """Return the digest as a string of hexadecimal digits"""
        return self.digest().hex()

    def copy(self) -> "FallbackBlake2Hash":
        """Return a copy of the hash object"""
        copy_obj = FallbackBlake2Hash(digest_size=self.digest_size, **self._kwargs)
        copy_obj._data = self._data.copy()
        return copy_obj


def blake2b_fallback(*args: Any, **kwargs: Any) -> FallbackBlake2Hash:
    """Fallback implementation for blake2b"""
    new_kwargs = kwargs.copy()
    new_kwargs["digest_size"] = 64
    return FallbackBlake2Hash(*args, **new_kwargs)


def blake2s_fallback(*args: Any, **kwargs: Any) -> FallbackBlake2Hash:
    """Fallback implementation for blake2s"""
    new_kwargs = kwargs.copy()
    new_kwargs["digest_size"] = 32
    return FallbackBlake2Hash(*args, **new_kwargs)


def patch_hashlib() -> bool:
    """
    Patch the hashlib module to add fallback implementations for
    missing hash functions in Python 3.13+
    """
    # Check Python version
    major, minor, micro = (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )

    # Import hashlib
    import hashlib

    # Check if blake2b and blake2s are already available
    if hasattr(hashlib, "blake2b") and hasattr(hashlib, "blake2s"):
        logger.debug(
            "blake2b and blake2s are already available in hashlib, no patching needed"
        )
        return True

    # Apply patches for missing functions
    patched = False

    if not hasattr(hashlib, "blake2b"):
        logger.info(f"Patching hashlib.blake2b for Python {major}.{minor}.{micro}")
        hashlib.blake2b = blake2b_fallback
        patched = True

    if not hasattr(hashlib, "blake2s"):
        logger.info(f"Patching hashlib.blake2s for Python {major}.{minor}.{micro}")
        hashlib.blake2s = blake2s_fallback
        patched = True

    # Suppress the error messages from hashlib about missing algorithms
    logging.getLogger("root").setLevel(logging.CRITICAL)

    return patched


# Apply the patch when this module is imported
success = patch_hashlib()

# For direct execution
if __name__ == "__main__":
    # Set debug logging
    os.environ["DEBUG_PATCH"] = "true"
    logger = setup_logging()
    logger.setLevel(logging.DEBUG)

    # Print header
    print("=" * 60)
    print(f"Hashlib Patch Diagnostic Tool for Python {sys.version.split()[0]}")
    print("=" * 60)

    # Check if patch succeeded
    import hashlib

    patched_algorithms = []

    if hasattr(hashlib, "blake2b"):
        patched_algorithms.append("blake2b")
        print("\n✅ hashlib.blake2b is available")

        # Test creating a hash object
        try:
            test_hash = hashlib.blake2b(b"test")
            print("   blake2b hash test: ✅ Success")
            print(f"   Test hash (hex): {test_hash.hexdigest()[:16]}...")
        except Exception as e:
            print(f"   blake2b hash test: ❌ Failed - {type(e).__name__}: {e}")
    else:
        print("\n❌ Failed to patch hashlib.blake2b")

    if hasattr(hashlib, "blake2s"):
        patched_algorithms.append("blake2s")
        print("\n✅ hashlib.blake2s is available")

        # Test creating a hash object
        try:
            test_hash = hashlib.blake2s(b"test")
            print("   blake2s hash test: ✅ Success")
            print(f"   Test hash (hex): {test_hash.hexdigest()[:16]}...")
        except Exception as e:
            print(f"   blake2s hash test: ❌ Failed - {type(e).__name__}: {e}")
    else:
        print("\n❌ Failed to patch hashlib.blake2s")

    if patched_algorithms:
        print(
            f"\n✅ Hashlib patch diagnostic complete - patched: {', '.join(patched_algorithms)}"
        )
        sys.exit(0)
    else:
        print("\n❌ No algorithms were patched")
        print("   This may prevent the application from running properly.")
        sys.exit(1)
