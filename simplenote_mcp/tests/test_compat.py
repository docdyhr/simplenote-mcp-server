#!/usr/bin/env python
"""
Tests for the compatibility modules.

This file contains tests for the cross-version compatibility
modules to ensure they work correctly across Python versions.
"""

import os
import sys

import pytest

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Import the compatibility module
from simplenote_mcp.server.compat import Path


class TestPathCompat:
    """Test the Path compatibility class."""

    def test_path_exists(self):
        """Test that Path class exists and can be imported."""
        assert Path is not None, "Path class should be available"

    def test_path_instantiation(self):
        """Test path instantiation."""
        path = Path("test/path")
        assert path is not None, "Should be able to instantiate Path"
        assert str(path) == "test/path", "Path string representation should match"

    def test_path_join(self):
        """Test joining paths."""
        path = Path("test") / "path" / "file.txt"
        assert str(path) == os.path.join("test", "path", "file.txt"), (
            "Path joining should work"
        )

    def test_path_parent(self):
        """Test path parent property."""
        path = Path("test/path/file.txt")
        parent = path.parent
        assert parent is not None, "Parent should not be None"
        assert str(parent) == os.path.dirname("test/path/file.txt"), (
            "Parent should be the directory"
        )

    def test_path_name(self):
        """Test path name property."""
        path = Path("test/path/file.txt")
        assert path.name == "file.txt", "Name should be the filename"

    def test_path_suffix(self):
        """Test path suffix property."""
        path = Path("test/path/file.txt")
        assert path.suffix == ".txt", "Suffix should be the file extension"

    def test_path_resolve(self):
        """Test path resolve method."""
        # Create a test file
        test_file = os.path.join(os.path.dirname(__file__), "test_file.tmp")
        with open(test_file, "w") as f:
            f.write("test")

        try:
            path = Path(test_file)
            resolved = path.resolve()
            assert os.path.isabs(str(resolved)), "Resolved path should be absolute"
            assert os.path.exists(str(resolved)), "Resolved path should exist"
        finally:
            # Clean up
            os.unlink(test_file)

    def test_path_mkdir(self):
        """Test path mkdir method."""
        # Create a test directory
        test_dir = os.path.join(os.path.dirname(__file__), "test_dir")
        path = Path(test_dir)

        try:
            # Remove if exists
            if os.path.exists(test_dir):
                os.rmdir(test_dir)

            # Test mkdir
            path.mkdir()
            assert os.path.exists(test_dir), "Directory should be created"
            assert os.path.isdir(test_dir), "Should be a directory"

            # Test parents parameter
            nested_dir = os.path.join(test_dir, "nested", "dir")
            nested_path = Path(nested_dir)
            nested_path.mkdir(parents=True)
            assert os.path.exists(nested_dir), "Nested directory should be created"

            # Test exist_ok parameter
            path.mkdir(exist_ok=True)  # Should not raise
        finally:
            # Clean up
            nested_dir = os.path.join(test_dir, "nested", "dir")
            if os.path.exists(nested_dir):
                os.rmdir(nested_dir)
            nested_parent = os.path.join(test_dir, "nested")
            if os.path.exists(nested_parent):
                os.rmdir(nested_parent)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)

    def test_path_unlink(self):
        """Test path unlink method."""
        # Create a test file
        test_file = os.path.join(os.path.dirname(__file__), "test_file.tmp")
        with open(test_file, "w") as f:
            f.write("test")

        path = Path(test_file)
        path.unlink()
        assert not os.path.exists(test_file), "File should be removed"

    def test_path_glob(self):
        """Test path glob method."""
        # Create test directory structure
        test_dir = os.path.join(os.path.dirname(__file__), "test_glob")
        os.makedirs(test_dir, exist_ok=True)

        try:
            # Create test files
            for name in ["file1.txt", "file2.txt", "other.py"]:
                with open(os.path.join(test_dir, name), "w") as f:
                    f.write("test")

            path = Path(test_dir)

            # Test *.txt pattern
            txt_files = list(path.glob("*.txt"))
            assert len(txt_files) == 2, "Should find 2 txt files"
            assert all(file.suffix == ".txt" for file in txt_files), (
                "All files should have .txt suffix"
            )

            # Test *.py pattern
            py_files = list(path.glob("*.py"))
            assert len(py_files) == 1, "Should find 1 py file"
            assert py_files[0].suffix == ".py", "File should have .py suffix"
        finally:
            # Clean up
            for name in ["file1.txt", "file2.txt", "other.py"]:
                try:
                    os.unlink(os.path.join(test_dir, name))
                except Exception:
                    pass
            try:
                os.rmdir(test_dir)
            except Exception:
                pass


class TestOtherCompat:
    """Test other compatibility features."""

    def test_path_module_functionality(self):
        """Test that the correct Path implementation is used based on Python version."""
        # This just verifies that the Path class has the expected functionality
        if sys.version_info >= (3, 13):
            # Python 3.13+: We should be using our custom Path implementation
            import inspect

            path_module = inspect.getmodule(Path)
            assert "compat" in str(path_module), (
                "Path should come from our compat module in Python 3.13+"
            )
        else:
            # Python < 3.13: We should be using pathlib.Path
            import pathlib

            assert Path == pathlib.Path, (
                "Path should be identical to pathlib.Path in Python < 3.13"
            )


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
