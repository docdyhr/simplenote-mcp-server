#!/bin/bash
# Map an evaluation suite name to its timeout/description.
# Reads SUITE from the environment; writes suite/timeout/description to
# $GITHUB_OUTPUT.

set -euo pipefail

{
  echo "suite=${SUITE}"
  case "${SUITE}" in
    smoke) echo "timeout=5"; echo "description=Quick smoke tests" ;;
    basic) echo "timeout=10"; echo "description=Standard evaluation suite" ;;
    comprehensive) echo "timeout=20"; echo "description=Full comprehensive evaluation" ;;
  esac
} >> "$GITHUB_OUTPUT"
