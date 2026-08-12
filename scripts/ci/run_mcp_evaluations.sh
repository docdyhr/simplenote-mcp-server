#!/bin/bash
# Run the selected MCP evaluation suite and capture output for
# scripts/ci/parse_eval_results.py. Reads SUITE, DESCRIPTION from the
# environment. A non-zero eval exit code is expected/handled downstream,
# not treated as a script failure here.

set -uo pipefail

echo "Running ${DESCRIPTION}..."
case "${SUITE}" in
  smoke) npm run eval:smoke > evaluation-output.txt 2>&1 ;;
  basic) npm run eval:basic > evaluation-output.txt 2>&1 ;;
  comprehensive) timeout 1200s npm run eval:comprehensive > evaluation-output.txt 2>&1 ;;
esac
EVAL_EXIT_CODE=$?
echo "exit_code=${EVAL_EXIT_CODE}" >> "$GITHUB_OUTPUT"
echo "=== Evaluation Output ==="
cat evaluation-output.txt
echo "========================="
cp evaluation-output.txt eval-results.txt
