# simplenote_mcp/server/compat/__init__.py
"""
Compatibility module for resolving differences between Python versions.

This module handles compatibility issues between different Python versions.
"""

import importlib
import os
import sys

# Import directly from pathlib (works with Python 3.12)
from pathlib import Path, PurePath
from typing import Any, Optional, Type, TypeVar, Union

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


T = TypeVar("T")


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
