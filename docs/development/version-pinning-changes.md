# Tool Version Pinning Changes

## Overview

This document summarizes the changes made to pin tool versions in CI/CD workflows to match the versions specified in the pre-commit configuration, ensuring consistency across all environments.

## Changes Made

### Pre-commit Configuration (Reference)

The following versions are specified in `.pre-commit-config.yaml`:

- **Ruff**: `v0.12.0` (from `astral-sh/ruff-pre-commit`)
- **MyPy**: `v1.16.1` (from `pre-commit/mirrors-mypy`)

### Updated Workflows

#### 1. Main CI Pipeline (`.github/workflows/ci.yml`)

**Before:**
```yaml
pip install ruff mypy pytest pytest-asyncio pytest-cov requests
```

**After:**
```yaml
pip install ruff==0.12.0 mypy==1.16.1 pytest pytest-asyncio pytest-cov requests
```

#### 2. Code Quality (`.github/workflows/code-quality.yml`)

**Changes in 3 jobs:**

- **pre-commit job:**
  ```yaml
  pip install pre-commit ruff==0.12.0 mypy==1.16.1 pytest pytest-asyncio pytest-cov pytest-mock
  ```

- **security job:**
  ```yaml
  pip install ruff==0.12.0
  ```

- **type-check job:**
  ```yaml
  pip install mypy==1.16.1
  ```

#### 3. Formatting Check (`.github/workflows/formatting-check.yml`)

**Changes in 3 jobs:**

- **format-check job:**
  ```yaml
  pip install pre-commit ruff==0.12.0 mypy==1.16.1 types-requests types-setuptools types-PyYAML pytest
  ```

- **quick-lint job:**
  ```yaml
  pip install ruff==0.12.0
  ```

- **type-check job:**
  ```yaml
  pip install mypy==1.16.1 types-requests types-setuptools types-PyYAML
  ```

#### 4. Test Workflow (`.github/workflows/test.yml`)

**lint job:**
```yaml
pip install ruff==0.12.0 mypy==1.16.1
```

#### 5. Python Tests (integrated in `.github/workflows/ci.yml`)

**test job:**
```yaml
pip install pytest pytest-cov pytest-asyncio pytest-mock ruff==0.12.0 mypy==1.16.1
```

#### 6. Debug CI (`.github/workflows/debug-ci.yml`)

**debug-environment job:**
```yaml
pip install ruff==0.12.0 mypy==1.16.1 pytest pytest-asyncio pytest-cov
```

### Workflows Not Changed

The following workflows were **not modified** because they don't install ruff or mypy directly:

- `release.yml` - Uses pre-commit which respects pinned versions
- `performance.yml` - Doesn't use linting tools
- `security.yml` - Uses bandit/safety, not ruff for security
- `badge-check.yml` - Only installs web scraping tools
- `docs.yml` - Only installs documentation tools

## Benefits

### 1. **Consistency Across Environments**
- Local pre-commit hooks and CI workflows now use identical tool versions
- Eliminates "works on my machine" issues related to tool version differences

### 2. **Predictable Behavior**
- Same linting rules and formatting behavior across all environments
- Reproducible results in CI/CD pipelines

### 3. **Reduced Debugging**
- Fewer issues caused by tool version mismatches
- More reliable automated fixes and formatting

### 4. **Better Developer Experience**
- Pre-commit results match CI results
- No surprises when code passes locally but fails in CI

## Verification

To verify the changes work correctly:

### 1. **Automated Validation**
```bash
# Run the version pinning validation script
python scripts/validate-version-pinning.py
```

**Latest validation results:**
```
🎉 SUCCESS: All tool versions are properly pinned and consistent!

✅ Summary:
   • Pre-commit tools: 2
   • Workflow files checked: 12
   • Files with tool installations: 6
   • Issues found: 0
```

### 2. **Local Testing**
```bash
# Test pre-commit hooks
pre-commit run --all-files

# Check tool versions
ruff --version  # Should show 0.11.5
mypy --version  # Should show 1.15.0
```

### 3. **CI Testing**
- Push changes to a feature branch
- Verify all workflows pass with consistent tool versions
- Check workflow logs for version confirmations

### 4. **Version Verification Commands**
Added to most workflows:
```yaml
- name: ✅ Verify Installation
  run: |
    echo "🔧 Checking tools..."
    ruff --version
    mypy --version
```

## Maintenance

### Updating Tool Versions

When updating tool versions in the future:

1. **Update pre-commit config first:**
   ```yaml
   # .pre-commit-config.yaml
   - repo: https://github.com/astral-sh/ruff-pre-commit
     rev: v0.13.0  # New version
```

2. **Update all CI workflows:**
   - Search for `ruff==0.12.0` and replace with new version
   - Search for `mypy==1.16.1` and replace with new version

3. **Test locally before committing:**
   ```bash
   pre-commit autoupdate
   pre-commit run --all-files
   ```

### Monitoring

- **Tool Release Notes**: Monitor Ruff and MyPy releases for breaking changes
- **Pre-commit Updates**: Use `pre-commit autoupdate` regularly
- **CI Health**: Watch for sudden CI failures after tool updates
- **Regular Validation**: Run `python scripts/validate-version-pinning.py` after changes

## Troubleshooting

### Common Issues

1. **Version Not Found**
   - Check if the version exists on PyPI
   - Verify version format (e.g., `0.11.5` vs `v0.11.5`)

2. **Dependency Conflicts**
   - Update other dependencies if they conflict with pinned versions
   - Consider using version ranges for non-critical dependencies

3. **Tool Behavior Changes**
   - Review tool changelogs when updating versions
   - Update configuration files if needed (pyproject.toml, mypy.ini)

### Emergency Rollback

If issues arise, quickly rollback by:

1. Reverting to previous tool versions in all workflows
2. Running `pre-commit autoupdate` to sync pre-commit config
3. Testing locally before pushing changes

## Related Files

- `.pre-commit-config.yaml` - Source of truth for tool versions
- `pyproject.toml` - Tool configuration settings
- `mypy.ini` - MyPy-specific configuration
- `scripts/validate-version-pinning.py` - Validation script
- All `.github/workflows/*.yml` files - CI/CD implementations

## Validation Script

The project includes an automated validation script at `scripts/validate-version-pinning.py` that:

- Extracts tool versions from `.pre-commit-config.yaml`
- Scans all GitHub workflow files for tool installations
- Validates that all versions are pinned and consistent
- Provides detailed reports of any mismatches

This script should be run after any changes to tool versions or workflow files.

---

**Last Updated**: January 2025  
**Next Review**: When updating tool versions or adding new workflows  
**Validation Status**: ✅ All versions pinned and consistent (ruff 0.12.0, mypy 1.16.1 - last checked: January 2025)
