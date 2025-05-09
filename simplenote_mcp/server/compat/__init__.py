# simplenote_mcp/server/compat/__init__.py
"""
Compatibility module for resolving differences between Python versions.

This module handles compatibility issues between different Python versions,
particularly focused on changes in Python 3.13+ such as the pathlib
restructuring.
"""

import importlib
import os
import sys
from typing import Any, Optional, Type, TypeVar, Union

# Try different import approaches for Path
try:
    from pathlib import Path, PurePath  # type: ignore
except ImportError:
    try:
        from pathlib._local import Path, PurePath  # type: ignore
    except ImportError:
        # Last resort: try to use the pathlib_patch if available
        try:
            # Try to import the patch from project root
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
            import pathlib_patch  # noqa
            from pathlib import Path, PurePath  # type: ignore # noqa
        except ImportError as err:
            raise ImportError(
                "Could not import Path from pathlib or pathlib._local. "
                "Python 3.13+ requires the pathlib_patch.py to be available."
            ) from err

# Export Path for project-wide use
__all__ = ["Path", "PurePath", "get_optional_module", "is_module_available"]


def is_module_available(module_name: str) -> bool:
    """Check if a module is available for import.

    Args:
        module_name: The name of the module to check

    Returns:
        True if the module is available, False otherwise
    """
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


T = TypeVar('T')


def get_optional_module(module_name: str, default: Any = None) -> Optional[Any]:
    """Import a module that might not be available.

    Args:
        module_name: The name of the module to import
        default: The default value to return if the module is not available

    Returns:
        The imported module or the default value
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return default
