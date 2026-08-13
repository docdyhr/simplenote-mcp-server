#!/bin/bash
# Check whether ANTHROPIC_API_KEY is available (it isn't for Dependabot/fork
# PRs, which have no repo secret access) and write has-api-key to
# $GITHUB_OUTPUT. Writes a placeholder evaluation-output.txt when absent so
# downstream steps don't fail trying to read it.

set -euo pipefail

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "has-api-key=true" >> "$GITHUB_OUTPUT"
  echo "✅ Anthropic API key is available"
else
  echo "has-api-key=false" >> "$GITHUB_OUTPUT"
  echo "⚠️ Anthropic API key not available (Dependabot/fork PR) — skipping LLM evaluations"
  echo "Evaluations skipped: API key not available" > evaluation-output.txt
fi
