#!/usr/bin/env python3
"""Parse mcp-evals output (evaluation-output.txt) into pass/fail counts.

mcp-evals 2.x prints each eval under "Evaluation Results:" as
``JSON.stringify(result, null, 2)``. For YAML evals the result is the grader's
reply after ``JSON.parse``: an object with 1-5 ratings for accuracy,
completeness, relevance, clarity and reasoning. When grading fails, or the
grader fences its JSON in ```json so the parse fails, mcp-evals substitutes
all-zero ratings with ``overall_comments: "Error running evaluation: ..."``;
that eval is ungraded, not scored 0. JS/TS evals may return the reply as a
string, and a thrown eval gives ``{"error": ...}``. An eval passes when the
mean of its five ratings is at least PASS_MARK; ungraded and errored evals
count as failed. The pass rate is the share of evals that passed.

Reads INPUT_FAIL_THRESHOLD and EVAL_EXIT_CODE from the environment; writes
pass_rate/total_tests/passed_tests/failed_tests/quality_gate_passed/status to
$GITHUB_OUTPUT, and a JSON summary to evaluation-summary.json. Exits 1 when
the run produced no usable result (a crash, a non-zero mcp-evals exit, or no
evals), so the job fails visibly instead of reporting 0 tests.
"""

import json
import os
import re
import sys

OUTPUT_FILE = "evaluation-output.txt"
RESULTS_MARKER = "Evaluation Results:"
SKIPPED_MARKER = "Evaluations skipped:"  # written by check_openai_api_key.sh
CRITERIA = ("accuracy", "completeness", "relevance", "clarity", "reasoning")
PASS_MARK = 3.5
# mcp-evals' placeholder when grading or JSON.parse fails (all ratings 0)
UNGRADED_PREFIX = "Error running evaluation:"

_NAME_LINE = re.compile(r"^(?P<name>[^\s:][^:\n]*):[ \t]*$", re.MULTILINE)
_decoder = json.JSONDecoder()


def _grade(value):
    """Return (mean rating, None) for a graded reply, else (None, reason)."""
    if isinstance(value, dict):
        candidates = [value]
    elif isinstance(value, str):
        candidates = []
        for match in re.finditer(r"\{", value):
            try:
                obj, _ = _decoder.raw_decode(value, match.start())
            except json.JSONDecodeError:
                continue
            candidates.append(obj)
    else:
        return None, "no 1-5 ratings in grader reply"
    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        ratings = [
            r
            for r in (obj.get(c) for c in CRITERIA)
            if isinstance(r, (int, float)) and not isinstance(r, bool)
        ]
        if len(ratings) == len(CRITERIA) and all(1 <= r <= 5 for r in ratings):
            return sum(ratings) / len(ratings), None
        comment = " ".join(str(obj.get("overall_comments", "")).split())
        if comment.startswith(UNGRADED_PREFIX):
            return None, "ungraded: " + comment[:200]
    return None, "no 1-5 ratings in grader reply"


def _parse_evals(content):
    """Return one dict per eval printed after RESULTS_MARKER, or None."""
    start = content.find(RESULTS_MARKER)
    if start == -1:
        return None
    text = content[start + len(RESULTS_MARKER) :]
    evals = []
    for match in _NAME_LINE.finditer(text):
        pos = match.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text) or text[pos] not in '"{':
            continue
        try:
            value, _ = _decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            continue
        name = match.group("name").strip()
        if isinstance(value, dict) and "error" in value:
            evals.append(
                {
                    "name": name,
                    "score": None,
                    "passed": False,
                    "error": str(value["error"]),
                }
            )
            continue
        score, error = _grade(value)
        evals.append(
            {
                "name": name,
                "score": score,
                "passed": score is not None and score >= PASS_MARK,
                "error": error,
            }
        )
    return evals


def parse_evaluation_results(content, exit_code=""):
    """Summarise mcp-evals output; exit_code is the mcp-evals exit status."""
    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "pass_rate": 0.0,
        "pass_mark": PASS_MARK,
        "status": "error",
        "error": None,
        "details": [],
    }
    if content is None:
        results["error"] = f"no {OUTPUT_FILE}: the evaluation step did not run"
        return results
    if content.lstrip().startswith(SKIPPED_MARKER):
        results["status"] = "skipped"
        return results
    if exit_code not in ("", "0"):
        results["error"] = f"mcp-evals exited with exit code {exit_code}" + (
            " (timed out: it hangs after an LLM API error)"
            if exit_code == "124"
            else ""
        )
        return results

    evals = _parse_evals(content)
    if not evals:
        results["error"] = (
            f"no '{RESULTS_MARKER}' section in the output"
            if evals is None
            else f"'{RESULTS_MARKER}' section lists no evals"
        )
        return results

    passed = sum(e["passed"] for e in evals)
    results.update(
        total_tests=len(evals),
        passed_tests=passed,
        failed_tests=len(evals) - passed,
        pass_rate=passed / len(evals) * 100,
        details=evals,
    )
    if passed == len(evals):
        results["status"] = "success"
    elif results["pass_rate"] >= 90:
        results["status"] = "good"
    elif results["pass_rate"] >= 70:
        results["status"] = "acceptable"
    else:
        results["status"] = "poor"
    return results


def main():
    try:
        with open(OUTPUT_FILE) as f:
            content = f.read()
    except FileNotFoundError:
        content = None
    results = parse_evaluation_results(content, os.environ.get("EVAL_EXIT_CODE", ""))

    fail_threshold = float(os.environ.get("INPUT_FAIL_THRESHOLD", "70"))
    usable = results["status"] not in ("error", "skipped")
    quality_gate_passed = usable and results["pass_rate"] >= fail_threshold

    print("Evaluation Results:")
    for e in results["details"]:
        score = "n/a" if e["score"] is None else f"{e['score']:.1f}"
        mark = "PASS" if e["passed"] else "FAIL"
        print(
            f"  {mark} {e['name']}: {score}"
            + (f" ({e['error']})" if e["error"] else "")
        )
    print(f"  Total Tests: {results['total_tests']}")
    print(f"  Passed: {results['passed_tests']} (mean rating >= {PASS_MARK})")
    print(f"  Failed: {results['failed_tests']}")
    print(f"  Pass Rate: {results['pass_rate']:.1f}%")
    print(f"  Threshold: {fail_threshold}%")
    print(f"  Status: {results['status']}")
    if results["error"]:
        print(f"  Error: {results['error']}")

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"pass_rate={results['pass_rate']:.1f}\n")
        f.write(f"total_tests={results['total_tests']}\n")
        f.write(f"passed_tests={results['passed_tests']}\n")
        f.write(f"failed_tests={results['failed_tests']}\n")
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

    if results["status"] == "error":
        print(f"::error::Evaluations produced no result: {results['error']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
