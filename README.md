# Simplenote MCP Server

![Simplenote MCP Server Logo](assets/logo.png)

A lightweight MCP server that integrates [Simplenote](https://simplenote.com/) with [Claude Desktop](https://github.com/johnsmith9982/claude-desktop) using the [MCP Python SDK](https://github.com/johnsmith9982/mcp-python-sdk).

This allows Claude Desktop to interact with your Simplenote notes as a memory backend or content source.

[![MCP Server](https://img.shields.io/badge/MCP-Server-purple.svg)](https://github.com/modelcontextprotocol)
[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](./CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](./pyproject.toml)
[![Tests](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/python-tests.yml/badge.svg)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/python-tests.yml)
[![Code Quality](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml/badge.svg)](https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/code-quality.yml)
[![codecov](https://codecov.io/gh/docdyhr/simplenote-mcp-server/branch/main/graph/badge.svg)](https://codecov.io/gh/docdyhr/simplenote-mcp-server)
[![smithery badge](https://smithery.ai/badge/@docdyhr/simplenote-mcp-server)](https://smithery.ai/server/@docdyhr/simplenote-mcp-server)

---

## 🔧 Features

- 📝 Read and list Simplenote notes
- 🔍 Advanced search with boolean operators, phrase matching, and filters
- 🔐 Token-based authentication via `.env` or manual entry
- ⚡ Local, fast, and easy to run
- 🧩 Compatible with Claude Desktop and other MCP clients

---

## Project Structure

```plaintext
simplenote_mcp/            # Main package
├── logs/                  # Log files directory
├── scripts/               # Helper scripts for testing and management
├── server/                # Main server code
└── tests/                 # Test utilities and client
```

## Overview

This project provides an MCP server that allows you to interact with your Simplenote account through Claude Desktop or any other MCP-compatible client.

Key features:

- List all your Simplenote notes as resources
- View note contents
- Create, update, and delete notes
- Search notes by content with advanced search capabilities
- Filter with boolean operators, tags, dates, and phrase matching

## Installation

### Installing via Smithery

To install Simplenote Integration Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@docdyhr/simplenote-mcp-server):

```bash
npx -y @smithery/cli install @docdyhr/simplenote-mcp-server --client claude
```

### Prerequisites

- Python 3.11 or higher
- A Simplenote account
- (Optional) [uv](https://github.com/astral-sh/uv) for faster dependency installation

### Step 1: Clone the repository

```bash
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
```

### Step 2: Set up a virtual environment (recommended)

It's recommended to create a virtual environment to isolate dependencies:

```bash
# Using venv
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# OR
.venv\Scripts\activate     # On Windows
```

### Step 3: Install the package

#### Using uv (recommended)

```bash
uv pip install -e .
```

#### Using pip

```bash
pip install -e .
```

### Step 4: Verify installation

```bash
which simplenote-mcp-server  # On Unix/macOS
# OR
where simplenote-mcp-server  # On Windows
```

## Configuration

### Environment Variables

The Simplenote MCP Server uses the following environment variables for configuration:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SIMPLENOTE_EMAIL` | Yes | - | Your Simplenote account email |
| `SIMPLENOTE_PASSWORD` | Yes | - | Your Simplenote account password |
| `SYNC_INTERVAL_SECONDS` | No | 120 | Interval (in seconds) between background cache synchronizations |
| `DEFAULT_RESOURCE_LIMIT` | No | 100 | Default maximum number of notes to return when listing resources |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_TO_FILE` | No | true | Whether to write logs to files |
| `LOG_FORMAT` | No | standard | Log format (standard or json) |
| `MCP_DEBUG` | No | false | Enable additional debug logging |

### Setting Environment Variables

You can set these variables in several ways:

#### 1. In your terminal session

```bash
export SIMPLENOTE_EMAIL=your.email@example.com
export SIMPLENOTE_PASSWORD=your-password
export LOG_LEVEL=DEBUG  # Optional
```

#### 2. In your .bashrc, .zshrc, or equivalent

Add the exports above to your shell configuration file to make them persistent.

#### 3. In Claude Desktop configuration

For Claude Desktop integration, add them to your `claude_desktop_config.json` file (see the "Claude Desktop Integration" section below).

## Usage

### Running the server

```bash
python simplenote_mcp_server.py
```

Or, after installation:

```bash
simplenote-mcp-server
```

## Testing the server

The server can be tested by running:

```bash
# Test Simplenote connectivity
python simplenote_mcp/tests/test_mcp_client.py

# Test pagination and cache performance
python simplenote_mcp/tests/test_pagination_and_cache.py

# Run cache optimization benchmarks
python simplenote_mcp/tests/benchmark_cache.py

# Start the server in the foreground
python simplenote_mcp_server.py
```

## Claude Desktop Integration

There are two ways to use Simplenote MCP Server with Claude Desktop:

### Method 1: Manual Connection (Temporary)

1. Run the server in a terminal window:

   ```bash
   simplenote-mcp-server
   ```

2. In Claude Desktop:
   - Click the "+" button in the sidebar
   - Select "Connect to Tool"
   - Choose "Connect to subprocess"
   - Enter `simplenote-mcp-server`
   - Click "Connect"

This connection will persist until you close Claude Desktop or stop the server.

### Method 2: Automatic Integration (Permanent)

For a more seamless experience, configure Claude Desktop to automatically start the server:

1. Locate your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the following section to your configuration (adjust paths as needed):

   ```json
   {
     "mcpServers": {
       "simplenote": {
         "description": "Access and manage your Simplenote notes",
         "command": "/path/to/your/python",
         "args": [
           "/path/to/simplenote_mcp_server.py"
         ],
         "autostart": true,
         "disabled": false,
         "restartOnCrash": true,
         "env": {
           "SIMPLENOTE_EMAIL": "your.email@example.com",
           "SIMPLENOTE_PASSWORD": "your-password",
           "LOG_LEVEL": "INFO"
         }
       }
     }
   }
   ```

3. Restart Claude Desktop using the provided script:

   ```bash
   ./simplenote_mcp/scripts/restart_claude.sh
   ```

4. Verify the connection using the included verification script:

   ```bash
   ./simplenote_mcp/scripts/verify_tools.sh
   ```

## Available Capabilities

Simplenote MCP Server provides the following capabilities to Claude and other MCP clients:

### Resources

Simplenote notes are exposed as resources with the URI format `simplenote://note/{note_id}`:

- **List Resources** - Browse your Simplenote notes
  - Supports tag filtering (`tag` parameter)
  - Supports limiting results (`limit` parameter)
  - Supports pagination (`offset` parameter)
  - Supports sorting (`sort_by` and `sort_direction` parameters)
  - Returns notes with comprehensive pagination metadata

- **Read Resource** - View the content and metadata of a specific note

With a total of 10 implemented capabilities (8 tools and 2 prompts) as of version 1.4.0, the server provides a comprehensive interface for managing your Simplenote notes.

### Advanced Search Capabilities

The server supports powerful search functionality with the following features:

- **Boolean Logic**: Combine search terms with `AND`, `OR`, and `NOT` operators

  ```text
  project AND meeting AND NOT cancelled
  ```

- **Phrase Matching**: Search for exact phrases using quotes

  ```text
  "action items" AND project
  ```

- **Tag Filtering**: Filter by tags directly in the query or via parameters

  ```text
  meeting tag:work tag:important
  ```

- **Date Range Filtering**: Limit results by modification date

  ```text
  project from:2023-01-01 to:2023-12-31
  ```

- **Combining Methods**: Mix and match all of the above in a single query

  ```text
  "status update" AND project tag:work from:2023-01-01 NOT cancelled
  ```

The search engine uses a sophisticated query parser and boolean expression evaluator to process complex search expressions. Results are ranked by relevance, with higher scores given to:

- Title matches (when the search term appears in the first line)
- Tag matches (when the search term matches a note tag)
- Recent notes (with a recency bonus for newer notes)
- Multiple term occurrences (more mentions = higher score)

### Tools

The server provides the following tools for Simplenote interaction:

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_note` | Create a new note | `content` (required): Note content<br>`tags` (optional): Comma-separated tags |
| `update_note` | Update an existing note | `note_id` (required): The ID of the note<br>`content` (required): New content<br>`tags` (optional): Comma-separated tags |
| `delete_note` | Move a note to trash | `note_id` (required): The ID of the note to delete |
| `get_note` | Get a note by ID | `note_id` (required): The ID of the note to retrieve |
| `search_notes` | Search for notes with advanced capabilities | `query` (required): Search terms with boolean operators & filters<br>`limit` (optional): Maximum results to return<br>`offset` (optional): Number of results to skip for pagination<br>`tags` (optional): Tags to filter by (alternative to tag: syntax)<br>`from_date` (optional): Start date filter (alternative to from: syntax)<br>`to_date` (optional): End date filter (alternative to to: syntax) |
| `add_tags` | Add tags to an existing note | `note_id` (required): The ID of the note to modify<br>`tags` (required): Comma-separated tags to add |
| `remove_tags` | Remove tags from an existing note | `note_id` (required): The ID of the note to modify<br>`tags` (required): Comma-separated tags to remove |
| `replace_tags` | Replace all tags on an existing note | `note_id` (required): The ID of the note to modify<br>`tags` (required): Comma-separated new tags |

### Prompts

The server provides prompt templates for more interactive experiences:

| Prompt | Description | Parameters |
|--------|-------------|------------|
| `create_note_prompt` | Create a new note with content | `content` (required): Note content<br>`tags` (optional): Comma-separated tags |
| `search_notes_prompt` | Search for notes matching a query | `query` (required): Search terms |

## Versioning

This project follows [Semantic Versioning](https://semver.org/). See the [CHANGELOG.md](./CHANGELOG.md) file for details on version history and changes.

To release a new version, use the release script:

```bash
./simplenote_mcp/scripts/release.sh [patch|minor|major]
```

## Included Scripts

This project comes with several helper scripts in the `simplenote_mcp/scripts` directory:

1. **restart_claude.sh** - Restarts Claude Desktop and the Simplenote MCP server
2. **cleanup_servers.sh** - Gracefully terminates all running server instances
3. **check_server_pid.sh** - Checks the status of running server instances
4. **watch_logs.sh** - Monitors the Simplenote MCP server logs in real-time
5. **verify_tools.sh** - Checks if Simplenote tools are properly registered
6. **test_tool_visibility.sh** - Tests if tools are visible in Claude Desktop
7. **release.sh** - Releases a new version with semantic versioning

Testing utilities in the `simplenote_mcp/tests` directory:

1. **test_mcp_client.py** - Tests connectivity with the Simplenote MCP server
2. **test_pagination_and_cache.py** - Tests pagination functionality and cache optimization
3. **benchmark_cache.py** - Benchmarks cache performance improvements
4. **monitor_server.py** - Helps debug communications between Claude Desktop and the server

## Caching Mechanism

The Simplenote MCP Server uses a sophisticated in-memory caching system to provide fast access to your notes while minimizing API calls to Simplenote.

### Pagination Support

The server supports pagination for efficiently handling large note collections:

1. **Resource Listing Pagination**
   - Use `offset` parameter to skip a specified number of notes
   - Use `limit` parameter to control results per page
   - Access comprehensive pagination metadata in the response
   - Sort results with `sort_by` ("modifydate", "createdate", "title") and `sort_direction` ("asc" or "desc")

2. **Search Pagination**
   - Use `offset` and `limit` parameters with search queries
   - Pagination metadata includes: total results, current page, total pages, next/previous page offsets

3. **Performance Optimizations**
   - Efficient indexed lookups for tag filtering
   - Query result caching for frequently used searches
   - Pre-filtering before complex searches

### How Caching Works

1. **Initial Cache Loading**
   - When the server starts, it fetches all notes from Simplenote
   - Notes are stored in memory for quick access
   - The server records the current sync timestamp

2. **Background Synchronization**
   - The server periodically checks for changes using the Simplenote API
   - Only changes since the last sync are fetched (using the `index_since` mechanism)
   - New and updated notes are added to the cache
   - Deleted notes are removed from the cache
   - Default sync interval is 120 seconds (configurable)

3. **Performance Benefits**
   - Faster response times for all operations
   - Reduced API calls to Simplenote's servers
   - Support for efficient filtering and searching
   - Optimized for large collections with pagination support
   - Indexed lookups for tags and content
   - Query result caching for repeated searches
   - Optimized for large collections with pagination support
   - Indexed lookups for tags and content
   - Query result caching for repeated searches

## Troubleshooting

### Common Issues

#### Authentication Problems

**Symptoms**: Error messages about missing or invalid credentials.

**Solutions**:

- Verify that `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` are correctly set
- Check for typos in your email address and password
- Make sure password contains no special characters that might need escaping

#### Server Not Starting

**Symptoms**: Server fails to start, Claude Desktop can't connect.

**Solutions**:

- Check log files: `cat simplenote_mcp/logs/server.log`
- Look for Python errors in your terminal
- Verify Python version is 3.9 or higher: `python --version`
- Confirm the package is properly installed: `which simplenote-mcp-server`

#### Claude Desktop Can't Find Tools

**Symptoms**: Claude says it doesn't have access to Simplenote tools.

**Solutions**:

1. Verify the server is running:

   ```bash
   ps aux | grep simplenote-mcp
   ```

2. Check if tools are properly registered:

   ```bash
   ./simplenote_mcp/scripts/verify_tools.sh
   ```

3. Restart Claude Desktop and the server:

   ```bash
   ./simplenote_mcp/scripts/restart_claude.sh
   ```

4. Watch logs for communication errors:

   ```bash
   ./simplenote_mcp/scripts/watch_logs.sh
   ```

5. **Test performance and pagination**:

   ```bash
   python simplenote_mcp/tests/test_pagination_and_cache.py
   ```

6. **Clean up all server instances and start fresh**:

   ```bash
   ./simplenote_mcp/scripts/cleanup_servers.sh
   simplenote-mcp-server
   ```

### Log Files

The server creates log files in the following locations:

- Main log: `simplenote_mcp/logs/server.log`
- Legacy log (for debugging): `/tmp/simplenote_mcp_debug.log`

Set `LOG_LEVEL=DEBUG` for more detailed logs.

### Diagnostic Tools

The project includes several diagnostic tools:

1. **check_server_pid.sh** - Checks server process status:

   ```bash
   ./simplenote_mcp/scripts/check_server_pid.sh
   ```

2. **verify_tools.sh** - Checks tool registration:

   ```bash
   ./simplenote_mcp/scripts/verify_tools.sh
   ```

3. **test_tool_visibility.sh** - Tests if Claude sees the tools:

   ```bash
   ./simplenote_mcp/scripts/test_tool_visibility.sh
   ```

4. **monitor_server.py** - Monitors MCP protocol messages:

   ```bash
   python simplenote_mcp/tests/monitor_server.py
   ```

5. **test_mcp_client.py** - Tests basic connectivity:

   ```bash
   python simplenote_mcp/tests/test_mcp_client.py
   ```

6. **benchmark_cache.py** - Benchmarks cache performance:

   ```bash
   python simplenote_mcp/tests/benchmark_cache.py
   ```

7. **run_tests.py** - Run all tests with various options:

   ```bash
   python simplenote_mcp/tests/run_tests.py --category performance
   ```

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for planned features and goals.

## Development

### Code Quality

This project uses a streamlined approach to code quality with [Ruff](https://github.com/astral-sh/ruff) as the primary linting tool:

- **Ruff** - A fast Python linter that handles:
  - Code style checking (previously flake8)
  - Import sorting (previously isort)
  - Code formatting (previously black)
  - Security checks (previously bandit)
  - Type annotation validation
  - Docstring formatting

The linting setup can be verified with:

```bash
./scripts/verify_linting_setup.sh
```

For detailed information about the linting setup, see [docs/linting_guide.md](docs/linting_guide.md).

## Contributing

Contributions are welcome! Please open an issue first to discuss any significant changes. Read our [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## Security

For security vulnerabilities, please review our [Security Policy](./.github/SECURITY.md).

## Related Projects

Model Context Protocol (MCP) [Example Servers](https://modelcontextprotocol.io/examples)
