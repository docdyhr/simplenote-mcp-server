# Documentation Guide for Simplenote MCP Server

**Last Updated:** 2025-10-20  
**Purpose:** Guide for maintaining and navigating the project's extensive documentation

---

## 📚 Documentation Overview

This project contains **536+ markdown files** covering various aspects of development, deployment, and maintenance. This guide helps you navigate and maintain this documentation effectively.

## 🗂️ Documentation Structure

### Core Documentation (User-Facing)

| File | Purpose | Audience |
|------|---------|----------|
| `README.md` | Project overview, quick start, features | All users |
| `CONTRIBUTING.md` | Contribution guidelines | Contributors |
| `LICENSE` | MIT license | Legal/compliance |
| `SECURITY.md` | Security policy and reporting | Security researchers |
| `CHANGELOG.md` | Version history | All users |

### Development Documentation

| Directory | Purpose | Contents |
|-----------|---------|----------|
| `docs/` | Main documentation hub | API docs, guides, tutorials |
| `docs/api/` | API reference | Server API, types, examples |
| `docs/development/` | Developer guides | Setup, testing, conventions |
| `docs/ci-cd/` | CI/CD documentation | Workflows, badges, Docker |
| `docs/releases/` | Release notes | Version-specific changes |

### Project Management Documentation

| File Pattern | Purpose | Status |
|--------------|---------|--------|
| `*_SUMMARY.md` | Project summaries | Archive candidate |
| `*_REPORT.md` | Status reports | Keep latest only |
| `*_ANALYSIS.md` | Technical analysis | Reference material |
| `TODO.md` | Active roadmap | **Keep updated** |
| `PROJECT_STATUS_*.md` | Status snapshots | Archive older ones |

### Specialized Documentation

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `DOCKER_README.md` | Docker Hub description | On Docker changes |
| `AGENTS.md` | AI agent integration | As needed |
| `CLAUDE.md` | Claude Desktop setup | On MCP changes |
| `.github/copilot-instructions.md` | Copilot rules | Rarely |

---

## 🎯 Documentation Maintenance Guidelines

### Version References

**CRITICAL:** Always update version references when releasing:

```bash
# Check version consistency
python scripts/quality/check_version_consistency.py

# Files to update on version bump:
# - VERSION
# - pyproject.toml
# - simplenote_mcp/__init__.py
# - helm/simplenote-mcp-server/Chart.yaml
# - README.md (badge)
# - docs/installation.md (badge)
# - docs/api/server.md (API version)
```

### Documentation Review Checklist

Before each release:

- [ ] Update version numbers across all docs
- [ ] Review and update TODO.md roadmap
- [ ] Archive old status reports (>3 months)
- [ ] Update coverage metrics in README
- [ ] Update CHANGELOG.md with release notes
- [ ] Review security documentation
- [ ] Update Docker and Helm docs if changed

### Archiving Old Documentation

**When to Archive:**

- Status reports older than 3 months
- Summaries of completed work
- Historical analysis documents
- Deprecated feature documentation

**How to Archive:**

```bash
# Create archive directory if it doesn't exist
mkdir -p docs/archive/$(date +%Y)

# Move old files
mv PROJECT_STATUS_JANUARY_2025.md docs/archive/2025/
mv *_SUMMARY.md docs/archive/2025/
```

**Current Archive Snapshot (2025):**

The following historical summaries now live under `docs/archive/2025/` for easier browsing:

- `docs/archive/2025/CONTEXT_TEST_IMPLEMENTATION_SUMMARY.md`
- `docs/archive/2025/CI_CD_FIXES_SUMMARY.md`
- `docs/archive/2025/DOCKER_HUB_FIX_SUMMARY.md`
- `docs/archive/2025/EVALUATION_IMPROVEMENTS_SUMMARY.md`
- `docs/archive/2025/FINAL_RESOLUTION_SUMMARY.md`
- `docs/archive/2025/IMPROVEMENTS_SUMMARY_OCT_2025.md`
- `docs/archive/2025/ISSUE_RESOLUTION_SUMMARY.md`
- `docs/archive/2025/MCP_EVALS_INTEGRATION_SUMMARY.md`
- `docs/archive/2025/PR_RESOLUTION_FINAL_SUMMARY.md`
- `docs/archive/2025/PR_RESOLUTION_SUMMARY.md`
- `docs/archive/2025/PROJECT_COMPLETION_SUMMARY.md`
- `docs/archive/2025/PROJECT_IMPROVEMENTS_SUMMARY_2025_01.md`

Use this directory as the canonical home for future legacy summaries so the repository root stays focused on active work.

**What to Keep:**

- Latest status report
- Active roadmap (TODO.md)
- Security reports (last 2 years)
- Current release notes
- API documentation

---

## 📋 Documentation Categories

### 1. User Documentation (Keep Fresh)

**Location:** Root directory and `docs/`

**Files:**
- `README.md` - Main entry point
- `docs/installation.md` - Installation guide
- `docs/configuration.md` - Configuration options
- `docs/troubleshooting.md` - Common issues

**Maintenance:** Review quarterly, update on major changes

### 2. Developer Documentation (Active)

**Location:** `docs/development/`, `docs/api/`

**Files:**
- API reference documentation
- Development setup guides
- Testing strategies
- Contributing guidelines

**Maintenance:** Update with code changes

### 3. Operations Documentation (Important)

**Location:** `docs/deployment/`, Docker files

**Files:**
- Docker deployment guides
- Kubernetes/Helm documentation
- CI/CD workflow documentation
- Monitoring and observability guides

**Maintenance:** Update with infrastructure changes

### 4. Project Management (Archive Regularly)

**Location:** Root directory

**Files:**
- Status reports
- Resolution summaries
- Completion reports
- Analysis documents

**Maintenance:** Keep last 2-3 months, archive rest

### 5. Historical Documentation (Archive)

**Location:** `docs/archive/`

**Files:**
- Completed migration guides
- Resolved issue summaries
- Historical status reports
- Deprecated features

**Maintenance:** Move files older than 6 months

---

## 🔍 Finding Documentation

### Quick Reference

```bash
# Find documentation by topic
grep -r "search term" docs/ --include="*.md"

# List all markdown files
find . -name "*.md" -type f | sort

# Find files modified recently
find docs/ -name "*.md" -mtime -30

# Find large documentation files
find docs/ -name "*.md" -size +100k
```

### Documentation Index

**Getting Started:**
- `README.md` - Start here
- `docs/installation.md` - Installation
- `CONTRIBUTING.md` - Contributing

**Development:**
- `docs/development/` - Developer guides
- `docs/api/` - API reference
- `docs/testing.md` - Testing guide

**Deployment:**
- `DOCKER_README.md` - Docker guide
- `docs/kubernetes.md` - K8s deployment
- `helm/` - Helm charts

**Operations:**
- `docs/monitoring.md` - Monitoring
- `docs/security.md` - Security
- `docs/troubleshooting.md` - Issues

**Project Management:**
- `TODO.md` - Current roadmap
- `CHANGELOG.md` - Version history
- Latest `PROJECT_STATUS_*.md` - Current status

---

## 📝 Writing Documentation

### Style Guidelines

**Formatting:**
- Use clear, descriptive headers (##, ###)
- Include table of contents for long documents
- Use code blocks with language tags
- Add badges for status indicators

**Structure:**
```markdown
# Document Title

**Last Updated:** YYYY-MM-DD
**Status:** [Active|Deprecated|Archived]

## Overview
Brief description...

## Contents
- [Section 1](#section-1)
- [Section 2](#section-2)

## Details
...
```

**Best Practices:**
- Write for your audience (user vs developer)
- Include examples and code snippets
- Link to related documentation
- Keep paragraphs short and scannable
- Use tables for structured data
- Add visual indicators (✅ ❌ ⚠️ 💡)

### Markdown Standards

```markdown
# Use ATX-style headers (# ## ###)
# NOT underline style (=== ---)

Use **bold** for emphasis
Use `code` for inline code
Use > for important callouts

[Link text](relative/path.md) for internal links
[Link text](https://example.com) for external

```language
code blocks with language tags
```
```

### Documentation Templates

**Status Report Template:**
```markdown
# Project Status - [Month Year]

**Status:** ✅ [Status]
**Last Updated:** [Date]

## Executive Summary
Brief overview...

## Key Metrics
| Metric | Value | Status |
|--------|-------|--------|

## Recent Achievements
- Achievement 1
- Achievement 2

## Current Issues
- Issue 1

## Next Steps
- Step 1
```

**Feature Documentation Template:**
```markdown
# Feature Name

**Status:** [Alpha|Beta|Stable]
**Since:** Version X.Y.Z

## Overview
What does this feature do?

## Usage
How to use it with examples

## Configuration
Options and settings

## Examples
Real-world use cases

## Troubleshooting
Common issues and solutions
```

---

## 🔄 Documentation Workflow

### For New Features

1. **Document as you code**
   - Update API docs for new endpoints
   - Add usage examples
   - Document configuration options

2. **Update user-facing docs**
   - Add to README if major feature
   - Update installation guide if needed
   - Add troubleshooting entries

3. **Update changelog**
   - Add entry to CHANGELOG.md
   - Follow conventional commit format
   - Include version and date

### For Bug Fixes

1. **Update troubleshooting guide**
   - Add issue and solution
   - Include error messages
   - Provide diagnostic steps

2. **Update changelog**
   - Document the fix
   - Reference issue number

### For Releases

1. **Version updates** (use script)
   ```bash
   python scripts/quality/check_version_consistency.py --fix
   ```

2. **Release notes**
   - Create `docs/releases/vX.Y.Z.md`
   - Update CHANGELOG.md
   - Update README badges

3. **Archive old reports**
   - Move old status reports
   - Update documentation index

---

## 🎯 Documentation Priorities

### High Priority (Update Always)

1. ✅ **README.md** - Project entry point
2. ✅ **CHANGELOG.md** - Version history
3. ✅ **TODO.md** - Active roadmap
4. ✅ **API documentation** - Keep in sync with code
5. ✅ **Security documentation** - Critical for users

### Medium Priority (Update Regularly)

6. 📋 **Installation guides** - Review quarterly
7. 📋 **Configuration docs** - On config changes
8. 📋 **Troubleshooting** - Add common issues
9. 📋 **CI/CD docs** - On workflow changes
10. 📋 **Docker/K8s docs** - On infrastructure changes

### Low Priority (Update As Needed)

11. 📝 **Development guides** - Stable processes
12. 📝 **Historical reports** - Archive instead
13. 📝 **Analysis documents** - Reference only
14. 📝 **Completed summaries** - Archive

---

## 🧹 Documentation Cleanup Plan

### Phase 1: Immediate (Completed)
- ✅ Fix version inconsistencies
- ✅ Update coverage metrics
- ✅ Create this guide

### Phase 2: Short-term (Next Week)
- [ ] Archive status reports older than 3 months
- [ ] Consolidate duplicate summaries
- [ ] Create docs/archive/ structure
- [ ] Update documentation index

### Phase 3: Medium-term (Next Month)
- [ ] Review all documentation for accuracy
- [ ] Remove deprecated content
- [ ] Improve cross-linking between docs
- [ ] Add more examples and tutorials

### Phase 4: Ongoing
- [ ] Review docs quarterly
- [ ] Update on each release
- [ ] Collect user feedback
- [ ] Improve based on common questions

---

## 📊 Documentation Metrics

**Current State:**
- Total markdown files: 536+
- Documentation directories: 10+
- Status reports: 15+
- API documentation: Complete
- User guides: Complete
- Developer guides: Complete

**Target State:**
- Active documentation: ~100 files
- Archived documentation: ~400 files
- Documentation coverage: 100%
- Average age: < 6 months
- Update frequency: Quarterly

---

## 💡 Tips and Best Practices

### For Contributors

1. **Always update docs with code changes**
2. **Use the templates provided**
3. **Link related documentation**
4. **Include examples and code snippets**
5. **Test documentation instructions**

### For Maintainers

1. **Review docs in every PR**
2. **Archive old content regularly**
3. **Keep TODO.md current**
4. **Update version references**
5. **Maintain the CHANGELOG**

### For Users

1. **Start with README.md**
2. **Check troubleshooting for issues**
3. **Review examples in docs/**
4. **Join discussions for help**
5. **Contribute improvements**

---

## 🔗 Related Resources

- [Contributing Guide](../CONTRIBUTING.md)
- [Style Guide](.github/copilot-instructions.md)
- [Roadmap](../TODO.md)
- [Changelog](../CHANGELOG.md)
- [Security Policy](../SECURITY.md)

---

## 📞 Documentation Help

**Issues with documentation?**
- Create an issue with label `documentation`
- Tag it with specific area (api, setup, deployment)
- Provide suggestions for improvement

**Want to contribute?**
- See [CONTRIBUTING.md](../CONTRIBUTING.md)
- Follow the templates above
- Update the index when adding new docs
- Test your documentation changes

---

**Last Review:** 2025-10-20  
**Next Review:** 2026-01-20  
**Maintained by:** Core team
