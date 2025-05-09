#!/usr/bin/env python
"""
patch_pathlib.py - Comprehensive monkey patch for Python 3.13 pathlib compatibility

This script fixes the breaking change in Python 3.13 where Path is no longer directly
available in the pathlib module but moved to pathlib._local.

Usage:
1. Run this script directly before starting your application:
   python patch_pathlib.py && python your_app.py

2. Import it at the very beginning of your application:
   import patch_pathlib  # Must be first import
   # rest of your imports...

Author: Claude
Created: May 9, 2025
"""

import logging
import os
import sys

# Configure logging
log_level = os.environ.get("PATCH_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "pathlib_patch.log")
        ),
    ],
)

logger = logging.getLogger("pathlib_patch")


def apply_pathlib_patch():
    """
    Monkey patch pathlib to expose the Path class from pathlib._local in Python 3.13+.
    """
    logger.info("Checking if Python 3.13+ pathlib patching is needed...")

    # Check Python version
    major, minor = sys.version_info.major, sys.version_info.minor
    logger.info(f"Python version: {major}.{minor}")

    # Skip if not Python 3.13+
    if (major, minor) < (3, 13):
        logger.info("Python version is below 3.13, no patching needed")
        return False

    # Check if pathlib is already patched
    import pathlib

    if hasattr(pathlib, "Path"):
        logger.info("pathlib.Path already exists, no patching needed")
        return False

    logger.info("Python 3.13+ detected and pathlib.Path is missing, applying patch...")

    try:
        # Import pathlib._local module where Path now lives in Python 3.13+
        import pathlib._local

        # Classes to patch from _local to pathlib
        classes_to_patch = [
            "Path",
            "PurePath",
            "PosixPath",
            "WindowsPath",
            "PurePosixPath",
            "PureWindowsPath",
        ]

        # Transfer all the relevant classes from pathlib._local to pathlib
        for class_name in classes_to_patch:
            if hasattr(pathlib._local, class_name):
                setattr(pathlib, class_name, getattr(pathlib._local, class_name))
                logger.info(f"Patched {class_name} from pathlib._local to pathlib")
            else:
                logger.warning(f"Could not find {class_name} in pathlib._local")

        # Fix __all__ to include the patched classes
        if hasattr(pathlib, "__all__"):
            if isinstance(pathlib.__all__, list):
                pathlib.__all__.extend(
                    [c for c in classes_to_patch if c not in pathlib.__all__]
                )
            else:
                # If __all__ is not a list (e.g., a tuple), create a new one
                pathlib.__all__ = list(pathlib.__all__) + [
                    c for c in classes_to_patch if c not in pathlib.__all__
                ]
            logger.info("Updated pathlib.__all__ to include patched classes")
        else:
            pathlib.__all__ = classes_to_patch
            logger.info("Created pathlib.__all__ with patched classes")

        # Verify the patch worked
        if hasattr(pathlib, "Path"):
            logger.info("Patch successful! pathlib.Path is now available")
            return True
        else:
            logger.error("Patch failed! pathlib.Path is still missing after patching")
            return False

    except ImportError as e:
        logger.error(f"Failed to import pathlib._local: {e}")
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error while patching pathlib: {type(e).__name__}: {e}"
        )
        return False


# Apply the patch when this module is imported
success = apply_pathlib_patch()

# For command-line usage
if __name__ == "__main__":
    if success:
        print("Successfully patched pathlib for Python 3.13+ compatibility")
        sys.exit(0)
    else:
        print("Failed to patch pathlib - see pathlib_patch.log for details")
        sys.exit(1)
