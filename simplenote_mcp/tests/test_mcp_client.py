#!/usr/bin/env python
# test_mcp_client.py - Simple test client for the Simplenote MCP server

import asyncio
import os
import sys

# Add the parent directory to the Python path so we can import the server module
script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Now we can import from our compatibility module
from simplenote_mcp.server.compat import Path

# Set project root path as a string for system path
PROJECT_ROOT_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT_PATH))

from simplenote_mcp.server import get_simplenote_client  # noqa: E402


async def test_simplenote_connection() -> bool:
    """Test the connection to Simplenote."""
    print("Testing Simplenote connection...")
    try:
        client = get_simplenote_client()
        notes, status = client.get_note_list()
        print(f"Connection successful! Found {len(notes)} notes (status: {status})")

        # Print the first few notes
        print("\nFirst 5 notes:")
        for i, note in enumerate(notes[:5]):
            first_line = (
                note.get("content", "").splitlines()[0][:50]
                if note.get("content")
                else "No content"
            )
            print(f"{i + 1}. {first_line}...")

        return True
    except Exception as e:
        print(f"Error connecting to Simplenote: {e}")
        return False


async def test_read_note() -> bool:
    """Test reading a specific note."""
    print("\nTesting note retrieval...")
    try:
        client = get_simplenote_client()
        notes, status = client.get_note_list()

        if not notes:
            print("No notes found to test reading.")
            return False

        # Get the first note
        note_id = notes[0]["key"]
        print(f"Reading note with ID: {note_id}")

        note, status = client.get_note(note_id)
        if status == 0:
            first_line = (
                note.get("content", "").splitlines()[0][:50]
                if note.get("content")
                else "No content"
            )
            print(f"Successfully retrieved note: {first_line}...")
            return True
        else:
            print(f"Failed to retrieve note (status: {status})")
            return False
    except Exception as e:
        print(f"Error reading note: {e}")
        return False


async def test_create_note() -> bool:
    """Test creating a new note."""
    print("\nTesting note creation...")
    try:
        client = get_simplenote_client()

        test_content = f"Test note created by test_mcp_client.py at {__import__('datetime').datetime.now()}"
        note = {"content": test_content, "tags": ["test", "mcp"]}

        created_note, status = client.add_note(note)
        if status == 0:
            print(f"Successfully created note with ID: {created_note.get('key')}")
            return True
        else:
            print(f"Failed to create note (status: {status})")
            return False
    except Exception as e:
        print(f"Error creating note: {e}")
        return False


async def main() -> bool:
    """Run all tests."""
    print("=" * 50)
    print("SIMPLENOTE MCP SERVER TEST CLIENT")
    print("=" * 50)

    # Check environment variables
    username = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get(
        "SIMPLENOTE_USERNAME"
    )
    password = os.environ.get("SIMPLENOTE_PASSWORD")

    if not username or not password:
        print("ERROR: Missing environment variables.")
        print("Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD.")
        return False

    print(f"Using credentials for: {username[:3]}***")

    # Run tests
    tests = [
        ("Connection to Simplenote", await test_simplenote_connection()),
        ("Reading a note", await test_read_note()),
        ("Creating a note", await test_create_note()),
    ]

    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, result in tests:
        status = "PASSED" if result else "FAILED"
        status_colored = (
            f"\033[92m{status}\033[0m" if result else f"\033[91m{status}\033[0m"
        )
        print(f"{name}: {status_colored}")
        all_passed = all_passed and result

    print("\nOverall status:", "PASSED" if all_passed else "FAILED")
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
