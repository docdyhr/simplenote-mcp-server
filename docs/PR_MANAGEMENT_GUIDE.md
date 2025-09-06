# Pull Request Management Guide for Single-Developer Projects

This guide provides best practices for managing pull requests in a single-developer environment, balancing code quality with development efficiency.

## 🎯 Overview

As a solo developer, you have flexibility in your PR workflow while still maintaining good practices for:
- Code review and quality assurance
- Change tracking and documentation
- CI/CD pipeline validation
- Future collaboration readiness

## 🔧 Setup

### Prerequisites
1. **GitHub Personal Access Token** with repo permissions
2. **Branch protection rules** (optional but recommended)
3. **CI/CD pipeline** for automated testing

### Environment Setup
```bash
# Set your GitHub token
export GITHUB_TOKEN="your_personal_access_token"

# Make the PR management script executable
chmod +x scripts/manage-prs.py
```

## 📋 PR Workflow Options

### Option 1: Self-Review Workflow (Recommended)
Best for feature development and significant changes.

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes and commit
git add .
git commit -m "feat: implement new feature"
git push origin feature/new-feature

# 3. Create PR via GitHub UI or CLI
gh pr create --title "Add new feature" --body "Description of changes"

# 4. Review your own PR
python scripts/manage-prs.py --review <pr_number>

# 5. Wait for CI/CD to pass
# 6. Merge when ready
python scripts/manage-prs.py --merge <pr_number> [--squash]
```

### Option 2: Direct Push Workflow
For hotfixes and minor changes.

```bash
# For small changes, push directly to main
git checkout main
git pull origin main
# Make small changes
git add .
git commit -m "fix: minor bug fix"
git push origin main
```

## 🔍 PR Review Checklist

Even when reviewing your own code, use this checklist:

### Code Quality
- [ ] **Functionality**: Does the code do what it's supposed to do?
- [ ] **Readability**: Is the code clear and well-documented?
- [ ] **Performance**: Are there any obvious performance issues?
- [ ] **Security**: Are there any security vulnerabilities?
- [ ] **Error Handling**: Are edge cases and errors handled properly?

### Testing
- [ ] **Unit Tests**: Are new features covered by tests?
- [ ] **Integration Tests**: Do existing tests still pass?
- [ ] **Manual Testing**: Have you tested the changes manually?

### Documentation
- [ ] **Code Comments**: Are complex parts well-commented?
- [ ] **README Updates**: Does documentation need updating?
- [ ] **API Changes**: Are breaking changes documented?

### CI/CD
- [ ] **All Checks Pass**: Green build status
- [ ] **Coverage**: Test coverage meets requirements
- [ ] **Linting**: Code style checks pass

## 🚀 Merge Strategies

### When to Use Each Strategy

**Squash Merge** (`--squash`)
- ✅ Small features or bug fixes
- ✅ Multiple commits that should be consolidated
- ✅ Experimental commits you want to clean up
- ❌ Large features with logical commit history

**Regular Merge**
- ✅ Large features with meaningful commit history
- ✅ When you want to preserve the development timeline
- ✅ Collaborative work (future consideration)

**Rebase and Merge**
- ✅ When you want linear history
- ✅ Clean, atomic commits
- ❌ Shared branches (not applicable for solo dev)

### Examples

```bash
# Small feature - squash merge
python scripts/manage-prs.py --merge 123 --squash

# Large feature - regular merge
python scripts/manage-prs.py --merge 124

# Keep branch for future reference
python scripts/manage-prs.py --merge 125 --keep-branch
```

## 🧹 Branch Management

### Branch Naming Conventions
```
feature/description-of-feature
bugfix/issue-description
hotfix/critical-fix
docs/documentation-update
refactor/code-improvement
```

### Cleanup Strategy
```bash
# List open PRs
python scripts/manage-prs.py --list

# Clean up merged branches
python scripts/manage-prs.py --cleanup-branches

# Manual cleanup
git branch -d feature/completed-feature
git push origin --delete feature/completed-feature
```

## 📊 PR Templates

### Feature PR Template
```markdown
## 🚀 Feature: [Feature Name]

### What
Brief description of what this PR adds.

### Why
Explanation of why this change is needed.

### How
Technical details of the implementation.

### Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] CI/CD pipeline passes

### Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated if needed
- [ ] Breaking changes documented
```

### Bugfix PR Template
```markdown
## 🐛 Bugfix: [Bug Description]

### Problem
Description of the bug and its impact.

### Root Cause
What was causing the issue.

### Solution
How the fix addresses the problem.

### Testing
- [ ] Bug reproduction confirmed
- [ ] Fix verified manually
- [ ] Regression tests added
- [ ] CI/CD pipeline passes
```

## 🔄 Automation Scripts

### Quick Commands
```bash
# List all open PRs
python scripts/manage-prs.py --list

# Detailed review of PR #123
python scripts/manage-prs.py --review 123

# Merge PR #123 with squash
python scripts/manage-prs.py --merge 123 --squash

# Close PR #123 with comment
python scripts/manage-prs.py --close 123 --comment "Superseded by #124"

# Clean up merged branches
python scripts/manage-prs.py --cleanup-branches
```

### GitHub CLI Integration
```bash
# Create PR with GitHub CLI
gh pr create --fill

# List PRs
gh pr list

# Merge PR
gh pr merge 123 --squash --delete-branch

# View PR in browser
gh pr view 123 --web
```

## 🛡️ Protection Rules

Consider setting up branch protection rules even for solo projects:

### Main Branch Protection
- Require status checks to pass
- Require up-to-date branches
- Dismiss stale reviews
- Restrict pushes to matching branches

### Benefits
- Prevents accidental direct pushes to main
- Ensures CI/CD runs before merge
- Maintains consistent workflow
- Prepares for future collaboration

## 🎨 Best Practices Summary

### Do's ✅
- **Create meaningful PR titles and descriptions**
- **Wait for CI/CD to pass before merging**
- **Use appropriate merge strategies**
- **Clean up branches regularly**
- **Document breaking changes**
- **Test changes before merging**

### Don'ts ❌
- **Don't skip CI/CD checks**
- **Don't merge failing tests**
- **Don't accumulate stale branches**
- **Don't rush the review process**
- **Don't ignore security warnings**

## 🔧 Troubleshooting

### Common Issues

**Authentication Errors**
```bash
# Check if token is set
echo $GITHUB_TOKEN

# Verify token permissions
gh auth status
```

**Merge Conflicts**
```bash
# Update branch with latest main
git checkout feature/branch
git rebase main

# Resolve conflicts and continue
git add .
git rebase --continue
```

**Failed Status Checks**
```bash
# Check workflow status
gh run list --branch feature/branch

# View logs for failed run
gh run view <run-id> --log-failed
```

## 📚 Additional Resources

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Git Best Practices](https://git-scm.com/docs/gitworkflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

**Remember**: The goal is to maintain code quality while keeping development velocity high. Adapt these practices to fit your specific project needs and development style.
