#!/bin/bash
# Run the selected MCP evaluation suite and capture output for
# scripts/ci/parse_eval_results.py. Reads SUITE, DESCRIPTION from the
# environment. The eval exit code goes to $GITHUB_OUTPUT for
# parse_eval_results.py, which reports a non-zero one as an error.
#
# Each timeout is a minute under the step's timeout-minutes in
# determine_eval_suite.sh: mcp-evals 2.0.1 never exits after an LLM API
# error in an eval (a 401 or rate limit), so without it the step is
# killed and nothing reports why. A timeout exits 124 instead.

set -uo pipefail

echo "Running ${DESCRIPTION}..."
case "${SUITE}" in
  smoke) timeout 4m npm run eval:smoke > evaluation-output.txt 2>&1 ;;
  basic) timeout 9m npm run eval:basic > evaluation-output.txt 2>&1 ;;
  comprehensive) timeout 19m npm run eval:comprehensive > evaluation-output.txt 2>&1 ;;
esac
EVAL_EXIT_CODE=$?
echo "exit_code=${EVAL_EXIT_CODE}" >> "$GITHUB_OUTPUT"
echo "=== Evaluation Output ==="
cat evaluation-output.txt
echo "========================="
cp evaluation-output.txt eval-results.txt
