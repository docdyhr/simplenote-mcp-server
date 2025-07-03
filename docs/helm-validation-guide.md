# Helm Template Validation Guide

## Overview

This guide explains how to properly validate Helm charts and why standard YAML parsers fail on Helm templates, along with best practices for handling these validation challenges.

## The Problem: Why YAML Parsers Fail on Helm Templates

### Root Cause

Helm templates use **Go template syntax** embedded within YAML files. Standard YAML parsers don't understand this templating language and treat it as invalid YAML syntax.

### Example of the Conflict

```yaml
# Standard YAML (works with any YAML parser)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app

# Helm Template (fails with standard YAML parsers)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "simplenote-mcp-server.fullname" . }}  # ← Go template syntax
  labels:
    {{- include "simplenote-mcp-server.labels" . | nindent 4 }}  # ← Template functions
spec:
  {{- if not .Values.autoscaling.enabled }}  # ← Conditional logic
  replicas: {{ .Values.replicaCount }}
  {{- end }}
```

### What YAML Parsers See

When a standard YAML parser encounters Helm templates, it sees:
- `{{ }}` - Invalid flow mapping syntax
- `{{- }}` - Unknown YAML directive
- `.Values.something` - Invalid key structure
- `if/else` statements - Not valid YAML constructs
- Template functions like `include`, `nindent` - Undefined references

## Current Diagnostic Output

### Sample Errors from yamllint
```
helm/simplenote-mcp-server/templates/deployment.yaml
  4:11      error    too many spaces inside braces  (braces)
  4:54      error    too many spaces inside braces  (braces)
  6:7       error    syntax error: expected the node content, but found '-' (syntax)
  8:41      error    too many spaces inside braces  (braces)
  9:3       error    wrong indentation: expected 0 but found 2  (indentation)
```

### Why These Are False Positives
- **Line 4**: `{{ include "..." . }}` - Valid Go template, invalid YAML
- **Line 6**: `{{-` - Valid template whitespace control, invalid YAML
- **Line 8**: Template variable reference - Valid in Helm, invalid in YAML
- **Line 9**: Indentation is correct for rendered YAML, wrong for template

## Solutions and Best Practices

### 1. Exclude Helm Templates from Standard YAML Validation

#### A. yamllint Configuration

Create `.yamllint.yml`:
```yaml
---
extends: default

# Ignore Helm template files
ignore: |
  helm/*/templates/*.yaml
  helm/*/templates/*.yml
  **/templates/*.yaml
  **/templates/*.yml

rules:
  line-length:
    max: 120
    level: warning
  document-start:
    present: false
```

#### B. Pre-commit Hook Configuration

Update `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
        args: ["--unsafe"]
        exclude: ^helm/  # Exclude Helm templates
```

#### C. VS Code Settings

Update `.vscode/settings.json`:
```json
{
  "files.associations": {
    "**/helm/**/templates/*.yaml": "helm",
    "**/helm/**/templates/*.yml": "helm"
  },
  "[helm]": {
    "yaml.validate": false
  },
  "files.watcherExclude": {
    "**/helm/**/templates/*.yaml": true
  }
}
```

### 2. Use Helm-Specific Validation Tools

#### A. Native Helm Commands

```bash
# Lint the chart (primary validation)
helm lint helm/simplenote-mcp-server/

# Test template rendering
helm template test-release helm/simplenote-mcp-server/

# Dry-run installation
helm install test-release helm/simplenote-mcp-server/ --dry-run --debug

# Validate dependencies
helm dependency update helm/simplenote-mcp-server/
```

#### B. Automated Helm Validation Script

Use the provided `scripts/validate-helm.py`:

```bash
# Validate all charts in project
python scripts/validate-helm.py

# Validate specific chart
python scripts/validate-helm.py --chart helm/simplenote-mcp-server

# Verbose output for debugging
python scripts/validate-helm.py --verbose
```

### 3. CI/CD Integration

#### A. GitHub Actions Workflow

```yaml
name: Helm Validation

on:
  push:
    paths:
      - 'helm/**'
  pull_request:
    paths:
      - 'helm/**'

jobs:
  helm-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: '3.12.0'
          
      - name: Validate Helm Charts
        run: |
          python scripts/validate-helm.py --verbose
          
      - name: Lint Charts
        run: |
          helm lint helm/simplenote-mcp-server/
```

#### B. Make Target

Add to `Makefile`:
```makefile
.PHONY: helm-validate
helm-validate:
	@echo "Validating Helm charts..."
	python scripts/validate-helm.py
	helm lint helm/simplenote-mcp-server/

.PHONY: helm-test
helm-test:
	@echo "Testing Helm chart rendering..."
	helm template test-release helm/simplenote-mcp-server/
	helm install test-release helm/simplenote-mcp-server/ --dry-run
```

### 4. IDE and Editor Configuration

#### A. VS Code Extensions

Install recommended extensions:
- **Helm Intellisense** (`Tim-Koehler.helm-intellisense`)
- **YAML** (`redhat.vscode-yaml`)
- **Kubernetes** (`ms-kubernetes-tools.vscode-kubernetes-tools`)

#### B. IntelliJ/PyCharm

Add file type associations:
```xml
<component name="FileTypeManager">
  <extensionMap>
    <mapping pattern="*/helm/*/templates/*.yaml" type="Helm" />
    <mapping pattern="*/templates/*.yaml" type="Helm" />
  </extensionMap>
</component>
```

### 5. Team Development Guidelines

#### A. Development Workflow

1. **Before committing Helm changes:**
   ```bash
   helm lint helm/simplenote-mcp-server/
   python scripts/validate-helm.py
   ```

2. **Testing template changes:**
   ```bash
   helm template test-release helm/simplenote-mcp-server/ --debug
   ```

3. **Validating with different values:**
   ```bash
   helm template test-release helm/simplenote-mcp-server/ \
     --set replicaCount=3 \
     --set image.tag=latest
   ```

#### B. Code Review Checklist

For Helm template changes:
- [ ] `helm lint` passes without errors
- [ ] Templates render correctly with default values
- [ ] Templates render correctly with common value overrides
- [ ] Security contexts are properly configured
- [ ] Resource limits are specified
- [ ] Image pull policies are set correctly

### 6. Advanced Validation Techniques

#### A. Schema Validation

Create custom schemas for your templates:
```yaml
# helm/simplenote-mcp-server/schemas/values.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "service"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository", "tag"],
      "properties": {
        "repository": {"type": "string"},
        "tag": {"type": "string"},
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"]
        }
      }
    }
  }
}
```

#### B. Security Scanning

Use tools like `helm-security` or `kubesec`:
```bash
# Install kubesec
curl -sSX GET https://api.github.com/repos/controlplaneio/kubesec/releases/latest | \
  jq -r '.assets[] | select(.name=="kubesec_linux_amd64.tar.gz") | .browser_download_url' | \
  xargs curl -sSL | tar xvz

# Scan rendered templates
helm template test-release helm/simplenote-mcp-server/ | ./kubesec scan -
```

#### C. Policy Validation

Use Open Policy Agent (OPA) with Gatekeeper policies:
```bash
# Install conftest
go install github.com/open-policy-agent/conftest@latest

# Validate against policies
helm template test-release helm/simplenote-mcp-server/ | conftest verify --policy policies/
```

## Common Helm Template Issues and Solutions

### 1. Indentation Problems

**Problem:**
```yaml
spec:
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}  # Wrong indentation
{{- end }}
```

**Solution:**
```yaml
spec:
  {{- with .Values.nodeSelector }}
  nodeSelector:
    {{- toYaml . | nindent 4 }}  # Correct indentation
  {{- end }}
```

### 2. Missing Conditionals

**Problem:**
```yaml
env:
  - name: DEBUG
    value: {{ .Values.debug }}  # Will break if debug is not set
```

**Solution:**
```yaml
env:
  {{- if .Values.debug }}
  - name: DEBUG
    value: {{ .Values.debug | quote }}
  {{- end }}
```

### 3. Unsafe Value Rendering

**Problem:**
```yaml
annotations:
  description: {{ .Values.description }}  # Unsafe for special characters
```

**Solution:**
```yaml
annotations:
  description: {{ .Values.description | quote }}  # Safe rendering
```

## Validation Results Interpretation

### Successful Validation Output

```
✓ Helm is available: v3.12.0
✓ Found: Chart.yaml
✓ Found: values.yaml
✓ Found: templates/
✓ Chart metadata valid: simplenote-mcp-server v0.1.0
✓ Helm lint passed
✓ Template rendering with default values passed
✓ Dry-run installation passed
✓ Generated 5 Kubernetes resource files
✓ Validated 5 Kubernetes resources
```

### Common Warning Interpretations

- **"Security context not configured"** - Add security contexts to values.yaml
- **"Resource limits not configured"** - Specify CPU/memory limits
- **"Dry-run installation had issues"** - Check for missing dependencies or invalid configurations

## Troubleshooting

### Chart Doesn't Lint

1. Check Chart.yaml syntax:
   ```bash
   cat helm/simplenote-mcp-server/Chart.yaml | yq eval '.'
   ```

2. Validate values.yaml:
   ```bash
   cat helm/simplenote-mcp-server/values.yaml | yq eval '.'
   ```

3. Test individual templates:
   ```bash
   helm template test-release helm/simplenote-mcp-server/ -s templates/deployment.yaml
   ```

### Templates Don't Render

1. Check for syntax errors in templates
2. Verify all referenced values exist in values.yaml
3. Test with minimal values:
   ```bash
   echo "replicaCount: 1" | helm template test-release helm/simplenote-mcp-server/ -f -
   ```

### Kubernetes Resources Invalid

1. Validate against Kubernetes schemas:
   ```bash
   helm template test-release helm/simplenote-mcp-server/ | kubectl apply --dry-run=client -f -
   ```

2. Check API versions:
   ```bash
   kubectl api-resources | grep -E "(apps|extensions)"
   ```

## Summary

### Key Points

1. **68 YAML warnings are expected** - Standard YAML parsers cannot understand Go template syntax
2. **Use Helm-specific tools** - `helm lint`, `helm template`, and custom validation scripts
3. **Exclude from standard validation** - Configure yamllint, pre-commit, and IDEs to skip Helm templates
4. **Focus on rendered output** - Validate what Kubernetes will actually receive
5. **Implement proper CI/CD** - Use Helm validation in automated pipelines

### Recommended Workflow

1. ✅ **Exclude Helm templates** from standard YAML validation
2. ✅ **Use Helm native tools** for validation (`helm lint`, `helm template`)
3. ✅ **Implement automated validation** with scripts and CI/CD
4. ✅ **Configure IDEs properly** to handle Helm template syntax
5. ✅ **Focus on security and best practices** in chart development

This approach eliminates false positive warnings while ensuring comprehensive validation of your Helm charts using the appropriate tools designed for Helm template syntax.
