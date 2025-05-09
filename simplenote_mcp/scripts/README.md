# Simplenote MCP Server Scripts

This directory contains utility and diagnostic scripts for the Simplenote MCP server.

## Server Management Scripts

### `restart_claude.sh`
Restarts both Claude and the Simplenote MCP server.

```bash
./restart_claude.sh
```

### `cleanup_servers.sh`
Terminates all running instances of the Simplenote MCP server.

```bash
./cleanup_servers.sh
```

### `check_server_pid.sh`
Checks the status of the Simplenote MCP server process.

```bash
./check_server_pid.sh
```

### `watch_logs.sh`
Monitors the server log file in real-time.

```bash
./watch_logs.sh
```

## Testing Scripts

### `verify_tools.sh`
Verifies that all tools are properly registered with the MCP server.

```bash
./verify_tools.sh
```

### `test_tool_visibility.sh`
Tests whether Claude can see the registered tools.

```bash
./test_tool_visibility.sh
```

## Diagnostic Tools

### `diagnose_api.py`
Comprehensive diagnostic tool for troubleshooting Simplenote API connectivity issues.

```bash
# Basic usage
python simplenote_mcp/scripts/diagnose_api.py

# With verbose output
python simplenote_mcp/scripts/diagnose_api.py --verbose
```

This script performs the following tests:
- Internet connectivity
- DNS resolution for Simplenote API endpoints
- TLS/SSL connection to Simplenote servers
- HTTP connections to Simplenote API
- Authentication with Simplenote credentials
- Simplenote client library availability and functionality
- API performance with multiple requests

A detailed report is saved to `simplenote_mcp/logs/api_diagnostic_report.txt`.

### `analyze_logs.py`
Analyzes the Simplenote MCP server log files to identify patterns and issues.

```bash
# Analyze the default log file
python simplenote_mcp/scripts/analyze_logs.py

# Analyze a specific log file
python simplenote_mcp/scripts/analyze_logs.py --log /path/to/your/logfile.log
```

This script provides:
- Error pattern identification
- Network connectivity analysis
- Authentication issue detection
- Sync statistics
- Import error diagnosis
- Timing patterns for recurring issues
- Targeted recommendations based on detected problems

A detailed analysis report is saved to `simplenote_mcp/logs/log_analysis_report.txt`.

## Usage Examples

### Diagnosing Connection Issues
If you're experiencing connectivity problems with the Simplenote API:

```bash
# First, analyze existing logs
python simplenote_mcp/scripts/analyze_logs.py

# Then run detailed diagnostics
python simplenote_mcp/scripts/diagnose_api.py --verbose

# Check the reports and follow recommendations
cat simplenote_mcp/logs/log_analysis_report.txt
cat simplenote_mcp/logs/api_diagnostic_report.txt
```

### Restarting After Issues
If you need to restart the server after resolving issues:

```bash
# Clean up any lingering processes
./simplenote_mcp/scripts/cleanup_servers.sh

# Restart the server
./simplenote_mcp/scripts/restart_claude.sh

# Monitor the new logs
./simplenote_mcp/scripts/watch_logs.sh
```
