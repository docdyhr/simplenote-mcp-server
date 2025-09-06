# Disabled Workflows

These workflows have been disabled to reduce CI/CD complexity and queue congestion.
They can be re-enabled if needed by moving them back to the parent directory.

## Disabled Workflows:

1. **ci-original-backup.yml** - Backup of original CI, replaced by optimized version
2. **ci-optimized.yml** - Template kept for reference, main ci.yml is now optimized
3. **debug-ci.yml** - Debugging workflow, enable only when needed
4. **test-notifications.yml** - Test workflow for notifications
5. **quick-validation.yml** - Redundant with main CI validation job
6. **performance.yml** - Can be run on-demand instead of automatically

## To Re-enable:
Move the workflow file back to `.github/workflows/` directory.

## To Run Manually:
Most of these can be triggered manually via workflow_dispatch if needed.