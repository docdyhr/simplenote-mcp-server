#!/usr/bin/env python3
"""
Smart Validator for Claude Code
Provides intelligent code validation and suggestions for the Simplenote MCP Server
"""

import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation check"""

    file: str
    check: str
    status: str  # 'pass', 'warn', 'fail'
    message: str
    line: int | None = None
    column: int | None = None
    suggestion: str | None = None
    auto_fixable: bool = False


class SmartValidator:
    """Intelligent code validator with MCP-specific checks"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: list[ValidationResult] = []

    def validate_file(self, file_path: Path) -> list[ValidationResult]:
        """Validate a single file with all applicable checks"""
        self.results = []

        if not file_path.exists():
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="existence",
                    status="fail",
                    message="File does not exist",
                )
            )
            return self.results

        if file_path.suffix == ".py":
            self._validate_python_file(file_path)
        elif file_path.suffix == ".yml" or file_path.suffix == ".yaml":
            self._validate_yaml_file(file_path)
        elif file_path.suffix == ".md":
            self._validate_markdown_file(file_path)

        return self.results

    def _validate_python_file(self, file_path: Path):
        """Validate Python file with MCP-specific checks"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            try:
                tree = ast.parse(content)
                self.results.append(
                    ValidationResult(
                        file=str(file_path),
                        check="syntax",
                        status="pass",
                        message="Valid Python syntax",
                    )
                )
            except SyntaxError as e:
                self.results.append(
                    ValidationResult(
                        file=str(file_path),
                        check="syntax",
                        status="fail",
                        message=f"Syntax error: {e.msg}",
                        line=e.lineno,
                        column=e.offset,
                    )
                )
                return

            # MCP-specific checks
            self._check_mcp_patterns(file_path, content, tree)
            self._check_security_patterns(file_path, content)
            self._check_performance_patterns(file_path, content, tree)
            self._check_testing_patterns(file_path, content, tree)
            self._check_documentation_patterns(file_path, content, tree)

        except Exception as e:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="read",
                    status="fail",
                    message=f"Failed to read file: {e}",
                )
            )

    def _check_mcp_patterns(self, file_path: Path, content: str, tree: ast.AST):
        """Check MCP-specific patterns and best practices"""

        # Check for proper MCP handler patterns
        if "tool_handlers" in str(file_path):
            self._check_tool_handler_patterns(file_path, content, tree)

        # Check for proper error handling
        if "server" in str(file_path):
            self._check_server_patterns(file_path, content, tree)

        # Check for proper validation decorators
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_function_validation(file_path, node)

    def _check_tool_handler_patterns(
        self, file_path: Path, content: str, tree: ast.AST
    ):
        """Check tool handler specific patterns"""

        # Check for proper inheritance
        has_base_handler = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and "Handler" in base.id:
                        has_base_handler = True
                        break

        if "handler" in str(file_path).lower() and not has_base_handler:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="mcp_pattern",
                    status="warn",
                    message="Tool handler should inherit from base handler class",
                    suggestion="Inherit from ToolHandlerBase or appropriate base class",
                )
            )

        # Check for proper validation decorators
        if "@validate_" not in content and "Handler" in content:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="mcp_pattern",
                    status="warn",
                    message="Tool handlers should use validation decorators",
                    suggestion="Add @validate_note_id_required or similar decorators",
                )
            )

    def _check_server_patterns(self, file_path: Path, content: str, tree: ast.AST):
        """Check server-specific patterns"""

        # Check for proper async patterns
        has_async_handler = False
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith(
                "handle_"
            ):
                has_async_handler = True
                break

        if "handle_" in content and not has_async_handler:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="mcp_pattern",
                    status="warn",
                    message="MCP handlers should be async functions",
                    suggestion="Convert handler functions to async def",
                )
            )

        # Check for proper error handling in handlers
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith(
                "handle_"
            ):
                has_try_except = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        has_try_except = True
                        break

                if not has_try_except:
                    self.results.append(
                        ValidationResult(
                            file=str(file_path),
                            check="error_handling",
                            status="warn",
                            message=f"Handler {node.name} should have try-except block",
                            line=node.lineno,
                            suggestion="Add try-except for proper error handling",
                        )
                    )

    def _check_function_validation(self, file_path: Path, node: ast.FunctionDef):
        """Check function validation patterns"""

        # Check for validation decorators on public functions
        if not node.name.startswith("_") and len(node.args.args) > 1:
            has_validation = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and "validate" in decorator.id:
                    has_validation = True
                    break
                elif isinstance(decorator, ast.Call) and hasattr(decorator.func, "id"):
                    if "validate" in decorator.func.id:
                        has_validation = True
                        break

            # Only warn for functions that likely need validation
            if "note_id" in [arg.arg for arg in node.args.args] and not has_validation:
                self.results.append(
                    ValidationResult(
                        file=str(file_path),
                        check="validation",
                        status="warn",
                        message=f"Function {node.name} should validate note_id parameter",
                        line=node.lineno,
                        suggestion="Add @validate_note_id_required decorator",
                    )
                )

    def _check_security_patterns(self, file_path: Path, content: str):
        """Check for security patterns and vulnerabilities"""

        # Check for hardcoded credentials
        credential_patterns = [
            r'SIMPLENOTE_PASSWORD\s*=\s*["\'][^"\']+["\']',
            r'SIMPLENOTE_EMAIL\s*=\s*["\'][^"\']+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            for pattern in credential_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.results.append(
                        ValidationResult(
                            file=str(file_path),
                            check="security",
                            status="fail",
                            message="Hardcoded credential detected",
                            line=i,
                            suggestion="Use environment variables: os.getenv('VARIABLE_NAME')",
                        )
                    )

        # Check for SQL injection patterns
        sql_patterns = [r'f".*{.*}.*".*SQL', r'".*%s.*".*execute', r"query.*\+.*user"]

        for i, line in enumerate(lines, 1):
            for pattern in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.results.append(
                        ValidationResult(
                            file=str(file_path),
                            check="security",
                            status="warn",
                            message="Potential SQL injection vulnerability",
                            line=i,
                            suggestion="Use parameterized queries",
                        )
                    )

    def _check_performance_patterns(self, file_path: Path, content: str, tree: ast.AST):
        """Check for performance anti-patterns"""

        # Check for synchronous calls in async functions
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Check for blocking calls
                        if isinstance(child.func, ast.Attribute):
                            if (
                                child.func.attr in ["sleep", "wait"]
                                and not isinstance(child.func.value, ast.Name)
                                or child.func.value.id != "asyncio"
                            ):
                                self.results.append(
                                    ValidationResult(
                                        file=str(file_path),
                                        check="performance",
                                        status="warn",
                                        message=f"Use asyncio.{child.func.attr} in async function",
                                        line=child.lineno,
                                        suggestion=f"Replace with await asyncio.{child.func.attr}()",
                                    )
                                )

        # Check for inefficient loops
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check for list concatenation in loops
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(
                        child.op, ast.Add
                    ):
                        self.results.append(
                            ValidationResult(
                                file=str(file_path),
                                check="performance",
                                status="warn",
                                message="List concatenation in loop is inefficient",
                                line=node.lineno,
                                suggestion="Use list.extend() or list comprehension",
                            )
                        )

    def _check_testing_patterns(self, file_path: Path, content: str, tree: ast.AST):
        """Check testing patterns and coverage"""

        if "test_" not in str(file_path):
            return

        # Check for proper test structure
        test_classes = []
        test_functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                test_classes.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                test_functions.append(node)

        if not test_classes and not test_functions:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="testing",
                    status="warn",
                    message="No test classes or functions found",
                    suggestion="Add test classes or functions starting with 'test_'",
                )
            )

        # Check for async test patterns
        for func in test_functions:
            if isinstance(func, ast.FunctionDef) and "async" not in [
                d.id for d in func.decorator_list if isinstance(d, ast.Name)
            ]:
                # Check if function uses await
                for node in ast.walk(func):
                    if isinstance(node, ast.Await):
                        self.results.append(
                            ValidationResult(
                                file=str(file_path),
                                check="testing",
                                status="warn",
                                message=f"Test {func.name} uses await but is not async",
                                line=func.lineno,
                                suggestion="Add @pytest.mark.asyncio decorator and make function async",
                            )
                        )
                        break

    def _check_documentation_patterns(
        self, file_path: Path, content: str, tree: ast.AST
    ):
        """Check documentation patterns"""

        # Check for docstrings in classes and functions
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef | ast.FunctionDef)
                and not node.name.startswith("_")
                and not ast.get_docstring(node)
            ):
                self.results.append(
                    ValidationResult(
                        file=str(file_path),
                        check="documentation",
                        status="warn",
                        message=f"{type(node).__name__.lower()} {node.name} missing docstring",
                        line=node.lineno,
                        suggestion="Add descriptive docstring",
                    )
                )

    def _validate_yaml_file(self, file_path: Path):
        """Validate YAML files"""
        try:
            import yaml

            with open(file_path) as f:
                yaml.safe_load(f)
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="yaml_syntax",
                    status="pass",
                    message="Valid YAML syntax",
                )
            )
        except yaml.YAMLError as e:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="yaml_syntax",
                    status="fail",
                    message=f"YAML syntax error: {e}",
                )
            )
        except ImportError:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="yaml_syntax",
                    status="warn",
                    message="PyYAML not available for validation",
                )
            )

    def _validate_markdown_file(self, file_path: Path):
        """Validate Markdown files"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for broken links (simple pattern)
            broken_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            for _link_text, link_url in broken_links:
                if link_url.startswith("http"):
                    continue  # Skip external links for now

                if link_url.startswith("/"):
                    link_path = self.project_root / link_url.lstrip("/")
                else:
                    link_path = file_path.parent / link_url

                if not link_path.exists():
                    self.results.append(
                        ValidationResult(
                            file=str(file_path),
                            check="markdown_links",
                            status="warn",
                            message=f"Broken link: {link_url}",
                            suggestion="Check link target exists",
                        )
                    )

        except Exception as e:
            self.results.append(
                ValidationResult(
                    file=str(file_path),
                    check="markdown",
                    status="fail",
                    message=f"Failed to validate markdown: {e}",
                )
            )


def main():
    """Main CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Smart validator for Simplenote MCP Server"
    )
    parser.add_argument("files", nargs="*", help="Files to validate")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues where possible"
    )
    parser.add_argument(
        "--warnings-as-errors", action="store_true", help="Treat warnings as errors"
    )

    args = parser.parse_args()

    project_root = Path.cwd()
    while (
        not (project_root / "pyproject.toml").exists()
        and project_root != project_root.parent
    ):
        project_root = project_root.parent

    validator = SmartValidator(project_root)
    all_results = []

    # Determine files to validate
    files_to_validate = []
    if args.files:
        files_to_validate = [Path(f) for f in args.files]
    else:
        # Auto-detect changed files
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1..HEAD"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                files_to_validate = [
                    Path(f.strip()) for f in result.stdout.split("\n") if f.strip()
                ]
        except Exception:
            pass

        if not files_to_validate:
            # Fallback to Python files in project
            files_to_validate = list(project_root.rglob("*.py"))
            files_to_validate = [
                f
                for f in files_to_validate
                if "test_" not in str(f) or len(files_to_validate) < 10
            ]

    # Validate files
    for file_path in files_to_validate:
        if file_path.exists():
            results = validator.validate_file(file_path)
            all_results.extend(results)

    # Output results
    if args.json:
        print(json.dumps([asdict(r) for r in all_results], indent=2))
    else:
        # Pretty print results
        error_count = 0
        warn_count = 0

        for result in all_results:
            if result.status == "fail":
                print(
                    f"❌ {result.file}:{result.line or ''} [{result.check}] {result.message}"
                )
                if result.suggestion:
                    print(f"   💡 {result.suggestion}")
                error_count += 1
            elif result.status == "warn":
                print(
                    f"⚠️  {result.file}:{result.line or ''} [{result.check}] {result.message}"
                )
                if result.suggestion:
                    print(f"   💡 {result.suggestion}")
                warn_count += 1

        # Summary
        print(f"\n📊 Validation complete: {error_count} errors, {warn_count} warnings")

        if error_count > 0 or (args.warnings_as_errors and warn_count > 0):
            sys.exit(1)


if __name__ == "__main__":
    main()
