# Docker Hub Overview Fix Guide

## Problem

The Docker Hub repository at https://hub.docker.com/r/docdyhr/simplenote-mcp-server shows no overview/description because Docker Hub no longer automatically syncs README files from GitHub repositories.

## Root Cause

- **Discontinued Feature**: Docker Hub stopped automatically pulling README.md files from linked GitHub repositories
- **Manual Setup Required**: Repository descriptions must be manually set or automated through API calls
- **Missing Workflow Step**: The current CI/CD pipeline doesn't include README synchronization

## Solutions

### 🚀 Solution 1: Automated GitHub Actions (Recommended)

The most reliable solution is to add automatic README synchronization to your GitHub Actions workflow.

#### Implementation

The workflow has been updated to include the `update-docker-hub-description` job that:

1. **Triggers after successful image build**
2. **Uses dedicated Docker README** (`DOCKER_README.md`)
3. **Updates both full description and short description**
4. **Runs only on non-PR events** (push to main, tags, manual dispatch)

#### Workflow Configuration

```yaml
update-docker-hub-description:
  needs: build-and-push
  runs-on: ubuntu-latest
  timeout-minutes: 5
  if: github.event_name != 'pull_request'

  steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Update Docker Hub repository description
      uses: peter-evans/dockerhub-description@v4
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_TOKEN }}
        repository: ${{ env.IMAGE_NAME }}
        readme-filepath: ./DOCKER_README.md
        short-description: "A Model Context Protocol (MCP) server that provides seamless integration with Simplenote for note management and search capabilities."
```

#### Required Secrets

Ensure these secrets are configured in your GitHub repository:

- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_TOKEN`: Docker Hub access token (not password)

#### Getting Docker Hub Access Token

1. Go to [Docker Hub Security Settings](https://hub.docker.com/settings/security)
2. Click "New Access Token"
3. Name: `GitHub Actions`
4. Permissions: `Read, Write, Delete`
5. Copy the generated token
6. Add to GitHub Secrets as `DOCKER_TOKEN`

### 📝 Solution 2: Manual Update Script

For immediate fix or one-time updates, use the provided Python script.

#### Using the Shell Script (Easiest)

```bash
# Set environment variables
export DOCKER_USERNAME=your-username
export DOCKER_TOKEN=your-access-token

# Run the update script
./scripts/update-dockerhub-readme.sh
```

#### Using the Python Script Directly

```bash
# Install requirements
pip install requests

# Set environment variables
export DOCKER_USERNAME=your-username
export DOCKER_TOKEN=your-access-token
export DOCKER_REPOSITORY=docdyhr/simplenote-mcp-server
export README_FILE=DOCKER_README.md

# Run the script
python scripts/update-dockerhub-readme.py
```

#### Script Features

- ✅ **Validation**: Checks credentials and file existence
- ✅ **Error Handling**: Comprehensive error reporting
- ✅ **Configuration**: Environment variable configuration
- ✅ **Safety**: Confirmation prompts before updates
- ✅ **Feedback**: Detailed progress and status reporting

### 🛠️ Solution 3: Docker CLI Plugin

For developers who prefer CLI tools, use the `docker-pushrm` plugin.

#### Installation

```bash
# Install docker-pushrm plugin
mkdir -p ~/.docker/cli-plugins
curl -fsSL https://github.com/christian-korneck/docker-pushrm/releases/latest/download/docker-pushrm_linux_amd64 -o ~/.docker/cli-plugins/docker-pushrm
chmod +x ~/.docker/cli-plugins/docker-pushrm
```

#### Usage

```bash
# Update README from current directory
docker pushrm docdyhr/simplenote-mcp-server

# Use specific README file
docker pushrm docdyhr/simplenote-mcp-server --file DOCKER_README.md

# Include short description
docker pushrm docdyhr/simplenote-mcp-server --short "MCP server for Simplenote integration"
```

### 🌐 Solution 4: Manual Web Interface

As a last resort, manually update through Docker Hub web interface.

#### Steps

1. Go to [Docker Hub Repository](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
2. Click "Edit" on the repository page
3. Copy content from `DOCKER_README.md`
4. Paste into the "Full description" field
5. Update "Short description" field
6. Click "Update"

## Implementation Status

### ✅ Completed

- [x] Created Docker-specific README (`DOCKER_README.md`)
- [x] Updated GitHub Actions workflow with README sync
- [x] Created manual update scripts (Python + Shell)
- [x] Added comprehensive error handling and validation
- [x] Configured proper secrets management

### 📋 Required Actions

#### For Repository Owner

1. **Verify Secrets**: Ensure `DOCKER_USERNAME` and `DOCKER_TOKEN` are set in GitHub repository secrets
2. **Test Workflow**: Push a commit to main branch to trigger automatic README sync
3. **Verify Result**: Check Docker Hub repository for updated overview

#### For Contributors

1. **Update Docker README**: Modify `DOCKER_README.md` for Docker Hub specific content
2. **Test Scripts**: Use manual scripts for immediate updates if needed
3. **Monitor Workflow**: Ensure README sync job passes in CI/CD pipeline

## File Structure

```
simplenote-mcp-server/
├── DOCKER_README.md                          # Docker Hub specific README
├── README.md                                 # GitHub repository README
├── .github/workflows/docker-publish.yml      # Updated with README sync
├── scripts/
│   ├── update-dockerhub-readme.py           # Python update script
│   └── update-dockerhub-readme.sh           # Shell wrapper script
└── docs/
    └── docker-hub-overview-fix.md           # This guide
```

## Expected Results

### Before Fix
- ❌ Empty overview section on Docker Hub
- ❌ No description or usage instructions
- ❌ Poor discoverability and user experience

### After Fix
- ✅ Comprehensive overview with usage examples
- ✅ Detailed installation and configuration instructions
- ✅ Security information and best practices
- ✅ Troubleshooting guide and support links
- ✅ Professional appearance with badges and formatting

## Verification

### Check Automated Sync

1. **Trigger Workflow**: Push to main branch or create a tag
2. **Monitor Actions**: Watch GitHub Actions for `update-docker-hub-description` job
3. **Verify Success**: Ensure job completes successfully
4. **Check Docker Hub**: Visit repository page and verify overview is populated

### Check Manual Update

1. **Run Script**: Execute manual update script
2. **Verify Output**: Ensure script reports success
3. **Check Docker Hub**: Verify changes appear on repository page

### Validation Commands

```bash
# Check if workflow job exists
grep -A 10 "update-docker-hub-description" .github/workflows/docker-publish.yml

# Verify Docker README exists
ls -la DOCKER_README.md

# Test manual script (dry run)
./scripts/update-dockerhub-readme.sh --check

# Check Docker Hub API response
curl -s "https://hub.docker.com/v2/repositories/docdyhr/simplenote-mcp-server/" | jq '.description'
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

**Symptoms**: `401 Unauthorized` or `403 Forbidden` errors

**Solutions**:
- Verify `DOCKER_USERNAME` is correct
- Ensure `DOCKER_TOKEN` is an access token, not password
- Check token permissions include `Read, Write` for repositories
- Regenerate token if older than 1 year

#### 2. Workflow Failures

**Symptoms**: GitHub Actions job fails

**Solutions**:
- Check secrets are configured correctly in repository settings
- Verify repository name matches `IMAGE_NAME` environment variable
- Ensure workflow has proper permissions for secrets access

#### 3. README Not Updating

**Symptoms**: Script succeeds but overview doesn't change

**Solutions**:
- Wait 5-10 minutes for Docker Hub cache refresh
- Check if README content is valid markdown
- Verify file encoding is UTF-8
- Clear browser cache and refresh Docker Hub page

#### 4. Script Permission Errors

**Symptoms**: `Permission denied` when running shell script

**Solutions**:
```bash
# Make script executable
chmod +x scripts/update-dockerhub-readme.sh

# Run with explicit shell
bash scripts/update-dockerhub-readme.sh
```

#### 5. Python Dependencies

**Symptoms**: `ModuleNotFoundError: No module named 'requests'`

**Solutions**:
```bash
# Install requests module
pip install requests

# Use virtual environment
python -m venv venv
source venv/bin/activate
pip install requests
```

### Debug Commands

```bash
# Check current Docker Hub description
curl -s "https://hub.docker.com/v2/repositories/docdyhr/simplenote-mcp-server/" | jq '.description'

# Validate README content
python -c "
import sys
with open('DOCKER_README.md', 'r') as f:
    content = f.read()
    print(f'README length: {len(content)} characters')
    print(f'Valid UTF-8: {content.encode(\"utf-8\")}' if content else 'Empty file')
"

# Test Docker Hub API authentication
curl -X POST "https://hub.docker.com/v2/users/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"'$DOCKER_USERNAME'","password":"'$DOCKER_TOKEN'"}'
```

## Monitoring

### Automated Monitoring

The GitHub Actions workflow includes monitoring for the README sync job:

- **Job Status**: Tracked in workflow notifications
- **Failure Alerts**: Included in notification system
- **Success Confirmation**: Logs successful updates

### Manual Verification

Set up periodic checks:

```bash
# Create a simple monitoring script
cat > check-docker-hub-readme.sh << 'EOF'
#!/bin/bash
DESCRIPTION=$(curl -s "https://hub.docker.com/v2/repositories/docdyhr/simplenote-mcp-server/" | jq -r '.description // "EMPTY"')
if [[ "$DESCRIPTION" == "EMPTY" || "$DESCRIPTION" == "null" ]]; then
    echo "❌ Docker Hub overview is empty"
    exit 1
else
    echo "✅ Docker Hub overview is populated"
    echo "Description: $DESCRIPTION"
    exit 0
fi
EOF

chmod +x check-docker-hub-readme.sh
./check-docker-hub-readme.sh
```

## Maintenance

### Regular Updates

1. **Keep README Current**: Update `DOCKER_README.md` when features change
2. **Monitor Workflow**: Ensure README sync continues working
3. **Update Scripts**: Keep manual scripts up to date with API changes
4. **Refresh Tokens**: Rotate Docker Hub access tokens annually

### Best Practices

1. **Dedicated Docker README**: Use separate `DOCKER_README.md` for Docker Hub
2. **Container-Specific Content**: Focus on Docker usage, not general project info
3. **Keep It Concise**: Docker Hub users want quick start information
4. **Include Examples**: Provide copy-paste Docker commands
5. **Security Information**: Highlight security features and best practices

## Support

If you continue experiencing issues:

1. **Check GitHub Actions**: Review workflow logs for detailed error messages
2. **Test Scripts Locally**: Run manual scripts to isolate the problem
3. **Verify Docker Hub**: Ensure repository exists and is accessible
4. **Contact Support**: Create GitHub issue with error details and logs

## Success Metrics

### Key Indicators

- ✅ Docker Hub overview populated with comprehensive description
- ✅ GitHub Actions workflow includes successful README sync job
- ✅ Manual update scripts work reliably
- ✅ Repository description automatically updates with each release

### Verification Checklist

- [ ] Docker Hub overview shows comprehensive description
- [ ] Installation instructions are clear and accurate
- [ ] Security information is prominently displayed
- [ ] Usage examples are provided
- [ ] Troubleshooting guide is available
- [ ] Links to documentation work correctly
- [ ] Badges display current status
- [ ] Short description is concise and descriptive

---

**Last Updated**: 2025-07-03  
**Status**: ✅ Implementation Complete  
**Next Review**: Monthly or on major releases
