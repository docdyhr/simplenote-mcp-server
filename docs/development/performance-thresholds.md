# Performance Threshold Monitoring and Alerting

This document describes the performance threshold monitoring system implemented for the Simplenote MCP Server. The system provides automated monitoring of key performance metrics and triggers alerts when performance degrades beyond acceptable levels.

## Overview

The performance threshold system monitors critical server metrics and provides two types of monitoring:

1. **Absolute Threshold Monitoring**: Alerts when metrics exceed predefined warning or critical levels
2. **Regression Detection**: Alerts when performance degrades significantly compared to historical baselines

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Performance Monitoring                    │
├─────────────────────────────────────────────────────────────┤
│  MetricsCollector  │  PerformanceThresholdMonitor          │
│  ├─ Resource Usage │  ├─ Threshold Definitions              │
│  ├─ API Metrics    │  ├─ Violation Detection                │
│  ├─ Cache Metrics  │  ├─ Regression Analysis                │
│  └─ Tool Metrics   │  └─ Alert Generation                   │
└─────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────┐
                        │  Alerting       │
                        │  System         │
                        ├─────────────────┤
                        │ Security Alerts │
                        │ File Logging    │
                        │ Email/Webhook   │
                        └─────────────────┘
```

## Key Components

### PerformanceThreshold

Defines individual performance thresholds with:
- **Metric identification**: JSON path to extract values from metrics
- **Warning/Critical levels**: Threshold values for different alert severities
- **Regression detection**: Baseline comparison for performance degradation
- **Consecutive violations**: Number of consecutive violations required before alerting

### PerformanceThresholdMonitor

Monitors all thresholds and:
- Extracts metric values using JSON path notation
- Tracks baseline history for regression detection
- Evaluates thresholds against current metrics
- Generates alert violations
- Implements alert cooldown to prevent spam

### Integration Points

- **MetricsCollector**: Automatically checks thresholds during metrics collection
- **HTTP Endpoints**: Provides `/thresholds` endpoint for status monitoring
- **Alerting System**: Triggers security alerts for threshold violations

## Default Thresholds

### API Performance
- **P95 Response Time**: Warning > 1s, Critical > 3s
- **P99 Response Time**: Warning > 2s, Critical > 5s  
- **API Success Rate**: Warning < 95%, Critical < 90%

### Cache Performance
- **Cache Hit Rate**: Warning < 50%, Critical < 25%
- **Cache Efficacy Score**: Warning < 60, Critical < 30

### Resource Usage
- **CPU Usage**: Warning > 80%, Critical > 95%
- **Memory Usage**: Warning > 80%, Critical > 90%

### Tool Performance
- **Tool Execution Time P95**: Warning > 2s, Critical > 5s

### Throughput (Optional)
- **API Request Rate**: Warning < 1 req/min, Critical < 0.1 req/min (disabled by default)

## Configuration

### Environment Variables

Threshold monitoring uses existing configuration:
- `METRICS_COLLECTION_INTERVAL`: How often to check thresholds (default: 60s)
- `ENABLE_HTTP_ENDPOINT`: Enable `/thresholds` endpoint access
- Alert configuration through security alerting system

### Threshold Customization

Thresholds can be customized by modifying `DEFAULT_THRESHOLDS` in `thresholds.py`:

```python
PerformanceThreshold(
    name="Custom API Response Time",
    metric_type=MetricType.RESPONSE_TIME,
    metric_path="api.response_times.custom_endpoint.p95_time",
    operator=ThresholdOperator.GREATER_THAN,
    warning_value=0.5,  # 500ms
    critical_value=1.0,  # 1s
    unit="s",
    description="Custom endpoint response time",
    regression_multiplier=1.3,  # 30% increase triggers regression
    consecutive_violations=3,  # Alert after 3 consecutive violations
)
```

## Metric Path Notation

The system uses JSON path notation to extract values from metrics:

### Simple Paths
- `cache.hit_rate` → Extract hit rate from cache metrics
- `resources.cpu.current` → Extract current CPU usage

### Wildcard Aggregation
- `api.response_times.*.p95_time` → Max P95 across all API endpoints
- `tools.execution_times.*.avg_time` → Average across all tools

Aggregation rules:
- **Response/Execution Times**: Maximum (worst case)
- **Hit/Success Rates**: Minimum (worst case)
- **Other metrics**: Average

## Regression Detection

Regression detection compares current metrics against historical baselines:

### Baseline Calculation
- Uses median of values from first half of baseline window
- Requires minimum 3 data points for stability
- Default baseline window: 60 minutes

### Regression Triggers
- **Response Times/Resource Usage**: Increase by regression multiplier (e.g., 1.5x)
- **Hit Rates/Success Rates**: Decrease by regression multiplier

### Alert Severity
- **Medium**: 1.5x - 2.0x change
- **High**: > 2.0x change

## HTTP API

### GET /thresholds

Returns comprehensive threshold status:

```json
{
  "total_thresholds": 9,
  "enabled_thresholds": 8,
  "thresholds": [
    {
      "name": "API P95 Response Time",
      "enabled": true,
      "metric_type": "response_time",
      "current_value": 0.856,
      "baseline_value": 0.723,
      "warning_threshold": 1.0,
      "critical_threshold": 3.0,
      "unit": "s",
      "status": "healthy",
      "severity": null,
      "message": "",
      "consecutive_warnings": 0,
      "consecutive_criticals": 0
    }
  ]
}
```

### Status Values
- `healthy`: Metric within acceptable range
- `violation`: Threshold violation detected
- `error`: Unable to retrieve metric value

## Alert Integration

### Alert Types
All threshold violations use `AlertType.SECURITY_THRESHOLD_EXCEEDED` with:
- **Severity**: Based on threshold level (MEDIUM for warning, CRITICAL for critical)
- **Context**: Includes current value, thresholds, and metric information
- **Cooldown**: 5-minute cooldown between identical alerts

### Alert Destinations
- **File Logging**: JSON alerts in security log files
- **Email/Webhook**: For HIGH and CRITICAL severity alerts (if configured)
- **HTTP Health Checks**: Threshold violations affect health status

## Operational Procedures

### Monitoring Setup
1. **Enable HTTP endpoints** for threshold monitoring access
2. **Configure alert destinations** (email, webhook, file logging)
3. **Set up external monitoring** to query `/thresholds` endpoint
4. **Tune thresholds** based on observed baseline performance

### Responding to Alerts

#### API Performance Degradation
1. Check system resource usage (CPU, memory, disk)
2. Review recent code changes or deployments
3. Analyze API endpoint usage patterns
4. Check Simplenote API status and connectivity

#### Cache Performance Issues
1. Review cache configuration and size limits
2. Check for changes in data access patterns
3. Analyze cache eviction rates and memory usage
4. Consider cache warming strategies

#### Resource Exhaustion
1. Check for memory leaks or runaway processes
2. Review system load and concurrent connections
3. Analyze disk I/O and available space
4. Consider scaling or optimization needs

### Threshold Tuning
1. **Monitor baseline performance** for 1-2 weeks
2. **Analyze percentile distributions** for realistic thresholds
3. **Adjust warning levels** to catch issues early without noise
4. **Set critical levels** for genuine outage conditions
5. **Test regression sensitivity** with controlled load changes

## Development and Testing

### Adding New Thresholds
1. Define the threshold in `DEFAULT_THRESHOLDS`
2. Add corresponding metric collection if needed
3. Test threshold evaluation with mock data
4. Update documentation and HTTP endpoint lists

### Testing Framework
- **Unit tests**: `test_performance_thresholds.py`
- **Mock metrics**: Test threshold evaluation without live data
- **Integration tests**: Verify alerting integration
- **Load testing**: Validate thresholds under real load conditions

### Debugging Tools
- **Threshold Status Endpoint**: Real-time threshold status
- **Metrics Logs**: Historical performance data
- **Alert History**: Review past violations and patterns
- **Manual Threshold Checks**: `check_performance_thresholds()` function

## Best Practices

### Threshold Design
- **Set warning levels** at 80% of problem thresholds
- **Use consecutive violations** to avoid transient alert noise
- **Include regression detection** for gradual performance degradation
- **Provide clear alert messages** with actionable information

### Operational Monitoring  
- **Monitor threshold effectiveness** - adjust based on false positive/negative rates
- **Review alert patterns** regularly to identify systemic issues
- **Maintain baseline history** for accurate regression detection
- **Document threshold rationale** for future maintenance

### Performance Impact
- **Threshold checking** runs every metrics collection interval (60s default)
- **Memory usage** is bounded by sample limits (1000 samples max)
- **Alert cooldowns** prevent excessive notification volume
- **Async processing** prevents blocking metrics collection

## Troubleshooting

### Common Issues

#### No Alerts Despite Performance Problems
- Check if thresholds are enabled
- Verify metric paths are correct
- Review consecutive violation requirements
- Check alert cooldown periods

#### Too Many False Positive Alerts  
- Increase consecutive violation counts
- Adjust threshold levels based on actual baselines
- Review metric extraction logic for accuracy
- Consider longer baseline windows for regression detection

#### Missing Metrics in Threshold Evaluation
- Verify metrics are being collected properly
- Check JSON path syntax for metric extraction
- Review wildcard aggregation behavior
- Ensure required metrics exist in output

#### Regression Detection Not Working
- Check baseline history accumulation
- Verify sufficient data points (minimum 3)
- Review baseline window configuration
- Test regression multiplier sensitivity

### Diagnostic Commands

```bash
# Check current threshold status
curl http://localhost:8080/thresholds

# View metrics being monitored
curl http://localhost:8080/metrics

# Check alert log files
tail -f simplenote_mcp/logs/security_alerts.json

# Run threshold tests
python -m pytest simplenote_mcp/tests/test_performance_thresholds.py -v
```

## Future Enhancements

### Planned Improvements
- **Dynamic threshold adjustment** based on historical patterns
- **Anomaly detection** using statistical analysis
- **Custom alerting rules** via configuration files
- **Integration with external monitoring systems** (Prometheus, Grafana)
- **Performance trend analysis** and forecasting

### Metric Expansion
- **Network latency thresholds** for external API calls
- **Concurrent connection limits** monitoring
- **Database query performance** (if applicable)
- **Custom business metrics** threshold support

This threshold system provides a robust foundation for proactive performance monitoring and helps ensure the Simplenote MCP Server maintains optimal performance characteristics under various load conditions.
