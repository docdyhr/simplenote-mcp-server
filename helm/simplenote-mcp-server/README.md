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
| `mcpHttp.authToken` | Bearer token for the MCP HTTP transport; required if `MCP_HTTP_HOST` is non-loopback | `""` |
| `monitoring.port` | Port for the separate health/metrics endpoint | `8080` |
| `monitoring.authToken` | Bearer token for the health/metrics endpoint; only needed if `HTTP_HOST` is overridden to non-loopback | `""` |

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
- The health/metrics endpoint (`monitoring.port`, default `HTTP_HOST=127.0.0.1`) is not exposed via
  the Service and isn't reachable outside the pod by default. Liveness/readiness probes run as
  `exec` checks from inside the container rather than `httpGet`, since kubelet's `httpGet` connects
  to the Pod IP, not the pod's own loopback. If you override `HTTP_HOST` to a non-loopback address,
  the server refuses to start unless `monitoring.authToken` is also set — loopback callers (the
  probes above) stay trusted either way.

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
