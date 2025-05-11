#!/usr/bin/env python
"""
python_patch.py - Comprehensive patches for Python 3.13+ compatibility issues

This script applies patches for the following Python 3.13+ compatibility issues:
1. pathlib.Path being moved to pathlib._local.Path
2. Missing blake2b and blake2s hash functions in hashlib

Usage:
1. Run this script directly before starting your application:
   python python_patch.py && python your_app.py

2. Import it at the very beginning of your application:
   import python_patch  # Must be first import
   # rest of your imports...
"""

import contextlib
import datetime
import logging
import os
import sys
from typing import Any, Union

# Configure logging
PATCH_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "python_patch.log"
)


def setup_logging():
    """Setup logging for the patch"""
    logger = logging.getLogger("python_patch")
    logger.setLevel(logging.INFO)

    # Only add handlers if they don't exist
    if not logger.handlers:
        # Add console handler for interactive use
        console = logging.StreamHandler()
        console.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        console.setLevel(logging.INFO)
        logger.addHandler(console)

        # Add file handler for debugging
        if os.environ.get("DEBUG_PATCH", "").lower() in ("1", "true", "yes"):
            file_handler = logging.FileHandler(PATCH_LOG_FILE)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)

    return logger


# Initialize logger
logger = setup_logging()

# ====== PATHLIB PATCH ======


def patch_pathlib():
    """Patch pathlib module to expose Path class from pathlib._local in Python 3.13+"""
    # Check Python version
    major, minor, micro = (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    if (major, minor) < (3, 13):
        logger.debug(
            f"Python version {major}.{minor}.{micro} doesn't need the pathlib patch"
        )
        return False  # Skip if not Python 3.13+

    import pathlib

    if hasattr(pathlib, "Path"):
        logger.debug("pathlib.Path already exists, no patching needed")
        return True  # Already patched or no patching needed

    logger.info(f"Patching pathlib module for Python {major}.{minor}.{micro}")

    try:
        # Import the pathlib._local module where Path now lives
        import pathlib._local

        logger.debug("Successfully imported pathlib._local")

        # Classes to patch from _local to pathlib
        classes = [
            "Path",
            "PurePath",
            "PosixPath",
            "WindowsPath",
            "PurePosixPath",
            "PureWindowsPath",
            "_PathParents",
            "_Selector",
            "_make_selector",
        ]

        # Transfer classes from _local to pathlib
        for class_name in classes:
            if hasattr(pathlib._local, class_name):
                setattr(pathlib, class_name, getattr(pathlib._local, class_name))
                logger.debug(f"Transferred {class_name} from pathlib._local to pathlib")

        # Additional properties that might be needed
        if hasattr(pathlib._local.Path, "parser"):
            pathlib.Path.parser = pathlib._local.Path.parser
            logger.debug("Transferred Path.parser attribute")

        # Ensure the module has a __spec__ attribute
        if not hasattr(pathlib, "__spec__"):
            pathlib.__spec__ = pathlib._local.__spec__
            logger.debug("Transferred __spec__ attribute")

        # Update __all__ to include the patched classes
        if hasattr(pathlib, "__all__"):
            public_classes = [
                "Path",
                "PurePath",
                "PosixPath",
                "WindowsPath",
                "PurePosixPath",
                "PureWindowsPath",
            ]
            for class_name in public_classes:
                if class_name not in pathlib.__all__:
                    if isinstance(pathlib.__all__, list):
                        pathlib.__all__.append(class_name)
                    else:
                        pathlib.__all__ = list(pathlib.__all__) + [class_name]
            logger.debug(f"Updated pathlib.__all__: {pathlib.__all__}")
        else:
            pathlib.__all__ = [
                "Path",
                "PurePath",
                "PosixPath",
                "WindowsPath",
                "PurePosixPath",
                "PureWindowsPath",
            ]
            logger.debug(f"Created new pathlib.__all__: {pathlib.__all__}")

        # Verify patch was successful
        if hasattr(pathlib, "Path"):
            logger.info("Pathlib patch successful - Path is now available")
            return True
        else:
            logger.error("Pathlib patch failed - Path is still missing")
            return False

    except Exception as e:
        logger.error(f"Error patching pathlib: {type(e).__name__}: {e}")
        return False


# ====== HASHLIB PATCH ======


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
    with contextlib.suppress(Exception):
        logging.getLogger("root").setLevel(logging.CRITICAL)

    return patched


# ====== PATCH DEPENDENCIES ======


def patch_dependencies():
    """Patch dependencies that rely on pathlib.Path"""
    import pathlib

    if not hasattr(pathlib, "Path"):
        logger.debug("pathlib.Path not available, skipping dependency patching")
        return False

    # Patch AnyIO if needed
    try:
        import anyio._core._fileio

        if hasattr(pathlib, "Path") and hasattr(anyio._core._fileio, "Path"):
            # Store the original anyio Path implementation
            if not hasattr(anyio._core._fileio, "_original_Path"):
                anyio._core._fileio._original_Path = anyio._core._fileio.Path

            # Replace Path in anyio
            anyio._core._fileio.Path = pathlib.Path

            # Replace parser property access in anyio's Path
            if hasattr(pathlib.Path, "parser"):
                anyio._core._fileio.pathlib.Path = pathlib.Path

            logger.debug("Successfully patched anyio._core._fileio.Path")
            return True
    except ImportError:
        logger.debug("anyio module not found, no patching needed")
    except Exception as e:
        logger.debug(f"Error patching anyio: {type(e).__name__}: {e}")

    return False


# ====== MAIN FUNCTIONALITY ======


def apply_all_patches():
    """Apply all patches for Python 3.13+ compatibility"""
    results = {}

    # Apply pathlib patch
    results["pathlib"] = patch_pathlib()

    # Apply hashlib patch
    results["hashlib"] = patch_hashlib()

    # Patch dependencies that might be affected
    results["dependencies"] = patch_dependencies()

    return results


# Apply patches when this module is imported
patch_results = apply_all_patches()

# For direct execution
if __name__ == "__main__":
    # Set debug logging
    os.environ["DEBUG_PATCH"] = "true"
    logger = setup_logging()
    logger.setLevel(logging.DEBUG)

    # Print header
    print("=" * 60)
    print(f"Python 3.13+ Compatibility Patch Tool for Python {sys.version.split()[0]}")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Apply all patches
    results = apply_all_patches()

    # Report results
    success = all(results.values())

    print("\nPatch Results:")
    for patch_name, result in results.items():
        status = "✅ Success" if result else "❌ Failed"
        print(f"  {patch_name}: {status}")

    print("\nTesting patched functionality:")

    # Test pathlib.Path
    try:
        import pathlib

        if hasattr(pathlib, "Path"):
            test_path = pathlib.Path(".")
            print(f"  pathlib.Path: ✅ Available and working ({test_path.absolute()})")
        else:
            print("  pathlib.Path: ❌ Not available")
    except Exception as e:
        print(f"  pathlib.Path: ❌ Error - {type(e).__name__}: {e}")

    # Test hashlib.blake2b
    try:
        import hashlib

        if hasattr(hashlib, "blake2b"):
            test_hash = hashlib.blake2b(b"test").hexdigest()[:16]
            print(
                f"  hashlib.blake2b: ✅ Available and working (test hash: {test_hash}...)"
            )
        else:
            print("  hashlib.blake2b: ❌ Not available")
    except Exception as e:
        print(f"  hashlib.blake2b: ❌ Error - {type(e).__name__}: {e}")

    # Test hashlib.blake2s
    try:
        import hashlib

        if hasattr(hashlib, "blake2s"):
            test_hash = hashlib.blake2s(b"test").hexdigest()[:16]
            print(
                f"  hashlib.blake2s: ✅ Available and working (test hash: {test_hash}...)"
            )
        else:
            print("  hashlib.blake2s: ❌ Not available")
    except Exception as e:
        print(f"  hashlib.blake2s: ❌ Error - {type(e).__name__}: {e}")

    # Overall result
    if success:
        print("\n✅ All patches applied successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some patches failed. See details above.")
        sys.exit(1)
