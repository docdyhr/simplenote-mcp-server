#!/usr/bin/env python3
"""
Development Assistant for Claude Code
Provides intelligent development assistance and automation for the Simplenote MCP Server
"""

import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class DevelopmentAssistant:
    """Intelligent development assistant for Claude Code"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_file = project_root / ".claude-assistant.json"
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load assistant configuration"""
        default_config = {
            "auto_test": True,
            "auto_format": True,
            "watch_patterns": ["**/*.py", "tests/**/*.py"],
            "ignore_patterns": ["**/__pycache__/**", "**/*.pyc"],
            "notifications": True,
            "learning_mode": True,
            "patterns": {},
            "suggestions": [],
        }

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")

        return default_config

    def _save_config(self):
        """Save assistant configuration"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def learn_from_action(self, action: str, context: dict[str, Any], success: bool):
        """Learn from user actions to improve suggestions"""
        if not self.config.get("learning_mode", False):
            return

        pattern_key = f"{action}_{context.get('file_type', 'unknown')}"

        if pattern_key not in self.config["patterns"]:
            self.config["patterns"][pattern_key] = {
                "success_count": 0,
                "failure_count": 0,
                "contexts": [],
            }

        pattern = self.config["patterns"][pattern_key]

        if success:
            pattern["success_count"] += 1
        else:
            pattern["failure_count"] += 1

        pattern["contexts"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "success": success,
            }
        )

        # Keep only recent contexts
        pattern["contexts"] = pattern["contexts"][-10:]

        self._save_config()

    def suggest_actions(self, current_file: str | None = None) -> list[str]:
        """Suggest relevant actions based on context and learning"""
        suggestions = []

        if current_file:
            file_path = Path(current_file)

            # File type specific suggestions
            if file_path.suffix == ".py":
                suggestions.extend(self._python_file_suggestions(file_path))
            elif "test_" in file_path.name:
                suggestions.extend(self._test_file_suggestions(file_path))

        # Project level suggestions
        suggestions.extend(self._project_level_suggestions())

        return suggestions

    def _python_file_suggestions(self, file_path: Path) -> list[str]:
        """Suggestions for Python files"""
        suggestions = []

        try:
            with open(file_path) as f:
                content = f.read()

            # Check if file needs formatting
            result = subprocess.run(
                ["ruff", "check", str(file_path)], capture_output=True, text=True
            )
            if result.returncode != 0:
                suggestions.append("🔧 Run formatter on this file")

            # Check if file has tests
            test_file = self.project_root / "tests" / f"test_{file_path.name}"
            if not test_file.exists() and "def " in content:
                suggestions.append("🧪 Create test file for this module")

            # Check for TODO comments
            if "TODO" in content or "FIXME" in content:
                suggestions.append("📝 Review TODO/FIXME comments")

        except Exception:  # noqa: BLE001
            pass  # File read error, skip suggestions

        return suggestions

    def _test_file_suggestions(self, file_path: Path) -> list[str]:
        """Suggestions for test files"""
        suggestions = []

        # Check if tests are passing
        result = subprocess.run(
            ["python", "-m", "pytest", str(file_path), "-q"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            suggestions.append("⚠️ Fix failing tests in this file")

        # Check test coverage
        module_name = file_path.name.replace("test_", "").replace(".py", "")
        module_path = self.project_root / "simplenote_mcp" / f"{module_name}.py"
        if module_path.exists():
            suggestions.append(f"📊 Check coverage for {module_name}")

        return suggestions

    def _project_level_suggestions(self) -> list[str]:
        """Project level suggestions"""
        suggestions = []

        # Check if there are uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )
        if result.stdout.strip():
            suggestions.append("📋 Review uncommitted changes")

        # Check if CI is failing
        try:
            result = subprocess.run(
                ["gh", "run", "list", "--limit", "1", "--json", "conclusion"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs and runs[0].get("conclusion") == "failure":
                    suggestions.append("🚨 Fix failing CI/CD pipeline")
        except Exception:  # noqa: BLE001
            pass  # gh CLI not available or API error

        return suggestions

    def auto_fix_common_issues(self, file_path: str | None = None) -> dict[str, Any]:
        """Automatically fix common issues"""
        results = {"fixes_applied": [], "suggestions": [], "errors": []}

        try:
            # Auto format if enabled
            if self.config.get("auto_format", True):
                if file_path:
                    result = subprocess.run(
                        ["ruff", "format", file_path], capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        results["fixes_applied"].append(f"Formatted {file_path}")
                else:
                    result = subprocess.run(
                        ["ruff", "format", "."], capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        results["fixes_applied"].append("Formatted all Python files")

            # Auto fix linting issues
            if file_path:
                result = subprocess.run(
                    ["ruff", "check", "--fix", file_path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout:
                    results["fixes_applied"].append(
                        f"Fixed linting issues in {file_path}"
                    )
            else:
                result = subprocess.run(
                    ["ruff", "check", "--fix", "."], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout:
                    results["fixes_applied"].append("Fixed linting issues")

        except Exception as e:
            results["errors"].append(str(e))

        return results

    def run_intelligent_tests(self, file_path: str | None = None) -> dict[str, Any]:
        """Run tests intelligently based on file changes"""
        results = {"tests_run": [], "passed": 0, "failed": 0, "output": ""}

        # Determine which tests to run
        test_files = []

        if file_path:
            file_path = Path(file_path)

            # If it's a test file, run it directly
            if "test_" in file_path.name:
                test_files.append(str(file_path))
            else:
                # Find related test file
                test_file = self.project_root / "tests" / f"test_{file_path.name}"
                if test_file.exists():
                    test_files.append(str(test_file))

                # Also find tests that import this module
                module_name = str(file_path).replace(".py", "").replace("/", ".")
                if module_name.startswith("simplenote_mcp"):
                    for test_file in (self.project_root / "tests").glob("test_*.py"):
                        try:
                            with open(test_file) as f:
                                content = f.read()
                                if module_name in content:
                                    test_files.append(str(test_file))
                        except Exception:  # noqa: BLE001
                            pass  # Skip unreadable test files

        # Remove duplicates
        test_files = list(set(test_files))

        if not test_files:
            # Run all tests as fallback
            test_files = ["tests/"]

        # Run tests
        try:
            env = os.environ.copy()
            env["SIMPLENOTE_OFFLINE_MODE"] = "true"

            for test_target in test_files:
                cmd = ["python", "-m", "pytest", test_target, "-v", "--tb=short"]
                result = subprocess.run(cmd, capture_output=True, text=True, env=env)

                results["tests_run"].append(test_target)
                results["output"] += result.stdout + result.stderr

                # Parse results
                if "passed" in result.stdout:
                    passed = len(
                        [
                            line
                            for line in result.stdout.split("\n")
                            if "::" in line and "PASSED" in line
                        ]
                    )
                    results["passed"] += passed

                if "failed" in result.stdout:
                    failed = len(
                        [
                            line
                            for line in result.stdout.split("\n")
                            if "::" in line and "FAILED" in line
                        ]
                    )
                    results["failed"] += failed

        except Exception as e:
            results["output"] += f"Error running tests: {e}"

        return results

    def generate_test_suggestions(self, file_path: str) -> list[str]:
        """Generate test suggestions for a file"""
        suggestions = []

        try:
            import ast

            with open(file_path) as f:
                content = f.read()

            tree = ast.parse(content)

            # Find functions that need tests
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    test_file = (
                        self.project_root / "tests" / f"test_{Path(file_path).name}"
                    )

                    if test_file.exists():
                        with open(test_file) as f:
                            test_content = f.read()

                        if f"test_{node.name}" not in test_content:
                            suggestions.append(f"Add test for function: {node.name}")
                    else:
                        suggestions.append(
                            f"Create test file and add test for: {node.name}"
                        )

        except Exception as e:
            suggestions.append(f"Could not analyze file: {e}")

        return suggestions

    def monitor_project(self, duration: int = 60):
        """Monitor project for changes and provide real-time assistance"""
        print(f"🔍 Monitoring project for {duration} seconds...")

        last_modification_times = {}

        # Get initial modification times
        for pattern in self.config.get("watch_patterns", []):
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    last_modification_times[str(file_path)] = file_path.stat().st_mtime

        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                # Check for modified files
                for pattern in self.config.get("watch_patterns", []):
                    for file_path in self.project_root.glob(pattern):
                        if file_path.is_file():
                            current_mtime = file_path.stat().st_mtime
                            file_str = str(file_path)

                            if file_str not in last_modification_times:
                                print(f"📄 New file: {file_path.name}")
                                last_modification_times[file_str] = current_mtime

                                # Provide suggestions for new file
                                suggestions = self.suggest_actions(file_str)
                                for suggestion in suggestions:
                                    print(f"  💡 {suggestion}")

                            elif current_mtime > last_modification_times[file_str]:
                                print(f"✏️  Modified: {file_path.name}")
                                last_modification_times[file_str] = current_mtime

                                # Auto-fix if enabled
                                if self.config.get("auto_format", True):
                                    fixes = self.auto_fix_common_issues(file_str)
                                    for fix in fixes["fixes_applied"]:
                                        print(f"  🔧 {fix}")

                                # Auto-test if enabled
                                if (
                                    self.config.get("auto_test", True)
                                    and file_path.suffix == ".py"
                                ):
                                    test_results = self.run_intelligent_tests(file_str)
                                    if test_results["failed"] > 0:
                                        print(
                                            f"  ❌ {test_results['failed']} test(s) failed"
                                        )
                                    elif test_results["passed"] > 0:
                                        print(
                                            f"  ✅ {test_results['passed']} test(s) passed"
                                        )

                time.sleep(1)

            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"⚠️ Error during monitoring: {e}")
                time.sleep(5)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Development Assistant for Simplenote MCP Server"
    )
    parser.add_argument(
        "--monitor", type=int, default=0, help="Monitor project for N seconds"
    )
    parser.add_argument("--suggest", action="store_true", help="Show suggestions")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--test", action="store_true", help="Run intelligent tests")
    parser.add_argument("--file", help="Target specific file")
    parser.add_argument(
        "--generate-tests", action="store_true", help="Generate test suggestions"
    )
    parser.add_argument("--config", action="store_true", help="Show configuration")

    args = parser.parse_args()

    # Find project root
    project_root = Path.cwd()
    while (
        not (project_root / "pyproject.toml").exists()
        and project_root != project_root.parent
    ):
        project_root = project_root.parent

    assistant = DevelopmentAssistant(project_root)

    if args.config:
        print(json.dumps(assistant.config, indent=2))
        return

    if args.monitor > 0:
        assistant.monitor_project(args.monitor)
        return

    if args.suggest:
        suggestions = assistant.suggest_actions(args.file)
        print("💡 Suggestions:")
        for suggestion in suggestions:
            print(f"  {suggestion}")
        return

    if args.fix:
        results = assistant.auto_fix_common_issues(args.file)
        print("🔧 Auto-fix results:")
        for fix in results["fixes_applied"]:
            print(f"  ✅ {fix}")
        for error in results["errors"]:
            print(f"  ❌ {error}")
        return

    if args.test:
        results = assistant.run_intelligent_tests(args.file)
        print("🧪 Test results:")
        print(f"  Tests run: {len(results['tests_run'])}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        if results["failed"] > 0:
            print("\n📋 Output:")
            print(results["output"])
        return

    if args.generate_tests and args.file:
        suggestions = assistant.generate_test_suggestions(args.file)
        print(f"🧪 Test suggestions for {args.file}:")
        for suggestion in suggestions:
            print(f"  {suggestion}")
        return

    # Default: show general suggestions
    suggestions = assistant.suggest_actions()
    print("💡 General suggestions:")
    for suggestion in suggestions:
        print(f"  {suggestion}")


if __name__ == "__main__":
    main()
