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
- **Test client**: `python simplenote_mcp/tests/test_mcp_client.py`
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
5. **Linting errors**: Run `ruff check . --fix` to automatically fix many common linting issues

## Linting Configuration and Common Fixes

### Ruff Linting Issues

#### Import Issues (E402, F401, F811)
- **E402**: Module level import not at top of file
  - Move all imports to the top of the file, before any code
  - If you need to modify sys.path before imports, use conditional imports or move the code to a function
- **F401**: Unused imports
  - Remove unused imports or mark with `# noqa: F401` if needed for side effects
- **F811**: Redefinition of imports
  - Remove duplicate imports of the same module/symbol

#### Code Style Issues (W293, B904, E722)
- **W293**: Blank line contains whitespace
  - Remove whitespace from blank lines in docstrings and code
- **B904**: Raise with `from` in except clauses
  - Use `raise new_error from original_error` instead of just `raise new_error`
  - To suppress the original error context, use `raise new_error from None`
- **E722**: Do not use bare `except`
  - Always catch specific exceptions: `except ValueError:` not `except:`
  - Use `except Exception:` for general error handling, but prefer specific exceptions

#### Unused Variables and Expressions (F841, B007, B018)
- **F841**: Unused local variables
  - Remove variables that are assigned but never used
  - If needed for API compatibility, prefix with underscore `_variable`
- **B007**: Unused loop control variable
  - Rename unused loop variables: `for _i in range(5):` instead of `for i in range(5):`
- **B018**: Useless expression
  - Assign expression to a variable or remove it
  - For side effects (like `1/0` for testing), assign to `_`: `_ = 1/0`

#### Simplification Issues (SIM102, SIM103, SIM212)
- **SIM102**: Nested if statements
  - Combine with `and`: `if cond1 and cond2:` instead of `if cond1: if cond2:`
- **SIM103**: Return condition directly
  - Use `return not condition` instead of `if condition: return False return True`
- **SIM212**: Simplify conditionals
  - Use `value if value else default` instead of `default if not value else value`

#### Unused Arguments (ARG001, ARG002)
- **ARG001/ARG002**: Unused function/method arguments
  - Remove unused parameters or prefix with underscore: `def func(_unused):`
  - If needed for API compatibility, explicitly mark with comment: `# Required by API`

## Important Code Sections
- **Tool definition** (in handle_list_tools): Defines tools using JSON Schema format
- **Authentication** (in get_simplenote_client): Handles Simplenote authentication
- **Server initialization** (in run): Sets up the MCP server and capabilities

## Code Style Guidelines
- **Imports**: 
  - Group imports in this order: standard library, third-party, local imports
  - Include a blank line between groups
  - All imports must be at the top of the file (E402)
  - Avoid unused imports (F401)
  - Avoid redefinition of imports (F811)

- **Typing**: 
  - Use type hints for all function arguments and return values
  - Use `Optional[Type]` for parameters that can be None
  - Use `-> None` for functions that don't return a value

- **Naming**: 
  - Use `snake_case` for variables, functions, methods, and modules
  - Use `CamelCase` for classes
  - Prefix unused loop variables with underscore (`_variable`) (B007)
  - Prefix private attributes with underscore (_)

- **Error handling**: 
  - Use try/except blocks with specific exceptions (E722)
  - Always use `raise ... from err` or `raise ... from None` in except blocks (B904)
  - Include meaningful error messages
  - Log exceptions with appropriate level (debug, info, warning, error)

- **String formatting**: 
  - Prefer f-strings over other formats
  - For logging, use %-formatting or str.format() instead of f-strings
  - Avoid string concatenation with + for performance reasons

- **Docstrings**: 
  - Use docstrings for all functions explaining purpose and parameters
  - Follow Google docstring format
  - Avoid whitespace in blank lines within docstrings (W293)

- **Variables and assignments**:
  - Remove or use unused variables (F841)
  - Rename unused loop control variables with underscore prefix (B007)
  - Avoid useless expressions without assignment (B018)

- **Code structure**:
  - Keep lines under 88 characters
  - Use simplification suggestions from Ruff (SIM102, SIM103, SIM212)
  - Avoid unnecessary nesting of if statements

- **Function parameters**:
  - Remove or use all function parameters (ARG001, ARG002)
  - Use default parameters appropriately

- **Logging**: 
  - Use the log_debug function for debug logging to stderr
  - Include contextual information in log messages

## Branch Management
- **Feature branches**: Create a new branch for each feature using the naming convention `feature/feature-name`
- **Implementation**: Implement and test the feature in its branch
- **Merging**: After implementation is complete, remember to merge the feature branch into `main`
- **Clean up**: Delete feature branches after a successful merge to keep the repository clean
