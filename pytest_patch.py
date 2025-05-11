#!/usr/bin/env python
"""
pytest_patch.py - Patch for pytest compatibility with Python 3.13+

This script adds compatibility for pytest with Python 3.13+ by creating
a _pytest.pathlib module that pytest depends on but may not be available
due to Python's internal restructuring of pathlib.

Usage:
1. Import it before loading pytest:
   import pytest_patch
   import pytest
   ...
"""

import logging
import os
import sys
from types import ModuleType

# Configure logging
PATCH_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pytest_patch.log"
)


def setup_logging():
    """Setup logging for the patch"""
    logger = logging.getLogger("pytest_patch")
    logger.setLevel(logging.INFO)

    # Only add handlers if they don't exist
    if not logger.handlers:
        # Add console handler
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


def apply_pytest_patch():
    """Apply the pytest patch for Python 3.13+ compatibility"""
    # Check Python version
    major, minor, micro = (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    if (major, minor) < (3, 13):
        logger.debug(
            f"Python version {major}.{minor}.{micro} doesn't need the pytest patch"
        )
        return False

    # Check if _pytest.pathlib already exists
    if "_pytest.pathlib" in sys.modules:
        logger.debug("_pytest.pathlib already exists, no patching needed")
        return True

    # Ensure pathlib is available
    try:
        import pathlib

        if not hasattr(pathlib, "Path"):
            logger.error("pathlib.Path is not available, cannot apply pytest patch")
            return False

        # Create a new module for _pytest.pathlib
        pytest_pathlib = ModuleType("_pytest.pathlib")

        # Add core functionality needed by pytest
        # These functions are used by pytest's code module
        pytest_pathlib.absolutepath = lambda p: str(pathlib.Path(p).absolute())
        pytest_pathlib.bestrelpath = lambda path, other: str(
            pathlib.Path(other).relative_to(path) if str(path) in str(other) else other
        )

        # Add commonpath function (needed in findpaths.py)
        def common_path(paths):
            """Find the common path prefix for all paths"""
            if not paths:
                return ""

            paths = [pathlib.Path(p) for p in paths]
            common = str(paths[0])

            for path in paths[1:]:
                path_str = str(path)
                if len(path_str) < len(common):
                    if common.startswith(path_str):
                        common = path_str
                    else:
                        common = os.path.dirname(common)
                elif not path_str.startswith(common):
                    common = os.path.dirname(common)

            return common

        pytest_pathlib.commonpath = common_path

        # Register the module
        sys.modules["_pytest.pathlib"] = pytest_pathlib
        logger.info(
            f"Created _pytest.pathlib compatibility module for Python {major}.{minor}.{micro}"
        )
        return True
    except Exception as e:
        logger.error(f"Error patching pytest: {type(e).__name__}: {e}")
        return False


# Apply the patch when this module is imported
patched = apply_pytest_patch()

# For direct execution
if __name__ == "__main__":
    # Set debug logging
    os.environ["DEBUG_PATCH"] = "true"
    logger = setup_logging()
    logger.setLevel(logging.DEBUG)

    # Print header
    print("=" * 60)
    print(f"pytest Patch for Python {sys.version.split()[0]}")
    print("=" * 60)

    # Apply patch
    success = apply_pytest_patch()

    # Report results
    if success:
        print("✅ pytest patch applied successfully")
        sys.exit(0)
    else:
        print("❌ Failed to apply pytest patch")
        sys.exit(1)
