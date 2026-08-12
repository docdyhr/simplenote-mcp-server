#!/usr/bin/env python3
"""Manual smoke test fallback for when OPENAI_API_KEY is unavailable.

Import-checks core server modules; used by mcp-evaluations.yml when the
mclenhard/mcp-evals action can't run.
"""

import sys

sys.path.insert(0, ".")

try:
    from simplenote_mcp.server import SimplenoteServer  # noqa: F401

    print("✅ Server class import successful")
except Exception as e:
    print(f"❌ Server import failed: {e}")

try:
    from simplenote_mcp.tools import note_tools  # noqa: F401

    print("✅ Tools import successful")
except Exception as e:
    print(f"❌ Tools import failed: {e}")
