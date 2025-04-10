#!/usr/bin/env python
# monitor_server.py - Monitor communication with Claude Desktop

import json
import sys
import time
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "simplenote_mcp" / "logs"
MONITORING_LOG_FILE = LOG_DIR / "monitoring.log"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# For backwards compatibility
LEGACY_MONITORING_LOG_FILE = Path("/tmp/simplenote_monitoring.log")

# Print both to console and to debug log
def debug_print(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {message}")

    # Log to the new location
    with open(MONITORING_LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {message}\n")

    # Also log to legacy location for backwards compatibility
    with open(LEGACY_MONITORING_LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {message}\n")

# Clear the log files
open(MONITORING_LOG_FILE, "w").close()
open(LEGACY_MONITORING_LOG_FILE, "w").close()

debug_print("=== Starting MCP communication monitor ===")

# Buffer for input
buffer = ""

# Process messages
while True:
    try:
        # Read a chunk from stdin
        chunk = sys.stdin.buffer.read1(1024).decode('utf-8')
        if not chunk:
            debug_print("No more input, exiting")
            break

        # Add to buffer
        buffer += chunk

        # Process complete messages
        while '\r\n' in buffer:
            message, buffer = buffer.split('\r\n', 1)

            # Parse the message
            try:
                data = json.loads(message)

                # Log based on message type
                if 'method' in data:
                    method = data.get('method', '')
                    debug_print(f">>> Request: {method}")

                    # If it's a tools method, log more details
                    if 'tools' in method:
                        debug_print(f"TOOLS REQUEST: {json.dumps(data)}")

                        # Respond with tool list if it's a tools/list request
                        if method == 'tools/list':
                            response = {
                                "jsonrpc": "2.0",
                                "id": data.get("id"),
                                "result": {
                                    "tools": [
                                        {
                                            "name": "create_note",
                                            "description": "Create a new note in Simplenote",
                                            "parameters": [
                                                {
                                                    "name": "content",
                                                    "description": "The content of the note",
                                                    "required": True
                                                },
                                                {
                                                    "name": "tags",
                                                    "description": "Tags for the note (comma-separated)",
                                                    "required": False
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                            response_json = json.dumps(response)
                            sys.stdout.write(f"Content-Length: {len(response_json)}\r\n\r\n{response_json}")
                            sys.stdout.flush()
                            debug_print(f"<<< Response: tools/list with {len(response['result']['tools'])} tools")
                elif 'result' in data:
                    debug_print(f"<<< Response: id={data.get('id')}")

            except json.JSONDecodeError:
                debug_print(f"Failed to parse message: {message}")
            except Exception as e:
                debug_print(f"Error processing message: {str(e)}")

    except KeyboardInterrupt:
        debug_print("Interrupted, exiting")
        break
    except Exception as e:
        debug_print(f"Unexpected error: {str(e)}")
        break

debug_print("=== Monitor exited ===")
