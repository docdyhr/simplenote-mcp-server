# Security Monitoring Guide

This document describes the automated security monitoring and maintenance procedures for the simplenote-mcp-server project.

## 📊 Overview

The project uses multiple layers of automated security monitoring to ensure dependencies remain secure and vulnerabilities are quickly identified and resolved.

## 🛡️ Security Tools

### 1. GitHub Dependabot

**Purpose**: Automated dependency updates and security alerts

**Configuration**: `.github/dependabot.yml`

**Features**:
- **Weekly scheduled scans**: Sunday (Python), Monday (GitHub Actions), Tuesday (Docker)
- **Security-only updates**: High-priority security patches grouped separately
- **Grouped updates**: Related dependencies bundled into single PRs
- **Auto-labeling**: Dependencies tagged for easy filtering

**Update Groups**:
- `security-dependencies`: Critical security packages (starlette, urllib3, requests)
- `production-dependencies`: Core runtime packages (mcp, simplenote)
- `development-dependencies`: Dev tools (ruff, mypy, pytest, black)

### 2. pip-audit

**Purpose**: CVE scanning for Python dependencies

**Integration**: GitHub Actions workflow (`.github/workflows/security.yml`)

**Schedule**: 
- Every push to main/develop
- Every PR
- Weekly (Monday 3 AM UTC)
- Manual trigger via workflow_dispatch

**Features**:
- Scans all installed packages against OSV and PyPI databases
- Generates JSON reports for tracking
- Reports uploaded as GitHub Actions artifacts (30-day retention)
- Continues on error to not block PRs

**Usage**:
```bash
# Local scan
pip-audit --desc

# Generate report
pip-audit --desc --format json > pip-audit-report.json

# Skip specific vulnerabilities (if needed)
pip-audit --ignore-vuln VULN-ID-HERE
```

### 3. Bandit

**Purpose**: Python code security static analysis

**Integration**: GitHub Actions (security.yml) and pre-commit hooks

**Configuration**: `pyproject.toml` → `[tool.bandit]`

**Scans for**:
- Hardcoded credentials (B105, B106, B107)
- SQL injection vulnerabilities (B608)
- Shell injection risks (B602, B605, B607)
- Insecure cryptographic usage (B303, B304, B305)
- Pickle/marshal usage (B301, B302)

**Exclusions**:
- Test files (`tests/`, `*test*.py`)
- Scripts directory (diagnostic tools)
- Known safe patterns (documented in config)

### 4. Safety

**Purpose**: Known vulnerability database scanning

**Integration**: GitHub Actions security workflow

**Database**: Checks against Safety DB for known vulnerable packages

**Note**: Safety has limited free tier; pip-audit provides similar coverage with OSV database

### 5. CodeQL

**Purpose**: Deep semantic code analysis

**Integration**: `.github/workflows/codeql-analysis.yml`

**Schedule**:
- Every push to main/develop
- Every PR
- Weekly Monday 3 AM UTC

**Queries**:
- `security-extended`: Comprehensive security patterns
- `security-and-quality`: Combined security and code quality

**Language**: Python

## 🔔 Alert Handling

### Severity Levels

| Severity | Response Time | Action |
|----------|--------------|---------|
| **Critical** | Immediate (< 24 hours) | Emergency patch, hotfix release |
| **High** | 1-3 days | Priority fix, patch release |
| **Medium** | 1-2 weeks | Regular update cycle |
| **Low** | Next minor release | Bundled with other updates |

### Response Workflow

1. **Alert Received**
   - GitHub Security Advisory created
   - Dependabot PR auto-created (if fix available)
   - Email notification sent to maintainers

2. **Assessment**
   - Review CVE details and impact
   - Check if vulnerability affects our usage
   - Determine urgency based on:
     - Exploitability
     - Public exploit availability
     - Attack surface in our codebase

3. **Remediation**
   - Review Dependabot PR
   - Run full test suite
   - Check for breaking changes
   - Merge PR or manual fix if needed

4. **Verification**
   - CI/CD pipeline passes
   - pip-audit shows vulnerability resolved
   - Security scan artifacts clean

5. **Documentation**
   - Update CHANGELOG.md with security fix
   - Document CVE and resolution
   - Tag release if necessary

## 📈 Monitoring Dashboards

### GitHub Security Tab

**Location**: `https://github.com/docdyhr/simplenote-mcp-server/security`

**Views**:
- **Security Overview**: High-level status
- **Dependabot Alerts**: Open vulnerabilities
- **Security Advisories**: Published advisories
- **Code Scanning Alerts**: CodeQL findings

### Actions Artifacts

**Location**: GitHub Actions run artifacts

**Available Reports**:
- `pip-audit-report`: JSON format, 30-day retention
- CodeQL SARIF results (automatic upload to Security tab)

**Access**:
```bash
# Via gh CLI
gh run list --workflow security.yml
gh run view RUN_ID
gh run download RUN_ID --name pip-audit-report
```

## 🔧 Local Security Scanning

### Quick Security Check

```bash
# Run all security checks locally
./scripts/security-check.sh

# Or manually:
bandit -r simplenote_mcp/
pip-audit --desc
ruff check --select=S .
```

### Pre-commit Hooks

Security checks run automatically on commit:
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📝 Best Practices

### For Maintainers

1. **Review Dependabot PRs weekly**
   - Don't let security PRs sit idle
   - Merge or close with documented reason

2. **Monitor Security Tab regularly**
   - Check for new alerts weekly
   - Ensure no stale issues remain open

3. **Keep CI workflows updated**
   - Actions versions (Dependabot handles this)
   - Security tool versions

4. **Document security decisions**
   - If ignoring a vulnerability, document why in CHANGELOG
   - Add skip rules to pip-audit if necessary (rare)

5. **Test before merging security updates**
   - Run full test suite
   - Check Docker builds
   - Verify MCP protocol compliance

### For Contributors

1. **Never commit credentials**
   - Use environment variables
   - Check with `detect-secrets` or similar

2. **Follow security patterns**
   - Input validation
   - Parameterized queries
   - Proper exception handling

3. **Run security checks locally**
   - Pre-commit hooks will catch issues
   - Fix before pushing

## 🚨 Incident Response

### Security Vulnerability Reported

1. **Acknowledge** (< 24 hours)
2. **Assess** severity and impact
3. **Patch** vulnerability
4. **Test** thoroughly
5. **Release** fix version
6. **Disclose** via GitHub Security Advisory
7. **Notify** users via release notes

### Contact

- **Security Issues**: File a private security advisory on GitHub
- **Public Discussion**: Use GitHub Discussions
- **Email**: [Listed in SECURITY.md]

## 📊 Metrics

### Security Health Indicators

Track these metrics for project health:

- **Time to Patch Critical**: Target < 24 hours
- **Open Security Alerts**: Target = 0
- **Dependabot PR Merge Rate**: Target > 80%
- **Security Scan Pass Rate**: Target = 100%
- **Days Since Last Security Review**: Target < 7 days

## 🔄 Continuous Improvement

### Monthly Review

- Review security scanning effectiveness
- Update security tool versions
- Audit ignored vulnerabilities
- Refine Dependabot grouping rules

### Quarterly Assessment

- Review incident response procedures
- Update severity response times if needed
- Evaluate new security tools
- Train on new vulnerability types

## 📚 Resources

### External Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [CVE Database](https://cve.mitre.org/)
- [OSV Vulnerability Database](https://osv.dev/)

### Internal Documentation

- [SECURITY.md](../SECURITY.md) - Security policy
- [CHANGELOG.md](../CHANGELOG.md) - Security fix history
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Secure development guidelines

## 🎯 Success Criteria

The security monitoring system is effective when:

✅ All critical vulnerabilities are patched within 24 hours  
✅ Zero open high/critical security alerts  
✅ Security scans run on every PR and push  
✅ Dependabot PRs are reviewed within 7 days  
✅ Security documentation is kept up-to-date  
✅ Team responds to security reports within 24 hours  

---

**Last Updated**: 2025-10-29  
**Version**: 1.0  
**Maintained By**: @docdyhr
