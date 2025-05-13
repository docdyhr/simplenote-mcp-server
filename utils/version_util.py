#!/usr/bin/env python
import sys
import logging

def check_python_version(major: int, minor: int) -> bool:
    """Check if the current Python version meets the required major and minor versions."""
    current_version = sys.version_info
    if (current_version.major, current_version.minor) < (major, minor):
        logging.debug(f"Python version {current_version.major}.{current_version.minor} is lower than required {major}.{minor}")
        return False
    return True