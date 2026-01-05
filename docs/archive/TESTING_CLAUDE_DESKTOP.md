# Testing Simplenote MCP Server with Claude Desktop

**Production Validation Guide for v1.9.0**

This guide helps you test the new v1.9.0 release with its **98% startup performance improvement** and verify that Claude Desktop integration works flawlessly.

---

## 🎯 What's New in v1.9.0

- ✅ **Sub-second startup** (was 55+ seconds, now < 1 second)
- ✅ **Fixed Claude Desktop timeout** issue completely
- ✅ **Non-blocking cache initialization** with background loading
- ✅ **Graceful empty cache handling** during startup
- ✅ **Zero regressions** - all existing functionality maintained

---

## ✅ Prerequisites

1. **Claude Desktop** installed on your system
2. **Simplenote account** with email and password
3. **Python 3.10+** installed
4. **Git repository** updated to latest version with the timeout fix

---

## 🚀 Installation Steps

### Option 1: Direct Python Installation (Recommended for Testing)

1. **Update to latest version**:
   ```bash
   cd simplenote-mcp-server
   git pull origin main
   ```

2. **Install in development mode**:
   ```bash
   pip install -e .
   ```

3. **Verify installation**:
   ```bash
   python -c "from simplenote_mcp.server import run_main; print('✅ Installation successful')"
   ```

### Option 2: Install from PyPI

```bash
pip install --upgrade simplenote-mcp-server
```

---

## ⚙️ Configuration

### 1. Set Environment Variables

**macOS/Linux**:
```bash
export SIMPLENOTE_EMAIL="your-email@example.com"
export SIMPLENOTE_PASSWORD="your-password"
export SIMPLENOTE_LOG_LEVEL="INFO"  # Optional: DEBUG for more details
```

**Windows (PowerShell)**:
```powershell
$env:SIMPLENOTE_EMAIL="your-email@example.com"
$env:SIMPLENOTE_PASSWORD="your-password"
$env:SIMPLENOTE_LOG_LEVEL="INFO"
```

### 2. Configure Claude Desktop

Edit your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "python",
      "args": ["-m", "simplenote_mcp.server"],
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password",
        "SIMPLENOTE_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Using absolute path** (if Python not in PATH):
```json
{
  "mcpServers": {
    "simplenote": {
      "command": "/full/path/to/python",
      "args": ["-m", "simplenote_mcp.server"],
      "env": {
        "SIMPLENOTE_EMAIL": "your-email@example.com",
        "SIMPLENOTE_PASSWORD": "your-password"
      }
    }
  }
}
```

---

## 🧪 Testing Steps

### 1. Restart Claude Desktop

1. **Quit Claude Desktop completely** (Cmd+Q on macOS)
2. **Wait 5 seconds**
3. **Relaunch Claude Desktop**

### 2. Check Connection Status

In Claude Desktop, look for:
- ✅ **"simplenote" server listed** in available MCP servers
- ✅ **Green/connected status indicator**
- ✅ **No error messages** in the UI

### 3. Test Basic Functionality

Try these commands in Claude Desktop:

**List Notes**:
```
Show me my Simplenote notes
```

**Search Notes**:
```
Search my notes for "project"
```

**Create Note**:
```
Create a new note with content: "Test note from Claude Desktop v1.9.0"
```

---

## ⚡ v1.9.0 Specific Validation

### Performance Testing

**Expected**: Server should start in **< 1 second**

1. **Check Startup Time**:
   ```bash
   # Time the server startup
   time python -m simplenote_mcp.server --help
   
   # Expected output: real < 1.0s
   ```

2. **Monitor Claude Desktop Startup**:
   - Launch Claude Desktop
   - **Expected**: Immediate response, no timeout errors
   - **Expected**: Tools available within 1-2 seconds
   - **Previous issue**: 55+ second timeout and failure

### Functionality Validation

Test all major features to ensure no regressions:

1. **Cache Operations** (Background Loading):
   ```
   # Immediately after startup
   Show me all my notes
   ```
   - **Expected**: May return empty initially, then populate
   - **Expected**: No errors or crashes
   - **New behavior**: Graceful empty cache handling

2. **Search During Background Sync**:
   ```
   Search for "test"
   ```
   - **Expected**: Works immediately even during cache load
   - **Expected**: Results improve as cache populates
   - **New behavior**: Non-blocking operations

3. **Large Note Collections** (if you have 500+ notes):
   - **Expected**: Startup still < 1 second
   - **Expected**: Search remains responsive
   - **Monitor**: Memory usage should be reasonable

### Log Validation

Check logs for clean operation:

**macOS**:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Windows**:
```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp*.log" -Tail 50 -Wait
```

**Expected in logs**:
- ✅ "Server starting" message
- ✅ "Cache initialized (background loading)" message
- ✅ "Background sync started" message
- ✅ No "timeout" errors
- ✅ No "BrokenResourceError" messages
- ✅ No unawaited coroutine warnings

**Should NOT see**:
- ❌ Timeout errors
- ❌ BrokenResourceError
- ❌ RuntimeWarning about coroutines
- ❌ Authentication failures (if credentials correct)

---

## 📊 Success Criteria

Your v1.9.0 installation is working correctly if:

- [ ] ✅ Server starts in < 1 second
- [ ] ✅ Claude Desktop shows "simplenote" server connected
- [ ] ✅ Can list notes immediately
- [ ] ✅ Can search notes without delay
- [ ] ✅ Can create new notes
- [ ] ✅ Can update existing notes
- [ ] ✅ No timeout errors in logs
- [ ] ✅ No error messages in Claude Desktop
- [ ] ✅ Background sync completes without issues

---

## 📊 Expected Behavior

### ✅ Success Indicators

1. **Fast Startup** (< 2 seconds):
   - Server connects immediately
   - No timeout errors
   - Notes appear within 30 seconds as cache loads

2. **Clean Logs**:
   ```
   INFO - MCP server ready in 0.8s (cache loading in background)
   INFO - Background cache initialization starting...
   INFO - Background cache initialization completed successfully
   ```

3. **Responsive Operations**:
   - List notes returns results immediately (or empty during initial load)
   - Search works as cache populates
   - Create/update operations succeed

### ❌ Failure Indicators (Should NOT Happen)

1. **Timeout Error**:
   ```
   McpError: MCP error -32001: Request timed out
   ```

2. **Long Startup** (> 10 seconds):
   - Server takes forever to connect
   - Claude Desktop shows "Connecting..." for extended time

3. **Error Messages**:
   ```
   anyio.BrokenResourceError
   unhandled errors in a TaskGroup
   ```

---

## 🔍 Monitoring & Logs

### View Real-Time Logs

**macOS**:
```bash
tail -f ~/Library/Logs/Claude/mcp-server-simplenote.log
```

**Windows**:
```powershell
Get-Content "$env:APPDATA\Claude\logs\mcp-server-simplenote.log" -Wait
```

### Key Log Messages to Look For

**✅ Good (Expected)**:
```
INFO - Starting MCP server STDIO transport
INFO - Server components started in 0.12s
INFO - MCP server ready in 0.85s (cache loading in background)
INFO - Background cache initialization starting...
DEBUG - Simplenote API connection successful, received 4031 items
INFO - Background cache initialization completed successfully
```

**❌ Bad (Report if seen)**:
```
ERROR - Error creating STDIO server: unhandled errors
ERROR - Request timed out
RuntimeWarning: coroutine 'LogPatternMonitor._process_log_line' was never awaited
anyio.BrokenResourceError
```

---

## 🐛 Troubleshooting

### Issue: Server Not Connecting

**Check**:
1. Environment variables are set correctly
2. Python path is correct in config
3. Simplenote credentials are valid

**Solution**:
```bash
# Test authentication manually
python -c "from simplenote import Simplenote; s = Simplenote('email', 'pass'); print(s.get_note_list())"
```

### Issue: Slow Startup (But Eventually Works)

**This might be expected** if you have many notes (4000+):
- Initial connection should be < 2 seconds
- Cache loading happens in background (may take 20-30 seconds)
- Server remains responsive during loading

**Not expected**:
- Startup taking > 10 seconds before responding
- Timeout errors before connection established

### Issue: Notes Not Appearing

**Check**:
1. Look at logs - is cache initialization completing?
2. Wait 30-60 seconds for initial load
3. Try creating a new note to verify write access

---

## 📈 Performance Benchmarks

### Expected Timing

| Operation | Time | Notes |
|-----------|------|-------|
| **Server Startup** | < 1s | Server ready to accept requests |
| **First Response** | < 2s | Initial handshake complete |
| **Cache Load** | 20-30s | Background, non-blocking |
| **List Notes** | < 0.5s | After cache loaded |
| **Search Notes** | < 1s | After cache loaded |
| **Create Note** | 1-3s | API call + cache update |

### Your Results

Fill in after testing:

| Operation | Your Time | Status |
|-----------|-----------|--------|
| Server Startup | ___ s | ✅/❌ |
| First Response | ___ s | ✅/❌ |
| Cache Load | ___ s | ✅/❌ |
| List Notes | ___ s | ✅/❌ |

---

## 🎯 Test Checklist

- [ ] Configured environment variables
- [ ] Updated `claude_desktop_config.json`
- [ ] Restarted Claude Desktop
- [ ] Server appears in MCP servers list
- [ ] Server connects within 2 seconds
- [ ] No timeout errors in logs
- [ ] Can list notes (empty or populated)
- [ ] Can search notes
- [ ] Can create new note
- [ ] Background cache loads successfully
- [ ] All notes appear after cache load

---

## 📞 Getting Help

### If Testing Fails

1. **Check the fix is applied**:
   ```bash
   git log --oneline -1
   # Should show: "fix: resolve Claude Desktop timeout..."
   ```

2. **Verify version**:
   ```bash
   python -c "from simplenote_mcp import __version__; print(__version__)"
   # Should be 1.8.1 or higher
   ```

3. **Review documentation**:
   - `CLAUDE_DESKTOP_TIMEOUT_FIX.md` - Technical details
   - `PROJECT_IMPROVEMENTS_SUMMARY_2025_01.md` - Complete summary

4. **Report issue**:
   - Include log output from `mcp-server-simplenote.log`
   - Note timing of each operation
   - Specify number of notes in your Simplenote account

---

## ✅ Success!

If all tests pass, you should see:

```
✅ Server starts in < 1 second
✅ No timeout errors
✅ Notes load in background
✅ All operations work smoothly
✅ Clean logs with no warnings
```

**Congratulations!** Your Simplenote MCP Server is working correctly with Claude Desktop.

---

**Last Updated**: January 26, 2025  
**Fix Version**: 1.8.1+  
**Status**: Ready for Testing
