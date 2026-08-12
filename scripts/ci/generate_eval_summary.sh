#!/bin/bash
# Write evaluation-summary.md. Reads HAS_OPENAI_KEY, EVENT_NAME, REPOSITORY,
# COMMIT_SHA from the environment.

set -euo pipefail

{
  echo "# MCP Evaluation Summary"
  echo ""
  echo "## Configuration"
  echo "- OpenAI API Key Available: ${HAS_OPENAI_KEY}"
  echo "- Trigger: ${EVENT_NAME}"
  echo "- Repository: ${REPOSITORY}"
  echo "- Commit: ${COMMIT_SHA}"
  echo ""
  if [ "${HAS_OPENAI_KEY}" == "false" ]; then
    echo "## Notice"
    echo "OpenAI API key was not available, so only manual tests were run."
    echo "To run full evaluations, please configure the OPENAI_API_KEY secret."
  else
    echo "## Evaluation Status"
    echo "Full MCP evaluations were attempted with OpenAI integration."
  fi
} > evaluation-summary.md
