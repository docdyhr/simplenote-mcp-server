#!/bin/bash
# Check whether OPENAI_API_KEY is available and write has-openai-key to
# $GITHUB_OUTPUT.

set -euo pipefail

if [ -n "${OPENAI_API_KEY:-}" ]; then
  echo "has-openai-key=true" >> "$GITHUB_OUTPUT"
  echo "✅ OpenAI API key is available"
else
  echo "has-openai-key=false" >> "$GITHUB_OUTPUT"
  echo "⚠️ OpenAI API key is not available - evaluations will be skipped"
fi
