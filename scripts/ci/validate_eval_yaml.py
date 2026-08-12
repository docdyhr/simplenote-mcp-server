#!/usr/bin/env python3
"""Validate evals/*.yaml files: YAML syntax, then required-field structure.

Syntax errors exit non-zero; missing required fields only print a warning.
"""

import os
import sys

import yaml

REQUIRED_FIELDS = ["model", "evals"]


def validate_syntax(filepath):
    print(f"Validating {filepath}")
    try:
        with open(filepath) as f:
            yaml.safe_load(f)
        print(f"✅ {filepath} is valid YAML")
        return True
    except Exception as e:
        print(f"❌ Invalid YAML in {filepath}: {e}")
        return False


def check_structure(filepath):
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            print(f"⚠️ {os.path.basename(filepath)}: Root should be a dictionary")
            return

        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            print(f"⚠️ {os.path.basename(filepath)}: Missing required fields: {missing}")
        else:
            print(f"✅ {os.path.basename(filepath)}: Structure looks good")
    except Exception as e:
        print(f"❌ {os.path.basename(filepath)}: Error checking structure: {e}")


def main():
    yaml_files = sorted(
        os.path.join("evals", f) for f in os.listdir("evals") if f.endswith(".yaml")
    )

    all_valid = True
    for filepath in yaml_files:
        if not validate_syntax(filepath):
            all_valid = False

    if not all_valid:
        print("❌ YAML validation failed")
        sys.exit(1)

    print("Checking evaluation file structure...")
    for filepath in yaml_files:
        check_structure(filepath)


if __name__ == "__main__":
    main()
