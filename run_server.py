#!/usr/bin/env python
"""
run_server.py - Simplenote MCP Server Launcher for Python 3.12

This script launches the Simplenote MCP server designed for Python 3.12.

Usage:
    python run_server.py [--debug] [--verbose]

Options:
    --debug     Enable debug mode (sets LOG_LEVEL=DEBUG and MCP_DEBUG=true)
    --verbose   Enable verbose output for the server

Author: Claude
Created: May 11, 2025
"""

import argparse
import atexit
import contextlib
import datetime
import logging
import os
import signal
import sys
import time
from pathlib import Path
from subprocess import PIPE, Popen

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("simplenote-mcp-launcher")

# Ensure we're in the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

logger.info("✅ pathlib.Path is available")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Launch Simplenote MCP Server for Python 3.12"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--sync-interval",
        type=int,
        default=120,
        help="Sync interval in seconds (default: 120)",
    )
    parser.add_argument(
        "--log-file",
        action="store_true",
        help="Enable logging to file in addition to stderr",
    )
    return parser.parse_args()


def check_credentials():
    """Check if Simplenote credentials are set in the environment."""
    email = os.environ.get("SIMPLENOTE_EMAIL") or os.environ.get("SIMPLENOTE_USERNAME")
    password = os.environ.get("SIMPLENOTE_PASSWORD")

    if not email or not password:
        logger.warning("⚠️  Simplenote credentials not found in environment variables")
        logger.warning("   Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD")
        return False

    # Mask the email for privacy in logs
    masked_email = (
        email[:3] + "*" * (len(email) - 6) + email[-3:] if len(email) > 6 else "***"
    )
    logger.info(f"✅ Found credentials for: {masked_email}")
    return True


def check_server_status():
    """Check if the server is already running."""
    pid_file = Path("/tmp/simplenote_mcp_server.pid")
    alt_pid_file = Path("/tmp/simplenote_mcp_server_alt.pid")

    for file in [pid_file, alt_pid_file]:
        if file.exists():
            try:
                pid = int(file.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)  # This will raise OSError if process doesn't exist
                logger.warning(f"⚠️  Server already running with PID {pid}")
                logger.warning(
                    "   To stop it, run: ./simplenote_mcp/scripts/cleanup_servers.sh"
                )
                return True
            except (OSError, ValueError):
                # Process doesn't exist or PID file contains invalid data
                logger.info(f"Found stale PID file: {file} - ignoring")
                with contextlib.suppress(OSError):
                    file.unlink()  # Remove stale PID file
    return False


def run_server():
    """Run the Simplenote MCP server."""
    args = parse_arguments()

    # Set environment variables based on arguments
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["MCP_DEBUG"] = "true"
        logger.setLevel(logging.DEBUG)
        logger.info("🔍 Debug mode enabled")

    # Set sync interval if specified
    if args.sync_interval:
        os.environ["SYNC_INTERVAL_SECONDS"] = str(args.sync_interval)

    # Enable file logging if requested
    if args.log_file:
        os.environ["LOG_TO_FILE"] = "true"

    # Ensure debug patch output if in debug mode
    if args.debug:
        os.environ["DEBUG_PATCH"] = "true"

    # Check for credentials
    check_credentials()

    # Check if server is already running
    if check_server_status():
        response = input("Server appears to be running. Launch anyway? (y/n): ")
        if response.lower() != "y":
            logger.info("Aborted. Use cleanup script to stop existing servers.")
            sys.exit(0)

    # Print startup information
    logger.info("\n=== Starting Simplenote MCP Server ===")
    logger.info(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python version: {sys.version.split()[0]}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    logger.info(f"Verbose mode: {'Enabled' if args.verbose else 'Disabled'}")
    logger.info(f"Sync interval: {args.sync_interval} seconds")
    logger.info(f"File logging: {'Enabled' if args.log_file else 'Disabled'}")

    # Launch the server
    try:
        logger.info("\nStarting server...")
        server_path = Path(script_dir) / "simplenote_mcp_server.py"

        # Prepare environment for the process
        process_env = os.environ.copy()

        # Use the same Python interpreter that's running this script
        cmd = [sys.executable, str(server_path)]
        process = Popen(
            cmd,
            stdout=PIPE if not args.verbose else None,
            stderr=PIPE if not args.verbose else None,
            env=process_env,
        )

        # Register cleanup function
        def cleanup():
            if process and process.poll() is None:
                logger.info("\nStopping server...")
                try:
                    process.terminate()
                    # Wait briefly for clean shutdown
                    for _ in range(10):
                        if process.poll() is not None:
                            break
                        time.sleep(0.5)
                    # Force kill if still running
                    if process.poll() is None:
                        logger.warning(
                            "Server not responding to terminate signal, force killing..."
                        )
                        process.kill()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")

        atexit.register(cleanup)

        # Register signal handlers
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, lambda _s, _f: (cleanup(), sys.exit(0)))

        # Wait briefly for startup
        logger.info("Waiting for server to initialize...")
        time.sleep(3)

        if process.poll() is not None:
            # Server exited immediately
            stdout, stderr = process.communicate()
            logger.error("❌ Server failed to start")
            if stderr:
                logger.error("\nError output:")
                for line in stderr.decode().splitlines():
                    logger.error(f"  {line}")
            if stdout:
                logger.info("\nStandard output:")
                for line in stdout.decode().splitlines():
                    logger.info(f"  {line}")
            sys.exit(1)

        logger.info("✅ Server started successfully")
        logger.info(f"   PID: {process.pid}")

        # Create a PID file
        pid_file = Path("/tmp") / "simplenote_mcp_launcher.pid"
        pid_file.write_text(str(os.getpid()))

        logger.info("\nPress Ctrl+C to stop the server")

        # Log file locations
        log_files = [
            Path(script_dir) / "simplenote_mcp" / "logs" / "server.log",
            Path("/tmp") / "simplenote_mcp_debug.log",
            Path("/tmp") / "simplenote_mcp_debug_extra.log",
            Path("/Users/thomas/Library/Logs/Claude/mcp-server-simplenote.log"),
        ]

        logger.info("\nServer logs will be written to:")
        for log_file in log_files:
            if log_file.exists() or log_file.parent.exists():
                logger.info(f"   {log_file}")

        # Keep the script running and monitor the process
        try:
            while process.poll() is None:
                time.sleep(1)

            # If we get here, the process exited
            exit_code = process.returncode
            stdout, stderr = process.communicate()

            logger.warning(f"Server process exited with code {exit_code}")

            if stderr:
                logger.error("Error output from server:")
                for line in stderr.decode().splitlines():
                    logger.error(f"  {line}")

            if exit_code != 0:
                logger.error("Server crashed or exited with an error")
                sys.exit(exit_code)
            else:
                logger.info("Server shut down gracefully")

        except KeyboardInterrupt:
            logger.info("\nInterrupted by user, shutting down server...")
            cleanup()

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up PID file
        pid_file = Path("/tmp") / "simplenote_mcp_launcher.pid"
        if pid_file.exists():
            with contextlib.suppress(Exception):
                pid_file.unlink()


if __name__ == "__main__":
    run_server()
