# Getting Started with Simplenote MCP Server

This tutorial will help you set up and use the Simplenote MCP Server with Claude Desktop.

## Prerequisites

- Python 3.10 or higher
- Claude Desktop app
- Simplenote account

## Quick Start

### 1. Install the Server

```bash
# Clone the repository
git clone https://github.com/yourusername/simplenote-mcp-server.git
cd simplenote-mcp-server

# Install using pip
pip install -e .

# Or use Docker (recommended)
docker build -t simplenote-mcp-server .
```

### 2. Configure Claude Desktop

Add to your Claude Desktop config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "python",
      "args": ["-m", "simplenote_mcp.server"],
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```

For Docker setup:
```json
{
  "mcpServers": {
    "simplenote": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "simplenote-mcp-server"],
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After updating the config, restart Claude Desktop to load the server.

## Basic Usage

In Claude Desktop, you can now:

### Create Notes
```
Can you create a note titled "Meeting Notes" with today's action items?
```

### Search Notes
```
Search for all notes containing "project update"
```

### Update Notes
```
Update my "Todo List" note to add "Review documentation"
```

### Get Specific Notes
```
Show me the contents of my "Ideas" note
```

### Delete Notes
```
Delete the note titled "Old Meeting Notes"
```

## Verifying Setup

1. Check if the server is running:
   ```bash
   ./simplenote_mcp/scripts/check_server_pid.sh
   ```

2. View server logs:
   ```bash
   ./simplenote_mcp/scripts/watch_logs.sh
   ```

3. Test tools are available:
   ```bash
   ./simplenote_mcp/scripts/verify_tools.sh
   ```

## Troubleshooting

### Server Not Connecting
- Verify credentials in config file
- Check logs: `tail -f ~/.cache/simplenote-mcp/server.log`
- Ensure only one server instance is running

### Tools Not Available
- Restart Claude Desktop
- Run cleanup script: `./simplenote_mcp/scripts/cleanup_servers.sh`
- Verify MCP server appears in Claude's server list

### Authentication Issues
- Double-check email and password
- Ensure no special characters need escaping in JSON
- Try logging into Simplenote web to verify credentials

## Example Workflow

1. **Capture Ideas**
   ```
   Create a note called "Project Ideas" and add:
   - Mobile app redesign
   - API performance optimization
   - User onboarding improvements
   ```

2. **Organize Tasks**
   ```
   Search for all notes with "todo" and create a summary
   ```

3. **Update Progress**
   ```
   Update "Sprint Tasks" note - mark "Database migration" as complete
   ```

## Next Steps

- Explore the [full documentation](README.md)
- Check available [scripts](simplenote_mcp/scripts/) for automation
- Review [CLAUDE.md](CLAUDE.md) for development guidelines
