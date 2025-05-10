# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure
```
simplenote_mcp/            # Main package
├── logs/                  # Log files directory
├── scripts/               # Helper scripts for testing and management
├── server/                # Main server code
│   ├── __init__.py        # Package exports
│   └── server.py          # Server implementation
└── tests/                 # Test utilities and client
```

## Commands
- **Install**: `uv pip install -e .` or `pip install -e .`
- **Run server**: `python simplenote_mcp_server.py` or `simplenote-mcp`
- **Restart Claude and server**: `./simplenote_mcp/scripts/restart_claude.sh`
- **Clean up server processes**: `./simplenote_mcp/scripts/cleanup_servers.sh`
- **Check server status**: `./simplenote_mcp/scripts/check_server_pid.sh`
- **Watch logs**: `./simplenote_mcp/scripts/watch_logs.sh`
- **Verify tools**: `./simplenote_mcp/scripts/verify_tools.sh`
- **Test tool visibility**: `./simplenote_mcp/scripts/test_tool_visibility.sh`
- **Test Simplenote client library integration**: `pytest simplenote_mcp/tests/test_mcp_client.py`
- **Run all tests**: `pytest`
- **Lint**: `ruff check .`
- **Format**: `black .`
- **Type check**: `mypy simplenote_mcp`

## Environment Setup
- Set `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` environment variables for authentication
- For Claude Desktop integration, add these variables to `claude_desktop_config.json`

## Server Structure
The Simplenote MCP server provides:
1. **Resources**: `list_resources()`, `read_resource()`
2. **Tools**: `create_note`, `update_note`, `delete_note`, `get_note`, `search_notes`
3. **Prompts**: `create_note_prompt`, `search_notes_prompt`

## Common Issues and Solutions
1. **Tool registration issues**: Run `./simplenote_mcp/scripts/verify_tools.sh` and check logs with `./simplenote_mcp/scripts/watch_logs.sh`
2. **Authentication issues**: Check environment variables or Claude Desktop config
3. **API format issues**: The MCP library uses JSON Schema format with `inputSchema` property
4. **Multiple server instances**: If multiple server instances are running and causing issues, use `./simplenote_mcp/scripts/cleanup_servers.sh` to terminate them gracefully

## Important Code Sections
- **Tool definition** (in handle_list_tools): Defines tools using JSON Schema format
- **Authentication** (in get_simplenote_client): Handles Simplenote authentication
- **Server initialization** (in run): Sets up the MCP server and capabilities

## Code Style Guidelines
- **Imports**: Group standard library, third-party, and local imports with a blank line between groups
- **Typing**: Use type hints for all function arguments and return values
- **Naming**: Use snake_case for variables/functions, CamelCase for classes
- **Error handling**: Use try/except blocks with specific exceptions
- **String formatting**: Prefer f-strings over other formats
- **Docstrings**: Use docstrings for all functions explaining purpose and parameters
- **Line length**: Keep lines under 88 characters
- **Logging**: Use the log_debug function for debug logging to stderr
