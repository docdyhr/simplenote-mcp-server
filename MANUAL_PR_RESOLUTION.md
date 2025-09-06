# Manual PR Resolution Guide for Single Developer

This guide helps you manually resolve pull requests without requiring GitHub API access, following best practices for solo development.

## 🔍 Step 1: Identify Your PRs

### Using GitHub Web Interface
1. Go to: `https://github.com/docdyhr/simplenote-mcp-server/pulls`
2. Review all open PRs
3. Note the PR numbers and branch names

### Using Git Locally
```bash
# List all remote branches (shows PR branches)
git branch -r

# See recent branches
git for-each-ref --sort=-committerdate refs/remotes/origin --format='%(refname:short) %(committerdate:short)'
```

## 🔍 Step 2: Review Each PR

### Manual Review Process

For each PR, perform these checks:

```bash
# 1. Fetch latest changes
git fetch origin

# 2. Check out the PR branch
git checkout <pr-branch-name>

# 3. Review the changes
git log main..<pr-branch-name> --oneline
git diff main..<pr-branch-name>

# 4. Run tests locally
python -m pytest tests/ -v

# 5. Check code quality
python -m ruff check .
python -m ruff format --check .
python -m mypy simplenote_mcp/

# 6. Check security
python -m bandit -r simplenote_mcp/
```

### Review Checklist
- [ ] **Functionality**: Code works as expected
- [ ] **Tests**: All tests pass
- [ ] **Quality**: Linting and formatting pass
- [ ] **Security**: No security issues
- [ ] **Documentation**: Updated if needed
- [ ] **Breaking Changes**: Documented

## 🚀 Step 3: Merge Strategy Decision

### Choose Your Merge Strategy

**Option A: Squash Merge (Recommended for small features)**
```bash
# Switch to main
git checkout main
git pull origin main

# Squash merge the PR branch
git merge --squash <pr-branch-name>

# Create a single commit
git commit -m "feat: descriptive commit message

- Summary of changes
- Key improvements
- Fixes #issue-number (if applicable)"

# Push to main
git push origin main
```

**Option B: Regular Merge (For larger features)**
```bash
# Switch to main
git checkout main
git pull origin main

# Merge with merge commit
git merge --no-ff <pr-branch-name> -m "Merge pull request #<number> from <branch>

<PR title and description>"

# Push to main
git push origin main
```

**Option C: Rebase and Merge (For clean linear history)**
```bash
# Switch to PR branch
git checkout <pr-branch-name>

# Rebase onto main
git rebase main

# Switch to main
git checkout main
git pull origin main

# Fast-forward merge
git merge <pr-branch-name>

# Push to main
git push origin main
```

## 🧹 Step 4: Cleanup

### Close PR on GitHub
1. Go to the PR page on GitHub
2. Add a comment explaining the resolution
3. Close the PR manually

### Delete Branches
```bash
# Delete local branch
git branch -d <pr-branch-name>

# Delete remote branch
git push origin --delete <pr-branch-name>
```

## 📋 Common PR Resolution Scenarios

### Scenario 1: Simple Feature PR
```bash
# Example: PR #15 - Add new endpoint
git checkout feature/new-endpoint
python -m pytest tests/ -v  # Verify tests pass
git checkout main
git merge --squash feature/new-endpoint
git commit -m "feat: add new endpoint for note search

- Implements /search endpoint
- Adds validation for search parameters
- Includes comprehensive tests
- Updates API documentation

Closes #15"
git push origin main
git branch -d feature/new-endpoint
git push origin --delete feature/new-endpoint
```

### Scenario 2: Bug Fix PR
```bash
# Example: PR #16 - Fix cache invalidation
git checkout bugfix/cache-invalidation
python -m pytest tests/ -v  # Verify fix works
git checkout main
git merge --squash bugfix/cache-invalidation
git commit -m "fix: resolve cache invalidation issue

- Fixes issue where cache wasn't cleared on note updates
- Adds proper cleanup in cache.py
- Includes regression test
- Improves error handling

Fixes #14"
git push origin main
git branch -d bugfix/cache-invalidation
git push origin --delete bugfix/cache-invalidation
```

### Scenario 3: Documentation Update
```bash
# Example: PR #17 - Update README
git checkout docs/readme-update
git checkout main
git merge --squash docs/readme-update
git commit -m "docs: update README with new features

- Documents new search endpoint
- Updates installation instructions
- Adds troubleshooting section
- Fixes broken links"
git push origin main
git branch -d docs/readme-update
git push origin --delete docs/readme-update
```

## 🛡️ Safety Checks Before Merging

### Pre-Merge Validation
```bash
#!/bin/bash
# Save as scripts/pre-merge-check.sh

echo "🔍 Pre-merge validation for branch: $1"
BRANCH=$1

# Switch to branch
git checkout $BRANCH

# Run comprehensive tests
echo "🧪 Running tests..."
python -m pytest tests/ -v --tb=short

# Check code quality
echo "🎨 Checking code quality..."
python -m ruff check .
python -m ruff format --check .

# Type checking
echo "🔍 Type checking..."
python -m mypy simplenote_mcp/

# Security scan
echo "🛡️ Security scan..."
python -m bandit -r simplenote_mcp/ -ll

# Check for conflicts with main
echo "🔀 Checking for conflicts..."
git merge-tree $(git merge-base main $BRANCH) main $BRANCH

echo "✅ Pre-merge checks complete!"
```

Usage:
```bash
chmod +x scripts/pre-merge-check.sh
./scripts/pre-merge-check.sh feature/my-branch
```

## 📝 PR Resolution Templates

### Success Comment Template
```markdown
## ✅ PR Merged Successfully

This PR has been reviewed and merged into main.

**Merge Strategy**: [Squash/Regular/Rebase] merge
**Commit**: [commit-hash]

### Changes Included:
- [Brief summary of changes]
- [Key improvements]
- [Any breaking changes]

### Verification:
- ✅ All tests pass
- ✅ Code quality checks pass
- ✅ Security scan clean
- ✅ Manual testing completed

Thanks for the contribution! 🎉
```

### Close Without Merge Template
```markdown
## ❌ PR Closed

This PR is being closed without merging for the following reason(s):

**Reason**: [Superseded by another PR / Approach changed / etc.]

### Details:
[Explain why the PR wasn't merged]

### Next Steps:
[Any follow-up actions needed]

Thanks for the work on this! 🙏
```

## 🔄 Batch Operations

### Handle Multiple PRs
```bash
#!/bin/bash
# Process multiple PRs in sequence

PRS=("feature/auth-improvement" "bugfix/memory-leak" "docs/api-update")

for branch in "${PRS[@]}"; do
    echo "Processing $branch..."
    
    # Run checks
    ./scripts/pre-merge-check.sh $branch
    
    # If checks pass, merge
    if [ $? -eq 0 ]; then
        git checkout main
        git pull origin main
        git merge --squash $branch
        
        # Prompt for commit message
        echo "Enter commit message for $branch:"
        git commit
        
        git push origin main
        git branch -d $branch
        git push origin --delete $branch
        
        echo "✅ $branch merged and cleaned up"
    else
        echo "❌ $branch failed checks, skipping"
    fi
    
    echo "---"
done
```

## 📊 Post-Resolution Actions

### Update Project Status
After resolving PRs, update relevant documentation:

1. **Update REMAINING_ISSUES.md** if PRs fixed known issues
2. **Update README.md** if new features were added
3. **Update CHANGELOG.md** with changes
4. **Tag a new release** if appropriate

### Verify CI/CD Pipeline
```bash
# Trigger workflows manually if needed
git commit --allow-empty -m "chore: trigger CI after PR merges"
git push origin main
```

## 🎯 Best Practices Summary

### Do's ✅
- **Always run tests before merging**
- **Use descriptive commit messages**
- **Clean up branches after merging**
- **Document significant changes**
- **Follow consistent merge strategy**

### Don'ts ❌
- **Don't merge failing tests**
- **Don't skip code quality checks**
- **Don't leave stale branches**
- **Don't merge without review (even self-review)**

---

**Remember**: Even as a solo developer, maintaining good PR hygiene helps with:
- Code quality assurance
- Change documentation
- Future collaboration
- Project maintenance

This manual process gives you full control while maintaining professional standards.
