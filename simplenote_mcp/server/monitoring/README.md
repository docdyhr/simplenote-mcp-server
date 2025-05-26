# Simplenote MCP Server Monitoring

A comprehensive performance monitoring system for the Simplenote MCP Server that tracks API performance, cache efficiency, tool usage, and system resources.

## Features

- **API Performance Tracking**: Monitor API call success rates, response times, and error rates
- **Cache Metrics**: Track cache hit/miss rates, size utilization, and efficiency
- **Tool Usage Statistics**: Record tool calls and execution time metrics
- **System Resource Monitoring**: Track CPU, memory, and disk usage
- **Real-time Metrics Dashboard**: View metrics in a terminal-based UI
- **Metrics Persistence**: Save metrics to JSON for historical analysis
- **Low Overhead**: Designed for minimal performance impact

## Requirements

The monitoring system has minimal requirements:

- Python 3.7+
- `psutil` library for system resource monitoring

Optional dependencies for enhanced visualization:
- `rich` for enhanced terminal UI
- `asciichartpy` for ASCII charts

Install optional dependencies with:
```bash
pip install rich asciichartpy
```

## Usage

### Basic Integration

To use the monitoring system in your code:

1. Import the necessary functions:

```python
from simplenote_mcp.server.monitoring.metrics import (
    start_metrics_collection,
    record_api_call,
    record_response_time,
    record_cache_hit,
    record_cache_miss
)
```

2. Initialize metrics collection:

```python
# Start metrics collection with 60 second interval
start_metrics_collection(interval=60)
```

3. Instrument your code:

```python
# Record API calls
record_api_call("get_note", success=True)
record_response_time("get_note", 0.123)  # time in seconds

# Record cache operations
record_cache_hit()  # When note is found in cache
record_cache_miss()  # When note must be fetched from API
```

### Viewing Metrics

Run the monitoring dashboard:

```bash
python -m simplenote_mcp.scripts.monitoring_dashboard
```

Dashboard options:
- `--refresh SECONDS`: Set refresh interval (default: 3s)
- `--rich`: Use enhanced UI if Rich library is available

### Metrics JSON Format

Metrics are saved to `simplenote_mcp/logs/metrics/performance_metrics.json` with the following structure:

```json
{
  "timestamp": "2023-08-01T12:34:56.789012",
  "server_info": {
    "start_time": "2023-08-01T12:00:00.000000",
    "uptime_seconds": 2096.789012,
    "uptime": "0d 0h 34m 56s",
    "platform": "Linux",
    "python_version": "3.10.6"
  },
  "api": {
    "calls": { "count": 125, "rate_1min": 2.8, "rate_5min": 3.2 },
    "successes": { "count": 123, "rate_1min": 2.8, "rate_5min": 3.1 },
    "failures": { "count": 2, "rate_1min": 0.0, "rate_5min": 0.1 },
    "success_rate": 98.4
  },
  "cache": {
    "hits": { "count": 1089, "rate_1min": 21.5, "rate_5min": 19.8 },
    "misses": { "count": 125, "rate_1min": 2.8, "rate_5min": 3.2 },
    "hit_rate": 89.7,
    "size": 1214,
    "max_size": 2000,
    "utilization": 60.7
  }
}
```

## API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `start_metrics_collection(interval=60)` | Start metrics collection with specified interval |
| `record_api_call(endpoint, success=True, error_type=None)` | Record an API call with outcome |
| `record_response_time(endpoint, duration)` | Record response time in seconds |
| `record_cache_hit()` | Record a cache hit |
| `record_cache_miss()` | Record a cache miss |
| `record_tool_call(tool_name)` | Record a tool call |
| `record_tool_execution_time(tool_name, duration)` | Record tool execution time |
| `update_cache_size(current_size, max_size)` | Update cache size metrics |
| `get_metrics()` | Get current metrics dictionary |

### Classes

| Class | Description |
|-------|-------------|
| `MetricsCollector` | Singleton for collecting and managing metrics |
| `PerformanceMetrics` | Container for all metrics types |
| `ApiMetrics` | API call performance metrics |
| `CacheMetrics` | Cache performance metrics |
| `ResourceMetrics` | System resource usage metrics |
| `ToolMetrics` | Tool usage metrics |

## Configuration

The monitoring system can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_COLLECTION_INTERVAL` | Collection interval in seconds | 60 |
| `METRICS_MAX_SAMPLES` | Maximum samples to keep per metric | 1000 |
| `METRICS_FILE_PATH` | Custom path for metrics JSON file | `logs/metrics/performance_metrics.json` |

## Troubleshooting

### Common Issues

1. **Dashboard shows "Metrics file not found"**
   - Ensure the server is running with monitoring enabled
   - Check file permissions for the logs directory

2. **High CPU usage when monitoring is enabled**
   - Increase the collection interval (e.g., 300 seconds)
   - Reduce the maximum samples per metric

3. **Missing metrics for specific components**
   - Ensure all components are properly instrumented
   - Check for errors in the server logs

## Contributing

To extend the monitoring system:

1. Add new metric types in `metrics.py`
2. Update the dashboard in `monitoring_dashboard.py`
3. Add tests in `test_performance_monitoring.py`
4. Update documentation

Please follow the project's code style guidelines when contributing.
