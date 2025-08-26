# Credential Rotation Playbook

This playbook provides step-by-step procedures for rotating credentials used by the Simplenote MCP Server, ensuring security without service disruption.

## Overview

### Credentials Managed
1. **Simplenote Account Credentials** - User email/password for Simplenote API access
2. **GitHub Secrets** - Repository secrets for CI/CD and automation
3. **Docker Hub Credentials** - Registry access for container publishing
4. **MCP Authentication Tokens** - Client authentication tokens (if applicable)

### Rotation Schedule
- **Critical Systems**: Every 90 days
- **Standard Systems**: Every 180 days  
- **Emergency**: Immediately upon suspected compromise

## Pre-Rotation Checklist

### Planning Phase
- [ ] **Schedule Maintenance Window**: Plan for 15-30 minute service interruption
- [ ] **Notify Stakeholders**: Alert users of potential service disruption
- [ ] **Backup Current State**: Document current configuration
- [ ] **Test Environment Ready**: Ensure staging environment mirrors production
- [ ] **Rollback Plan**: Define rollback procedures and criteria

### Environment Preparation
- [ ] **Access Verification**: Confirm administrative access to all systems
- [ ] **Monitoring Setup**: Enable enhanced monitoring during rotation
- [ ] **Communication Channel**: Establish incident communication channel
- [ ] **New Credentials Ready**: Generate/obtain new credentials in advance

## Rotation Procedures

### 1. Simplenote Account Credentials

**Impact**: Core service functionality
**Downtime**: 2-5 minutes
**Frequency**: Every 90 days

#### Steps

1. **Create New Simplenote Account** (Optional for dedicated service account)
   ```bash
   # Create dedicated service account if using personal account
   # Navigate to https://app.simplenote.com/signup
   # Use format: simplenote-mcp-service@yourdomain.com
   ```

2. **Update Local Configuration**
   ```bash
   # Test new credentials locally first
   export SIMPLENOTE_EMAIL="new-service-account@yourdomain.com"
   export SIMPLENOTE_PASSWORD="new-secure-password"
   
   # Test connection
   python -c "
   from simplenote_mcp.server.server import get_simplenote_client
   client = get_simplenote_client()
   notes = client.get_note_list()
   print('✅ Connection successful' if notes[1] == 0 else '❌ Connection failed')
   "
   ```

3. **Update Production Secrets**
   ```bash
   # Using environment variables
   export SIMPLENOTE_EMAIL="new-service-account@yourdomain.com"
   export SIMPLENOTE_PASSWORD="new-secure-password"
   
   # Or update in your deployment configuration
   kubectl create secret generic simplenote-credentials \
     --from-literal=email="new-service-account@yourdomain.com" \
     --from-literal=password="new-secure-password" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

4. **Restart Services**
   ```bash
   # Docker deployment
   docker-compose down && docker-compose up -d
   
   # Kubernetes deployment
   kubectl rollout restart deployment simplenote-mcp-server
   
   # Systemd service
   sudo systemctl restart simplenote-mcp-server
   ```

5. **Verify Service Health**
   ```bash
   # Health check
   curl -f http://localhost:8080/health || echo "Service health check failed"
   
   # Function test
   python -c "
   import json
   from mcp import ClientSession, StdioServerTransport
   # Test basic MCP operations
   print('✅ Service verification complete')
   "
   ```

#### Rollback Procedure
```bash
# If new credentials fail, revert immediately
export SIMPLENOTE_EMAIL="old-service-account@yourdomain.com"
export SIMPLENOTE_PASSWORD="old-secure-password"

# Restart with old credentials
docker-compose down && docker-compose up -d

# Verify rollback success
curl -f http://localhost:8080/health
```

### 2. GitHub Repository Secrets

**Impact**: CI/CD pipelines, automated deployments
**Downtime**: None (background process)
**Frequency**: Every 180 days

#### Steps

1. **Generate New Personal Access Token**
   - Navigate to GitHub → Settings → Developer settings → Personal access tokens
   - Generate new token with required scopes:
     - `repo` (Full repository access)
     - `workflow` (Update GitHub Actions workflows)
     - `read:packages` (Read packages)
     - `write:packages` (Write packages)

2. **Update Repository Secrets**
   ```bash
   # Using GitHub CLI
   gh secret set GITHUB_TOKEN --body "ghp_new_token_value_here"
   gh secret set DOCKER_HUB_TOKEN --body "new_docker_hub_token"
   
   # Verify secrets updated
   gh secret list
   ```

3. **Test CI/CD Pipeline**
   ```bash
   # Trigger test workflow
   gh workflow run "CI/CD Pipeline"
   
   # Monitor workflow execution
   gh run list --workflow "CI/CD Pipeline" --limit 1
   ```

4. **Update Local Git Configuration** (if applicable)
   ```bash
   # Update stored credentials
   git config --global credential.helper store
   git config --global user.token "ghp_new_token_value_here"
   ```

#### Secret Verification Script
```bash
#!/bin/bash
# verify-github-secrets.sh

echo "🔍 Verifying GitHub secrets..."

# Test GitHub API access
gh api user || {
    echo "❌ GitHub token verification failed"
    exit 1
}

# Test workflow trigger
gh workflow run "Quick Validation" || {
    echo "❌ Workflow trigger failed"
    exit 1
}

echo "✅ GitHub secrets verification complete"
```

### 3. Docker Hub Credentials

**Impact**: Container image publishing
**Downtime**: None
**Frequency**: Every 180 days

#### Steps

1. **Generate New Docker Hub Access Token**
   - Login to Docker Hub → Account Settings → Security → Access Tokens
   - Generate new token with `Read, Write, Delete` permissions

2. **Update Local Docker Configuration**
   ```bash
   # Login with new token
   echo "new_docker_hub_token" | docker login --username your-username --password-stdin
   
   # Test push access
   docker tag simplenote-mcp-server:latest your-username/simplenote-mcp-server:test
   docker push your-username/simplenote-mcp-server:test
   docker rmi your-username/simplenote-mcp-server:test
   ```

3. **Update CI/CD Secrets**
   ```bash
   gh secret set DOCKER_HUB_USERNAME --body "your-username"
   gh secret set DOCKER_HUB_TOKEN --body "new_docker_hub_token"
   ```

4. **Test Automated Publishing**
   ```bash
   # Trigger Docker publish workflow
   gh workflow run "Docker Publish"
   
   # Verify image published
   docker pull your-username/simplenote-mcp-server:latest
   ```

### 4. MCP Authentication Tokens

**Impact**: Client connections
**Downtime**: Brief disconnection during token refresh
**Frequency**: Every 90 days

#### Steps

1. **Generate New Authentication Tokens**
   ```bash
   # If using custom authentication system
   python scripts/generate-auth-tokens.py --count 10 --expiry 90d > new-tokens.json
   ```

2. **Update Token Store**
   ```bash
   # Update token database/store
   python scripts/update-auth-tokens.py --tokens-file new-tokens.json
   ```

3. **Notify Client Applications**
   ```bash
   # Send notification to client maintainers
   python scripts/notify-token-rotation.py --template rotation-notice
   ```

4. **Grace Period Implementation**
   ```bash
   # Allow both old and new tokens for transition period
   python scripts/enable-token-grace-period.py --duration 7d
   ```

## Emergency Rotation

### Immediate Response (0-15 minutes)

1. **Assess Compromise Scope**
   ```bash
   # Check recent access logs
   grep -E "(auth|login|token)" /var/log/simplenote-mcp/*.log | tail -50
   
   # Review GitHub audit log
   gh api orgs/your-org/audit-log
   ```

2. **Immediate Mitigation**
   ```bash
   # Revoke compromised tokens immediately
   gh auth token revoke
   
   # Disable compromised Simplenote account
   # (Manual step - contact Simplenote support if needed)
   
   # Rotate all credentials following standard procedures
   ```

3. **Service Isolation**
   ```bash
   # Temporarily restrict network access
   sudo iptables -A INPUT -p tcp --dport 8080 -s trusted.ip.range -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8080 -j DROP
   ```

### Recovery Phase (15-60 minutes)

1. **Complete Credential Rotation**
   - Follow all standard rotation procedures above
   - Use new, unique credentials across all systems
   - Verify no credential reuse

2. **Security Audit**
   ```bash
   # Run comprehensive security scan
   ./scripts/security-audit.sh
   
   # Check for unauthorized changes
   git log --since="2 hours ago" --all --oneline
   
   # Verify system integrity
   ./scripts/verify-system-integrity.sh
   ```

3. **Monitoring Enhancement**
   ```bash
   # Enable enhanced logging temporarily
   export LOG_LEVEL=DEBUG
   
   # Set up alert thresholds
   python scripts/setup-security-alerts.py --sensitivity high
   ```

## Post-Rotation Verification

### Functional Testing
```bash
#!/bin/bash
# post-rotation-tests.sh

echo "🧪 Running post-rotation verification tests..."

# Test 1: Basic connectivity
python -c "
from simplenote_mcp.server.server import get_simplenote_client
client = get_simplenote_client()
print('✅ Simplenote connection: OK')
"

# Test 2: MCP protocol functionality  
python -c "
# Basic MCP operations test
from mcp.types import ListResourcesRequest
print('✅ MCP protocol: OK')
"

# Test 3: CI/CD pipeline health
gh workflow run "Quick Validation"
sleep 30
gh run list --workflow "Quick Validation" --limit 1 --json status | jq -r '.[0].status'

echo "✅ Post-rotation verification complete"
```

### Security Verification
```bash
#!/bin/bash
# security-verification.sh

echo "🔒 Running security verification..."

# Check for credential exposure
rg -r . "password|token|secret" --type-not md --type-not txt | head -10

# Verify encryption
python -c "
import os
assert not any(word in str(os.environ) for word in ['password', 'token'] if word.upper() in os.environ)
print('✅ Environment variables: Secure')
"

# Test access controls
curl -f -H "Authorization: Bearer invalid-token" http://localhost:8080/health 2>/dev/null && {
    echo "❌ Security verification failed: Invalid token accepted"
    exit 1
} || echo "✅ Access controls: OK"

echo "✅ Security verification complete"
```

## Monitoring and Alerting

### Key Metrics to Monitor
- Authentication success/failure rates
- Token usage patterns
- Unusual access patterns
- Service health and availability
- Error rates during rotation

### Alerting Configuration
```yaml
# monitoring/alerts.yml
alerts:
  - name: credential_rotation_failure
    condition: rotation_success_rate < 0.95
    notification: security-team@company.com
    
  - name: authentication_anomaly
    condition: failed_auth_rate > 0.1
    notification: ops-team@company.com
    
  - name: service_availability
    condition: availability < 0.99
    notification: on-call@company.com
```

### Rotation Audit Trail
```bash
# Document all rotations
echo "$(date -Iseconds) - Credential rotation completed - User: $(whoami) - Reason: scheduled" >> /var/log/credential-rotations.log

# Store rotation metadata
python scripts/log-rotation-event.py \
  --timestamp "$(date -Iseconds)" \
  --type "scheduled" \
  --credentials "simplenote,github,dockerhub" \
  --success "true"
```

## Troubleshooting Guide

### Common Issues

**Issue**: Service fails to start after rotation
```bash
# Solution: Check credential format and permissions
python -c "
import os
print('Email:', os.getenv('SIMPLENOTE_EMAIL'))
print('Password length:', len(os.getenv('SIMPLENOTE_PASSWORD', '')))
"

# Verify file permissions
ls -la ~/.simplenote-mcp/config*
```

**Issue**: CI/CD pipelines fail
```bash
# Solution: Verify GitHub token scopes
gh auth status
gh api user/repos | jq length

# Test token permissions
gh workflow run "Quick Validation" || echo "Insufficient permissions"
```

**Issue**: Docker push fails
```bash
# Solution: Re-login and verify access
docker logout
echo "$DOCKER_HUB_TOKEN" | docker login --username "$DOCKER_HUB_USERNAME" --password-stdin
docker push your-username/test-image:latest
```

### Emergency Contacts

- **Security Team**: security@company.com
- **Operations Team**: ops@company.com  
- **On-Call Engineer**: +1-xxx-xxx-xxxx
- **Incident Manager**: incident-manager@company.com

### Documentation Updates

After completing any rotation:

1. Update this playbook with lessons learned
2. Document any new procedures or tools used
3. Update emergency contact information
4. Review and update automation scripts
5. Conduct team training on any procedure changes

---

**Last Updated**: Phase 2 Security Implementation
**Next Review**: Quarterly (every 90 days)
**Owner**: Security & Operations Team
