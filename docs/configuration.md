# Configuration

This guide covers how to configure the Simplenote MCP Server for your environment.

## Environment Variables

The Simplenote MCP Server is configured primarily through environment variables. Here are all the available options:

### Required Variables

These variables must be set for the server to function:

| Variable | Description | Example |
|----------|-------------|---------|
| `SIMPLENOTE_EMAIL` | Your Simplenote account email address | `user@example.com` |
| `SIMPLENOTE_PASSWORD` | Your Simplenote account password | `your-secure-password` |

### Optional Variables

These variables can be set to customize the server behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CACHE_SIZE` | `1000` | Maximum number of notes to cache in memory |
| `CACHE_TTL` | `300` | Cache time-to-live in seconds (5 minutes) |
| `SYNC_INTERVAL` | `60` | How often to sync with Simplenote in seconds |
| `MAX_SEARCH_RESULTS` | `100` | Maximum number of search results to return |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `RETRY_ATTEMPTS` | `3` | Number of retry attempts for failed requests |
| `SIMPLENOTE_OFFLINE_MODE` | `false` | Run in offline mode for testing |

## Setting Environment Variables

### Linux/macOS

```bash
# Set variables for current session
export SIMPLENOTE_EMAIL="your-email@example.com"
export SIMPLENOTE_PASSWORD="your-password"
export LOG_LEVEL="DEBUG"

# Or create a .env file (not recommended for production)
echo 'SIMPLENOTE_EMAIL=your-email@example.com' > .env
echo 'SIMPLENOTE_PASSWORD=your-password' >> .env
echo 'LOG_LEVEL=INFO' >> .env
```

### Windows

```cmd
# Command Prompt
set SIMPLENOTE_EMAIL=your-email@example.com
set SIMPLENOTE_PASSWORD=your-password
set LOG_LEVEL=INFO

# PowerShell
$env:SIMPLENOTE_EMAIL="your-email@example.com"
$env:SIMPLENOTE_PASSWORD="your-password"
$env:LOG_LEVEL="INFO"
```

### Docker

```bash
# Using docker run
docker run -e SIMPLENOTE_EMAIL=your-email@example.com \
           -e SIMPLENOTE_PASSWORD=your-password \
           -e LOG_LEVEL=INFO \
           docdyhr/simplenote-mcp-server

# Using docker-compose
# Create a .env file:
echo 'SIMPLENOTE_EMAIL=your-email@example.com' > .env
echo 'SIMPLENOTE_PASSWORD=your-password' >> .env
echo 'LOG_LEVEL=INFO' >> .env

# Then run
docker-compose up
```

## Claude Desktop Integration

### Configuration File Location

The Claude Desktop configuration file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Basic Configuration

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password",
        "LOG_LEVEL": "INFO",
        "CACHE_SIZE": "500",
        "CACHE_TTL": "600",
        "MAX_SEARCH_RESULTS": "50"
      }
    }
  }
}
```

### Multiple Account Configuration

You can configure multiple Simplenote accounts:

```json
{
  "mcpServers": {
    "simplenote-personal": {
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "personal@example.com",
        "SIMPLENOTE_PASSWORD": "personal-password"
      }
    },
    "simplenote-work": {
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "work@company.com",
        "SIMPLENOTE_PASSWORD": "work-password"
      }
    }
  }
}
```

## Development Configuration

### Local Development

For local development, you can use a `.env` file:

```bash
# .env file
SIMPLENOTE_EMAIL=your-email@example.com
SIMPLENOTE_PASSWORD=your-password
LOG_LEVEL=DEBUG
CACHE_SIZE=100
SYNC_INTERVAL=30
SIMPLENOTE_OFFLINE_MODE=false
```

### Testing Configuration

For testing without real Simplenote API calls:

```bash
# Enable offline mode for testing
export SIMPLENOTE_OFFLINE_MODE=true
export LOG_LEVEL=DEBUG
```

### Debug Configuration

To enable detailed debugging:

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "simplenote-mcp-server",
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Security Best Practices

### Credential Management

1. **Never hardcode credentials** in configuration files committed to version control
2. **Use environment variables** or secure credential management systems
3. **Rotate passwords regularly** and update configurations accordingly
4. **Use strong, unique passwords** for your Simplenote account

### File Permissions

Ensure your configuration files have appropriate permissions:

```bash
# Make configuration file readable only by owner
chmod 600 ~/.config/Claude/claude_desktop_config.json

# For .env files
chmod 600 .env
```

### Docker Security

When using Docker, consider using secrets:

```yaml
# docker-compose.yml
version: '3.8'
services:
  simplenote-mcp:
    image: docdyhr/simplenote-mcp-server
    environment:
      - SIMPLENOTE_EMAIL_FILE=/run/secrets/simplenote_email
      - SIMPLENOTE_PASSWORD_FILE=/run/secrets/simplenote_password
    secrets:
      - simplenote_email
      - simplenote_password

secrets:
  simplenote_email:
    file: ./secrets/email.txt
  simplenote_password:
    file: ./secrets/password.txt
```

## Troubleshooting Configuration

### Common Issues

1. **Authentication Failed**
   - Verify email and password are correct
   - Check for typos in environment variables
   - Ensure Simplenote account is active

2. **Server Not Found**
   - Verify `simplenote-mcp-server` is in your PATH
   - Check installation with `which simplenote-mcp-server`
   - Reinstall if necessary

3. **Configuration Not Loading**
   - Restart Claude Desktop after configuration changes
   - Check file permissions
   - Validate JSON syntax

### Validation

Test your configuration:

```bash
# Test server starts correctly
simplenote-mcp-server --help

# Test with environment variables
export SIMPLENOTE_EMAIL=your-email@example.com
export SIMPLENOTE_PASSWORD=your-password
export SIMPLENOTE_OFFLINE_MODE=true
simplenote-mcp-server
```

### Logging

Check logs for configuration issues:

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check Claude Desktop logs (macOS)
tail -f ~/Library/Logs/Claude/claude_desktop.log

# Check server logs
simplenote-mcp-server 2>&1 | tee server.log
```

## Performance Tuning

### Cache Configuration

Optimize cache settings based on your usage:

```bash
# For heavy usage (many notes)
export CACHE_SIZE=2000
export CACHE_TTL=900  # 15 minutes

# For light usage (few notes)
export CACHE_SIZE=200
export CACHE_TTL=300  # 5 minutes
```

### Search Optimization

Configure search limits:

```bash
# Limit search results for better performance
export MAX_SEARCH_RESULTS=50

# Increase for comprehensive searches
export MAX_SEARCH_RESULTS=200
```

### Network Configuration

Adjust timeouts for your network:

```bash
# For slow connections
export REQUEST_TIMEOUT=60
export RETRY_ATTEMPTS=5

# For fast connections
export REQUEST_TIMEOUT=10
export RETRY_ATTEMPTS=2
```

## Migration from Previous Versions

### Version 1.5.x to 1.6.x

No configuration changes required. All existing configurations remain compatible.

### Version 1.4.x to 1.5.x

Update your Claude Desktop configuration to use the new command name:

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "simplenote-mcp-server",  // Changed from "python -m simplenote_mcp"
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```
