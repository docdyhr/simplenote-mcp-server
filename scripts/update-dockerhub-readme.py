#!/usr/bin/env python3
"""
Docker Hub README Update Script

This script manually updates the Docker Hub repository description
from a local README file using the Docker Hub API.

Usage:
    python scripts/update-dockerhub-readme.py

Environment Variables:
    DOCKER_USERNAME: Docker Hub username
    DOCKER_TOKEN: Docker Hub access token
    DOCKER_REPOSITORY: Repository name (default: docdyhr/simplenote-mcp-server)
    README_FILE: Path to README file (default: DOCKER_README.md)
"""

import os
import sys
from pathlib import Path

import requests


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


class DockerHubAPI:
    """Docker Hub API client for updating repository descriptions."""

    BASE_URL = "https://hub.docker.com/v2"

    def __init__(self, username: str, token: str):
        """Initialize the Docker Hub API client.

        Args:
            username: Docker Hub username
            token: Docker Hub access token
        """
        self.username = username
        self.token = token
        self.session = requests.Session()
        self._auth_token: str | None = None

    def authenticate(self) -> bool:
        """Authenticate with Docker Hub API.

        Returns:
            True if authentication successful, False otherwise
        """
        print_info("Authenticating with Docker Hub...")

        try:
            response = self.session.post(
                f"{self.BASE_URL}/users/login/",
                json={"username": self.username, "password": self.token},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                self._auth_token = data.get("token")
                if self._auth_token:
                    print_success("Authentication successful")
                    return True
                else:
                    print_error("No authentication token received")
                    return False
            else:
                print_error(f"Authentication failed: {response.status_code}")
                if response.text:
                    print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print_error(f"Authentication request failed: {e}")
            return False

    def get_repository_info(self, repository: str) -> dict | None:
        """Get current repository information.

        Args:
            repository: Repository name (e.g., "username/repository")

        Returns:
            Repository information dict or None if failed
        """
        print_info(f"Getting repository info for {repository}...")

        try:
            response = self.session.get(
                f"{self.BASE_URL}/repositories/{repository}/",
                headers={"Authorization": f"JWT {self._auth_token}"},
                timeout=30,
            )

            if response.status_code == 200:
                print_success("Repository info retrieved")
                return response.json()
            else:
                print_error(f"Failed to get repository info: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print_error(f"Repository info request failed: {e}")
            return None

    def update_repository_description(
        self,
        repository: str,
        full_description: str,
        short_description: str | None = None,
    ) -> bool:
        """Update repository description.

        Args:
            repository: Repository name (e.g., "username/repository")
            full_description: Full README content
            short_description: Short description (optional)

        Returns:
            True if update successful, False otherwise
        """
        print_info(f"Updating description for {repository}...")

        # Get current repository info
        repo_info = self.get_repository_info(repository)
        if not repo_info:
            return False

        # Prepare update data
        update_data = {"full_description": full_description}

        if short_description:
            update_data["description"] = short_description

        try:
            response = self.session.patch(
                f"{self.BASE_URL}/repositories/{repository}/",
                json=update_data,
                headers={"Authorization": f"JWT {self._auth_token}"},
                timeout=30,
            )

            if response.status_code == 200:
                print_success("Repository description updated successfully")
                return True
            else:
                print_error(f"Failed to update description: {response.status_code}")
                if response.text:
                    print_error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print_error(f"Update request failed: {e}")
            return False


def load_readme_file(file_path: Path) -> str | None:
    """Load README file content.

    Args:
        file_path: Path to README file

    Returns:
        README content or None if failed
    """
    print_info(f"Loading README from {file_path}...")

    try:
        if not file_path.exists():
            print_error(f"README file not found: {file_path}")
            return None

        content = file_path.read_text(encoding="utf-8")
        print_success(f"README loaded ({len(content)} characters)")
        return content

    except Exception as e:
        print_error(f"Failed to load README: {e}")
        return None


def get_config() -> dict:
    """Get configuration from environment variables and defaults.

    Returns:
        Configuration dictionary
    """
    config = {
        "username": os.getenv("DOCKER_USERNAME"),
        "token": os.getenv("DOCKER_TOKEN"),
        "repository": os.getenv("DOCKER_REPOSITORY", "docdyhr/simplenote-mcp-server"),
        "readme_file": os.getenv("README_FILE", "DOCKER_README.md"),
        "short_description": os.getenv(
            "SHORT_DESCRIPTION",
            "A Model Context Protocol (MCP) server that provides seamless "
            "integration with Simplenote for note management and search capabilities.",
        ),
    }

    return config


def validate_config(config: dict) -> bool:
    """Validate configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid, False otherwise
    """
    print_info("Validating configuration...")

    if not config["username"]:
        print_error("DOCKER_USERNAME environment variable not set")
        return False

    if not config["token"]:
        print_error("DOCKER_TOKEN environment variable not set")
        return False

    if not config["repository"]:
        print_error("Repository name not specified")
        return False

    readme_path = Path(config["readme_file"])
    if not readme_path.exists():
        print_error(f"README file not found: {readme_path}")
        return False

    print_success("Configuration valid")
    return True


def main() -> int:
    """Main function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print(f"{Colors.BOLD}{Colors.BLUE}Docker Hub README Update Script{Colors.RESET}\n")

    # Get and validate configuration
    config = get_config()
    if not validate_config(config):
        print_error("Configuration validation failed")
        return 1

    # Load README content
    readme_path = Path(config["readme_file"])
    readme_content = load_readme_file(readme_path)
    if not readme_content:
        return 1

    # Initialize Docker Hub API client
    api = DockerHubAPI(config["username"], config["token"])

    # Authenticate
    if not api.authenticate():
        print_error("Authentication failed")
        return 1

    # Update repository description
    success = api.update_repository_description(
        config["repository"], readme_content, config["short_description"]
    )

    if success:
        print_success(
            f"\n🎉 Docker Hub repository '{config['repository']}' updated successfully!"
        )
        print_info(f"View at: https://hub.docker.com/r/{config['repository']}")
        return 0
    else:
        print_error("\n❌ Failed to update Docker Hub repository")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
