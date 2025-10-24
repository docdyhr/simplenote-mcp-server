#!/usr/bin/env python3
"""Documentation archival script for simplenote-mcp-server.

This script identifies and archives old documentation files to keep the
project documentation clean and organized.

Usage:
    python scripts/quality/archive_old_docs.py --dry-run
    python scripts/quality/archive_old_docs.py --archive
    python scripts/quality/archive_old_docs.py --list-candidates

Exit codes:
    0: Success
    1: Error occurred
"""

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


class DocumentArchiver:
    """Manage archival of old documentation files."""

    # Patterns for files that should be archived
    ARCHIVE_PATTERNS = [
        "*_SUMMARY.md",
        "*_REPORT.md",
        "*_ANALYSIS.md",
        "*_FIXES.md",
        "*_RESOLUTION*.md",
        "PROJECT_STATUS_*.md",
        "*_TEST_*.md",
        "*_IMPLEMENTATION_*.md",
    ]

    # Files that should NEVER be archived
    PROTECTED_FILES = [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "SECURITY.md",
        "CHANGELOG.md",
        "TODO.md",
        "CLAUDE.md",
        "AGENTS.md",
        "DOCKER_README.md",
    ]

    # Directories to exclude from archival
    EXCLUDE_DIRS = [
        ".git",
        ".github",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "dist",
        "build",
        "archive",  # Don't archive already archived files
    ]

    def __init__(self, root: Path, age_threshold_days: int = 90):
        """Initialize document archiver.

        Args:
            root: Project root directory
            age_threshold_days: Archive files older than this many days
        """
        self.root = root
        self.age_threshold = timedelta(days=age_threshold_days)
        self.archive_dir = root / "docs" / "archive"

    def should_exclude_dir(self, path: Path) -> bool:
        """Check if directory should be excluded from scanning.

        Args:
            path: Directory path to check

        Returns:
            True if directory should be excluded
        """
        parts = path.relative_to(self.root).parts
        return any(exclude in parts for exclude in self.EXCLUDE_DIRS)

    def is_protected(self, file_path: Path) -> bool:
        """Check if file is protected from archival.

        Args:
            file_path: File path to check

        Returns:
            True if file should never be archived
        """
        return file_path.name in self.PROTECTED_FILES

    def matches_archive_pattern(self, file_path: Path) -> bool:
        """Check if file matches archival patterns.

        Args:
            file_path: File path to check

        Returns:
            True if file matches archive patterns
        """
        for pattern in self.ARCHIVE_PATTERNS:
            if file_path.match(pattern):
                return True
        return False

    def get_file_age(self, file_path: Path) -> timedelta:
        """Get age of file based on modification time.

        Args:
            file_path: File path to check

        Returns:
            Age of file as timedelta
        """
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        return datetime.now() - mtime

    def find_archive_candidates(self) -> list[tuple[Path, timedelta]]:
        """Find files that are candidates for archival.

        Returns:
            List of (file_path, age) tuples
        """
        candidates = []

        for md_file in self.root.rglob("*.md"):
            # Skip if in excluded directory
            if self.should_exclude_dir(md_file.parent):
                continue

            # Skip if protected
            if self.is_protected(md_file):
                continue

            # Check if matches archive pattern
            if self.matches_archive_pattern(md_file):
                age = self.get_file_age(md_file)
                if age > self.age_threshold:
                    candidates.append((md_file, age))

        # Sort by age (oldest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def create_archive_dir(self, year: int) -> Path:
        """Create archive directory for a specific year.

        Args:
            year: Year for the archive

        Returns:
            Path to the archive directory
        """
        archive_year_dir = self.archive_dir / str(year)
        archive_year_dir.mkdir(parents=True, exist_ok=True)
        return archive_year_dir

    def archive_file(self, file_path: Path, dry_run: bool = False) -> bool:
        """Archive a single file.

        Args:
            file_path: Path to file to archive
            dry_run: If True, don't actually move files

        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine archive year from file modification time
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            year = mtime.year

            # Create archive directory
            archive_year_dir = self.create_archive_dir(year)

            # Determine destination path
            relative_path = file_path.relative_to(self.root)
            dest_path = archive_year_dir / relative_path.name

            # Handle filename conflicts
            if dest_path.exists():
                base = dest_path.stem
                ext = dest_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = archive_year_dir / f"{base}_{counter}{ext}"
                    counter += 1

            if dry_run:
                print(f"  [DRY RUN] Would move: {relative_path} -> {dest_path}")
                return True
            else:
                shutil.move(str(file_path), str(dest_path))
                print(f"  ✅ Archived: {relative_path} -> {dest_path}")
                return True

        except Exception as e:
            print(f"  ❌ Error archiving {file_path}: {e}", file=sys.stderr)
            return False

    def archive_all(self, dry_run: bool = False) -> tuple[int, int]:
        """Archive all candidate files.

        Args:
            dry_run: If True, don't actually move files

        Returns:
            Tuple of (success_count, failure_count)
        """
        candidates = self.find_archive_candidates()

        if not candidates:
            print("✅ No files need archiving")
            return 0, 0

        print(f"📦 Found {len(candidates)} files to archive")
        print("=" * 70)

        success = 0
        failure = 0

        for file_path, _age in candidates:
            if self.archive_file(file_path, dry_run):
                success += 1
            else:
                failure += 1

        print("=" * 70)
        print(f"✅ Archived: {success} files")
        if failure > 0:
            print(f"❌ Failed:   {failure} files")

        return success, failure

    def list_candidates(self) -> None:
        """List all files that would be archived."""
        candidates = self.find_archive_candidates()

        if not candidates:
            print("✅ No files need archiving")
            return

        print(f"📋 Archive Candidates ({len(candidates)} files)")
        print("=" * 70)
        print(f"{'File':<50} {'Age (days)':<12} {'Size':<10}")
        print("-" * 70)

        total_size = 0
        for file_path, age in candidates:
            relative_path = file_path.relative_to(self.root)
            age_days = age.days
            size = file_path.stat().st_size
            size_kb = size / 1024

            total_size += size

            # Truncate long paths
            path_str = str(relative_path)
            if len(path_str) > 48:
                path_str = "..." + path_str[-45:]

            print(f"{path_str:<50} {age_days:<12} {size_kb:>8.1f} KB")

        print("-" * 70)
        print(f"Total: {len(candidates)} files, {total_size / 1024:.1f} KB")
        print("=" * 70)

    def create_archive_index(self) -> None:
        """Create an index of archived files."""
        if not self.archive_dir.exists():
            return

        index_path = self.archive_dir / "INDEX.md"

        with open(index_path, "w") as f:
            f.write("# Documentation Archive Index\n\n")
            f.write(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("This directory contains archived documentation files.\n\n")

            # List files by year
            for year_dir in sorted(self.archive_dir.iterdir()):
                if not year_dir.is_dir() or year_dir.name.startswith("."):
                    continue

                f.write(f"## {year_dir.name}\n\n")

                files = sorted(year_dir.glob("*.md"))
                if files:
                    f.write("| File | Size | Last Modified |\n")
                    f.write("|------|------|---------------|\n")

                    for file_path in files:
                        size_kb = file_path.stat().st_size / 1024
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        mtime_str = mtime.strftime("%Y-%m-%d")
                        f.write(
                            f"| [{file_path.name}]({year_dir.name}/{file_path.name}) | "
                            f"{size_kb:.1f} KB | {mtime_str} |\n"
                        )

                    f.write("\n")

        print(f"✅ Created archive index: {index_path}")


def main() -> int:
    """Main entry point for documentation archiver.

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    parser = argparse.ArgumentParser(
        description="Archive old documentation files to keep the project clean"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without actually moving files",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Actually archive the files (use --dry-run first to preview)",
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="List files that are candidates for archival",
    )
    parser.add_argument(
        "--age-threshold",
        type=int,
        default=90,
        help="Archive files older than this many days (default: 90)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Create an index of archived files",
    )
    args = parser.parse_args()

    # Validate we're in the right directory
    root = args.root
    if not (root / "pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Are you in the project root?")
        return 1

    # Create archiver
    archiver = DocumentArchiver(root, args.age_threshold)

    # Execute requested action
    if args.list_candidates:
        archiver.list_candidates()
        return 0

    if args.create_index:
        archiver.create_archive_index()
        return 0

    if args.archive or args.dry_run:
        success, failure = archiver.archive_all(dry_run=args.dry_run)

        if args.archive and success > 0:
            # Create index after archiving
            archiver.create_archive_index()

        if failure > 0:
            return 1

        return 0

    # No action specified, show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
