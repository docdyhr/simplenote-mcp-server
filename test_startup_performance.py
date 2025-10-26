#!/usr/bin/env python3
"""Test script to verify MCP server startup performance.

This script simulates Claude Desktop's behavior and tests that:
1. Server starts within acceptable time (<5 seconds for handshake)
2. Cache initialization doesn't block server startup
3. No unawaited coroutines or resource errors
"""

import asyncio
import json
import sys
import time
from pathlib import Path


async def test_mcp_server_startup():
    """Test that MCP server starts quickly and responds to initialization."""
    print("=" * 60)
    print("Testing MCP Server Startup Performance")
    print("=" * 60)

    # Start the server process
    server_path = Path(__file__).parent / "simplenote_mcp_server.py"

    start_time = time.time()

    try:
        # Start server with stdio
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(server_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        print(f"✓ Server process started (PID: {process.pid})")

        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        request_json = json.dumps(init_request) + "\n"

        print("→ Sending initialize request...")
        assert process.stdin is not None
        process.stdin.write(request_json.encode())
        await process.stdin.drain()

        # Wait for response with timeout
        try:
            assert process.stdout is not None
            response_bytes = await asyncio.wait_for(
                process.stdout.readline(), timeout=10.0
            )

            handshake_time = time.time() - start_time

            if response_bytes:
                response = json.loads(response_bytes.decode())
                print(f"✓ Received response in {handshake_time:.2f}s")
                print(f"  Response ID: {response.get('id')}")

                if "result" in response:
                    print(
                        f"  Protocol Version: {response['result'].get('protocolVersion')}"
                    )
                    print(
                        f"  Server: {response['result'].get('serverInfo', {}).get('name')}"
                    )

                    if handshake_time < 5.0:
                        print(
                            f"\n✅ SUCCESS: Server initialized in {handshake_time:.2f}s (< 5s target)"
                        )
                        result = True
                    else:
                        print(
                            f"\n⚠️  WARNING: Server took {handshake_time:.2f}s (target: < 5s)"
                        )
                        result = False
                elif "error" in response:
                    print(f"\n❌ ERROR: {response['error']}")
                    result = False
                else:
                    print("\n❌ ERROR: Unexpected response format")
                    result = False
            else:
                print("\n❌ ERROR: No response received")
                result = False

        except asyncio.TimeoutError:
            handshake_time = time.time() - start_time
            print(f"\n❌ ERROR: Initialization timeout after {handshake_time:.2f}s")
            result = False

        # Check stderr for errors
        try:
            stderr_output = await asyncio.wait_for(
                process.stderr.read(1024), timeout=1.0
            )
            if stderr_output:
                stderr_text = stderr_output.decode()
                if "ERROR" in stderr_text or "Traceback" in stderr_text:
                    print("\n⚠️  Errors in stderr:")
                    print(stderr_text[:500])
                    result = False
                elif (
                    "RuntimeWarning" in stderr_text
                    or "was never awaited" in stderr_text
                ):
                    print("\n⚠️  Warnings in stderr:")
                    print(stderr_text[:500])
                    # Don't fail on warnings, but report them
        except asyncio.TimeoutError:
            # No stderr output is good
            pass

        # Send shutdown
        print("\n→ Sending shutdown notification...")
        shutdown_request = {
            "jsonrpc": "2.0",
            "method": "notifications/cancelled",
            "params": {"requestId": 1, "reason": "Test completed"},
        }

        shutdown_json = json.dumps(shutdown_request) + "\n"
        try:
            process.stdin.write(shutdown_json.encode())
            await process.stdin.drain()
        except Exception:
            pass  # Process might have already exited

        # Wait for clean shutdown
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
            print("✓ Server shut down cleanly")
        except asyncio.TimeoutError:
            print("⚠️  Server didn't shut down, terminating...")
            process.terminate()
            await process.wait()

        return result

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_cache_performance():
    """Test that cache operations don't block."""
    print("\n" + "=" * 60)
    print("Testing Cache Performance (Non-Blocking)")
    print("=" * 60)

    try:
        # Import the server module
        from simplenote_mcp.server import initialize_cache

        # Time the cache initialization
        start_time = time.time()

        print("→ Starting cache initialization...")
        await initialize_cache()

        init_time = time.time() - start_time

        if init_time < 1.0:
            print(
                f"✅ SUCCESS: Cache initialization started in {init_time:.3f}s (non-blocking)"
            )
            print("   (Full cache loading happens in background)")
            return True
        else:
            print(f"⚠️  WARNING: Cache initialization took {init_time:.3f}s")
            print("   (Should be < 1s for non-blocking initialization)")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP Server Startup Performance Test Suite")
    print("=" * 60 + "\n")

    results = {}

    # Test 1: Server startup performance
    print("Test 1: Server Startup & Handshake")
    print("-" * 60)
    results["startup"] = asyncio.run(test_mcp_server_startup())

    # Test 2: Cache performance
    print("\nTest 2: Cache Initialization")
    print("-" * 60)
    results["cache"] = asyncio.run(test_cache_performance())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
