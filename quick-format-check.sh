#!/bin/bash
# Quick formatting check script
# This runs basic formatting and linting checks

echo "🔍 Running quick formatting checks..."
python3 scripts/run-quality-checks.py --skip-tests --skip-precommit
