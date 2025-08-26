#!/usr/bin/env python3
"""
Conventional Commit Parser and Changelog Generator

This script parses conventional commit messages and generates properly categorized
changelogs following the Conventional Commits specification (conventionalcommits.org).

Usage:
    python scripts/conventional_changelog.py [--since TAG] [--output FILE]
"""

import argparse
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CommitInfo:
    """Represents a parsed conventional commit."""

    type: str
    scope: str | None
    description: str
    body: str | None
    footer: str | None
    is_breaking: bool = False
    raw_commit: str = ""
    hash: str = ""
    author: str = ""
    date: str = ""


@dataclass
class ChangelogSection:
    """Represents a section in the changelog."""

    title: str
    commits: list[CommitInfo] = field(default_factory=list)
    order: int = 0


class ConventionalCommitParser:
    """Parser for conventional commit messages."""

    # Standard conventional commit types with their changelog categorization
    COMMIT_TYPES = {
        "feat": ("Features", 1, "✨"),
        "fix": ("Bug Fixes", 2, "🐛"),
        "perf": ("Performance Improvements", 3, "⚡"),
        "refactor": ("Code Refactoring", 4, "♻️"),
        "docs": ("Documentation", 5, "📚"),
        "style": ("Styles", 6, "💄"),
        "test": ("Tests", 7, "🧪"),
        "build": ("Build System", 8, "🏗️"),
        "ci": ("Continuous Integration", 9, "👷"),
        "chore": ("Chores", 10, "🔧"),
        "revert": ("Reverts", 11, "⏪"),
        "deps": ("Dependencies", 12, "⬆️"),
        "security": ("Security", 13, "🔒"),
        "cleanup": ("Code Cleanup", 14, "🧹"),
        "config": ("Configuration", 15, "⚙️"),
    }

    # Regex pattern for conventional commits
    COMMIT_PATTERN = re.compile(
        r"^(?P<type>\w+)(?:\((?P<scope>[\w\-\.\,\s]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
    )

    # Pattern for breaking change footers
    BREAKING_CHANGE_PATTERN = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)

    @classmethod
    def parse_commit(cls, commit_line: str, full_commit: str = "") -> CommitInfo | None:
        """Parse a single commit message into a CommitInfo object."""

        match = cls.COMMIT_PATTERN.match(commit_line.strip())
        if not match:
            # Handle non-conventional commits as 'other'
            return CommitInfo(
                type="other",
                scope=None,
                description=commit_line.strip(),
                body=None,
                footer=None,
                is_breaking=False,
                raw_commit=full_commit,
            )

        commit_type = match.group("type").lower()
        scope = match.group("scope")
        description = match.group("description")
        is_breaking = bool(match.group("breaking"))

        # Parse body and footer from full commit
        lines = full_commit.split("\n")
        body_lines = []
        footer_lines = []
        in_footer = False

        for line in lines[1:]:  # Skip first line (subject)
            if line.strip() == "":
                continue

            # Check for footer patterns
            if re.match(r"^[\w\-]+:", line) or line.startswith("BREAKING CHANGE:"):
                in_footer = True

            if in_footer:
                footer_lines.append(line)
            elif not in_footer and line.strip():
                body_lines.append(line)

        body = "\n".join(body_lines).strip() if body_lines else None
        footer = "\n".join(footer_lines).strip() if footer_lines else None

        # Check for breaking changes in footer
        if footer and cls.BREAKING_CHANGE_PATTERN.search(footer):
            is_breaking = True

        return CommitInfo(
            type=commit_type,
            scope=scope,
            description=description,
            body=body,
            footer=footer,
            is_breaking=is_breaking,
            raw_commit=full_commit,
        )

    @classmethod
    def get_commit_type_info(cls, commit_type: str) -> tuple[str, int, str]:
        """Get display name, order, and emoji for a commit type."""
        return cls.COMMIT_TYPES.get(commit_type, ("Other Changes", 99, "📝"))


class ChangelogGenerator:
    """Generates changelog from parsed commits."""

    def __init__(self, version: str = "Unreleased", date: str | None = None):
        self.version = version
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.sections: dict[str, ChangelogSection] = {}
        self.breaking_changes: list[CommitInfo] = []

    def add_commit(self, commit: CommitInfo) -> None:
        """Add a commit to the appropriate changelog section."""

        # Handle breaking changes separately
        if commit.is_breaking:
            self.breaking_changes.append(commit)

        # Get section info
        section_name, order, emoji = ConventionalCommitParser.get_commit_type_info(
            commit.type
        )

        # Create or get section
        if section_name not in self.sections:
            self.sections[section_name] = ChangelogSection(
                title=f"{emoji} {section_name}", order=order
            )

        self.sections[section_name].commits.append(commit)

    def _format_commit_entry(self, commit: CommitInfo) -> str:
        """Format a single commit entry for the changelog."""

        # Build the commit line
        parts = []

        # Add scope if present
        if commit.scope:
            parts.append(f"**{commit.scope}**: ")

        # Add description
        parts.append(commit.description)

        # Add breaking change indicator
        if commit.is_breaking:
            parts.append(" ⚠️ **BREAKING CHANGE**")

        # Add commit hash if available
        if commit.hash:
            short_hash = commit.hash[:8]
            parts.append(f" ([{short_hash}](../../commit/{commit.hash}))")

        return f"- {''.join(parts)}"

    def generate_markdown(self, include_metadata: bool = True) -> str:
        """Generate the complete changelog in Markdown format."""

        lines = []

        # Add header
        if include_metadata:
            lines.append(f"# Changes in {self.version}")
            lines.append(f"*Released on {self.date}*")
            lines.append("")

        # Add breaking changes section first if any
        if self.breaking_changes:
            lines.append("## ⚠️ BREAKING CHANGES")
            lines.append("")
            for commit in self.breaking_changes:
                lines.append(self._format_commit_entry(commit))
                # Add detailed breaking change description from footer
                if commit.footer and "BREAKING CHANGE:" in commit.footer:
                    for line in commit.footer.split("\n"):
                        if line.startswith("BREAKING CHANGE:"):
                            detail = line.replace("BREAKING CHANGE:", "").strip()
                            if detail:
                                lines.append(f"  - {detail}")
            lines.append("")

        # Add regular sections in order
        sorted_sections = sorted(self.sections.values(), key=lambda s: s.order)

        for section in sorted_sections:
            if not section.commits:
                continue

            lines.append(f"## {section.title}")
            lines.append("")

            # Group by scope for better organization
            scoped_commits = {}
            unscoped_commits = []

            for commit in section.commits:
                if commit.scope:
                    if commit.scope not in scoped_commits:
                        scoped_commits[commit.scope] = []
                    scoped_commits[commit.scope].append(commit)
                else:
                    unscoped_commits.append(commit)

            # Add scoped commits first (sorted by scope)
            for scope in sorted(scoped_commits.keys()):
                for commit in scoped_commits[scope]:
                    lines.append(self._format_commit_entry(commit))

            # Add unscoped commits
            for commit in unscoped_commits:
                lines.append(self._format_commit_entry(commit))

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def get_summary_stats(self) -> dict[str, int]:
        """Get summary statistics about the changelog."""

        stats = {
            "total_commits": sum(
                len(section.commits) for section in self.sections.values()
            ),
            "breaking_changes": len(self.breaking_changes),
            "sections": len([s for s in self.sections.values() if s.commits]),
        }

        # Add per-type counts
        for section in self.sections.values():
            if section.commits:
                section_key = section.title.split(" ", 1)[1].lower().replace(" ", "_")
                stats[section_key] = len(section.commits)

        return stats


def get_git_commits(
    since_tag: str | None = None, format_template: str = "%H|%an|%ad|%s"
) -> list[tuple[str, str]]:
    """Get git commits since a specific tag or all commits if no tag specified."""

    cmd = ["git", "log", f"--pretty=format:{format_template}", "--no-merges"]

    if since_tag:
        # Check if tag exists
        try:
            subprocess.run(
                ["git", "rev-parse", since_tag],
                check=True,
                capture_output=True,
                text=True,
            )
            cmd.append(f"{since_tag}..HEAD")
        except subprocess.CalledProcessError:
            print(f"Warning: Tag '{since_tag}' not found. Using all commits.")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = []

        for line in result.stdout.strip().split("\n"):
            if line:
                # Get commit details
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    commit_hash, author, date, subject = parts

                    # Get full commit message
                    full_msg_cmd = ["git", "show", "-s", "--format=%B", commit_hash]
                    full_msg_result = subprocess.run(
                        full_msg_cmd, capture_output=True, text=True
                    )
                    full_message = full_msg_result.stdout.strip()

                    commits.append((subject, full_message, commit_hash, author, date))

        return commits

    except subprocess.CalledProcessError as e:
        print(f"Error getting git commits: {e}")
        return []


def main():
    """Main entry point for the changelog generator."""

    parser = argparse.ArgumentParser(
        description="Generate changelog from conventional commits"
    )
    parser.add_argument("--since", help="Git tag to start from (e.g., v1.0.0)")
    parser.add_argument("--output", help="Output file path (default: changelog.md)")
    parser.add_argument(
        "--version", default="Unreleased", help="Version for the changelog header"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "summary"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Skip version and date metadata in output",
    )

    args = parser.parse_args()

    # Get commits
    print(f"Fetching commits since {args.since or 'beginning of history'}...")
    commits = get_git_commits(args.since)

    if not commits:
        print("No commits found.")
        return

    print(f"Found {len(commits)} commits to process.")

    # Parse commits and generate changelog
    generator = ChangelogGenerator(version=args.version)

    for subject, full_message, commit_hash, author, date in commits:
        commit_info = ConventionalCommitParser.parse_commit(subject, full_message)
        if commit_info:
            commit_info.hash = commit_hash
            commit_info.author = author
            commit_info.date = date
            generator.add_commit(commit_info)

    # Generate output based on format
    if args.format == "markdown":
        changelog_content = generator.generate_markdown(
            include_metadata=not args.no_metadata
        )

        # Write to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(changelog_content)
            print(f"Changelog written to {output_path}")
        else:
            print(changelog_content)

    elif args.format == "summary":
        stats = generator.get_summary_stats()
        print("\nChangelog Summary:")
        print(f"Total commits: {stats['total_commits']}")
        print(f"Breaking changes: {stats['breaking_changes']}")
        print(f"Sections: {stats['sections']}")

        # Show per-section counts
        for key, value in stats.items():
            if key not in ["total_commits", "breaking_changes", "sections"]:
                print(f"{key.replace('_', ' ').title()}: {value}")

    elif args.format == "json":
        import json

        stats = generator.get_summary_stats()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
