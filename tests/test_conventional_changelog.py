#!/usr/bin/env python3
"""
Tests for the conventional commit parser and changelog generator.

This test suite validates the parsing of conventional commits, categorization
of commit types, and generation of properly formatted changelogs.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the scripts directory to the Python path for testing
script_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(script_dir))

from conventional_changelog import (  # noqa: E402
    ChangelogGenerator,
    CommitInfo,
    ConventionalCommitParser,
)


class TestConventionalCommitParser:
    """Test suite for the ConventionalCommitParser class."""

    def test_parse_simple_commit(self):
        """Test parsing a simple conventional commit."""
        commit_line = "feat: add new authentication system"

        result = ConventionalCommitParser.parse_commit(commit_line)

        assert result is not None
        assert result.type == "feat"
        assert result.scope is None
        assert result.description == "add new authentication system"
        assert result.is_breaking is False

    def test_parse_commit_with_scope(self):
        """Test parsing a commit with a scope."""
        commit_line = "fix(api): resolve timeout issues in note retrieval"

        result = ConventionalCommitParser.parse_commit(commit_line)

        assert result is not None
        assert result.type == "fix"
        assert result.scope == "api"
        assert result.description == "resolve timeout issues in note retrieval"
        assert result.is_breaking is False

    def test_parse_breaking_change_commit(self):
        """Test parsing a breaking change commit."""
        commit_line = "feat!: implement new API versioning system"

        result = ConventionalCommitParser.parse_commit(commit_line)

        assert result is not None
        assert result.type == "feat"
        assert result.scope is None
        assert result.description == "implement new API versioning system"
        assert result.is_breaking is True

    def test_parse_commit_with_body_and_footer(self):
        """Test parsing a commit with body and footer."""
        full_commit = """feat(auth): add OAuth2 support

This commit adds OAuth2 authentication support for external integrations.
It includes support for authorization code flow and refresh tokens.

BREAKING CHANGE: The authentication API has changed significantly.
Closes: #123
Refs: #456"""

        result = ConventionalCommitParser.parse_commit(
            "feat(auth): add OAuth2 support", full_commit
        )

        assert result is not None
        assert result.type == "feat"
        assert result.scope == "auth"
        assert result.description == "add OAuth2 support"
        assert result.is_breaking is True  # Due to BREAKING CHANGE in footer
        assert "OAuth2 authentication support" in result.body
        assert "BREAKING CHANGE:" in result.footer

    def test_parse_non_conventional_commit(self):
        """Test parsing a non-conventional commit."""
        commit_line = "Update README with installation instructions"

        result = ConventionalCommitParser.parse_commit(commit_line)

        assert result is not None
        assert result.type == "other"
        assert result.scope is None
        assert result.description == "Update README with installation instructions"
        assert result.is_breaking is False

    def test_get_commit_type_info(self):
        """Test getting commit type information."""
        # Test known types
        name, order, emoji = ConventionalCommitParser.get_commit_type_info("feat")
        assert name == "Features"
        assert order == 1
        assert emoji == "✨"

        name, order, emoji = ConventionalCommitParser.get_commit_type_info("fix")
        assert name == "Bug Fixes"
        assert order == 2
        assert emoji == "🐛"

        # Test unknown type
        name, order, emoji = ConventionalCommitParser.get_commit_type_info("unknown")
        assert name == "Other Changes"
        assert order == 99
        assert emoji == "📝"

    def test_parse_various_commit_types(self):
        """Test parsing different types of conventional commits."""
        test_cases = [
            ("feat: add new feature", "feat", False),
            ("fix: resolve critical bug", "fix", False),
            ("docs: update API documentation", "docs", False),
            ("style: fix code formatting", "style", False),
            ("refactor: restructure authentication module", "refactor", False),
            ("perf: optimize database queries", "perf", False),
            ("test: add unit tests for cache", "test", False),
            ("chore: update dependencies", "chore", False),
            ("ci: fix GitHub Actions workflow", "ci", False),
            ("build: update webpack configuration", "build", False),
            ("deps: bump lodash from 4.17.19 to 4.17.21", "deps", False),
            ("security: fix SQL injection vulnerability", "security", False),
            ("cleanup: remove unused imports", "cleanup", False),
        ]

        for commit_line, expected_type, expected_breaking in test_cases:
            result = ConventionalCommitParser.parse_commit(commit_line)
            assert result is not None, f"Failed to parse: {commit_line}"
            assert result.type == expected_type, f"Wrong type for: {commit_line}"
            assert result.is_breaking == expected_breaking, (
                f"Wrong breaking flag for: {commit_line}"
            )


class TestChangelogGenerator:
    """Test suite for the ChangelogGenerator class."""

    def test_basic_changelog_generation(self):
        """Test basic changelog generation."""
        generator = ChangelogGenerator(version="v1.2.0")

        # Add some test commits
        commits = [
            CommitInfo(
                type="feat",
                scope=None,
                description="add user authentication system",
                body=None,
                footer=None,
                is_breaking=False,
            ),
            CommitInfo(
                type="fix",
                scope="api",
                description="resolve timeout issues",
                body=None,
                footer=None,
                is_breaking=False,
            ),
            CommitInfo(
                type="docs",
                scope=None,
                description="update installation guide",
                body=None,
                footer=None,
                is_breaking=False,
            ),
        ]

        for commit in commits:
            generator.add_commit(commit)

        changelog = generator.generate_markdown()

        # Verify structure
        assert "# Changes in v1.2.0" in changelog
        assert "## ✨ Features" in changelog
        assert "## 🐛 Bug Fixes" in changelog
        assert "## 📚 Documentation" in changelog

        # Verify content
        assert "add user authentication system" in changelog
        assert "**api**: resolve timeout issues" in changelog
        assert "update installation guide" in changelog

    def test_breaking_changes_section(self):
        """Test that breaking changes are highlighted properly."""
        generator = ChangelogGenerator(version="v2.0.0")

        # Add a breaking change commit
        breaking_commit = CommitInfo(
            type="feat",
            scope="api",
            description="redesign authentication API",
            body="Complete redesign of the authentication system",
            footer="BREAKING CHANGE: All existing auth tokens are invalid",
            is_breaking=True,
        )

        generator.add_commit(breaking_commit)

        changelog = generator.generate_markdown()

        # Verify breaking changes section
        assert "## ⚠️ BREAKING CHANGES" in changelog
        assert "⚠️ **BREAKING CHANGE**" in changelog
        assert "All existing auth tokens are invalid" in changelog

    def test_scoped_commits_organization(self):
        """Test that scoped commits are organized properly."""
        generator = ChangelogGenerator(version="v1.3.0")

        # Add commits with various scopes
        commits = [
            CommitInfo(
                type="fix",
                scope="api",
                description="fix endpoint timeout",
                body=None,
                footer=None,
            ),
            CommitInfo(
                type="fix",
                scope="ui",
                description="fix button alignment",
                body=None,
                footer=None,
            ),
            CommitInfo(
                type="fix",
                scope="api",
                description="fix rate limiting",
                body=None,
                footer=None,
            ),
            CommitInfo(
                type="fix",
                scope=None,
                description="fix general bug",
                body=None,
                footer=None,
            ),
        ]

        for commit in commits:
            generator.add_commit(commit)

        changelog = generator.generate_markdown()

        # Verify scoped commits are grouped and ordered
        lines = changelog.split("\n")
        fix_section_lines = []
        in_fix_section = False

        for line in lines:
            if "## 🐛 Bug Fixes" in line:
                in_fix_section = True
                continue
            elif line.startswith("## ") and in_fix_section:
                break
            elif in_fix_section and line.strip().startswith("- "):
                fix_section_lines.append(line)

        # Scoped commits should come first, then unscoped
        assert any("api" in line for line in fix_section_lines[:3])
        assert "fix general bug" in fix_section_lines[-1]

    def test_commit_hash_links(self):
        """Test that commit hashes are formatted as links."""
        generator = ChangelogGenerator(version="v1.4.0")

        commit = CommitInfo(
            type="feat",
            scope=None,
            description="add new feature",
            body=None,
            footer=None,
            hash="abc123def456",
        )

        generator.add_commit(commit)
        changelog = generator.generate_markdown()

        # Verify commit hash link
        assert "([abc123de](../../commit/abc123def456))" in changelog

    def test_summary_stats(self):
        """Test changelog summary statistics."""
        generator = ChangelogGenerator(version="v1.5.0")

        # Add various commits
        commits = [
            CommitInfo(
                type="feat", scope=None, description="feature 1", body=None, footer=None
            ),
            CommitInfo(
                type="feat", scope=None, description="feature 2", body=None, footer=None
            ),
            CommitInfo(
                type="fix", scope=None, description="fix 1", body=None, footer=None
            ),
            CommitInfo(
                type="docs", scope=None, description="docs 1", body=None, footer=None
            ),
            CommitInfo(
                type="feat",
                scope=None,
                description="breaking feature",
                body=None,
                footer=None,
                is_breaking=True,
            ),
        ]

        for commit in commits:
            generator.add_commit(commit)

        stats = generator.get_summary_stats()

        assert stats["total_commits"] == 5
        assert stats["breaking_changes"] == 1
        assert stats["sections"] == 3  # Features, Bug Fixes, Documentation
        assert stats["features"] == 3  # All feat commits
        assert stats["bug_fixes"] == 1
        assert stats["documentation"] == 1

    def test_no_metadata_output(self):
        """Test changelog generation without metadata."""
        generator = ChangelogGenerator(version="v1.6.0")

        commit = CommitInfo(
            type="feat", scope=None, description="add feature", body=None, footer=None
        )

        generator.add_commit(commit)
        changelog = generator.generate_markdown(include_metadata=False)

        # Should not include version header or date
        assert "# Changes in v1.6.0" not in changelog
        assert "*Released on" not in changelog
        # Should still include sections
        assert "## ✨ Features" in changelog


class TestIntegration:
    """Integration tests for the complete workflow."""

    @patch("conventional_changelog.get_git_commits")
    def test_end_to_end_changelog_generation(self, mock_get_commits):
        """Test complete changelog generation from git commits."""
        # Mock git commits
        mock_commits = [
            (
                "feat: add authentication",
                "feat: add authentication\n\nAdds OAuth2 support",
                "abc123",
                "dev",
                "2023-01-01",
            ),
            (
                "fix(api): resolve timeout",
                "fix(api): resolve timeout",
                "def456",
                "dev",
                "2023-01-02",
            ),
            (
                "docs: update README",
                "docs: update README",
                "ghi789",
                "dev",
                "2023-01-03",
            ),
            (
                "feat!: breaking change",
                "feat!: breaking change\n\nBREAKING CHANGE: API changed",
                "jkl012",
                "dev",
                "2023-01-04",
            ),
        ]
        mock_get_commits.return_value = mock_commits

        # This would normally be tested by running the script, but we can test the parsing logic
        generator = ChangelogGenerator(version="v2.0.0")

        for subject, full_message, commit_hash, author, date in mock_commits:
            commit_info = ConventionalCommitParser.parse_commit(subject, full_message)
            if commit_info:
                commit_info.hash = commit_hash
                commit_info.author = author
                commit_info.date = date
                generator.add_commit(commit_info)

        changelog = generator.generate_markdown()

        # Verify the complete changelog
        assert "## ⚠️ BREAKING CHANGES" in changelog
        assert "## ✨ Features" in changelog
        assert "## 🐛 Bug Fixes" in changelog
        assert "## 📚 Documentation" in changelog

        # Verify specific commits
        assert "add authentication" in changelog
        assert "**api**: resolve timeout" in changelog
        assert "update README" in changelog
        assert "⚠️ **BREAKING CHANGE**" in changelog
        assert "API changed" in changelog

    def test_commit_categorization_accuracy(self):
        """Test that commits are categorized accurately."""
        test_commits = [
            ("feat: add new feature", "Features"),
            ("fix: resolve bug", "Bug Fixes"),
            ("docs: update documentation", "Documentation"),
            ("style: fix formatting", "Styles"),
            ("refactor: restructure code", "Code Refactoring"),
            ("perf: optimize performance", "Performance Improvements"),
            ("test: add tests", "Tests"),
            ("build: update build system", "Build System"),
            ("ci: fix CI pipeline", "Continuous Integration"),
            ("chore: update dependencies", "Chores"),
            ("deps: bump version", "Dependencies"),
            ("security: fix vulnerability", "Security"),
            ("cleanup: remove unused code", "Code Cleanup"),
            ("config: update settings", "Configuration"),
            ("unknown: some other change", "Other Changes"),
        ]

        generator = ChangelogGenerator(version="test")

        for commit_line, _expected_section in test_commits:
            commit_info = ConventionalCommitParser.parse_commit(commit_line)
            generator.add_commit(commit_info)

        changelog = generator.generate_markdown()

        # Verify all expected sections are present
        expected_sections = {commit[1] for commit in test_commits}
        for section in expected_sections:
            if section == "Other Changes":
                assert "📝 Other Changes" in changelog
            else:
                # Find the emoji for this section
                for _commit_type, (
                    section_name,
                    _,
                    emoji,
                ) in ConventionalCommitParser.COMMIT_TYPES.items():
                    if section_name == section:
                        assert f"{emoji} {section}" in changelog
                        break


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
