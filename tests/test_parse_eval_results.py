"""Regression tests for scripts/ci/parse_eval_results.py.

Until 2026-10 the Evaluation Quality Gate never produced a result. The
parser looked for "N passed ... M failed" lines that mcp-evals never prints,
and it read a crash as "0 tests" with exit 0, so a run that crashed on start
(ERR_REQUIRE_ESM under Node 18) was reported as "PASSED (Below Threshold)".
mcp-evals 2.x prints each eval under "Evaluation Results:" as
``JSON.stringify(result, null, 2)``. For YAML evals that is the grader's
reply after ``JSON.parse`` (an object with 1-5 ratings), or, when grading or
the parse fails, an all-zero placeholder whose ``overall_comments`` starts
with "Error running evaluation:" (seen in the first real run: the grader had
fenced its JSON in ```json). JS/TS evals may return the reply as a string.
"""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "ci" / "parse_eval_results.py"
)
_spec = importlib.util.spec_from_file_location("parse_eval_results", SCRIPT)
assert _spec and _spec.loader
parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parser)

HEADER = (
    "Running evals file: /w/evals/simplenote-evals.yaml\n"
    "Using server file: /w/mcp-server-wrapper.ts\n"
    "Running all evaluations...\n\n"
)
LOG = "2026-10-23 20:06:26,311 - INFO - MCP server instance created successfully\n"


def _grade(score: float, comment: str = "ok") -> dict:
    """A YAML eval's result: the grader's reply after mcp-evals' JSON.parse."""
    return dict.fromkeys(parser.CRITERIA, score) | {"overall_comments": comment}


def _grade_text(score: float, fenced: bool = True) -> str:
    """A JS/TS eval's result: the grader's reply as text."""
    body = json.dumps(_grade(score), indent=2)
    return f"```json\n{body}\n```" if fenced else body


# mcp-evals' yaml-loader.js substitutes this when grade() or JSON.parse throws
UNGRADED = _grade(
    0,
    "Error running evaluation: Unexpected token '`', \"```json\n{\n\"... is not valid JSON",
)


def _output(results: dict[str, object]) -> str:
    """Render results the way mcp-evals 2.x's cli.js prints them."""
    out = HEADER
    for name in results:
        out += f"Running {name}...\n{LOG}"
    out += "\nEvaluation Results:\n"
    for name, result in results.items():
        out += f"\n{name}:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n"
    return out


def test_all_evals_graded_above_pass_mark():
    content = _output(
        {"a": _grade(5), "b": _grade_text(4), "c": _grade_text(4, fenced=False)}
    )
    r = parser.parse_evaluation_results(content, exit_code="0")
    assert (r["total_tests"], r["passed_tests"], r["failed_tests"]) == (3, 3, 0)
    assert r["pass_rate"] == 100.0
    assert r["status"] == "success"
    assert [e["score"] for e in r["details"]] == [5.0, 4.0, 4.0]


def test_first_real_run_mcp_evals_placeholder_is_ungraded_not_zero():
    # PR #1015's first run with a valid key: 7 graded evals, 2 placeholders
    scores = {"a": 4.4, "b": 5, "c": 4.6, "d": 5, "e": 5, "f": 4.4, "g": 5}
    results = {n: _grade(s) for n, s in scores.items()}
    results |= {"lifecycle": UNGRADED, "edge_cases": UNGRADED}
    r = parser.parse_evaluation_results(_output(results), exit_code="0")
    assert (r["total_tests"], r["passed_tests"], r["failed_tests"]) == (9, 7, 2)
    assert round(r["pass_rate"], 1) == 77.8
    assert r["status"] == "acceptable"
    by_name = {e["name"]: e for e in r["details"]}
    assert by_name["lifecycle"]["score"] is None  # not a 0.0 score
    assert by_name["lifecycle"]["error"].startswith(
        "ungraded: Error running evaluation:"
    )


def test_ratings_outside_one_to_five_are_not_a_grade():
    r = parser.parse_evaluation_results(_output({"x": _grade(0, "no")}), "0")
    assert r["details"][0]["score"] is None
    assert r["details"][0]["error"] == "no 1-5 ratings in grader reply"


def test_low_score_errors_and_ungraded_text_count_as_failed():
    content = _output(
        {
            "good": _grade(4),
            "low": _grade(3),  # mean 3.0 < 3.5 pass mark
            "broken": {"error": "Failed after 2 attempts. Last error: rate limited"},
            "prose": "The tools worked well, no JSON here.",
        }
    )
    r = parser.parse_evaluation_results(content, exit_code="0")
    assert (r["total_tests"], r["passed_tests"], r["failed_tests"]) == (4, 1, 3)
    assert r["pass_rate"] == 25.0
    assert r["status"] == "poor"
    by_name = {e["name"]: e for e in r["details"]}
    assert by_name["broken"]["error"].startswith("Failed after 2 attempts")
    assert by_name["prose"]["score"] is None
    assert by_name["low"]["passed"] is False


def test_pass_mark_is_inclusive_and_mixed_ratings_average():
    mixed = json.dumps(
        {
            "accuracy": 4,
            "completeness": 3,
            "relevance": 4,
            "clarity": 3,
            "reasoning": 3.5,
            "overall_comments": "borderline",
        }
    )
    r = parser.parse_evaluation_results(_output({"edge": mixed}), exit_code="0")
    assert r["details"][0]["score"] == 3.5
    assert r["passed_tests"] == 1


def test_crash_before_results_is_an_error():
    content = (
        "> npx mcp-eval evals/simplenote-evals.yaml mcp-server-wrapper.ts\n\n"
        "Error [ERR_REQUIRE_ESM]: require() of ES Module "
        "node_modules/tsx/dist/loader.mjs not supported.\n"
        "Node.js v18.20.8\n"
    )
    r = parser.parse_evaluation_results(content, exit_code="1")
    assert r["status"] == "error"
    assert r["total_tests"] == 0
    assert "exit code 1" in r["error"]


def test_nonzero_exit_is_an_error_even_with_results():
    r = parser.parse_evaluation_results(_output({"a": _grade(5)}), exit_code="2")
    assert r["status"] == "error"
    assert "timed out" not in r["error"]


def test_timeout_exit_says_it_timed_out():
    # run_mcp_evaluations.sh wraps mcp-evals in `timeout`, which exits 124:
    # mcp-evals 2.0.1 hangs after an LLM API error instead of exiting.
    r = parser.parse_evaluation_results("Running a...\n", exit_code="124")
    assert r["status"] == "error"
    assert "timed out" in r["error"]


def test_results_section_without_evals_is_an_error():
    r = parser.parse_evaluation_results(HEADER + "\nEvaluation Results:\n", "0")
    assert r["status"] == "error"


def test_skipped_placeholder_is_skipped_not_failed():
    r = parser.parse_evaluation_results(
        "Evaluations skipped: API key not available\n", exit_code=""
    )
    assert r["status"] == "skipped"
    assert r["total_tests"] == 0


@pytest.mark.parametrize(
    "threshold,expected_gate,expected_exit",
    [("25", "true", 0), ("70", "false", 0)],
)
def test_main_writes_outputs_and_summary(
    tmp_path, monkeypatch, threshold, expected_gate, expected_exit
):
    (tmp_path / "evaluation-output.txt").write_text(
        _output({"good": _grade(5), "low": _grade(2), "x": _grade(1), "y": _grade(1)})
    )
    out = tmp_path / "gh_output"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("INPUT_FAIL_THRESHOLD", threshold)
    monkeypatch.setenv("EVAL_EXIT_CODE", "0")
    assert parser.main() == expected_exit
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs["total_tests"] == "4"
    assert outputs["passed_tests"] == "1"
    assert outputs["pass_rate"] == "25.0"
    assert outputs["quality_gate_passed"] == expected_gate
    assert outputs["status"] == "poor"
    summary = json.loads((tmp_path / "evaluation-summary.json").read_text())
    assert summary["threshold"] == float(threshold)
    assert len(summary["details"]) == 4


@pytest.mark.parametrize(
    "content,exit_code,expected_status,expected_exit",
    [
        (None, "", "error", 1),  # no output file at all
        ("Error [ERR_REQUIRE_ESM]: ...\n", "1", "error", 1),
        ("Evaluations skipped: API key not available\n", "", "skipped", 0),
    ],
)
def test_main_exit_status(
    tmp_path, monkeypatch, content, exit_code, expected_status, expected_exit
):
    if content is not None:
        (tmp_path / "evaluation-output.txt").write_text(content)
    out = tmp_path / "gh_output"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("EVAL_EXIT_CODE", exit_code)
    assert parser.main() == expected_exit
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs["status"] == expected_status
    assert outputs["quality_gate_passed"] == "false"
