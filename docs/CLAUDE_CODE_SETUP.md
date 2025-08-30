# Claude Code Integration Guide

This guide explains how to maximize productivity on the Simplenote MCP Server project using Claude Code's advanced features and our custom configurations.

## 🚀 Quick Setup

### 1. Claude Code Configuration

Your project now includes comprehensive Claude Code support:

```bash
# Main configuration files
.claude-code-hooks.yaml          # Intelligent automation hooks
.claude-code-settings.json       # Claude Code IDE settings
scripts/claude-code-support/     # Supporting scripts
```

### 2. Essential Scripts

```bash
# Auto-test runner - intelligently runs relevant tests
./scripts/claude-code-support/auto-test.sh [options] [files...]

# Smart validator - comprehensive code analysis
./scripts/claude-code-support/smart-validator.py [files...]

# Development assistant - AI-powered development help
./scripts/claude-code-support/development-assistant.py [options]
```

### 3. Enable in Claude Code Settings

Add to your Claude Code settings:

```json
{
  "hooks": {
    "configFile": ".claude-code-hooks.yaml",
    "enabled": true
  },
  "projectSettings": ".claude-code-settings.json"
}
```

## 🎯 Key Features

### Intelligent Testing
- **Auto-detection**: Automatically runs relevant tests when files change
- **Smart targeting**: Only runs tests related to your changes
- **Offline mode**: Uses `SIMPLENOTE_OFFLINE_MODE=true` for consistent testing

```bash
# Quick test for changed files
./scripts/claude-code-support/auto-test.sh --quick

# Test with coverage
./scripts/claude-code-support/auto-test.sh --coverage

# Performance testing
./scripts/claude-code-support/auto-test.sh --performance
```

### Code Quality Automation
- **Real-time formatting**: Auto-format with Ruff on save
- **Smart validation**: MCP-specific pattern checking
- **Security scanning**: Automatic credential and vulnerability detection

```bash
# Comprehensive validation
./scripts/claude-code-support/smart-validator.py

# JSON output for tooling
./scripts/claude-code-support/smart-validator.py --json

# Auto-fix mode
./scripts/claude-code-support/smart-validator.py --fix
```

### Development Assistant
- **Context-aware suggestions**: AI suggestions based on current work
- **Auto-fix**: Automatically resolve common issues
- **Project monitoring**: Real-time development assistance

```bash
# Get suggestions for current context
./scripts/claude-code-support/development-assistant.py --suggest

# Auto-fix common issues
./scripts/claude-code-support/development-assistant.py --fix

# Monitor project for 5 minutes
./scripts/claude-code-support/development-assistant.py --monitor 300
```

## 🔧 Available Hooks

### Pre-Edit Hooks
- **Syntax validation**: Check Python syntax before editing
- **Backup creation**: Auto-backup critical files
- **Dependency checks**: Ensure required packages are installed

### Post-Edit Hooks  
- **Auto-formatting**: Ruff formatting on save
- **Type checking**: MyPy validation
- **Coverage updates**: Track test coverage changes

### Pre-Commit Hooks
- **Full test suite**: Run all tests before commit
- **Security scan**: Bandit vulnerability checking
- **Dependency audit**: pip-audit for known vulnerabilities
- **CI/CD validation**: Validate workflow files

### Tool-Specific Hooks
- **MCP validation**: Validate tool requests and responses
- **Search optimization**: Suggest query improvements
- **Performance monitoring**: Track cache efficiency

## 📋 Command Palette Integration

Access these commands via Claude Code's command palette:

| Command | Shortcut | Description |
|---------|----------|-------------|
| Quick Test | `Ctrl+T` | Run tests for changed files |
| Full Validation | `Ctrl+V` | Comprehensive code analysis |
| Development Assistant | `Ctrl+A` | Get AI suggestions |
| Auto Fix | `Ctrl+F` | Fix common issues |
| Coverage Report | - | Generate HTML coverage report |
| Performance Profile | - | Profile performance |

## 🧪 Testing Integration

### Intelligent Test Selection
The system automatically determines which tests to run based on:
- Direct file-to-test mapping (`server.py` → `test_server.py`)
- Import analysis (finds tests that import your module)  
- Change impact analysis (tests affected by your changes)

### Test Categories
```bash
# Unit tests only
./scripts/claude-code-support/auto-test.sh --quick

# Include integration tests  
./scripts/claude-code-support/auto-test.sh --all

# Performance regression tests
./scripts/claude-code-support/auto-test.sh --performance
```

### Coverage Tracking
- **Per-module coverage**: Track coverage for specific files
- **Regression detection**: Alert on coverage drops
- **Visual reports**: HTML coverage reports with highlighting

## 🔒 Security Features

### Automatic Security Scanning
- **Credential detection**: Prevents committing secrets
- **Vulnerability scanning**: pip-audit integration
- **Code pattern analysis**: Detect security anti-patterns

### Security Hooks
```yaml
# Example security configuration
security-hooks:
  - name: "Credential scan"
    trigger: "pre_commit"
    command: "grep -r 'SIMPLENOTE_PASSWORD' --exclude-dir=.git"
    
  - name: "License compliance"
    trigger: "dependency_added"
    command: "pip-licenses --summary"
```

## 📊 Performance Monitoring

### Real-time Performance Tracking
- **Cache efficiency**: Monitor hit rates and optimization opportunities
- **Function timing**: Track execution times for critical paths
- **Memory usage**: Alert on memory leaks or excessive usage

### Performance Hooks
```bash
# Check performance after changes to critical files
performance-hooks:
  - name: "Performance regression check"
    trigger: "file_modified"
    pattern: "**/cache.py|**/server.py"
```

## 🤖 AI-Assisted Development

### Smart Suggestions
The development assistant learns from your patterns and provides:
- **Context-aware suggestions**: Based on current file and project state
- **Pattern recognition**: Learn from successful development patterns
- **Proactive alerts**: Notify about potential issues before they become problems

### Learning Mode
```json
{
  "learning_mode": {
    "enabled": true,
    "track_patterns": true,
    "suggest_improvements": true
  }
}
```

## 📝 Code Snippets

### MCP Tool Handler Template
```python
# Trigger: mcp_tool_handler
class ${ToolName}Handler(ToolHandlerBase):
    """${Handler description}"""
    
    @validate_note_id_required
    async def handle(self, arguments: dict) -> List[TextContent]:
        """${Handle the tool request}"""
        # Implementation
        return [TextContent(type="text", text="Success")]
```

### Async Test Template
```python
# Trigger: async_test
@pytest.mark.asyncio
async def test_${function_name}():
    """${Test description}"""
    # Arrange
    
    # Act
    result = await ${function_call}
    
    # Assert
    assert result is not None
```

## 🔄 Workflow Integration

### Git Integration
- **Pre-commit validation**: Automatic quality checks before commit
- **Branch analysis**: Suggestions based on current branch
- **Merge conflict prevention**: Early detection of potential conflicts

### GitHub Actions Integration
- **CI status monitoring**: Track build status in real-time
- **Workflow validation**: Verify GitHub Actions syntax
- **Performance regression alerts**: Detect performance issues in CI

## 🎛️ Customization

### Project-Specific Configuration
Edit `.claude-code-hooks.yaml` to customize:

```yaml
# Enable/disable specific hook categories
hooks:
  pre-edit: true
  post-edit: true
  pre-commit: true
  security-hooks: true
  performance-hooks: false  # Disable if not needed

# Customize patterns
patterns:
  python_files: "**/*.py"
  test_files: "tests/**/*.py"
  ignore: ["**/__pycache__/**"]
```

### Personal Preferences
Edit `.claude-code-settings.json` for IDE integration:

```json
{
  "formatting": {
    "onSave": true,
    "command": "ruff format {file}"
  },
  "testing": {
    "autoRun": true,
    "coverage": true
  }
}
```

## 🚨 Troubleshooting

### Common Issues

**Scripts not executable:**
```bash
chmod +x scripts/claude-code-support/*.sh scripts/claude-code-support/*.py
```

**Hooks not running:**
```bash
# Check hook configuration
cat .claude-code-hooks.yaml

# Verify Claude Code settings
cat .claude-code-settings.json
```

**Tests failing in offline mode:**
```bash
# Ensure offline mode is set
export SIMPLENOTE_OFFLINE_MODE=true
./scripts/claude-code-support/auto-test.sh
```

### Debug Mode
Enable verbose output for troubleshooting:

```bash
# Verbose auto-testing
./scripts/claude-code-support/auto-test.sh --verbose

# Debug smart validator
./scripts/claude-code-support/smart-validator.py --verbose

# Development assistant debug
./scripts/claude-code-support/development-assistant.py --config
```

## 📈 Best Practices

### 1. Start Small
Begin with basic hooks enabled and gradually add more automation as you become comfortable.

### 2. Monitor Performance
Use the development assistant to monitor how hooks affect your workflow performance.

### 3. Customize for Your Style
Adjust hook triggers and automation levels to match your development style.

### 4. Regular Updates
Keep your hook configurations updated as the project evolves.

### 5. Share Configurations
Share successful hook patterns with your team for consistency.

## 🎉 Getting Started

1. **Enable the hooks**: Ensure `.claude-code-hooks.yaml` is configured in Claude Code
2. **Try a command**: Run `./scripts/claude-code-support/auto-test.sh --quick`  
3. **Edit a file**: Make a small change and observe automatic formatting/testing
4. **Use the assistant**: Run `./scripts/claude-code-support/development-assistant.py --suggest`
5. **Customize**: Adjust settings in `.claude-code-settings.json` to your preferences

## 💡 Pro Tips

- Use `Ctrl+T` frequently for quick test feedback
- Enable project monitoring during focused development sessions
- Review suggestions from the development assistant regularly
- Customize snippet templates for common MCP patterns
- Use the smart validator before commits for comprehensive quality checks

---

This configuration transforms Claude Code into a powerful, AI-assisted development environment specifically optimized for MCP server development! 🚀
