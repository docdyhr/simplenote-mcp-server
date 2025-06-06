#!/usr/bin/env python3
"""
This module provides functionality to validate badges in README files.

It checks if badge URLs are accessible and working correctly, categorizes them
by type (GitHub Actions, Coverage, PyPI, etc.), and generates detailed reports.

Usage:
    python badge_validator.py [--readme README.md] [--json output.json] [--quiet]
"""

import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Error: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)


class BadgeValidator:
    """Validates badges in README files."""

    def __init__(self, readme_path: str = "README.md") -> None:
        self.readme_path = Path(readme_path)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; BadgeValidator/1.0)"}
        )

    def extract_badge_urls(self) -> list[str]:
        """Extract all badge URLs from README."""
        if not self.readme_path.exists():
            raise FileNotFoundError(f"README file not found: {self.readme_path}")

        with open(self.readme_path, encoding="utf-8") as f:
            content = f.read()

        # Extract badge URLs using regex patterns
        badge_pattern = r"\[!\[.*?\]\((https://[^)]+)\)\]"
        img_pattern = r"!\[.*?\]\((https://[^)]+\.svg[^)]*)\)"

        badge_urls = re.findall(badge_pattern, content)
        img_urls = re.findall(img_pattern, content)

        # Remove duplicates and return sorted list
        all_urls = list(set(badge_urls + img_urls))
        return sorted(all_urls)

    def validate_badge(self, url: str) -> dict[str, Any]:
        """Validate a single badge URL."""
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)

            # Check HTTP status
            if response.status_code != 200:
                return {
                    "valid": False,
                    "status_code": response.status_code,
                    "message": f"HTTP {response.status_code}",
                }

            # Check content type for SVG badges
            content_type = response.headers.get("content-type", "").lower()
            if "svg" in url and "svg" not in content_type and "xml" not in content_type:
                return {
                    "valid": False,
                    "status_code": response.status_code,
                    "message": "Not SVG content",
                }

            # Check response size (empty responses might indicate issues)
            if len(response.content) < 100:
                return {
                    "valid": False,
                    "status_code": response.status_code,
                    "message": "Response too small",
                }

            return {"valid": True, "status_code": response.status_code, "message": "OK"}

        except requests.exceptions.Timeout:
            return {"valid": False, "status_code": 0, "message": "Timeout"}
        except requests.exceptions.ConnectionError:
            return {"valid": False, "status_code": 0, "message": "Connection Error"}
        except requests.exceptions.RequestException as e:
            return {
                "valid": False,
                "status_code": 0,
                "message": f"Request Error: {str(e)[:50]}",
            }
        except Exception as e:
            return {
                "valid": False,
                "status_code": 0,
                "message": f"Unexpected Error: {str(e)[:50]}",
            }

    def categorize_badge(self, url: str) -> str:
        """Categorize badge by URL pattern."""
        if "actions/workflows" in url:
            return "GitHub Actions"
        elif "codecov" in url:
            return "Coverage"
        elif "shields.io" in url:
            if any(keyword in url for keyword in ["python", "version", "license"]):
                return "Project Info"
            else:
                return "Development Tool"
        elif "smithery.ai" in url:
            return "MCP Registry"
        elif "github.com" in url and ("issues" in url or "stars" in url):
            return "GitHub Stats"
        elif any(
            domain in url for domain in ["pypi.org", "badge.fury.io", "pepy.tech"]
        ):
            return "PyPI"
        else:
            return "External Service"

    def validate_all_badges(self) -> dict[str, Any]:
        """Validate all badges and return results."""
        urls = self.extract_badge_urls()

        if not urls:
            return {
                "total": 0,
                "working": 0,
                "failing": 0,
                "results": [],
                "categories": {},
                "summary": "No badges found in README",
            }

        results = []
        categories = {}

        print(f"🔍 Validating {len(urls)} badges...")

        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] Checking {urlparse(url).netloc}...", end=" ")

            validation_result = self.validate_badge(url)
            is_valid = validation_result["valid"]
            status_code = validation_result["status_code"]
            message = validation_result["message"]
            category = self.categorize_badge(url)

            result = {
                "url": url,
                "valid": is_valid,
                "status_code": status_code,
                "message": message,
                "category": category,
            }

            results.append(result)

            # Update category stats
            if category not in categories:
                categories[category] = {"total": 0, "working": 0, "failing": 0}

            categories[category]["total"] += 1
            if is_valid:
                categories[category]["working"] += 1
                print("✅")
            else:
                categories[category]["failing"] += 1
                print(f"❌ ({message})")

            # Rate limiting
            time.sleep(0.5)

        working = sum(1 for r in results if r["valid"])
        failing = len(results) - working

        return {
            "total": len(results),
            "working": working,
            "failing": failing,
            "results": results,
            "categories": categories,
            "summary": f"{working} working, {failing} failing",
        }

    def check_badge_accessibility(self, url: str) -> dict[str, Any]:
        """Check if badge is accessible and responding."""
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            accessible = response.status_code == 200
        except Exception:
            accessible = False

        return {"url": url, "accessible": accessible}

    def analyze_badge_status(self, url: str) -> dict[str, Any]:
        """Analyze the status indicated by the badge."""
        # Placeholder for future implementation
        return {"url": url, "status": "unknown"}

    def generate_detailed_report(self, results: dict[str, Any]) -> None:
        """Generate detailed validation report."""
        # Placeholder for future implementation
        pass

    def generate_report(self, validation_results: dict) -> str:
        """Generate a detailed validation report."""
        if validation_results["total"] == 0:
            return "No badges found to validate."

        report = []
        report.append("🔍 BADGE VALIDATION REPORT")
        report.append("=" * 60)
        report.append("")

        # Summary
        total = validation_results["total"]
        working = validation_results["working"]
        failing = validation_results["failing"]

        report.append(f"📊 SUMMARY: {working}/{total} badges working")
        if failing == 0:
            report.append("🎉 ALL BADGES ARE WORKING!")
        else:
            report.append(f"⚠️  {failing} badges need attention")
        report.append("")

        # Category breakdown
        report.append("📋 BY CATEGORY:")
        for category, stats in validation_results["categories"].items():
            status = "✅" if stats["failing"] == 0 else "⚠️"
            report.append(
                f"  {status} {category}: {stats['working']}/{stats['total']} working"
            )
        report.append("")

        # Detailed results
        if failing > 0:
            report.append("❌ FAILING BADGES:")
            for result in validation_results["results"]:
                if not result["valid"]:
                    domain = urlparse(result["url"]).netloc
                    report.append(
                        f"  - {domain} ({result['category']}): {result['message']}"
                    )
                    report.append(f"    URL: {result['url']}")
            report.append("")

        report.append("✅ WORKING BADGES:")
        for category, stats in validation_results["categories"].items():
            if stats["working"] > 0:
                working_badges = [
                    r
                    for r in validation_results["results"]
                    if r["valid"] and r["category"] == category
                ]
                report.append(f"  {category} ({len(working_badges)}):")
                for badge in working_badges:
                    domain = urlparse(badge["url"]).netloc
                    report.append(f"    ✅ {domain}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)

    def export_json_report(
        self,
        validation_results: dict,
        output_path: str = "badge-validation-report.json",
    ) -> None:
        """Export validation results as JSON."""
        import json
        from datetime import datetime

        export_data = {
            "timestamp": datetime.now().isoformat(),
            "readme_path": str(self.readme_path),
            "validation_results": validation_results,
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"📄 JSON report exported to: {output_path}")


def main() -> int:
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate badges in README.md")
    parser.add_argument("--readme", default="README.md", help="Path to README file")
    parser.add_argument("--json", help="Export JSON report to specified file")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")

    args = parser.parse_args()

    try:
        validator = BadgeValidator(args.readme)

        if not args.quiet:
            print(f"📖 Reading badges from: {args.readme}")

        results = validator.validate_all_badges()

        if not args.quiet:
            print()
            print(validator.generate_report(results))

        if args.json:
            validator.export_json_report(results, args.json)

        # Exit with error code if badges are failing
        if results["failing"] > 0:
            if not args.quiet:
                print(
                    f"\n❌ Validation failed: {results['failing']} badges not working"
                )
            sys.exit(1)
        else:
            if not args.quiet:
                print("\n✅ All badges validated successfully!")
            sys.exit(0)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
