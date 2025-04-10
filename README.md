# Simplenote MCP Server

A simple MCP (Model Context Protocol) server that connects to Simplenote as a proof of concept.

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

## Project Structure

```
simplenote_mcp/
├── logs/          # Log files directory
├── scripts/       # Helper scripts for testing and management
├── server/        # Main server code
└── tests/         # Test utilities and client
```

## Overview

This project provides an MCP server that allows you to interact with your Simplenote account through Claude Desktop or any other MCP-compatible client. 

Key features:
- List all your Simplenote notes as resources
- View note contents
- Create, update, and delete notes
- Search notes by content

## Installation

### Using uv (recommended)

```bash
uv pip install -e .
```

### Using pip

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

```bash
export SIMPLENOTE_EMAIL=your.email@example.com
export SIMPLENOTE_PASSWORD=your-password
```

## Usage

### Running the server

```bash
python simplenote_mcp_server.py
```

Or, after installation:

```bash
simplenote-mcp
```

### Testing the server

The server can be tested by running:

```bash
# Test Simplenote connectivity
python simplenote_mcp/tests/test_mcp_client.py

# Start the server in the foreground
python simplenote_mcp_server.py
```

## Connecting with Claude Desktop

1. Run the server as described above
2. In Claude Desktop, connect to the server by selecting "Connect to Tool" and choosing "Connect to subprocess"
3. Enter `simplenote-mcp`

## Available Tools

- `create_note` - Create a new note in Simplenote
- `update_note` - Update an existing note in Simplenote
- `delete_note` - Delete a note from Simplenote
- `search_notes` - Search for notes in Simplenote

## Versioning

This project follows [Semantic Versioning](https://semver.org/). See the [CHANGELOG.md](./CHANGELOG.md) file for details on version history and changes.

To release a new version, use the release script:

```bash
./simplenote_mcp/scripts/release.sh [patch|minor|major]
```

## Included Scripts

This project comes with several helper scripts in the `simplenote_mcp/scripts` directory:

1. **restart_claude.sh** - Restarts Claude Desktop and the Simplenote MCP server
2. **watch_logs.sh** - Monitors the Simplenote MCP server logs in real-time
3. **verify_tools.sh** - Checks if Simplenote tools are properly registered
4. **test_tool_visibility.sh** - Tests if tools are visible in Claude Desktop
5. **release.sh** - Releases a new version with semantic versioning

Testing utilities in the `simplenote_mcp/tests` directory:

1. **test_mcp_client.py** - Tests connectivity with the Simplenote MCP server
2. **monitor_server.py** - Helps debug communications between Claude Desktop and the server

## Troubleshooting

If you're having trouble connecting Claude Desktop to the Simplenote MCP server:

1. **Check environment variables**: Make sure `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` are set in the environment where Claude Desktop is running.

2. **Restart Claude Desktop and the server**: Use the included restart script:
   ```bash
   ./simplenote_mcp/scripts/restart_claude.sh
   ```

3. **Check logs**: View the debug logs:
   ```bash
   cat simplenote_mcp/logs/server.log
   ```

4. **Monitor logs in real-time**:
   ```bash
   ./simplenote_mcp/scripts/watch_logs.sh
   ```

5. **Kill all server instances**:
   ```bash
   pkill -f "python.*simplenote_mcp.*server.py"
   ```

6. **Claude Desktop configuration**: In `~/Library/Application Support/Claude/claude_desktop_config.json`, ensure:
   ```json
   "simplenote": {
     "description": "Access and manage your Simplenote notes",
     "command": "/path/to/your/venv/bin/python",
     "args": [
       "/path/to/simplenote_mcp_server.py"
     ],
     "autostart": true,
     "disabled": false,
     "restartOnCrash": true,
     "env": {
       "SIMPLENOTE_EMAIL": "your.email@example.com",
       "SIMPLENOTE_PASSWORD": "your-password",
       "MCP_DEBUG": "true"
     }
   }
   ```
   Note the `env` section is important to pass environment variables to the server. Adding `"MCP_DEBUG": "true"` enables additional debug logging.

### Verifying Tool Registration

To verify that the Simplenote tools are properly registered with Claude Desktop:

```bash
./simplenote_mcp/scripts/verify_tools.sh
```

This script checks if:
- The Simplenote MCP server is running
- The tools are being properly registered
- What specific tools are available

If successful, you should see output like:

```
Checking if Simplenote MCP server is running...
✓ Simplenote MCP server is running

Checking Simplenote MCP server logs for tool registration...
✓ Tools are being properly returned by the server
✓ Registered tools: create_note, update_note, delete_note, search_notes

Simplenote MCP server appears to be working correctly.
Open Claude Desktop and check if the Simplenote tools are available using:

./simplenote_mcp/scripts/test_tool_visibility.sh
```

This script will open Claude Desktop and copy a test prompt to your clipboard that asks Claude to list available tools and specifically check for Simplenote tools.