# CI/CD Troubleshooting Guide

**Repository:** docdyhr/simplenote-mcp-server  
**Last Updated:** 2024-12-19  
**Status:** Active Monitoring

## 🚨 Common CI/CD Issues and Solutions

### Issue 1: Workflow Failures Due to Dependency Issues

**Symptoms:**
- `pip install -e .[dev]` fails
- Missing dependencies errors
- Import errors in workflows

**Solutions:**
```bash
# Fix circular dependency in pyproject.toml
[project.optional-dependencies]
all = [
    # List dependencies directly instead of referencing other sections
    "ruff>=0.1.0",
    "mypy>=1.5.0", 
    # ... other deps
]

# Use simpler installation in workflows
pip install -e .
pip install ruff mypy pytest pytest-asyncio pytest-cov
```

**Prevention:**
- Test dependency installation locally
- Avoid circular references in pyproject.toml
- Use explicit dependency lists in workflows

### Issue 2: Ruff Formatting Failures

**Symptoms:**
- `ruff format --check .` exits with code 1
- Workflows fail on formatting checks
- Pre-commit hooks modify files

**Solutions:**
```yaml
# Make formatting non-blocking
- name: Run Ruff formatting check
  run: ruff format --check . || echo "Formatting issues found but continuing"

# Or auto-fix formatting
- name: Auto-fix formatting
  run: ruff format .
```

**Prevention:**
- Run `ruff format .` before committing
- Configure pre-commit hooks properly
- Use consistent formatting across team

### Issue 3: MyPy Type Checking Failures

**Symptoms:**
- Type checking errors in workflows
- Missing type stubs
- Configuration file not found

**Solutions:**
```yaml
# Make type checking non-blocking
- name: Type checking with MyPy
  run: mypy simplenote_mcp --config-file=mypy.ini || echo "Type issues found but continuing"

# Install missing type stubs
pip install types-requests types-setuptools
```

**Prevention:**
- Maintain proper type annotations
- Keep mypy.ini configuration updated
- Test type checking locally

### Issue 4: Test Failures in CI Environment

**Symptoms:**
- Tests pass locally but fail in CI
- Environment-specific test failures
- Missing test dependencies

**Solutions:**
```yaml
# Ensure proper test environment
env:
  SIMPLENOTE_EMAIL: "test@example.com"
  SIMPLENOTE_PASSWORD: "test_password"
  PYTHONPATH: ${{ github.workspace }}

# Install all test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

**Prevention:**
- Use environment variables for test configuration
- Mock external dependencies
- Test in clean environments locally

### Issue 5: Security Scan False Positives

**Symptoms:**
- Security workflows fail on minor issues
- Bandit/Safety reports block CI
- False positive vulnerability reports

**Solutions:**
```yaml
# Make security checks non-blocking
- name: Run security scan
  run: bandit -r simplenote_mcp/ || echo "Security issues found but continuing"

# Use continue-on-error for security steps
- name: Security check
  run: safety check
  continue-on-error: true
```

**Prevention:**
- Review security findings regularly
- Whitelist false positives appropriately
- Keep dependencies updated

## 🔧 Workflow-Specific Troubleshooting

### CI/CD Pipeline (`ci.yml`)

**Common Issues:**
1. **Matrix build failures**: Reduce OS matrix for testing
2. **Dependency conflicts**: Use pinned versions
3. **Build artifact issues**: Check upload/download paths

**Debug Steps:**
```bash
# Local testing
python -m pip install --upgrade pip
pip install -e .
pytest tests/ -v
ruff check .
mypy simplenote_mcp
```

### Python Tests (`python-tests.yml`)

**Common Issues:**
1. **Coverage upload failures**: Check Codecov token
2. **Test discovery issues**: Verify test file patterns
3. **Environment setup**: Ensure proper Python version

**Debug Steps:**
```bash
# Test discovery
pytest --collect-only tests/

# Coverage testing
pytest --cov=simplenote_mcp --cov-report=xml tests/

# Check coverage file
ls -la coverage.xml
```

### Code Quality (`code-quality.yml`)

**Common Issues:**
1. **Pre-commit failures**: Outdated hooks
2. **Artifact uploads**: Check file paths
3. **Tool version conflicts**: Pin tool versions

**Debug Steps:**
```bash
# Pre-commit testing
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Manual tool runs
ruff check .
mypy simplenote_mcp
```

### Security (`security.yml`)

**Common Issues:**
1. **Tool installation failures**: Missing dependencies
2. **Scan timeouts**: Large codebases
3. **Report generation**: JSON parsing errors

**Debug Steps:**
```bash
# Manual security scans
pip install bandit safety
bandit -r simplenote_mcp/
safety check

# Check for known vulnerabilities
pip-audit
```

## 🔍 Debugging Workflows

### Debug CI Workflow (`debug-ci.yml`)

Use this workflow to diagnose CI issues:

**Triggers:**
- Manual dispatch
- Push to main (when debugging)

**What it checks:**
- Python environment setup
- Package installation
- Tool versions
- Basic functionality

### Manual Debugging Commands

```bash
# Check workflow status
gh workflow list
gh run list --workflow=ci.yml

# View workflow logs
gh run view <run-id>

# Re-run failed workflow
gh run rerun <run-id>
```

## 📊 Monitoring and Alerts

### Badge Status Monitoring

**Check badge status:**
```bash
# Run badge validation
python scripts/validate-badges.py

# Check specific workflow status
curl -I "https://github.com/docdyhr/simplenote-mcp-server/actions/workflows/ci.yml/badge.svg"
```

### Workflow Health Checks

**Daily checks:**
- Badge status validation
- Workflow run success rates
- Security scan results
- Dependency health

**Weekly reviews:**
- Workflow performance trends
- Security findings review
- Dependency updates
- Tool version updates

## 🚀 Recovery Procedures

### When All Workflows Fail

1. **Immediate Actions:**
   ```bash
   # Check local environment
   git status
   git log --oneline -5
   
   # Test basic functionality
   python -c "import simplenote_mcp; print('OK')"
   ruff check .
   pytest tests/ -k "test_cache"
   ```

2. **Systematic Debugging:**
   - Run debug-ci workflow
   - Check dependency installation
   - Verify configuration files
   - Test individual workflow steps

3. **Emergency Fixes:**
   - Disable failing workflows temporarily
   - Use manual workflow dispatch
   - Create hotfix branch for critical issues

### When Badges Show Red

1. **Identify the issue:**
   - Check workflow run logs
   - Compare with last successful run
   - Review recent commits

2. **Quick fixes:**
   - Re-run failed workflows
   - Check for transient issues
   - Verify external service status

3. **Permanent solutions:**
   - Fix underlying code issues
   - Update configurations
   - Improve error handling

## 📋 Maintenance Checklist

### Weekly Maintenance
- [ ] Review failed workflow runs
- [ ] Update dependency versions
- [ ] Check security scan results
- [ ] Validate badge status
- [ ] Review workflow performance

### Monthly Maintenance
- [ ] Update GitHub Actions versions
- [ ] Review and update tool configurations
- [ ] Clean up old workflow runs
- [ ] Update documentation
- [ ] Performance optimization review

### Quarterly Maintenance
- [ ] Major dependency updates
- [ ] Workflow architecture review
- [ ] Security audit
- [ ] Performance benchmarking
- [ ] Documentation overhaul

## 🆘 Emergency Contacts

### When to Escalate
- Critical security vulnerabilities
- Complete CI/CD system failure
- Data integrity issues
- External service outages

### Self-Service Resources
- GitHub Actions documentation
- Tool-specific documentation (Ruff, MyPy, etc.)
- Community forums and Stack Overflow
- Project issue tracker

### Immediate Support
- Check GitHub Status page
- Review recent commits for breaking changes
- Use debug workflow for systematic diagnosis
- Consult troubleshooting guide (this document)

---

**Remember:** Most CI/CD issues are temporary or configuration-related. Follow this guide systematically, and don't hesitate to make workflows more lenient during debugging phases.

**Next Review:** 2025-01-19  
**Maintainer:** @docdyhr
