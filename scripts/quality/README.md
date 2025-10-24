# Quality Automation Scripts

**Location:** `scripts/quality/`  
**Purpose:** Automated quality checks and maintenance tools  
**Created:** October 2025  
**Maintainer:** Core development team

---

## 📋 Overview

This directory contains automated scripts for maintaining project quality, consistency, and documentation health. These tools are designed to be used both locally during development and in CI/CD pipelines.

---

## 🛠️ Available Scripts

### 1. Version Consistency Checker

**File:** `check_version_consistency.py`  
**Purpose:** Ensure version numbers are consistent across all project files

**Features:**
- Checks VERSION file, pyproject.toml, __init__.py, Chart.yaml
- Automatic synchronization with `--fix` flag
- CI/CD integration ready
- Clear reporting format

**Usage:**
```bash
# Check version consistency
python scripts/quality/check_version_consistency.py

# Auto-fix inconsistencies (uses pyproject.toml as source of truth)
python scripts/quality/check_version_consistency.py --fix

# Specify custom root directory
python scripts/quality/check_version_consistency.py --root /path/to/project
```

**Output:**
```
📋 Version Check Results:
============================================================
✅ VERSION             : 1.8.0
✅ pyproject.toml      : 1.8.0
✅ __init__.py         : 1.8.0
✅ Chart.yaml          : 1.8.0
============================================================
✅ All versions are consistent: 1.8.0
```

**Exit Codes:**
- `0` - All versions consistent
- `1` - Version inconsistencies found
- `2` - Error reading files

---

### 2. Coverage Threshold Checker

**File:** `check_coverage.py`  
**Purpose:** Validate test coverage meets minimum thresholds

**Features:**
- Configurable coverage threshold (default: 65%)
- Detailed reporting by module
- Warning-only mode for gradual rollout
- Recommendations for improvement
- Identifies low-coverage modules

**Usage:**
```bash
# Check coverage against 65% threshold
python scripts/quality/check_coverage.py --threshold 65.0

# Detailed module-by-module report
python scripts/quality/check_coverage.py --threshold 65.0 --report

# Show improvement recommendations
python scripts/quality/check_coverage.py --threshold 65.0 --recommendations

# Warning mode (don't fail CI)
python scripts/quality/check_coverage.py --threshold 65.0 --warn-only

# Custom coverage file location
python scripts/quality/check_coverage.py --coverage-file path/to/coverage.json
```

**Output:**
```
📊 Coverage Summary
======================================================================
Total Coverage: 69.64%
Threshold:      65.00% ✅ (exceeds by 4.64%)
======================================================================

📁 Module Coverage (lowest to highest):
----------------------------------------------------------------------
⚠️ server/memory_monitor.py                             0.00%
⚠️ server/monitoring/thresholds.py                     27.23%
   ... (more modules) ...
✅ server/logger_factory.py                            99.39%
======================================================================

✅ Coverage check passed!
```

**Exit Codes:**
- `0` - Coverage meets or exceeds threshold
- `1` - Coverage below threshold (unless --warn-only)
- `2` - Error reading coverage data

---

### 3. Documentation Archival Tool

**File:** `archive_old_docs.py`  
**Purpose:** Manage and archive old documentation files

**Features:**
- Identifies documentation older than threshold (default: 90 days)
- Protected files (never archives core docs)
- Year-based archival structure
- Dry-run mode for safety
- Auto-generates archive index
- Smart conflict resolution

**Usage:**
```bash
# List files that would be archived
python scripts/quality/archive_old_docs.py --list-candidates

# Preview what would happen (dry run)
python scripts/quality/archive_old_docs.py --dry-run

# Actually archive old files
python scripts/quality/archive_old_docs.py --archive

# Create/update archive index
python scripts/quality/archive_old_docs.py --create-index

# Custom age threshold (days)
python scripts/quality/archive_old_docs.py --age-threshold 120 --dry-run
```

**Output:**
```
📋 Archive Candidates (8 files)
======================================================================
File                                               Age (days)   Size
----------------------------------------------------------------------
tests/TEST_SUMMARY.md                              153          5.4 KB
DOCKER_HUB_FIX_SUMMARY.md                          112          6.7 KB
DOCKER_FIXES.md                                    112          4.7 KB
...
----------------------------------------------------------------------
Total: 8 files, 47.5 KB
======================================================================
```

**Protected Files (Never Archived):**
- README.md
- CONTRIBUTING.md
- LICENSE
- SECURITY.md
- CHANGELOG.md
- TODO.md
- CLAUDE.md
- AGENTS.md
- DOCKER_README.md

**Archive Patterns (Archived When Old):**
- `*_SUMMARY.md`
- `*_REPORT.md`
- `*_ANALYSIS.md`
- `*_FIXES.md`
- `*_RESOLUTION*.md`
- `PROJECT_STATUS_*.md`
- `*_TEST_*.md`
- `*_IMPLEMENTATION_*.md`

**Exit Codes:**
- `0` - Success
- `1` - Error occurred

---

## 🔄 CI/CD Integration

### GitHub Actions Integration

Add to your workflow file (e.g., `.github/workflows/unified-ci.yml`):

```yaml
jobs:
  validate:
    steps:
      - name: Check version consistency
        run: |
          python scripts/quality/check_version_consistency.py

  test:
    steps:
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=simplenote_mcp --cov-report=json --cov-report=xml

      - name: Check coverage threshold
        run: |
          python scripts/quality/check_coverage.py --threshold 65.0 --warn-only
```

### Pre-commit Integration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: version-consistency
        name: Check version consistency
        entry: python scripts/quality/check_version_consistency.py
        language: system
        pass_filenames: false
        stages: [commit]
```

---

## 📊 Recommended Usage Patterns

### During Development

```bash
# Before committing a version bump
python scripts/quality/check_version_consistency.py --fix

# After running tests
python scripts/quality/check_coverage.py --threshold 65.0 --report
```

### During Release

```bash
# 1. Verify versions
python scripts/quality/check_version_consistency.py

# 2. Check coverage
python scripts/quality/check_coverage.py --threshold 65.0

# 3. Archive old docs
python scripts/quality/archive_old_docs.py --archive

# 4. Update archive index
python scripts/quality/archive_old_docs.py --create-index
```

### Quarterly Maintenance

```bash
# List documentation to archive
python scripts/quality/archive_old_docs.py --list-candidates

# Archive with 120-day threshold
python scripts/quality/archive_old_docs.py --age-threshold 120 --archive

# Generate fresh archive index
python scripts/quality/archive_old_docs.py --create-index
```

---

## 🎯 Quality Standards

### Version Consistency
- **Goal:** Single source of truth for version numbers
- **Enforced by:** `check_version_consistency.py`
- **Standard:** All version declarations must match

### Test Coverage
- **Minimum Baseline:** 65%
- **Target:** 70%+
- **Enforced by:** `check_coverage.py`
- **Mode:** Warning-only (gradually increasing)

### Documentation Freshness
- **Archive Threshold:** 90 days for status reports
- **Protected:** Core documentation never archived
- **Enforced by:** `archive_old_docs.py`
- **Review Frequency:** Quarterly

---

## 🔧 Script Requirements

All scripts require:
- Python 3.10+
- Standard library only (no external dependencies)
- Run from project root directory

### File Location Requirements

Scripts expect to find:
- `pyproject.toml` in root (version source of truth)
- `VERSION` file in root
- `simplenote_mcp/__init__.py` with `__version__`
- `helm/simplenote-mcp-server/Chart.yaml` for Helm version
- `coverage.json` for coverage checks (generated by pytest-cov)

---

## 📝 Development Guidelines

### Adding New Scripts

When adding a new quality script:

1. **Naming Convention:** Use `snake_case.py`
2. **Documentation:** Include comprehensive docstring
3. **Help Text:** Provide `--help` option with argparse
4. **Exit Codes:** Follow Unix conventions (0=success, 1=failure, 2=error)
5. **Dry Run:** Include `--dry-run` for destructive operations
6. **Logging:** Use clear emoji indicators (✅ ❌ ⚠️ 💡)
7. **Testing:** Test locally before committing
8. **README:** Update this file with new script documentation

### Code Style

- Follow PEP 8 conventions
- Use type hints for all functions
- Include Google-style docstrings
- Add example output in docstrings
- Handle errors gracefully

---

## 🐛 Troubleshooting

### Version Check Fails

**Problem:** Script reports version inconsistencies
```bash
❌ Version inconsistency detected!
   Found 2 different versions: {'1.6.0', '1.8.0'}
```

**Solution:**
```bash
# Auto-fix using pyproject.toml as source of truth
python scripts/quality/check_version_consistency.py --fix
```

### Coverage Check Fails

**Problem:** Coverage below threshold
```bash
❌ Coverage check failed: 62.50% < 65.00%
```

**Solutions:**
1. Use warning mode in CI: `--warn-only`
2. Lower threshold temporarily: `--threshold 60.0`
3. Add more tests to increase coverage
4. Use `--report` to see which modules need tests

### Archive Script Issues

**Problem:** "pyproject.toml not found"
```bash
❌ Error: pyproject.toml not found. Are you in the project root?
```

**Solution:**
```bash
# Run from project root or specify root
cd /path/to/project
python scripts/quality/archive_old_docs.py --archive

# OR
python scripts/quality/archive_old_docs.py --root /path/to/project --archive
```

---

## 📈 Metrics and Monitoring

### Version Consistency
- **Frequency:** Every commit (via pre-commit hook)
- **Failure Rate Target:** 0%
- **Current Status:** ✅ 100% consistent

### Coverage Threshold
- **Frequency:** Every test run
- **Current Coverage:** 69.64%
- **Threshold:** 65%
- **Status:** ✅ Exceeds target by 4.64%

### Documentation Health
- **Review Frequency:** Quarterly
- **Archive Candidates:** 8 files (47.5 KB)
- **Protected Files:** 9 core documents
- **Last Archive:** Pending

---

## 🔗 Related Documentation

- [DOCUMENTATION_GUIDE.md](../../docs/DOCUMENTATION_GUIDE.md) - Doc maintenance guide
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [TODO.md](../../TODO.md) - Project roadmap
- [CACHE_COVERAGE_PLAN.md](../../docs/testing/CACHE_COVERAGE_PLAN.md) - Coverage plan

---

## 📞 Support

**Issues:** Report problems via GitHub Issues  
**Questions:** See CONTRIBUTING.md for contact info  
**Improvements:** Pull requests welcome!

---

## 📜 Change Log

### 2025-10-20 - Initial Release
- ✅ Created `check_version_consistency.py`
- ✅ Created `check_coverage.py`
- ✅ Created `archive_old_docs.py`
- ✅ Added comprehensive documentation
- ✅ Integrated with CI/CD pipeline

---

**Last Updated:** October 20, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
