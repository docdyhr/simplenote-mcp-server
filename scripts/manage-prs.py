#!/usr/bin/env python3
"""
PR Management Script for Single-Developer Workflow

This script helps manage pull requests for solo developers following best practices.
It provides options to review, merge, squash, and clean up PRs efficiently.

Usage:
    python scripts/manage-prs.py --list
    python scripts/manage-prs.py --review <pr_number>
    python scripts/manage-prs.py --merge <pr_number> [--squash]
    python scripts/manage-prs.py --close <pr_number>
    python scripts/manage-prs.py --cleanup-branches

Requirements:
    - GITHUB_TOKEN environment variable set
    - Repository owner permissions
"""

import argparse
import os
import sys

import requests


class PRManager:
    """Manages pull requests for single-developer workflows."""

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")

        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make authenticated GitHub API request."""
        response = requests.request(method, url, headers=self.headers, **kwargs)
        if response.status_code == 401:
            print("❌ Authentication failed. Check your GITHUB_TOKEN.")
            sys.exit(1)
        return response

    def list_prs(self, state: str = "open") -> list[dict]:
        """List pull requests."""
        url = f"{self.base_url}/pulls"
        params = {"state": state, "per_page": 50}
        response = self._make_request("GET", url, params=params)

        if response.status_code != 200:
            print(f"❌ Failed to fetch PRs: {response.status_code}")
            return []

        return response.json()

    def get_pr_details(self, pr_number: int) -> dict | None:
        """Get detailed PR information."""
        url = f"{self.base_url}/pulls/{pr_number}"
        response = self._make_request("GET", url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch PR #{pr_number}: {response.status_code}")
            return None

        return response.json()

    def get_pr_files(self, pr_number: int) -> list[dict]:
        """Get files changed in PR."""
        url = f"{self.base_url}/pulls/{pr_number}/files"
        response = self._make_request("GET", url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch PR files: {response.status_code}")
            return []

        return response.json()

    def get_pr_status(self, pr_number: int) -> dict:
        """Get PR status checks."""
        pr = self.get_pr_details(pr_number)
        if not pr:
            return {}

        head_sha = pr["head"]["sha"]
        url = f"{self.base_url}/commits/{head_sha}/status"
        response = self._make_request("GET", url)

        if response.status_code != 200:
            return {"state": "unknown", "statuses": []}

        return response.json()

    def merge_pr(
        self, pr_number: int, squash: bool = False, delete_branch: bool = True
    ) -> bool:
        """Merge a pull request."""
        pr = self.get_pr_details(pr_number)
        if not pr:
            return False

        # Check if PR is mergeable
        if not pr.get("mergeable", False):
            print(f"❌ PR #{pr_number} is not mergeable. Check for conflicts.")
            return False

        # Determine merge method
        merge_method = "squash" if squash else "merge"

        # Prepare merge data
        merge_data = {
            "merge_method": merge_method,
            "commit_title": pr["title"],
            "commit_message": pr["body"] or "",
        }

        # Merge the PR
        url = f"{self.base_url}/pulls/{pr_number}/merge"
        response = self._make_request("PUT", url, json=merge_data)

        if response.status_code not in [200, 201]:
            print(f"❌ Failed to merge PR #{pr_number}: {response.status_code}")
            print(response.text)
            return False

        print(f"✅ Successfully merged PR #{pr_number}")

        # Delete branch if requested
        if delete_branch and pr["head"]["ref"] != pr["base"]["ref"]:
            self._delete_branch(pr["head"]["ref"])

        return True

    def close_pr(self, pr_number: int, comment: str = "") -> bool:
        """Close a pull request without merging."""
        url = f"{self.base_url}/pulls/{pr_number}"
        data = {"state": "closed"}

        response = self._make_request("PATCH", url, json=data)

        if response.status_code != 200:
            print(f"❌ Failed to close PR #{pr_number}: {response.status_code}")
            return False

        # Add comment if provided
        if comment:
            self._add_pr_comment(pr_number, comment)

        print(f"✅ Successfully closed PR #{pr_number}")
        return True

    def _add_pr_comment(self, pr_number: int, comment: str) -> None:
        """Add a comment to a PR."""
        url = f"{self.base_url}/issues/{pr_number}/comments"
        data = {"body": comment}
        self._make_request("POST", url, json=data)

    def _delete_branch(self, branch_name: str) -> None:
        """Delete a branch."""
        url = f"{self.base_url}/git/refs/heads/{branch_name}"
        response = self._make_request("DELETE", url)

        if response.status_code == 204:
            print(f"🗑️  Deleted branch: {branch_name}")
        else:
            print(f"⚠️  Could not delete branch: {branch_name}")

    def display_pr_summary(self, pr: dict) -> None:
        """Display a formatted PR summary."""
        print(f"\n{'=' * 60}")
        print(f"PR #{pr['number']}: {pr['title']}")
        print(f"{'=' * 60}")
        print(f"📅 Created: {pr['created_at'][:10]}")
        print(f"🔀 {pr['head']['ref']} → {pr['base']['ref']}")
        print(f"👤 Author: {pr['user']['login']}")
        print(f"🏷️  State: {pr['state']}")

        if pr.get("draft"):
            print("📝 Status: DRAFT")

        if pr["body"]:
            print(
                f"\n📄 Description:\n{pr['body'][:200]}{'...' if len(pr['body']) > 200 else ''}"
            )

    def review_pr(self, pr_number: int) -> None:
        """Conduct a comprehensive PR review."""
        print(f"🔍 Reviewing PR #{pr_number}...")

        # Get PR details
        pr = self.get_pr_details(pr_number)
        if not pr:
            return

        self.display_pr_summary(pr)

        # Get changed files
        files = self.get_pr_files(pr_number)
        print(f"\n📁 Files changed ({len(files)}):")
        for file in files[:10]:  # Show first 10 files
            status = file["status"]
            filename = file["filename"]
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            print(f"  {status.upper()}: {filename} (+{additions}/-{deletions})")

        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files")

        # Get status checks
        status = self.get_pr_status(pr_number)
        print(f"\n🔧 Status: {status.get('state', 'unknown').upper()}")

        for check in status.get("statuses", []):
            state_emoji = {"success": "✅", "failure": "❌", "pending": "⏳"}.get(
                check["state"], "❓"
            )
            print(f"  {state_emoji} {check['context']}: {check['description']}")

        # Provide merge recommendations
        print("\n💡 Recommendations:")
        if pr.get("mergeable"):
            print("  ✅ PR is ready to merge")
            if len(files) <= 3:
                print("  📝 Consider squash merge for small changes")
            else:
                print("  🔀 Regular merge recommended for multiple changes")
        else:
            print("  ⚠️  Resolve conflicts before merging")

        if pr["head"]["ref"].startswith("feature/") or pr["head"]["ref"].startswith(
            "fix/"
        ):
            print("  🗑️  Delete feature branch after merge")

    def cleanup_merged_branches(self) -> None:
        """Clean up branches that have been merged."""
        print("🧹 Cleaning up merged branches...")

        # Get merged PRs
        merged_prs = self.list_prs(state="closed")
        merged_branches = []

        for pr in merged_prs:
            if pr.get("merged_at") and pr["head"]["ref"] != pr["base"]["ref"]:
                merged_branches.append(pr["head"]["ref"])

        if not merged_branches:
            print("✅ No merged branches to clean up")
            return

        print(f"Found {len(merged_branches)} merged branches:")
        for branch in merged_branches[:5]:  # Show first 5
            print(f"  🗑️  {branch}")

        if len(merged_branches) > 5:
            print(f"  ... and {len(merged_branches) - 5} more")

        confirm = input("\nDelete these branches? (y/N): ")
        if confirm.lower() == "y":
            for branch in merged_branches:
                self._delete_branch(branch)


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Manage GitHub PRs for single-developer workflow"
    )
    parser.add_argument("--owner", default="docdyhr", help="Repository owner")
    parser.add_argument(
        "--repo", default="simplenote-mcp-server", help="Repository name"
    )

    # Actions
    parser.add_argument("--list", action="store_true", help="List open PRs")
    parser.add_argument("--review", type=int, metavar="PR", help="Review a specific PR")
    parser.add_argument("--merge", type=int, metavar="PR", help="Merge a specific PR")
    parser.add_argument("--close", type=int, metavar="PR", help="Close a specific PR")
    parser.add_argument(
        "--cleanup-branches", action="store_true", help="Clean up merged branches"
    )

    # Options
    parser.add_argument("--squash", action="store_true", help="Use squash merge")
    parser.add_argument(
        "--keep-branch", action="store_true", help="Keep branch after merge"
    )
    parser.add_argument("--comment", help="Add comment when closing PR")

    args = parser.parse_args()

    try:
        manager = PRManager(args.owner, args.repo)

        if args.list:
            prs = manager.list_prs()
            if not prs:
                print("✅ No open pull requests")
                return

            print(f"📋 Open Pull Requests ({len(prs)}):")
            for pr in prs:
                draft_indicator = " [DRAFT]" if pr.get("draft") else ""
                print(f"  #{pr['number']}: {pr['title']}{draft_indicator}")
                print(f"    🔀 {pr['head']['ref']} → {pr['base']['ref']}")
                print(f"    📅 {pr['created_at'][:10]}\n")

        elif args.review:
            manager.review_pr(args.review)

        elif args.merge:
            delete_branch = not args.keep_branch
            success = manager.merge_pr(args.merge, args.squash, delete_branch)
            if success:
                print("\n🎉 PR merged successfully!")

        elif args.close:
            comment = args.comment or ""
            success = manager.close_pr(args.close, comment)
            if success:
                print("\n✅ PR closed successfully!")

        elif args.cleanup_branches:
            manager.cleanup_merged_branches()

        else:
            parser.print_help()

    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
