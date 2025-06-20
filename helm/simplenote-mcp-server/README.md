# Simplenote MCP Server Helm Chart

This Helm chart deploys the Simplenote MCP Server on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+

## Installing the Chart

To install the chart with the release name `my-simplenote-mcp`:

```bash
helm install my-simplenote-mcp ./helm/simplenote-mcp-server
```

Or from a Helm repository (when published):

```bash
helm repo add simplenote-mcp https://docdyhr.github.io/simplenote-mcp-server
helm install my-simplenote-mcp simplenote-mcp/simplenote-mcp-server
```

## Configuration

The following table lists the configurable parameters and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `docdyhr/simplenote-mcp-server` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `simplenote.email` | Simplenote email | `""` |
| `simplenote.password` | Simplenote password | `""` |
| `simplenote.syncIntervalSeconds` | Sync interval | `120` |
| `simplenote.logLevel` | Log level | `INFO` |

## Setting Simplenote Credentials

### Option 1: Using values.yaml

```yaml
simplenote:
  email: "your-email@example.com"
  password: "your-password"
```

### Option 2: Using command line

```bash
helm install my-simplenote-mcp ./helm/simplenote-mcp-server \
  --set simplenote.email="your-email@example.com" \
  --set simplenote.password="your-password"
```

### Option 3: Using External Secrets

Enable external secrets and configure your secret store:

```yaml
externalSecrets:
  enabled: true
  secretStore:
    name: vault-backend
    kind: SecretStore
```

## Security Considerations

- The chart runs as a non-root user (UID 1000)
- Read-only root filesystem
- Dropped all capabilities
- No privilege escalation allowed
- Resource limits configured

## Monitoring

The chart includes:
- Liveness and readiness probes
- Resource limits and requests
- Optional horizontal pod autoscaling

## Examples

### Basic Installation

```bash
helm install simplenote-mcp ./helm/simplenote-mcp-server \
  --set simplenote.email="test@example.com" \
  --set simplenote.password="secret"
```

### Production Installation with HPA

```bash
helm install simplenote-mcp ./helm/simplenote-mcp-server \
  --set simplenote.email="prod@example.com" \
  --set simplenote.password="secret" \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=10
```

### Installation with Ingress

```bash
helm install simplenote-mcp ./helm/simplenote-mcp-server \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host="simplenote-mcp.example.com"
```

## Uninstalling the Chart

```bash
helm uninstall my-simplenote-mcp
```
