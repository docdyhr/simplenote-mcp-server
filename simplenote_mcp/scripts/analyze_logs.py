#!/usr/bin/env python
# analyze_logs.py - Log analyzer for Simplenote MCP server logs

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, project_root)

# Now we can import from the compatibility module

from simplenote_mcp.server.compat import Path

# Add the parent directory to the Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Constants
DEFAULT_LOG_PATH = "/Users/thomas/Library/Logs/Claude/mcp-server-simplenote.log"
REPORT_PATH = Path(PROJECT_ROOT) / "simplenote_mcp" / "logs" / "log_analysis_report.txt"

# Error patterns to look for
ERROR_PATTERNS = [
    r"Failed to get notes from Simplenote \(status (-?\d+)\)",
    r"Error initializing Simplenote client: (.+)",
    r"Simplenote API connection test failed with status (\d+)",
    r"Authentication failed with status code (\d+)",
    r"Error during sync: (.+)",
    r"Error in background sync: (.+)",
    r"Network error: (.+)",
    r"Backing off for ([\d\.]+)s after (\d+) consecutive failures",
    r"cannot import name '([^']+)' from '([^']+)'",
]


class LogAnalyzer:
    """Analyzer for Simplenote MCP server logs."""

    def __init__(self, log_path: str = DEFAULT_LOG_PATH):
        self.log_path = log_path
        self.logs = []
        self.errors = []
        self.error_counts = Counter()
        self.error_times = defaultdict(list)
        self.network_errors = []
        self.auth_errors = []
        self.sync_stats = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "consecutive_failures": 0,
        }
        self.import_errors = []
        self.server_starts = []
        self.server_stops = []
        self.status_codes = Counter()

    def load_logs(self) -> bool:
        """Load logs from file."""
        try:
            log_path = Path(self.log_path)
            if not log_path.exists():
                print(f"Log file not found: {self.log_path}")
                return False

            print(f"Loading logs from {self.log_path}")
            with open(self.log_path, "r") as f:
                self.logs = f.readlines()

            print(f"Loaded {len(self.logs)} log lines")
            return True
        except Exception as e:
            print(f"Error loading logs: {e}")
            return False

    def parse_logs(self) -> None:
        """Parse and analyze logs."""
        print("Analyzing logs...")

        # Different timestamp formats in the logs
        iso_timestamp_pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z"
        py_timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"

        # Combined regex for multiple timestamp formats
        timestamp_regex = f"({iso_timestamp_pattern}|{py_timestamp_pattern})"

        for line in self.logs:
            # Skip empty lines
            if not line.strip():
                continue

            # Check for server start/stop
            if "Initializing server" in line:
                match = re.search(timestamp_regex, line)
                if match:
                    self.server_starts.append(match.group(1))

            if "Server transport closed" in line or "Shutdown requested" in line:
                match = re.search(timestamp_regex, line)
                if match:
                    self.server_stops.append(match.group(1))

            # Count sync attempts
            if "Starting sync operation" in line:
                self.sync_stats["attempts"] += 1

            # Check for successful syncs
            if "Success - reset backoff parameters" in line:
                self.sync_stats["successes"] += 1

            # Track status codes
            status_match = re.search(r"status (\-?\d+)", line)
            if status_match:
                self.status_codes[status_match.group(1)] += 1

            # Check for import errors
            import_match = re.search(
                r"ImportError: cannot import name '([^']+)' from '([^']+)'", line
            )
            if import_match:
                self.import_errors.append(
                    {
                        "line": line.strip(),
                        "module": import_match.group(2),
                        "name": import_match.group(1),
                    }
                )

            # Check for errors
            if (
                "ERROR" in line
                or "Error" in line
                or "Failed" in line
                or "failed" in line
            ):
                self.errors.append(line.strip())

                # Check each error pattern
                for pattern in ERROR_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        error_type = pattern.split("\\")[0].replace("(", "").strip()
                        self.error_counts[error_type] += 1

                        # Extract timestamp
                        time_match = re.search(timestamp_regex, line)
                        if time_match:
                            self.error_times[error_type].append(time_match.group(1))

                        # Specific error tracking
                        if "Failed to get notes from Simplenote" in line:
                            self.network_errors.append(line.strip())
                            self.sync_stats["failures"] += 1

                        # Track consecutive failures
                        consecutive_match = re.search(
                            r"after (\d+) consecutive failures", line
                        )
                        if consecutive_match:
                            failures = int(consecutive_match.group(1))
                            if failures > self.sync_stats["consecutive_failures"]:
                                self.sync_stats["consecutive_failures"] = failures

            # Check for authentication errors
            if "Authentication" in line and ("failed" in line or "error" in line):
                self.auth_errors.append(line.strip())

    def generate_report(self) -> str:
        """Generate analysis report."""
        report = []
        report.append("=== Simplenote MCP Server Log Analysis ===")
        report.append(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Log file: {self.log_path}")
        report.append("")

        # Server uptime analysis
        report.append("=== Server Sessions ===")
        if self.server_starts:
            report.append(f"Server started {len(self.server_starts)} times")
            report.append(f"First start: {self.server_starts[0]}")
            report.append(f"Last start: {self.server_starts[-1]}")
        else:
            report.append("No server starts detected in logs")

        if len(self.server_starts) == len(self.server_stops) and self.server_starts:
            # Calculate total uptime if we have matching starts and stops
            report.append(f"Server stopped {len(self.server_stops)} times")
            report.append(f"Last stop: {self.server_stops[-1]}")
        elif self.server_stops:
            report.append(
                f"Server stopped {len(self.server_stops)} times (incomplete session data)"
            )

        report.append("")

        # Import errors
        if self.import_errors:
            report.append("=== Import Errors ===")
            report.append(f"Found {len(self.import_errors)} import errors")
            for i, error in enumerate(self.import_errors):
                report.append(
                    f"{i + 1}. Cannot import '{error['name']}' from '{error['module']}'"
                )
            report.append("")

        # Error summary
        report.append("=== Error Summary ===")
        if self.errors:
            report.append(f"Total errors: {len(self.errors)}")
            report.append("Top error types:")
            for error_type, count in self.error_counts.most_common(5):
                report.append(f"  - {error_type}: {count} occurrences")

            # Status code analysis
            if self.status_codes:
                report.append("\nAPI Status Codes:")
                for code, count in self.status_codes.most_common():
                    status_meaning = ""
                    if code == "0":
                        status_meaning = "(Success)"
                    elif code == "-1":
                        status_meaning = "(Network Error)"
                    elif code == "401":
                        status_meaning = "(Unauthorized)"
                    report.append(
                        f"  - Status {code} {status_meaning}: {count} occurrences"
                    )
        else:
            report.append("No errors found in logs")

        report.append("")

        # Network errors
        if self.network_errors:
            report.append("=== Network Issues ===")
            report.append(f"Network errors: {len(self.network_errors)}")
            report.append(f"Sample error: {self.network_errors[0]}")
            report.append("")

        # Authentication errors
        if self.auth_errors:
            report.append("=== Authentication Issues ===")
            report.append(f"Authentication errors: {len(self.auth_errors)}")
            report.append(f"Sample error: {self.auth_errors[0]}")
            report.append("")

        # Sync statistics
        report.append("=== Sync Statistics ===")
        report.append(f"Sync attempts: {self.sync_stats['attempts']}")
        report.append(f"Successful syncs: {self.sync_stats['successes']}")
        report.append(f"Failed syncs: {self.sync_stats['failures']}")

        if self.sync_stats["attempts"] > 0:
            success_rate = (
                self.sync_stats["successes"] / self.sync_stats["attempts"]
            ) * 100
            report.append(f"Sync success rate: {success_rate:.1f}%")

        if self.sync_stats["consecutive_failures"] > 0:
            report.append(
                f"Maximum consecutive failures: {self.sync_stats['consecutive_failures']}"
            )

        report.append("")

        # Error timing patterns
        report.append("=== Error Timing Patterns ===")
        has_timing_data = False
        for error_type, timestamps in self.error_times.items():
            if len(timestamps) >= 3:  # Only analyze if we have enough data points
                has_timing_data = True
                report.append(f"{error_type} errors:")
                report.append(f"  First occurrence: {timestamps[0]}")
                report.append(f"  Last occurrence: {timestamps[-1]}")
                report.append(f"  Total occurrences: {len(timestamps)}")

                # Try to detect patterns in timing
                try:
                    # Convert timestamps to datetime objects for timing analysis
                    # Handle multiple timestamp formats
                    datetime_objects = []
                    for ts in timestamps:
                        try:
                            if "T" in ts and "Z" in ts:  # ISO format
                                dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
                            else:  # Python logging format
                                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S,%f")
                            datetime_objects.append(dt)
                        except ValueError:
                            continue

                    if len(datetime_objects) >= 2:
                        # Calculate time differences
                        diffs = [
                            (
                                datetime_objects[i + 1] - datetime_objects[i]
                            ).total_seconds()
                            for i in range(len(datetime_objects) - 1)
                        ]

                        if diffs:
                            avg_interval = sum(diffs) / len(diffs)
                            min_interval = min(diffs)
                            max_interval = max(diffs)

                            report.append("  Time between occurrences:")
                            report.append(f"    Average: {avg_interval:.1f} seconds")
                            report.append(f"    Minimum: {min_interval:.1f} seconds")
                            report.append(f"    Maximum: {max_interval:.1f} seconds")
                except Exception as e:
                    report.append(f"  Error analyzing timestamps: {e}")

                report.append("")

        if not has_timing_data:
            report.append("Insufficient data for timing analysis")
            report.append("")

        # Recommendations
        report.append("=== Recommendations ===")

        # Import error recommendations
        if self.import_errors:
            for error in self.import_errors:
                if error["module"] == "pathlib" and error["name"] == "Path":
                    report.append(
                        "🔧 Python 3.13 pathlib compatibility issue detected:"
                    )
                    report.append(
                        "  - Update your code to handle the pathlib module changes in Python 3.13"
                    )
                    report.append(
                        "  - Try adding a fallback import: from pathlib._local import Path"
                    )
                    report.append(
                        "  - Consider downgrading to Python 3.12 until libraries are updated"
                    )

        # Network error recommendations
        if len(self.network_errors) > 10:
            report.append("🔧 Persistent network connectivity issues detected:")
            report.append("  - Check your internet connection")
            report.append(
                "  - Verify Simplenote API status at https://status.simplenote.com/"
            )
            report.append(
                "  - Check for firewalls or proxy settings that might be blocking the connection"
            )
            report.append(
                "  - Run the diagnose_api.py script for detailed connectivity diagnostics"
            )

        # Authentication recommendations
        if self.auth_errors:
            report.append("🔧 Authentication issues detected:")
            report.append(
                "  - Verify your SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD environment variables"
            )
            report.append(
                "  - Try logging in to the Simplenote website with the same credentials"
            )
            report.append(
                "  - Check if your account has been locked due to too many failed attempts"
            )

        # Frequent restarts
        if (
            len(self.server_starts) > 3
            and len(self.server_starts) / (len(self.errors) or 1) > 0.1
        ):
            report.append("🔧 Frequent server restarts detected:")
            report.append(
                "  - Use the server scripts to ensure clean process management"
            )
            report.append("  - Check for memory leaks or resource exhaustion")
            report.append(
                "  - Consider increasing logging to identify the cause of crashes"
            )

        # General recommendations
        report.append("\n🔧 General recommendations:")
        report.append(
            "  1. Run ./simplenote_mcp/scripts/diagnose_api.py for detailed API diagnostics"
        )
        report.append(
            "  2. Check environment variables (SIMPLENOTE_EMAIL, SIMPLENOTE_PASSWORD)"
        )
        report.append("  3. Set LOG_LEVEL=DEBUG for more detailed logging")
        report.append(
            "  4. Consider increasing SYNC_INTERVAL_SECONDS if API rate limiting is suspected"
        )
        report.append(
            "  5. Run ./simplenote_mcp/scripts/restart_claude.sh to restart the server cleanly"
        )
        report.append("  6. Set MCP_DEBUG=true for additional diagnostic information")

        return "\n".join(report)

    def run(self) -> None:
        """Run the log analysis."""
        if not self.load_logs():
            return

        self.parse_logs()
        report = self.generate_report()

        # Save report to file
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w") as f:
            f.write(report)

        print(report)
        print(f"\nReport saved to {REPORT_PATH}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Analyze Simplenote MCP server logs")
    parser.add_argument(
        "--log",
        "-l",
        default=DEFAULT_LOG_PATH,
        help=f"Path to log file (default: {DEFAULT_LOG_PATH})",
    )
    args = parser.parse_args()

    analyzer = LogAnalyzer(args.log)
    analyzer.run()


if __name__ == "__main__":
    main()
