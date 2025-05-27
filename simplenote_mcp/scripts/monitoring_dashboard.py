#!/usr/bin/env python
"""
Monitoring Dashboard for Simplenote MCP Server

A terminal-based dashboard that displays real-time metrics from the Simplenote MCP Server
including API performance, cache statistics, tool usage, and system resources.

Usage:
    python monitoring_dashboard.py [--refresh SECONDS]

Options:
    --refresh SECONDS    Refresh interval in seconds (default: 3)
"""

import argparse
import curses
import json
import locale
import sys
import time
from pathlib import Path
from typing import Any

# Try to import optional dependencies for enhanced visualization
try:
    import asciichartpy

    HAS_ASCII_CHART = True
except ImportError:
    HAS_ASCII_CHART = False

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table

    # These imports are not used directly in the code currently
    # from rich.layout import Layout
    # from rich.panel import Panel

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Set up paths
SCRIPT_DIR = Path(__file__).parent
METRICS_DIR = SCRIPT_DIR.parent / "logs" / "metrics"
METRICS_FILE = METRICS_DIR / "performance_metrics.json"

# Initialize locale for number formatting
locale.setlocale(locale.LC_ALL, "")


# Historical data storage
class MetricsHistory:
    """Stores historical metrics data for charting."""

    def __init__(self, max_points: int = 20):
        self.max_points = max_points
        self.api_response_times: list[float] = []
        self.cache_hit_rates: list[float] = []
        self.cpu_usage: list[float] = []
        self.memory_usage: list[float] = []
        self.tool_calls: dict[str, int] = {}

    def update(self, metrics: dict[str, Any]) -> None:
        """Update historical data with new metrics."""
        # API response times (average across all endpoints)
        if metrics.get("api", {}).get("response_times"):
            endpoints = metrics["api"]["response_times"]
            if endpoints:
                avg_times = [data.get("avg_time", 0) for data in endpoints.values()]
                if avg_times:
                    self.api_response_times.append(sum(avg_times) / len(avg_times))
                    self.api_response_times = self.api_response_times[
                        -self.max_points :
                    ]

        # Cache hit rate
        if "cache" in metrics and "hit_rate" in metrics["cache"]:
            self.cache_hit_rates.append(metrics["cache"]["hit_rate"])
            self.cache_hit_rates = self.cache_hit_rates[-self.max_points :]

        # CPU and memory usage
        if "resources" in metrics:
            if (
                "cpu" in metrics["resources"]
                and "current" in metrics["resources"]["cpu"]
            ):
                self.cpu_usage.append(metrics["resources"]["cpu"]["current"])
                self.cpu_usage = self.cpu_usage[-self.max_points :]

            if (
                "memory" in metrics["resources"]
                and "current" in metrics["resources"]["memory"]
            ):
                self.memory_usage.append(metrics["resources"]["memory"]["current"])
                self.memory_usage = self.memory_usage[-self.max_points :]

        # Tool calls
        if "tools" in metrics and "tool_calls" in metrics["tools"]:
            for tool, data in metrics["tools"]["tool_calls"].items():
                self.tool_calls[tool] = data.get("count", 0)


def load_metrics() -> dict[str, Any]:
    """Load the most recent metrics from the metrics file."""
    try:
        if not METRICS_FILE.exists():
            return {"error": "Metrics file not found"}

        with open(METRICS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to load metrics: {str(e)}"}


def format_number(number: float) -> str:
    """Format a number with thousands separator."""
    return locale.format_string("%.2f", number, grouping=True)


def format_percent(number: float) -> str:
    """Format a number as a percentage."""
    return locale.format_string("%.1f%%", number, grouping=True)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes, seconds = divmod(seconds, 60)
        return f"{int(minutes)}m {int(seconds)}s"


def create_ascii_chart(data: list[float], height: int = 10, width: int = 40) -> str:
    """Create an ASCII chart from the data."""
    if not HAS_ASCII_CHART or not data:
        return "No chart data available"

    # Pad data to width if needed
    if len(data) < width:
        data = [data[0]] * (width - len(data)) + data
    else:
        data = data[-width:]

    config = {"height": height, "format": lambda x: format_number(x)}

    return asciichartpy.plot(data, config)


def display_terminal_ui(
    stdscr, metrics_history: MetricsHistory, refresh_interval: int
) -> None:
    """Display a curses-based terminal UI."""
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    GREEN = curses.color_pair(1)
    YELLOW = curses.color_pair(2)
    RED = curses.color_pair(3)
    CYAN = curses.color_pair(4)
    # MAGENTA is not used in the current code
    # MAGENTA = curses.color_pair(5)

    try:
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Load current metrics
            metrics = load_metrics()
            if "error" in metrics:
                stdscr.addstr(0, 0, f"Error: {metrics['error']}")
                stdscr.refresh()
                time.sleep(refresh_interval)
                continue

            # Update history
            metrics_history.update(metrics)

            # Display header
            timestamp = metrics.get("timestamp", "Unknown")
            header = f"Simplenote MCP Server Monitoring - {timestamp}"
            stdscr.addstr(0, (width - len(header)) // 2, header, curses.A_BOLD)

            # Display server info
            server_info = metrics.get("server_info", {})
            uptime = server_info.get("uptime", "Unknown")
            stdscr.addstr(1, 0, f"Uptime: {uptime} | Refresh: {refresh_interval}s")

            # Row positions
            row = 3

            # API Section
            api_data = metrics.get("api", {})
            stdscr.addstr(row, 0, "API Performance", curses.A_BOLD | CYAN)
            row += 1

            calls = api_data.get("calls", {}).get("count", 0)
            success_rate = api_data.get("success_rate", 0)
            stdscr.addstr(row, 0, f"Total Calls: {calls} | Success Rate: ")
            color = (
                GREEN if success_rate > 95 else (YELLOW if success_rate > 80 else RED)
            )
            stdscr.addstr(f"{format_percent(success_rate)}", color)
            row += 1

            if "response_times" in api_data and api_data["response_times"]:
                # Show top 3 endpoints by usage
                stdscr.addstr(row, 0, "Top Endpoints:")
                row += 1

                endpoints = list(api_data["response_times"].items())
                endpoints.sort(key=lambda x: x[1].get("count", 0), reverse=True)
                for _i, (endpoint, data) in enumerate(endpoints[:3]):
                    count = data.get("count", 0)
                    avg_time = data.get("avg_time", 0)
                    p95_time = data.get("p95_time", 0)

                    stdscr.addstr(row, 2, f"{endpoint}: ")
                    stdscr.addstr(
                        f"{count} calls, Avg: {format_duration(avg_time)}, P95: {format_duration(p95_time)}"
                    )
                    row += 1

            # Cache Section
            row += 1
            cache_data = metrics.get("cache", {})
            stdscr.addstr(row, 0, "Cache Performance", curses.A_BOLD | CYAN)
            row += 1

            hit_rate = cache_data.get("hit_rate", 0)
            hits = cache_data.get("hits", {}).get("count", 0)
            misses = cache_data.get("misses", {}).get("count", 0)
            size = cache_data.get("size", 0)
            max_size = cache_data.get("max_size", 0)
            utilization = cache_data.get("utilization", 0)

            stdscr.addstr(row, 0, "Hit Rate: ")
            color = GREEN if hit_rate > 90 else (YELLOW if hit_rate > 70 else RED)
            stdscr.addstr(f"{format_percent(hit_rate)}", color)
            stdscr.addstr(f" ({hits} hits, {misses} misses)")
            row += 1

            stdscr.addstr(
                row,
                0,
                f"Size: {size} / {max_size} notes | Utilization: {format_percent(utilization)}",
            )
            row += 1

            # Resource Section
            row += 1
            resource_data = metrics.get("resources", {})
            stdscr.addstr(row, 0, "System Resources", curses.A_BOLD | CYAN)
            row += 1

            cpu_current = resource_data.get("cpu", {}).get("current", 0)
            cpu_max = resource_data.get("cpu", {}).get("max", 0)
            mem_current = resource_data.get("memory", {}).get("current", 0)
            mem_max = resource_data.get("memory", {}).get("max", 0)
            disk_usage = resource_data.get("disk", {}).get("usage_percent", 0)

            cpu_color = (
                GREEN if cpu_current < 50 else (YELLOW if cpu_current < 80 else RED)
            )
            mem_color = (
                GREEN if mem_current < 60 else (YELLOW if mem_current < 85 else RED)
            )
            disk_color = (
                GREEN if disk_usage < 70 else (YELLOW if disk_usage < 90 else RED)
            )

            stdscr.addstr(row, 0, "CPU: ")
            stdscr.addstr(f"{format_percent(cpu_current)}", cpu_color)
            stdscr.addstr(f" (max: {format_percent(cpu_max)})")
            row += 1

            stdscr.addstr(row, 0, "Memory: ")
            stdscr.addstr(f"{format_percent(mem_current)}", mem_color)
            stdscr.addstr(f" (max: {format_percent(mem_max)})")
            row += 1

            stdscr.addstr(row, 0, "Disk: ")
            stdscr.addstr(f"{format_percent(disk_usage)}", disk_color)
            row += 1

            # Tool Usage Section
            row += 1
            tool_data = metrics.get("tools", {})
            stdscr.addstr(row, 0, "Tool Usage", curses.A_BOLD | CYAN)
            row += 1

            if "tool_calls" in tool_data and tool_data["tool_calls"]:
                tools = list(tool_data["tool_calls"].items())
                tools.sort(key=lambda x: x[1].get("count", 0), reverse=True)

                for _i, (tool, data) in enumerate(tools[:5]):  # Show top 5 tools
                    count = data.get("count", 0)
                    stdscr.addstr(row, 0, f"{tool}: {count} calls")

                    # Show execution time if available
                    if tool in tool_data.get("execution_times", {}):
                        time_data = tool_data["execution_times"][tool]
                        avg_time = time_data.get("avg_time", 0)
                        stdscr.addstr(f" (avg: {format_duration(avg_time)})")

                    row += 1
                    if row >= height - 3:  # Leave room for footer
                        break

            # Footer
            footer = "Press 'q' to quit, 'r' to refresh now"
            if height > 5:  # Only show footer if we have space
                stdscr.addstr(height - 1, 0, footer)

            stdscr.refresh()

            # Wait for input or timeout
            stdscr.timeout(refresh_interval * 1000)
            key = stdscr.getch()
            if key == ord("q"):
                break

    except KeyboardInterrupt:
        pass


def display_rich_ui(metrics_history: MetricsHistory, refresh_interval: int) -> None:
    """Display a rich text-based UI using the rich library."""
    if not HAS_RICH:
        print("The 'rich' library is required for enhanced visualization.")
        print("Install with: pip install rich")
        return

    console = Console()

    try:
        while True:
            console.clear()

            # Load current metrics
            metrics = load_metrics()
            if "error" in metrics:
                console.print(f"[bold red]Error:[/bold red] {metrics['error']}")
                time.sleep(refresh_interval)
                continue

            # Update history
            metrics_history.update(metrics)

            # Header
            timestamp = metrics.get("timestamp", "Unknown")
            server_info = metrics.get("server_info", {})
            uptime = server_info.get("uptime", "Unknown")

            console.print(
                f"[bold blue]Simplenote MCP Server Monitoring[/bold blue] - {timestamp}"
            )
            console.print(
                f"Uptime: [green]{uptime}[/green] | Refresh: {refresh_interval}s"
            )
            console.print()

            # API Performance
            api_data = metrics.get("api", {})
            calls = api_data.get("calls", {}).get("count", 0)
            success_rate = api_data.get("success_rate", 0)

            api_table = Table(title="API Performance", box=box.ROUNDED)
            api_table.add_column("Metric")
            api_table.add_column("Value")

            success_color = (
                "green"
                if success_rate > 95
                else ("yellow" if success_rate > 80 else "red")
            )
            api_table.add_row("Total Calls", str(calls))
            api_table.add_row(
                "Success Rate",
                f"[{success_color}]{format_percent(success_rate)}[/{success_color}]",
            )

            if "response_times" in api_data and api_data["response_times"]:
                endpoints_table = Table(box=None)
                endpoints_table.add_column("Endpoint")
                endpoints_table.add_column("Calls")
                endpoints_table.add_column("Avg Time")
                endpoints_table.add_column("P95 Time")

                endpoints = list(api_data["response_times"].items())
                endpoints.sort(key=lambda x: x[1].get("count", 0), reverse=True)

                for endpoint, data in endpoints[:5]:  # Show top 5 endpoints
                    count = data.get("count", 0)
                    avg_time = data.get("avg_time", 0)
                    p95_time = data.get("p95_time", 0)

                    endpoints_table.add_row(
                        endpoint,
                        str(count),
                        format_duration(avg_time),
                        format_duration(p95_time),
                    )

                api_table.add_row("Top Endpoints", endpoints_table)

            console.print(api_table)
            console.print()

            # Cache Performance
            cache_data = metrics.get("cache", {})
            hit_rate = cache_data.get("hit_rate", 0)
            hits = cache_data.get("hits", {}).get("count", 0)
            misses = cache_data.get("misses", {}).get("count", 0)
            size = cache_data.get("size", 0)
            max_size = cache_data.get("max_size", 0)
            utilization = cache_data.get("utilization", 0)

            cache_table = Table(title="Cache Performance", box=box.ROUNDED)
            cache_table.add_column("Metric")
            cache_table.add_column("Value")

            hit_color = (
                "green" if hit_rate > 90 else ("yellow" if hit_rate > 70 else "red")
            )
            cache_table.add_row(
                "Hit Rate", f"[{hit_color}]{format_percent(hit_rate)}[/{hit_color}]"
            )
            cache_table.add_row("Hits/Misses", f"{hits} / {misses}")
            cache_table.add_row("Size", f"{size} / {max_size} notes")
            cache_table.add_row("Utilization", f"{format_percent(utilization)}")

            console.print(cache_table)
            console.print()

            # System Resources
            resource_data = metrics.get("resources", {})
            cpu_current = resource_data.get("cpu", {}).get("current", 0)
            cpu_max = resource_data.get("cpu", {}).get("max", 0)
            mem_current = resource_data.get("memory", {}).get("current", 0)
            mem_max = resource_data.get("memory", {}).get("max", 0)
            disk_usage = resource_data.get("disk", {}).get("usage_percent", 0)

            resource_table = Table(title="System Resources", box=box.ROUNDED)
            resource_table.add_column("Resource")
            resource_table.add_column("Current")
            resource_table.add_column("Maximum")

            cpu_color = (
                "green"
                if cpu_current < 50
                else ("yellow" if cpu_current < 80 else "red")
            )
            mem_color = (
                "green"
                if mem_current < 60
                else ("yellow" if mem_current < 85 else "red")
            )
            disk_color = (
                "green" if disk_usage < 70 else ("yellow" if disk_usage < 90 else "red")
            )

            resource_table.add_row(
                "CPU",
                f"[{cpu_color}]{format_percent(cpu_current)}[/{cpu_color}]",
                f"{format_percent(cpu_max)}",
            )
            resource_table.add_row(
                "Memory",
                f"[{mem_color}]{format_percent(mem_current)}[/{mem_color}]",
                f"{format_percent(mem_max)}",
            )
            resource_table.add_row(
                "Disk", f"[{disk_color}]{format_percent(disk_usage)}[/{disk_color}]", ""
            )

            console.print(resource_table)
            console.print()

            # Tool Usage
            tool_data = metrics.get("tools", {})
            if "tool_calls" in tool_data and tool_data["tool_calls"]:
                tool_table = Table(title="Tool Usage", box=box.ROUNDED)
                tool_table.add_column("Tool")
                tool_table.add_column("Calls")
                tool_table.add_column("Avg Time")

                tools = list(tool_data["tool_calls"].items())
                tools.sort(key=lambda x: x[1].get("count", 0), reverse=True)

                for tool, data in tools[:5]:  # Show top 5 tools
                    count = data.get("count", 0)
                    avg_time = 0

                    if tool in tool_data.get("execution_times", {}):
                        time_data = tool_data["execution_times"][tool]
                        avg_time = time_data.get("avg_time", 0)

                    tool_table.add_row(
                        tool,
                        str(count),
                        format_duration(avg_time) if avg_time > 0 else "N/A",
                    )

                console.print(tool_table)
                console.print()

            # Footer
            console.print("[dim]Press Ctrl+C to exit[/dim]")

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        console.print("[yellow]Dashboard stopped.[/yellow]")


def main():
    """Main entry point for the monitoring dashboard."""
    parser = argparse.ArgumentParser(
        description="Simplenote MCP Server Monitoring Dashboard"
    )
    parser.add_argument(
        "--refresh", type=int, default=3, help="Refresh interval in seconds"
    )
    parser.add_argument(
        "--rich", action="store_true", help="Use rich text UI if available"
    )
    args = parser.parse_args()

    # Create metrics history
    metrics_history = MetricsHistory()

    if not METRICS_FILE.exists():
        print(f"Error: Metrics file not found at {METRICS_FILE}")
        print(
            "Make sure the Simplenote MCP Server is running with performance monitoring enabled."
        )
        return 1

    print(f"Starting Simplenote MCP Monitoring Dashboard (refresh: {args.refresh}s)")
    print(f"Loading metrics from: {METRICS_FILE}")
    time.sleep(1)  # Give user a moment to read the startup message

    try:
        if args.rich and HAS_RICH:
            display_rich_ui(metrics_history, args.refresh)
        else:
            curses.wrapper(display_terminal_ui, metrics_history, args.refresh)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
