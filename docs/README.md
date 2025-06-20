# Simplenote MCP Server Documentation

Welcome to the comprehensive documentation for the Simplenote MCP Server project. This documentation is organized to help you quickly find the information you need.

## 🚀 Getting Started

Start here if you're new to the project:

- **[Getting Started Guide](getting-started.md)** - Quick setup and installation
- **[User Guides](user-guides.md)** - How to use the server effectively

## 📖 Main Documentation

### User Documentation
- [Getting Started](getting-started.md) - Installation and setup
- [User Guides](user-guides.md) - Feature usage and examples

### Development
- [Claude Integration](development/claude-integration.md) - Working with Claude AI
- [Code Formatting](development/formatting-checklist.md) - Formatting standards
- [Linting Guide](development/linting-guide.md) - Code quality tools
- [Technical Debt](development/technical-debt.md) - Known issues and improvements
- [Development TODO](development/todo.md) - Planned development tasks
- [Version Management](development/version-pinning-changes.md) - Dependency management

### Architecture & Operations
- [System Architecture](architecture/overview.md) - High-level system design
- [Health Monitoring](operations/health-monitoring-optimization.md) - Monitoring setup
- [Structured Logging](operations/structured-logging.md) - Logging implementation
- [Error Categorization](operations/error-categorization.md) - Error handling patterns

### CI/CD & DevOps
- [CI/CD Documentation](ci-cd/documentation.md) - Continuous integration setup
- [Docker Setup](ci-cd/docker-setup.md) - Container configuration
- [Badge Fixes](ci-cd/badge-fixes-summary.md) - CI badge maintenance
- [CI Fixes](ci-cd/fixes-summary.md) - Historical CI fixes
- [CI Improvements](ci-cd/improvements-summary.md) - CI enhancements
- [Workflow Analysis](ci-cd/workflow-analysis-report.md) - Workflow optimization

### Planning & Project Management
- [Product Requirements](planning/product-requirements.md) - Main PRD
- [Docker CI/CD Requirements](planning/docker-ci-cd-requirements.md) - Infrastructure PRD
- [Project Roadmap](planning/roadmap.md) - Future development plans

### Testing & Quality Assurance
- [Validation Steps](testing/validation-steps.md) - Testing procedures and checklists

### Releases
- [v1.6.0 Release Notes](releases/v1.6.0.md) - Latest release information

## 📂 Repository Structure

```
docs/
├── README.md                    # This file - documentation index
├── getting-started.md           # Quick start guide
├── user-guides.md              # User documentation
├── architecture/               # System design and architecture
├── development/                # Developer guides and tools
├── ci-cd/                      # CI/CD and DevOps documentation
├── operations/                 # Runtime operations and monitoring
├── planning/                   # Project management and requirements
├── testing/                    # Quality assurance and testing
└── releases/                   # Release notes and changelogs
```

## 🤝 Contributing to Documentation

When contributing to this documentation:

1. Follow the [Contributing Guidelines](../CONTRIBUTING.md)
2. Use clear, descriptive headings
3. Include code examples where appropriate
4. Keep the documentation up-to-date with code changes
5. Follow the established file naming conventions

### Documentation Standards

- Use kebab-case for file names (e.g., `getting-started.md`)
- Start each document with a clear title and purpose
- Include a table of contents for longer documents
- Use relative links when referencing other documentation
- Follow the project's markdown formatting standards

## 📋 Quick Reference

| Document Type | Location | Purpose |
|---------------|----------|---------|
| User guides | `docs/` root | End-user documentation |
| Development | `docs/development/` | Developer resources |
| Architecture | `docs/architecture/` | System design |
| Operations | `docs/operations/` | Runtime management |
| CI/CD | `docs/ci-cd/` | Build and deployment |
| Planning | `docs/planning/` | Project management |
| Testing | `docs/testing/` | Quality assurance |
| Releases | `docs/releases/` | Version information |

---

**Need help?** Check the [main README](../README.md) or [Contributing Guide](../CONTRIBUTING.md) for additional information.
