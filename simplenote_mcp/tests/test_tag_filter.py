#!/usr/bin/env python
"""Test script to verify tag filtering functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Now import the modules
# Skip these tests for now
import pytest

from simplenote_mcp.server.cache import initialize_cache  # noqa: E402
from simplenote_mcp.server.logging import logger  # noqa: E402
from simplenote_mcp.server.server import handle_list_resources  # noqa: E402

pytestmark = pytest.mark.skip(
    reason="Tests need to be refactored to use server instance directly"
)


async def main() -> None:
    """Run the tag filter test."""
    print("=== Testing Tag Filtering ===")
    print(
        f"Using credentials for: {os.environ.get('SIMPLENOTE_EMAIL', 'Not set')[:3]}***"
    )

    # Initialize the cache first
    print("Initializing cache...")
    await initialize_cache()
    print("Cache initialized!")

    # Test without filter first
    print("\n1. Testing list_resources without filter:")
    resources = await handle_list_resources()
    print(f"Found {len(resources)} resources")
    print("Sample resource names:")
    for i, resource in enumerate(resources[:5]):
        print(f"  {i + 1}. {resource.name}")

    # Now test with a tag filter
    test_tag = "test"  # Change this to any tag you know exists in your notes
    print(f"\n2. Testing list_resources with tag filter '{test_tag}':")
    filtered_resources = await handle_list_resources(tag=test_tag)
    print(f"Found {len(filtered_resources)} resources with tag '{test_tag}'")

    if filtered_resources:
        print("Sample tagged resource names:")
        for i, resource in enumerate(filtered_resources[:5]):
            print(f"  {i + 1}. {resource.name}")
            assert test_tag in resource.meta["tags"], (
                f"Tag '{test_tag}' not found in resource tags!"
            )

        print("\nVerifying all returned resources have the requested tag...")
        all_have_tag = all(test_tag in r.meta["tags"] for r in filtered_resources)
        if all_have_tag:
            print(f"✅ Success! All returned resources have the '{test_tag}' tag.")
        else:
            print(f"❌ Error! Some resources are missing the '{test_tag}' tag.")
    else:
        print(f"No resources found with tag '{test_tag}'. Try a different tag.")

    # Test with a limit
    limit = 3
    print(f"\n3. Testing list_resources with limit {limit}:")
    limited_resources = await handle_list_resources(limit=limit)
    print(f"Requested {limit} resources, got {len(limited_resources)} resources")
    assert len(limited_resources) <= limit, (
        f"Got {len(limited_resources)} resources, expected at most {limit}"
    )

    if len(limited_resources) == limit:
        print("✅ Success! Got exactly the requested number of resources.")
    else:
        print(
            f"⚠️ Note: Got {len(limited_resources)} resources, which is less than the requested limit of {limit}."
        )
        print("   This is fine if you have fewer total notes than the requested limit.")

    print("\n=== Tag Filtering Test Complete ===")


if __name__ == "__main__":
    # Configure logging
    logger.setLevel("INFO")

    # Run the test
    asyncio.run(main())
