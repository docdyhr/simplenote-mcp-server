# Quality Tools Quick Start Guide

**Version:** 1.8.1  
**Last Updated:** October 20, 2025  
**For:** Developers and Maintainers

---

## 🎯 Overview

This project includes three automated quality tools to maintain consistency and quality:

1. **Version Consistency Checker** - Ensures all version numbers match
2. **Coverage Threshold Checker** - Enforces test coverage standards
3. **Documentation Archival Tool** - Manages documentation lifecycle

---

## ⚡ Quick Commands

### Before Every Commit
```bash
# Check version consistency
python scripts/quality/check_version_consistency.py

# Check test coverage
python scripts/quality/check_coverage.py --threshold 65.0
```

### After Version Bump
```bash
# Auto-fix version inconsistencies
python scripts/quality/check_version_consistency.py --fix
```

### Quarterly Maintenance
```bash
# List old documentation
python scripts/quality/archive_old_docs.py --list-candidates

# Archive old docs (dry run first!)
python scripts/quality/archive_old_docs.py --dry-run
python scripts/quality/archive_old_docs.py --archive
```

---

## 📚 Tool Details

### 1. Version Consistency Checker

**Purpose:** Keep VERSION, pyproject.toml, __init__.py, and Chart.yaml synchronized

**Common Usage:**
```bash
# Check if versions match
python scripts/quality/check_version_consistency.py

# Auto-fix using pyproject.toml as source of truth
python scripts/quality/check_version_consistency.py --fix
```

**Output:**
```
📋 Version Check Results:
============================================================
✅ VERSION             : 1.8.1
✅ pyproject.toml      : 1.8.1
✅ __init__.py         : 1.8.1
✅ Chart.yaml          : 1.8.1
============================================================
✅ All versions are consistent: 1.8.1
```

**When to Use:**
- Before committing version bumps
- After manually editing version files
- In CI/CD pipeline (automatically)
- During release preparation

---

### 2. Coverage Threshold Checker

**Purpose:** Ensure test coverage meets minimum standards (65% baseline)

**Common Usage:**
```bash
# Simple check
python scripts/quality/check_coverage.py --threshold 65.0

# Detailed module report
python scripts/quality/check_coverage.py --threshold 65.0 --report

# Get improvement suggestions
python scripts/quality/check_coverage.py --threshold 65.0 --recommendations

# Warning mode (don't fail)
python scripts/quality/check_coverage.py --threshold 65.0 --warn-only
```

**Output:**
```
📊 Coverage Summary
======================================================================
Total Coverage: 69.64%
Threshold:      65.00% ✅ (exceeds by 4.64%)
======================================================================
```

**When to Use:**
- After running test suite
- Before merging pull requests
- In CI/CD pipeline (automatically)
- When improving test coverage

---

### 3. Documentation Archival Tool

**Purpose:** Keep documentation fresh by archiving old status reports

**Common Usage:**
```bash
# See what would be archived
python scripts/quality/archive_old_docs.py --list-candidates

# Preview archival (safe)
python scripts/quality/archive_old_docs.py --dry-run

# Actually archive files
python scripts/quality/archive_old_docs.py --archive

# Update archive index
python scripts/quality/archive_old_docs.py --create-index
```

**Output:**
```
📋 Archive Candidates (8 files)
======================================================================
File                                               Age (days)   Size
----------------------------------------------------------------------
tests/TEST_SUMMARY.md                              153          5.4 KB
DOCKER_HUB_FIX_SUMMARY.md                          112          6.7 KB
...
----------------------------------------------------------------------
Total: 8 files, 47.5 KB
======================================================================
```

**When to Use:**
- Quarterly documentation cleanup
- Before major releases
- When docs folder gets cluttered
- Manual cleanup needed

**What Gets Archived:**
- Status reports older than 90 days
- Summary documents older than 90 days
- Analysis documents older than 90 days
- Historical implementation notes

**What's Protected (Never Archived):**
- README.md, CONTRIBUTING.md, LICENSE
- SECURITY.md, CHANGELOG.md, TODO.md
- Core project documentation

---

## 🔄 Workflows

### Pre-Commit Workflow
```bash
# 1. Check versions
python scripts/quality/check_version_consistency.py

# 2. Run tests with coverage
pytest tests/ --cov=simplenote_mcp --cov-report=json

# 3. Check coverage
python scripts/quality/check_coverage.py --threshold 65.0

# 4. If all pass, commit!
git add .
git commit -m "feat: your feature"
```

### Release Workflow
```bash
# 1. Update version in pyproject.toml (e.g., 1.8.1 → 1.9.0)
vim pyproject.toml

# 2. Sync all version files
python scripts/quality/check_version_consistency.py --fix

# 3. Verify consistency
python scripts/quality/check_version_consistency.py

# 4. Update changelog
vim docs/changelog.md

# 5. Archive old docs
python scripts/quality/archive_old_docs.py --archive

# 6. Commit release
git add .
git commit -m "chore: release v1.9.0"
git tag v1.9.0
git push origin main --tags
```

### Quarterly Maintenance Workflow
```bash
# 1. Check project health
python scripts/quality/check_version_consistency.py
python scripts/quality/check_coverage.py --threshold 65.0 --report

# 2. Archive old documentation
python scripts/quality/archive_old_docs.py --list-candidates
python scripts/quality/archive_old_docs.py --archive

# 3. Update archive index
python scripts/quality/archive_old_docs.py --create-index

# 4. Review TODO.md and update roadmap
vim TODO.md

# 5. Commit maintenance changes
git add .
git commit -m "chore: quarterly maintenance"
```

---

## 🚨 Troubleshooting

### Version Check Fails
**Problem:** `❌ Version inconsistency detected!`

**Solution:**
```bash
python scripts/quality/check_version_consistency.py --fix
```

This uses pyproject.toml as the source of truth and updates all other files.

---

### Coverage Check Fails
**Problem:** `❌ Coverage check failed: 62.50% < 65.00%`

**Solutions:**
1. **Short-term:** Use warning mode
   ```bash
   python scripts/quality/check_coverage.py --threshold 65.0 --warn-only
   ```

2. **Long-term:** Improve coverage
   ```bash
   # See which modules need tests
   python scripts/quality/check_coverage.py --threshold 65.0 --report
   
   # Get recommendations
   python scripts/quality/check_coverage.py --recommendations
   ```

---

### Archive Script Can't Find Files
**Problem:** `❌ Error: pyproject.toml not found`

**Solution:** Run from project root
```bash
cd /path/to/simplenote-mcp-server
python scripts/quality/archive_old_docs.py --archive
```

---

## 📊 Current Project Status

**Version:** 1.8.1 ✅  
**Coverage:** 69.64% ✅ (exceeds 65% threshold)  
**Documentation:** 536+ files, 8 ready for archival  
**Quality:** All checks passing

---

## 🎓 Best Practices

### 1. Check Before Committing
Always run version and coverage checks before committing changes:
```bash
python scripts/quality/check_version_consistency.py && \
python scripts/quality/check_coverage.py --threshold 65.0 --warn-only
```

### 2. Use Auto-Fix for Versions
Don't manually sync versions - let the script do it:
```bash
python scripts/quality/check_version_consistency.py --fix
```

### 3. Preview Before Archiving
Always use `--dry-run` first to see what will be archived:
```bash
python scripts/quality/archive_old_docs.py --dry-run
```

### 4. Review Coverage Reports
Use detailed reports to prioritize testing efforts:
```bash
python scripts/quality/check_coverage.py --threshold 65.0 --report
```

### 5. Set Up Pre-Commit Hooks
Add to `.git/hooks/pre-commit` (or use pre-commit framework):
```bash
#!/bin/bash
python scripts/quality/check_version_consistency.py || exit 1
```

---

## 🔗 More Information

- **Full Documentation:** [scripts/quality/README.md](scripts/quality/README.md)
- **Documentation Guide:** [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md)
- **Coverage Plan:** [docs/testing/CACHE_COVERAGE_PLAN.md](docs/testing/CACHE_COVERAGE_PLAN.md)
- **Project Review:** [PROJECT_REVIEW_OCT_2025.md](PROJECT_REVIEW_OCT_2025.md)

---

## 💡 Tips

- **Tab completion:** Scripts support `--help` for all options
- **Emoji indicators:** ✅ success, ❌ failure, ⚠️ warning, 💡 tip
- **Exit codes:** 0 = success, 1 = failure, 2 = error
- **CI/CD ready:** All scripts designed for automation
- **No dependencies:** Scripts use only Python standard library

---

## 🆘 Getting Help

**Script Help:**
```bash
python scripts/quality/check_version_consistency.py --help
python scripts/quality/check_coverage.py --help
python scripts/quality/archive_old_docs.py --help
```

**Documentation:**
- [scripts/quality/README.md](scripts/quality/README.md) - Complete reference
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [GitHub Issues](https://github.com/docdyhr/simplenote-mcp-server/issues) - Report problems

---

**Quick Start Complete!** 🎉

You're now ready to use the quality automation tools. Start with:
```bash
python scripts/quality/check_version_consistency.py
```
