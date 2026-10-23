#!/bin/bash
# Check whether OPENAI_API_KEY is available (it isn't for Dependabot/fork
# PRs, which have no repo secret access) and write has-api-key to
# $GITHUB_OUTPUT. Every evals/*.yaml uses `provider: openai`, so this is the
# key mcp-evals needs. When it is absent, write the placeholder
# evaluation-output.txt that parse_eval_results.py reports as "skipped".

set -euo pipefail

if [ -n "${OPENAI_API_KEY:-}" ]; then
  echo "has-api-key=true" >> "$GITHUB_OUTPUT"
  echo "✅ OpenAI API key is available"
else
  echo "has-api-key=false" >> "$GITHUB_OUTPUT"
  echo "⚠️ OpenAI API key not available (Dependabot/fork PR) — skipping LLM evaluations"
  echo "Evaluations skipped: API key not available" > evaluation-output.txt
fi
