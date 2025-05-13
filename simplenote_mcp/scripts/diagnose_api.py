#!/usr/bin/env python
# diagnose_api.py - Diagnostic tool for Simplenote API connectivity

import argparse
import asyncio
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Dict, TypedDict

from simplenote_mcp.server.compat import Path

# Add the parent directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../"))
sys.path.insert(0, project_root)

# Set project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import server modules
try:
    from simplenote_mcp.server import get_simplenote_client
    from simplenote_mcp.server.config import get_config
except ImportError as e:
    print(f"Error importing server modules: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)

# Constants
SIMPLENOTE_API_HOST = "app.simplenote.com"  # Main domain that should resolve
SIMPLENOTE_AUTH_URL = "https://auth.simperium.com/1/authorized"
SIMPLENOTE_API_URL = (
    "https://app.simplenote.com"  # Main site URL for connectivity check
)
SIMPERIUM_API_HOST = "api.simperium.com"  # Actual API endpoint
DEFAULT_TIMEOUT = 10  # seconds
DIAGNOSTIC_REPORT_PATH = (
    Path(PROJECT_ROOT) / "simplenote_mcp" / "logs" / "api_diagnostic_report.txt"
)


# Type definitions
class ApiResult(TypedDict, total=False):
    attempt: int
    status: int
    elapsed: float
    notes_count: int
    error_message: str


def print_and_log(message: str) -> None:
    """Print message to console and add to log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)

    # Ensure logs directory exists
    log_dir = Path(PROJECT_ROOT) / "simplenote_mcp" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Append to diagnostic file
    with open(DIAGNOSTIC_REPORT_PATH, "a") as f:
        f.write(f"{formatted_message}\n")


def test_internet_connectivity() -> bool:
    """Test basic internet connectivity by pinging Google DNS."""
    print_and_log("\n=== Testing Internet Connectivity ===")

    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=DEFAULT_TIMEOUT)
        print_and_log(
            "✅ Internet connectivity check passed - successfully connected to Google DNS"
        )
        return True
    except (socket.timeout, socket.error) as e:
        print_and_log(f"❌ Internet connectivity check failed: {e}")
        print_and_log("  This suggests your machine has no internet connection")
        return False


def test_dns_resolution() -> bool:
    """Test DNS resolution for Simplenote domains."""
    print_and_log("\n=== Testing DNS Resolution ===")

    domains = [SIMPLENOTE_API_HOST, SIMPERIUM_API_HOST]
    success = True

    for domain in domains:
        try:
            ip_addresses = socket.gethostbyname_ex(domain)
            print_and_log(f"✅ DNS resolution successful for {domain}")
            print_and_log(f"  Hostname: {ip_addresses[0]}")
            print_and_log(f"  Aliases: {ip_addresses[1]}")
            print_and_log(f"  IP Addresses: {ip_addresses[2]}")
        except socket.gaierror as e:
            print_and_log(f"❌ DNS resolution failed for {domain}: {e}")
            print_and_log(
                f"  This suggests DNS issues or the {domain} domain is unreachable"
            )
            success = False

    return success


def test_tls_connection() -> bool:
    """Test TLS connection to Simplenote domains."""
    print_and_log("\n=== Testing TLS/SSL Connection ===")

    domains = [SIMPLENOTE_API_HOST, SIMPERIUM_API_HOST]
    context = ssl.create_default_context()
    success = True

    for domain in domains:
        try:
            with (
                socket.create_connection(
                    (domain, 443), timeout=DEFAULT_TIMEOUT
                ) as sock,
                context.wrap_socket(sock, server_hostname=domain) as ssock,
            ):
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert["issuer"])
                subject = dict(x[0] for x in cert["subject"])

                print_and_log(f"✅ TLS connection successful to {domain}")
                print_and_log(
                    f"  Certificate issuer: {issuer.get('organizationName', 'Unknown')}"
                )
                print_and_log(
                    f"  Certificate subject: {subject.get('commonName', 'Unknown')}"
                )
                print_and_log(
                    f"  Certificate valid until: {cert.get('notAfter', 'Unknown')}"
                )
        except (socket.error, ssl.SSLError) as e:
            print_and_log(f"❌ TLS connection failed to {domain}: {e}")
            print_and_log(
                f"  This suggests TLS/SSL issues or the {domain} endpoint is unreachable"
            )
            success = False

    return success


def test_http_connection() -> bool:
    """Test basic HTTP connection to Simplenote website."""
    print_and_log("\n=== Testing HTTP Connection ===")

    try:
        # Just check the main website response
        req = urllib.request.Request(SIMPLENOTE_API_URL, method="HEAD")
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            print_and_log("✅ HTTP connection successful to Simplenote website")
            print_and_log(f"  Status code: {response.status}")
            print_and_log(f"  Headers: {dict(response.headers)}")
            return True
    except urllib.error.HTTPError as e:
        # Some HTTP errors might be expected
        if e.code in (301, 302, 303, 307, 308):  # Redirects
            print_and_log(
                f"✅ HTTP connection successful to Simplenote website (received redirect {e.code})"
            )
            print_and_log(
                f"  Headers: {dict(e.headers) if hasattr(e, 'headers') else 'No headers'}"
            )
            return True
        else:
            print_and_log(
                f"❌ HTTP connection failed with unexpected status: {e.code} {e.reason}"
            )
            print_and_log(
                f"  Headers: {dict(e.headers) if hasattr(e, 'headers') else 'No headers'}"
            )
            return False
    except urllib.error.URLError as e:
        print_and_log(f"❌ HTTP connection failed: {e.reason}")
        if isinstance(e.reason, ssl.SSLError):
            print_and_log("  This suggests TLS/SSL issues with the Simplenote website")
        else:
            print_and_log("  This suggests network connectivity issues to Simplenote")
        return False
    except Exception as e:
        print_and_log(
            f"❌ HTTP connection failed with unexpected error: {type(e).__name__}: {e}"
        )
        return False


def test_api_auth() -> bool:
    """Test Simplenote API authentication."""
    print_and_log("\n=== Testing Simplenote API Authentication ===")

    config = get_config()

    if not config.has_credentials:
        print_and_log("❌ No Simplenote credentials found in environment variables")
        print_and_log("  Please set SIMPLENOTE_EMAIL and SIMPLENOTE_PASSWORD")
        return False

    # Get email with some redaction for privacy in logs
    email = config.simplenote_email or ""
    redacted_email = (
        f"{email[:3]}{'*' * (len(email) - 6)}{email[-3:]}" if len(email) > 6 else "***"
    )
    print_and_log(f"📧 Using email: {redacted_email}")

    try:
        client = get_simplenote_client()
        print_and_log("✅ Successfully created Simplenote client instance")

        # Now test authentication with a simple API call
        try:
            start_time = time.time()
            # Get notes to test auth - simplenote library 2.1.4 doesn't support 'limit' param
            notes, status = client.get_note_list(data=False)
            elapsed = time.time() - start_time

            if status == 0:
                print_and_log(f"✅ Authentication successful (took {elapsed:.2f}s)")
                print_and_log(f"  Received {len(notes)} notes in the response")
                return True
            else:
                print_and_log(
                    f"❌ Authentication failed with status code {status} (took {elapsed:.2f}s)"
                )
                print_and_log("  This suggests invalid credentials or an API issue")
                return False

        except Exception as e:
            print_and_log(f"❌ Authentication API call failed: {type(e).__name__}: {e}")
            return False

    except Exception as e:
        print_and_log(f"❌ Failed to create Simplenote client: {type(e).__name__}: {e}")
        return False


def test_simplenote_library() -> bool:
    """Test the simplenote library version and functionality."""
    print_and_log("\n=== Testing Simplenote Library ===")

    try:
        import simplenote

        print_and_log("✅ Successfully imported simplenote library")
        print_and_log(f"  Version: {getattr(simplenote, '__version__', 'Unknown')}")

        # Check if the Simplenote class exists and has the expected methods
        if hasattr(simplenote, "Simplenote"):
            print_and_log("✅ Found Simplenote class in the library")

            # Create an instance just to check the class (without auth)
            try:
                # Just testing if the class can be instantiated, the auth will fail
                instance = simplenote.Simplenote("test@example.com", "password")

                # Check for critical methods
                for method in [
                    "get_note_list",
                    "get_note",
                    "update_note",
                    "add_note",
                    "trash_note",
                    "delete_note",
                ]:
                    if hasattr(instance, method):
                        print_and_log(f"  ✓ Method found: {method}")
                    else:
                        print_and_log(f"  ✗ Method missing: {method}")

                return True
            except Exception as e:
                print_and_log(
                    f"❌ Error creating Simplenote instance: {type(e).__name__}: {e}"
                )
                return False
        else:
            print_and_log("❌ Simplenote class not found in the library")
            return False
    except ImportError as e:
        print_and_log(f"❌ Failed to import simplenote library: {e}")
        print_and_log("  Please make sure the simplenote package is installed")
        return False


def test_proxy_settings() -> None:
    """Check for system proxy settings that might interfere with API connections."""
    print_and_log("\n=== Checking Proxy Settings ===")

    proxies = {
        "http": os.environ.get("HTTP_PROXY", os.environ.get("http_proxy", "None")),
        "https": os.environ.get("HTTPS_PROXY", os.environ.get("https_proxy", "None")),
        "no_proxy": os.environ.get("NO_PROXY", os.environ.get("no_proxy", "None")),
    }

    print_and_log(f"  HTTP_PROXY: {proxies['http']}")
    print_and_log(f"  HTTPS_PROXY: {proxies['https']}")
    print_and_log(f"  NO_PROXY: {proxies['no_proxy']}")

    if proxies["http"] != "None" or proxies["https"] != "None":
        print_and_log("⚠️  Proxy settings detected that might affect API connectivity")
        print_and_log(
            "  If you're experiencing issues, try temporarily unsetting these variables"
        )
    else:
        print_and_log("✅ No proxy settings detected")


def test_api_performance() -> None:
    """Test Simplenote API performance with multiple requests."""
    print_and_log("\n=== Testing API Performance ===")

    try:
        client = get_simplenote_client()

        # Test multiple API calls to check for consistency
        results: list[ApiResult] = []
        for i in range(3):
            try:
                start_time = time.time()
                # simplenote library 2.1.4 doesn't support 'limit' param
                notes, status = client.get_note_list(data=False)
                elapsed = time.time() - start_time

                results.append(
                    {
                        "attempt": i + 1,
                        "status": 0,
                        "elapsed": elapsed,
                        "notes_count": len(notes) if isinstance(notes, list) else -1,
                        "error_message": "",
                    }
                )

                # Small delay between calls
                time.sleep(1)

            except Exception as e:
                print_and_log(f"❌ API call {i + 1} failed: {type(e).__name__}: {e}")
                results.append(
                    {
                        "attempt": i + 1,
                        "status": -1,  # Use numeric status for consistency
                        "elapsed": time.time() - start_time,
                        "notes_count": -1,  # Include notes_count for consistency
                        "error_message": str(e),  # Use consistent naming
                    }
                )

        # Report results
        success_count = sum(1 for r in results if r["status"] == 0)
        if success_count == len(results):
            print_and_log(
                f"✅ All API performance tests passed ({success_count}/{len(results)})"
            )
        else:
            print_and_log(
                f"⚠️  Some API performance tests failed ({success_count}/{len(results)} passed)"
            )

        for result in results:
            if result["status"] == 0:
                print_and_log(
                    f"  Attempt {result['attempt']}: ✓ Success in {result['elapsed']:.2f}s, {result['notes_count']} notes"
                )
            elif result["status"] == -1:
                print_and_log(
                    f"  Attempt {result['attempt']}: ✗ Error in {result['elapsed']:.2f}s - {result.get('error_message', 'Unknown error')}"
                )
            else:
                print_and_log(
                    f"  Attempt {result['attempt']}: ✗ Failed with status {result['status']} in {result['elapsed']:.2f}s"
                )

    except Exception as e:
        print_and_log(f"❌ API performance test setup failed: {type(e).__name__}: {e}")


def get_system_info() -> None:
    """Gather system information that might be relevant to API connection issues."""
    print_and_log("\n=== System Information ===")

    try:
        import platform

        print_and_log(
            f"  OS: {platform.system()} {platform.release()} ({platform.version()})"
        )
        print_and_log(f"  Python: {platform.python_version()}")
        print_and_log(f"  Machine: {platform.machine()}")
        print_and_log(f"  Node: {platform.node()}")

        # Check if running in a virtual environment
        in_venv = sys.prefix != sys.base_prefix
        print_and_log(f"  Virtual Environment: {'Yes' if in_venv else 'No'}")

        # Try to get network interface info on Unix-like systems
        if platform.system() in ("Linux", "Darwin"):
            try:
                import subprocess

                if platform.system() == "Darwin":  # macOS
                    output = subprocess.check_output(
                        ["networksetup", "-listallhardwareports"],
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                    )
                else:  # Linux
                    output = subprocess.check_output(
                        ["ip", "addr"],
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                    )
                print_and_log("  Network Interfaces:")
                print_and_log(
                    "  " + output.replace("\n", "\n  ")[:500] + "..."
                    if len(output) > 500
                    else output
                )
            except Exception as e:
                print_and_log(f"  Network interface info unavailable: {e}")

    except ImportError:
        print_and_log("  Platform module not available")


def provide_recommendations(test_results: Dict[str, bool]) -> None:
    """Provide recommendations based on test results."""
    print_and_log("\n=== Recommendations ===")

    if not test_results.get("internet", True):
        print_and_log("🔧 Your machine appears to have internet connectivity issues:")
        print_and_log("  - Check your network connection")
        print_and_log("  - Verify your Wi-Fi or Ethernet is connected")
        print_and_log("  - Try restarting your router/modem")
        print_and_log("  - Disable any VPN that might be interfering")
        return  # No point in continuing if there's no internet

    if not test_results.get("dns", True):
        print_and_log("🔧 DNS resolution issues detected:")
        print_and_log(
            "  - Try using alternative DNS servers (e.g., 8.8.8.8 or 1.1.1.1)"
        )
        print_and_log("  - Check if your hosts file has any entries for simplenote.com")
        print_and_log("  - Flush your DNS cache")

    if not test_results.get("tls", True):
        print_and_log("🔧 TLS/SSL connection issues detected:")
        print_and_log(
            "  - Check if your system date and time are correct (important for SSL certificates)"
        )
        print_and_log("  - Update your SSL certificates")
        print_and_log(
            "  - Check if a firewall or security software is blocking secure connections"
        )

    if not test_results.get("http", True):
        print_and_log("🔧 HTTP connection issues detected:")
        print_and_log(
            "  - Check if a firewall is blocking outbound connections to Simplenote"
        )
        print_and_log("  - Try accessing simplenote.com in a web browser")
        print_and_log("  - Check your proxy settings if you use a proxy")

    if not test_results.get("auth", True):
        print_and_log("🔧 Authentication issues detected:")
        print_and_log("  - Verify your Simplenote credentials are correct")
        print_and_log("  - Try logging into simplenote.com with the same credentials")
        print_and_log("  - Check if your Simplenote account has any restrictions")

    if not test_results.get("library", True):
        print_and_log("🔧 Simplenote library issues detected:")
        print_and_log(
            "  - Try reinstalling the simplenote library: pip install simplenote --upgrade"
        )
        print_and_log("  - Check the Python environment being used")

    # General recommendations
    print_and_log("\n🔧 General recommendations:")
    print_and_log(
        "  1. Check Simplenote service status at https://status.simplenote.com/"
    )
    print_and_log(
        "  2. Try using the official Simplenote app to confirm account access"
    )
    print_and_log("  3. Set LOG_LEVEL=DEBUG in your environment for more detailed logs")
    print_and_log(
        "  4. Increase SYNC_INTERVAL_SECONDS to reduce API load (e.g., 300 for 5 minutes)"
    )
    print_and_log("  5. Check your firewall and security software settings")

    print_and_log(
        f"\n📋 A detailed diagnostic report has been saved to:\n   {DIAGNOSTIC_REPORT_PATH}"
    )


async def main() -> None:
    """Main function to run diagnostic tests."""
    # Clear any existing report
    DIAGNOSTIC_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC_REPORT_PATH.write_text("=== Simplenote API Diagnostic Report ===\n")

    print_and_log(
        f"Starting Simplenote API diagnostics at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print_and_log(f"Report will be saved to: {DIAGNOSTIC_REPORT_PATH}")

    # Get system information
    get_system_info()

    # Check proxy settings
    test_proxy_settings()

    # Run tests and collect results
    test_results = {}

    # Test Internet connectivity
    test_results["internet"] = test_internet_connectivity()

    # Only continue if internet is working
    if test_results["internet"]:
        # Test DNS resolution
        test_results["dns"] = test_dns_resolution()

        # Test TLS connection
        test_results["tls"] = test_tls_connection()

        # Test HTTP connection
        test_results["http"] = test_http_connection()

        # Test Simplenote library
        test_results["library"] = test_simplenote_library()

        # Test API authentication
        test_results["auth"] = test_api_auth()

        # If auth succeeded, test API performance
        if test_results.get("auth", False):
            test_api_performance()

    # Provide recommendations based on test results
    provide_recommendations(test_results)

    print_and_log(
        f"\nDiagnostic tests completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Diagnose Simplenote API connectivity issues"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    args = parser.parse_args()

    if args.verbose:
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["MCP_DEBUG"] = "true"

    # Run the main async function
    asyncio.run(main())
