#!/usr/bin/env python
"""
pathlib_patch.py - Comprehensive monkey patch for Python 3.13+ pathlib compatibility

This script fixes the breaking change in Python 3.13 where Path is no longer directly
available in the pathlib module but moved to pathlib._local.

To use it, import this module at the very beginning of your application:
import pathlib_patch  # Must be first import

This patch is designed to handle dependencies that might also be affected by
the pathlib reorganization in Python 3.13+.
"""

import sys
import importlib.util
import types
import os
import logging
import datetime

# Configure logging - only if running as script or debug is enabled
PATCH_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    "pathlib_patch.log"
)

def setup_logging():
    """Setup logging for the pathlib patch"""
    logger = logging.getLogger("pathlib_patch")
    logger.setLevel(logging.INFO)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        # Add console handler for interactive use
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        console.setLevel(logging.INFO)
        logger.addHandler(console)
        
        # Add file handler for debugging
        if os.environ.get("DEBUG_PATCH", "").lower() in ("1", "true", "yes"):
            file_handler = logging.FileHandler(PATCH_LOG_FILE)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def patch_pathlib():
    """Patch pathlib module to expose Path class from pathlib._local in Python 3.13+"""
    # Check Python version
    major, minor, micro = sys.version_info.major, sys.version_info.minor, sys.version_info.micro
    if (major, minor) < (3, 13):
        logger.debug(f"Python version {major}.{minor}.{micro} doesn't need the pathlib patch")
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
            "Path", "PurePath", "PosixPath", "WindowsPath", 
            "PurePosixPath", "PureWindowsPath", 
            "_PathParents", "_Selector", "_make_selector"
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
            public_classes = ["Path", "PurePath", "PosixPath", "WindowsPath", 
                            "PurePosixPath", "PureWindowsPath"]
            for class_name in public_classes:
                if class_name not in pathlib.__all__:
                    if isinstance(pathlib.__all__, list):
                        pathlib.__all__.append(class_name)
                    else:
                        pathlib.__all__ = list(pathlib.__all__) + [class_name]
            logger.debug(f"Updated pathlib.__all__: {pathlib.__all__}")
        else:
            pathlib.__all__ = ["Path", "PurePath", "PosixPath", "WindowsPath", 
                             "PurePosixPath", "PureWindowsPath"]
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

# Apply the patch when this module is imported
success = patch_pathlib()

# Patch affected dependencies
def patch_dependencies():
    """Patch dependencies that rely on pathlib.Path"""
    if not success:
        return
    
    # List of modules that need patching
    patch_targets = [
        # (import_path, attribute_path, patch_type)
        ("anyio._core._fileio", "pathlib.Path", "attribute"),
        # Add more modules if needed
    ]
    
    for import_path, attribute_path, patch_type in patch_targets:
        try:
            # Import the module
            try:
                module = importlib.import_module(import_path)
                logger.debug(f"Successfully imported {import_path}")
            except ImportError:
                logger.debug(f"Module {import_path} not found, skipping patch")
                continue
            
            # Handle different patch types
            if patch_type == "attribute":
                # Parse the attribute path
                parts = attribute_path.split(".")
                parent_path = ".".join(parts[:-1])
                attr_name = parts[-1]
                
                # Get the parent object
                parent = module
                for part in parent_path.split("."):
                    if hasattr(parent, part):
                        parent = getattr(parent, part)
                    else:
                        logger.debug(f"Attribute {part} not found in {parent}, skipping patch")
                        break
                
                # Patch the attribute
                if hasattr(parent, attr_name) and hasattr(sys.modules["pathlib"], "Path"):
                    # Store original if not already stored
                    backup_name = f"_original_{attr_name}"
                    if not hasattr(parent, backup_name):
                        setattr(parent, backup_name, getattr(parent, attr_name))
                    
                    # Apply the patch
                    setattr(parent, attr_name, sys.modules["pathlib"].Path)
                    logger.debug(f"Patched {import_path}.{attribute_path}")
            
        except Exception as e:
            logger.debug(f"Error patching {import_path}: {type(e).__name__}: {e}")

# Monkey patch anyio._core._fileio.Path to use our patched pathlib.Path
try:
    import anyio._core._fileio
    import pathlib
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
except ImportError:
    logger.debug("anyio module not found, no patching needed")
except Exception as e:
    logger.debug(f"Error patching anyio: {type(e).__name__}: {e}")

# Patch other modules that might use pathlib
patch_dependencies()

# For direct execution
if __name__ == "__main__":
    # Set debug logging
    os.environ["DEBUG_PATCH"] = "true"
    logger = setup_logging()
    logger.setLevel(logging.DEBUG)
    
    # Print header
    print("=" * 60)
    print(f"Pathlib Patch Diagnostic Tool for Python {sys.version.split()[0]}")
    print(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check if patch succeeded
    import pathlib
    if hasattr(pathlib, "Path"):
        print("\n✅ pathlib.Path is available - patch successful or not needed")
        print(f"   Path class: {pathlib.Path}")
        
        # Test creating a Path object
        try:
            test_path = pathlib.Path(".")
            print(f"   Path object creation test: ✅ Success")
            print(f"   Path absolute: {test_path.absolute()}")
        except Exception as e:
            print(f"   Path object creation test: ❌ Failed - {type(e).__name__}: {e}")
        
        # Test anyio patch if anyio is installed
        try:
            import anyio._core._fileio
            print("\n✅ anyio is installed")
            print(f"   anyio._core._fileio.Path: {anyio._core._fileio.Path}")
            print(f"   anyio._core._fileio.pathlib.Path available: {hasattr(anyio._core._fileio.pathlib, 'Path')}")
        except ImportError:
            print("\nℹ️ anyio is not installed (no patching needed)")
        
        print("\n✅ Pathlib patch diagnostic complete - everything looks good!")
        sys.exit(0)
    else:
        print("\n❌ Failed to patch pathlib.Path")
        print("   This is a critical error that will prevent the application from running.")
        print("   Try using Python 3.12 instead, or check for errors in the log file.")
        sys.exit(1)