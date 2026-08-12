#!/usr/bin/env python3
"""Parse MCP evaluation output (eval-results.txt) into pass/fail counts.

Reads INPUT_FAIL_THRESHOLD from the environment; writes pass_rate/total_tests/
passed_tests/failed_tests/quality_gate_passed/status to $GITHUB_OUTPUT, and a
JSON summary to evaluation-summary.json.
"""

import json
import os
import re


def parse_evaluation_results(output_file):
    """Parse MCP evaluation results from output."""
    try:
        with open(output_file) as f:
            content = f.read()
    except FileNotFoundError:
        print("No evaluation output found")
        return None

    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "pass_rate": 0.0,
        "status": "unknown",
        "details": [],
        "error_summary": [],
    }

    for line in content.split("\n"):
        line = line.strip()

        if "passed" in line.lower() and "failed" in line.lower():
            match = re.search(r"(\d+)\s+passed.*?(\d+)\s+failed", line, re.IGNORECASE)
            if match:
                results["passed_tests"] = int(match.group(1))
                results["failed_tests"] = int(match.group(2))
                results["total_tests"] = (
                    results["passed_tests"] + results["failed_tests"]
                )

        elif "%" in line and ("pass" in line.lower() or "success" in line.lower()):
            match = re.search(r"(\d+(?:\.\d+)?)%", line)
            if match:
                results["pass_rate"] = float(match.group(1))

        elif "error" in line.lower() or "fail" in line.lower():
            if len(line) > 10:
                results["error_summary"].append(line)

        elif "evaluation" in line.lower() and (
            "complete" in line.lower() or "finished" in line.lower()
        ):
            results["details"].append(line)

    if results["total_tests"] > 0 and results["pass_rate"] == 0.0:
        results["pass_rate"] = (results["passed_tests"] / results["total_tests"]) * 100

    if results["total_tests"] == 0:
        results["status"] = "no_tests"
    elif results["failed_tests"] == 0:
        results["status"] = "success"
    elif results["pass_rate"] >= 90:
        results["status"] = "good"
    elif results["pass_rate"] >= 70:
        results["status"] = "acceptable"
    else:
        results["status"] = "poor"

    return results


def main():
    results = parse_evaluation_results("eval-results.txt")

    if not results:
        print("Failed to parse evaluation results")
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("pass_rate=0\n")
            f.write("total_tests=0\n")
            f.write("passed_tests=0\n")
            f.write("failed_tests=0\n")
            f.write("quality_gate_passed=false\n")
            f.write("status=error\n")
        return

    pass_rate = results["pass_rate"]
    total_tests = results["total_tests"]
    passed_tests = results["passed_tests"]
    failed_tests = results["failed_tests"]

    fail_threshold = float(os.environ.get("INPUT_FAIL_THRESHOLD", "70"))
    quality_gate_passed = pass_rate >= fail_threshold

    print("Evaluation Results:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Pass Rate: {pass_rate:.1f}%")
    print(f"  Threshold: {fail_threshold}%")
    print(f"  Quality Gate: {'PASSED' if quality_gate_passed else 'FAILED'}")

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"pass_rate={pass_rate:.1f}\n")
        f.write(f"total_tests={total_tests}\n")
        f.write(f"passed_tests={passed_tests}\n")
        f.write(f"failed_tests={failed_tests}\n")
        f.write(f"quality_gate_passed={str(quality_gate_passed).lower()}\n")
        f.write(f"status={results['status']}\n")

    with open("evaluation-summary.json", "w") as f:
        json.dump(
            {
                **results,
                "threshold": fail_threshold,
                "quality_gate_passed": quality_gate_passed,
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
