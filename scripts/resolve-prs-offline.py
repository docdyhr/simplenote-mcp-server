#!/usr/bin/env python3
"""
Offline PR Resolution Script for Single-Developer Workflow

This script helps resolve pull requests without requiring GitHub API access.
It provides a systematic approach to review, test, and merge PRs locally.

Usage:
    python scripts/resolve-prs-offline.py --list
    python scripts/resolve-prs-offline.py --review <branch-name>
    python scripts/resolve-prs-offline.py --merge <branch-name> [--squash]
    python scripts/resolve-prs-offline.py --cleanup
    python scripts/resolve-prs-offline.py --batch-resolve

Requirements:
    - Git repository with remote branches
    - Python testing environment set up
    - Code quality tools installed (ruff, mypy, bandit)
"""

import argparse
import subprocess
import sys


class OfflinePRResolver:
    """Manages pull request resolution without GitHub API access."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.main_branch = "main"

    def _run_command(
        self, cmd: list[str], capture_output: bool = True
    ) -> tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def _print_section(self, title: str, emoji: str = "🔍") -> None:
        """Print a formatted section header."""
        print(f"\n{emoji} {title}")
        print("=" * (len(title) + 4))

    def fetch_latest(self) -> bool:
        """Fetch latest changes from remote."""
        print("📡 Fetching latest changes from remote...")
        code, _, stderr = self._run_command(["git", "fetch", "origin"])
        if code != 0:
            print(f"❌ Failed to fetch: {stderr}")
            return False
        print("✅ Fetch completed")
        return True

    def list_remote_branches(self) -> list[dict[str, str]]:
        """List all remote branches that could be PRs."""
        print("🌿 Discovering remote branches...")

        code, stdout, stderr = self._run_command(
            [
                "git",
                "for-each-ref",
                "--sort=-committerdate",
                "refs/remotes/origin",
                "--format=%(refname:short)|%(committerdate:short)|%(authorname)|%(subject)",
            ]
        )

        if code != 0:
            print(f"❌ Failed to list branches: {stderr}")
            return []

        branches = []
        for line in stdout.strip().split("\n"):
            if not line or line.startswith(f"origin/{self.main_branch}"):
                continue

            parts = line.split("|", 3)
            if len(parts) >= 4:
                branch_name = parts[0].replace("origin/", "")
                branches.append(
                    {
                        "name": branch_name,
                        "full_name": parts[0],
                        "date": parts[1],
                        "author": parts[2],
                        "subject": parts[3],
                    }
                )

        return branches

    def analyze_branch_changes(self, branch_name: str) -> dict:
        """Analyze changes in a branch compared to main."""
        print(f"🔍 Analyzing changes in {branch_name}...")

        # Get commit count
        code, stdout, _ = self._run_command(
            ["git", "rev-list", "--count", f"{self.main_branch}..origin/{branch_name}"]
        )
        commit_count = int(stdout.strip()) if code == 0 and stdout.strip() else 0

        # Get file changes
        code, stdout, _ = self._run_command(
            [
                "git",
                "diff",
                "--name-status",
                f"{self.main_branch}...origin/{branch_name}",
            ]
        )

        file_changes = []
        if code == 0:
            for line in stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) >= 2:
                        file_changes.append({"status": parts[0], "file": parts[1]})

        # Get diff stats
        code, stdout, _ = self._run_command(
            ["git", "diff", "--stat", f"{self.main_branch}...origin/{branch_name}"]
        )
        diff_stats = stdout.strip() if code == 0 else ""

        # Check if branch is ahead/behind main
        code, stdout, _ = self._run_command(
            [
                "git",
                "rev-list",
                "--left-right",
                "--count",
                f"{self.main_branch}...origin/{branch_name}",
            ]
        )
        ahead_behind = (
            stdout.strip().split("\t") if code == 0 and stdout.strip() else ["0", "0"]
        )

        return {
            "commit_count": commit_count,
            "file_changes": file_changes,
            "diff_stats": diff_stats,
            "behind_main": int(ahead_behind[0]) if len(ahead_behind) > 0 else 0,
            "ahead_main": int(ahead_behind[1]) if len(ahead_behind) > 1 else 0,
        }

    def run_quality_checks(self, branch_name: str) -> dict[str, bool]:
        """Run code quality checks on a branch."""
        print(f"🧪 Running quality checks on {branch_name}...")

        # Checkout the branch
        code, _, stderr = self._run_command(["git", "checkout", branch_name])
        if code != 0:
            print(f"❌ Failed to checkout {branch_name}: {stderr}")
            return {}

        checks = {}

        # Run tests
        print("  📋 Running tests...")
        code, stdout, stderr = self._run_command(
            ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
        )
        checks["tests"] = code == 0
        if code != 0:
            print("    ❌ Tests failed")
        else:
            print("    ✅ Tests passed")

        # Run ruff linting
        print("  🎨 Running ruff linting...")
        code, _, _ = self._run_command(["python", "-m", "ruff", "check", "."])
        checks["ruff_lint"] = code == 0
        print(f"    {'✅' if code == 0 else '❌'} Ruff linting")

        # Run ruff formatting check
        print("  📝 Checking code formatting...")
        code, _, _ = self._run_command(
            ["python", "-m", "ruff", "format", "--check", "."]
        )
        checks["ruff_format"] = code == 0
        print(f"    {'✅' if code == 0 else '❌'} Code formatting")

        # Run mypy type checking
        print("  🔍 Running type checking...")
        code, _, _ = self._run_command(["python", "-m", "mypy", "simplenote_mcp/"])
        checks["mypy"] = code == 0
        print(f"    {'✅' if code == 0 else '❌'} Type checking")

        # Run bandit security scan
        print("  🛡️ Running security scan...")
        code, _, _ = self._run_command(
            ["python", "-m", "bandit", "-r", "simplenote_mcp/", "-ll"]
        )
        checks["bandit"] = code == 0
        print(f"    {'✅' if code == 0 else '❌'} Security scan")

        return checks

    def check_merge_conflicts(self, branch_name: str) -> bool:
        """Check if branch has merge conflicts with main."""
        print(f"🔀 Checking for merge conflicts with {self.main_branch}...")

        # Use merge-tree to check for conflicts
        code, stdout, _ = self._run_command(
            [
                "git",
                "merge-tree",
                f"$(git merge-base {self.main_branch} origin/{branch_name})",
                self.main_branch,
                f"origin/{branch_name}",
            ]
        )

        has_conflicts = "<<<<<<< " in stdout
        if has_conflicts:
            print("    ❌ Merge conflicts detected")
            return False
        else:
            print("    ✅ No merge conflicts")
            return True

    def display_branch_summary(self, branch: dict[str, str]) -> None:
        """Display a formatted branch summary."""
        print(f"\n{'─' * 60}")
        print(f"🌿 Branch: {branch['name']}")
        print(f"{'─' * 60}")
        print(f"📅 Date: {branch['date']}")
        print(f"👤 Author: {branch['author']}")
        print(f"💬 Last commit: {branch['subject']}")

        # Get additional analysis
        analysis = self.analyze_branch_changes(branch["name"])

        print("📊 Changes:")
        print(f"  • {analysis['commit_count']} commits ahead of {self.main_branch}")
        print(f"  • {len(analysis['file_changes'])} files changed")

        if analysis["behind_main"] > 0:
            print(f"  ⚠️  {analysis['behind_main']} commits behind {self.main_branch}")

        if analysis["file_changes"]:
            print("  📁 Modified files:")
            for change in analysis["file_changes"][:5]:  # Show first 5 files
                status_emoji = {
                    "A": "➕",
                    "M": "📝",
                    "D": "🗑️",
                    "R": "🔄",
                    "C": "📋",
                }.get(change["status"][0], "❓")
                print(f"    {status_emoji} {change['file']}")

            if len(analysis["file_changes"]) > 5:
                print(f"    ... and {len(analysis['file_changes']) - 5} more files")

        if analysis["diff_stats"]:
            stats_lines = analysis["diff_stats"].split("\n")
            print(f"  📈 Stats: {stats_lines[-1]}")

    def review_branch(self, branch_name: str) -> dict:
        """Perform comprehensive review of a branch."""
        self._print_section(f"Reviewing Branch: {branch_name}", "🔍")

        if not self.fetch_latest():
            return {"success": False, "reason": "Failed to fetch latest changes"}

        # Check if branch exists
        code, _, _ = self._run_command(
            ["git", "show-ref", f"refs/remotes/origin/{branch_name}"]
        )
        if code != 0:
            return {"success": False, "reason": f"Branch {branch_name} not found"}

        # Analyze changes
        analysis = self.analyze_branch_changes(branch_name)

        # Check for conflicts
        no_conflicts = self.check_merge_conflicts(branch_name)

        # Run quality checks
        quality_checks = self.run_quality_checks(branch_name)

        # Return to main branch
        self._run_command(["git", "checkout", self.main_branch])

        all_checks_pass = all(quality_checks.values()) and no_conflicts

        result = {
            "success": True,
            "analysis": analysis,
            "quality_checks": quality_checks,
            "no_conflicts": no_conflicts,
            "all_checks_pass": all_checks_pass,
            "recommendation": "ready_to_merge" if all_checks_pass else "needs_fixes",
        }

        self._print_review_summary(branch_name, result)
        return result

    def _print_review_summary(self, branch_name: str, result: dict) -> None:
        """Print a summary of the review results."""
        print(f"\n📋 Review Summary for {branch_name}")
        print("─" * 40)

        # Quality checks
        for check, passed in result["quality_checks"].items():
            emoji = "✅" if passed else "❌"
            print(f"{emoji} {check.replace('_', ' ').title()}")

        # Conflicts
        emoji = "✅" if result["no_conflicts"] else "❌"
        print(f"{emoji} No merge conflicts")

        # Overall recommendation
        if result["all_checks_pass"]:
            print("\n🎉 RECOMMENDATION: Ready to merge!")
            print("💡 Suggested merge strategies:")
            if result["analysis"]["commit_count"] <= 3:
                print("   • Squash merge (recommended for small changes)")
            else:
                print("   • Regular merge (preserve commit history)")
        else:
            print("\n⚠️  RECOMMENDATION: Needs fixes before merging")
            print("🔧 Please address the failing checks above")

    def merge_branch(
        self, branch_name: str, squash: bool = False, auto_confirm: bool = False
    ) -> bool:
        """Merge a branch into main."""
        self._print_section(f"Merging Branch: {branch_name}", "🚀")

        if not auto_confirm:
            # Ask for confirmation
            merge_type = "squash merge" if squash else "regular merge"
            confirm = input(f"Proceed with {merge_type} of {branch_name}? (y/N): ")
            if confirm.lower() != "y":
                print("❌ Merge cancelled")
                return False

        # Ensure we're on main and up to date
        code, _, stderr = self._run_command(["git", "checkout", self.main_branch])
        if code != 0:
            print(f"❌ Failed to checkout {self.main_branch}: {stderr}")
            return False

        code, _, stderr = self._run_command(["git", "pull", "origin", self.main_branch])
        if code != 0:
            print(f"❌ Failed to pull latest {self.main_branch}: {stderr}")
            return False

        # Perform the merge
        if squash:
            # Squash merge
            code, _, stderr = self._run_command(
                ["git", "merge", "--squash", f"origin/{branch_name}"]
            )
            if code != 0:
                print(f"❌ Squash merge failed: {stderr}")
                return False

            # Prompt for commit message
            print("\n📝 Enter commit message for squashed merge:")
            print("Suggested format: 'feat/fix: brief description'")
            commit_msg = input("Commit message: ")
            if not commit_msg:
                commit_msg = f"Merge branch {branch_name}"

            code, _, stderr = self._run_command(["git", "commit", "-m", commit_msg])
            if code != 0:
                print(f"❌ Failed to commit: {stderr}")
                return False
        else:
            # Regular merge
            code, _, stderr = self._run_command(
                [
                    "git",
                    "merge",
                    "--no-ff",
                    f"origin/{branch_name}",
                    "-m",
                    f"Merge branch '{branch_name}'",
                ]
            )
            if code != 0:
                print(f"❌ Merge failed: {stderr}")
                return False

        # Push to remote
        code, _, stderr = self._run_command(["git", "push", "origin", self.main_branch])
        if code != 0:
            print(f"❌ Failed to push: {stderr}")
            return False

        print(f"✅ Successfully merged {branch_name}")

        # Offer to delete the branch
        if not auto_confirm:
            delete_branch = input(f"Delete remote branch {branch_name}? (Y/n): ")
            if delete_branch.lower() != "n":
                self._delete_remote_branch(branch_name)

        return True

    def _delete_remote_branch(self, branch_name: str) -> None:
        """Delete a remote branch."""
        code, _, stderr = self._run_command(
            ["git", "push", "origin", "--delete", branch_name]
        )
        if code == 0:
            print(f"🗑️  Deleted remote branch: {branch_name}")
        else:
            print(f"⚠️  Could not delete remote branch {branch_name}: {stderr}")

    def cleanup_merged_branches(self) -> None:
        """Clean up local and remote branches that have been merged."""
        self._print_section("Cleaning Up Merged Branches", "🧹")

        # Get merged branches
        code, stdout, _ = self._run_command(
            ["git", "branch", "-r", "--merged", self.main_branch]
        )

        if code != 0:
            print("❌ Failed to get merged branches")
            return

        merged_branches = []
        for line in stdout.strip().split("\n"):
            branch = line.strip()
            if (
                branch
                and not branch.endswith(f"origin/{self.main_branch}")
                and "origin/" in branch
            ):
                branch_name = branch.replace("origin/", "")
                merged_branches.append(branch_name)

        if not merged_branches:
            print("✅ No merged branches to clean up")
            return

        print(f"Found {len(merged_branches)} merged branches:")
        for branch in merged_branches:
            print(f"  🗑️  {branch}")

        confirm = input(f"\nDelete these {len(merged_branches)} branches? (y/N): ")
        if confirm.lower() == "y":
            for branch in merged_branches:
                self._delete_remote_branch(branch)

    def batch_resolve_all(self) -> None:
        """Batch resolve all eligible PRs."""
        self._print_section("Batch Resolving All PRs", "⚡")

        branches = self.list_remote_branches()

        if not branches:
            print("✅ No branches found to resolve")
            return

        print(f"Found {len(branches)} potential PR branches:")
        for i, branch in enumerate(branches, 1):
            print(f"{i}. {branch['name']} - {branch['subject']}")

        confirm = input(f"\nProcess all {len(branches)} branches? (y/N): ")
        if confirm.lower() != "y":
            print("❌ Batch resolution cancelled")
            return

        resolved_count = 0
        failed_count = 0

        for branch in branches:
            print(f"\n{'═' * 60}")
            print(f"Processing {branch['name']}...")

            review_result = self.review_branch(branch["name"])

            if review_result.get("all_checks_pass", False):
                # Determine merge strategy based on commit count
                squash = review_result["analysis"]["commit_count"] <= 3

                if self.merge_branch(branch["name"], squash=squash, auto_confirm=True):
                    resolved_count += 1
                else:
                    failed_count += 1
            else:
                print(f"❌ Skipping {branch['name']} - quality checks failed")
                failed_count += 1

        print("\n🎉 Batch resolution complete!")
        print(f"✅ Resolved: {resolved_count}")
        print(f"❌ Failed/Skipped: {failed_count}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Resolve GitHub PRs offline for single-developer workflow"
    )

    # Actions
    parser.add_argument(
        "--list", action="store_true", help="List potential PR branches"
    )
    parser.add_argument(
        "--review", type=str, metavar="BRANCH", help="Review a specific branch"
    )
    parser.add_argument(
        "--merge", type=str, metavar="BRANCH", help="Merge a specific branch"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up merged branches"
    )
    parser.add_argument(
        "--batch-resolve", action="store_true", help="Batch resolve all eligible PRs"
    )

    # Options
    parser.add_argument("--squash", action="store_true", help="Use squash merge")
    parser.add_argument(
        "--auto-confirm", action="store_true", help="Skip confirmation prompts"
    )

    args = parser.parse_args()

    try:
        resolver = OfflinePRResolver()

        if args.list:
            branches = resolver.list_remote_branches()
            if not branches:
                print("✅ No potential PR branches found")
                return

            print(f"🌿 Found {len(branches)} potential PR branches:")
            print("=" * 60)
            for branch in branches:
                resolver.display_branch_summary(branch)

        elif args.review:
            result = resolver.review_branch(args.review)
            if not result.get("success", False):
                print(f"❌ Review failed: {result.get('reason', 'Unknown error')}")
                sys.exit(1)

        elif args.merge:
            if not resolver.merge_branch(args.merge, args.squash, args.auto_confirm):
                sys.exit(1)

        elif args.cleanup:
            resolver.cleanup_merged_branches()

        elif args.batch_resolve:
            resolver.batch_resolve_all()

        else:
            # Default: list branches
            branches = resolver.list_remote_branches()
            if branches:
                print(f"🌿 Found {len(branches)} potential PR branches")
                print("\nUse --help to see available actions")
            else:
                print("✅ No potential PR branches found")

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
