"""Version checking and update utilities."""

from __future__ import annotations

import json
import logging
import subprocess  # nosec B404
from datetime import datetime, timedelta
from enum import Enum
from itertools import pairwise
from pathlib import Path
from typing import Any, ClassVar

import requests

from budjira import __version__
from budjira.config import get_settings

logger = logging.getLogger(__name__)


class InstallMethod(str, Enum):
    """How the running budjira was installed."""

    GIT_CLONE = "git-clone"
    UV_TOOL = "uv-tool"
    PIPX = "pipx"
    UNKNOWN = "unknown"


def detect_install_method(package_path: Path | None = None) -> InstallMethod:
    """Detect how the running budjira was installed.

    Detection is based on where the ``budjira`` package lives: uv and pipx both
    place tool environments in recognizable directory layouts, and the install
    script places a git checkout that carries a ``.git`` directory.

    Args:
        package_path: Path of the budjira package (defaults to the running one)

    Returns:
        The detected install method, or ``InstallMethod.UNKNOWN``
    """
    resolved = (package_path or Path(__file__).parent.parent).resolve()
    parts = resolved.parts

    for first, second in pairwise(parts):
        if (first, second) == ("uv", "tools"):
            return InstallMethod.UV_TOOL
        if (first, second) == ("pipx", "venvs"):
            return InstallMethod.PIPX

    for parent in resolved.parents:
        if (parent / ".git").exists():
            return InstallMethod.GIT_CLONE

    return InstallMethod.UNKNOWN


class VersionChecker:
    """Check for updates from GitHub Releases."""

    GITHUB_API_URL = "https://api.github.com/repos/cdds-ab/budjira/releases/latest"
    CACHE_FILENAME = "update_check.json"

    def __init__(self) -> None:
        """Initialize version checker."""
        self.settings = get_settings()
        self.cache_file = self.settings.data_dir / self.CACHE_FILENAME
        self.current_version = __version__

    def _get_headers(self) -> dict[str, str]:
        """Get headers for GitHub API request with optional authentication.

        Returns:
            Headers dict with optional GitHub token
        """
        import os

        headers = {"Accept": "application/vnd.github.v3+json"}

        # Use GitHub token if available (avoids rate limiting)
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        return headers

    def _load_cache(self) -> dict[str, Any] | None:
        """Load cached update check result.

        Returns:
            Cached data if exists and valid, None otherwise
        """
        if not self.cache_file.exists():
            return None

        try:
            data = json.loads(self.cache_file.read_text())

            # Check if cache is still valid
            checked_at = datetime.fromisoformat(data["checked_at"])
            cache_ttl = timedelta(hours=self.settings.global_config.update_check_interval_hours)

            if datetime.now() - checked_at < cache_ttl:
                return data  # type: ignore[no-any-return]

            return None
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _save_cache(self, latest_version: str, release_url: str, release_notes: str) -> None:
        """Save update check result to cache.

        Args:
            latest_version: Latest version from GitHub
            release_url: URL to the release page
            release_notes: Release notes/body
        """
        data = {
            "checked_at": datetime.now().isoformat(),
            "current_version": self.current_version,
            "latest_version": latest_version,
            "release_url": release_url,
            "release_notes": release_notes,
        }

        self.cache_file.write_text(json.dumps(data, indent=2))

    def check_for_updates(self, force: bool = False) -> tuple[bool, str | None, str | None, str | None]:
        """Check if a new version is available.

        Args:
            force: Force check even if cache is valid

        Returns:
            Tuple of (update_available, latest_version, release_url, release_notes)
        """
        # Load from cache unless forced
        if not force:
            cached = self._load_cache()
            if cached:
                return (
                    self._is_newer_version(cached["latest_version"]),
                    cached["latest_version"],
                    cached["release_url"],
                    cached["release_notes"],
                )

        # Fetch from GitHub API
        try:
            response = requests.get(self.GITHUB_API_URL, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            release_data = response.json()

            latest_version = release_data["tag_name"].lstrip("v")
            release_url = release_data["html_url"]
            release_notes = release_data.get("body", "")

            # Save to cache
            self._save_cache(latest_version, release_url, release_notes)

            return (
                self._is_newer_version(latest_version),
                latest_version,
                release_url,
                release_notes,
            )

        except requests.RequestException as e:
            # Network error or API rate limiting
            logger.warning(f"Failed to check for updates: {e}")
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 403:
                logger.info(
                    "GitHub API rate limit may be exceeded. "
                    "Set GITHUB_TOKEN or GH_TOKEN environment variable to increase limits."
                )
            return (False, None, None, None)
        except (KeyError, ValueError) as e:
            # API response format changed
            logger.warning(f"Failed to parse GitHub API response: {e}")
            return (False, None, None, None)

    def _is_newer_version(self, latest_version: str) -> bool:
        """Check if latest version is newer than current.

        Args:
            latest_version: Version string to compare

        Returns:
            True if latest is newer than current
        """
        try:
            # Simple version comparison (assumes semantic versioning)
            current_parts = [int(x) for x in self.current_version.split(".")]
            latest_parts = [int(x) for x in latest_version.split(".")]

            # Pad to same length
            max_len = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))

            return latest_parts > current_parts

        except (ValueError, AttributeError):
            return False

    INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/cdds-ab/budjira/master/install.sh"

    UPGRADE_COMMANDS: ClassVar[dict[InstallMethod, list[str]]] = {
        InstallMethod.UV_TOOL: ["uv", "tool", "upgrade", "budjira"],
        InstallMethod.PIPX: ["pipx", "upgrade", "budjira"],
    }

    def perform_update(self) -> tuple[bool, str]:
        """Perform self-update using the mechanism matching the install method.

        Returns:
            Tuple of (success, message)
        """
        method = detect_install_method()
        logger.debug(f"Detected install method: {method.value}")

        if method is InstallMethod.UNKNOWN:
            # Running the install script here would create a second, git-clone
            # install that can shadow the real one depending on PATH order.
            return (
                False,
                "Could not determine how budjira was installed, so it was not touched. "
                "Please update it manually with the tool you installed it with "
                "(for example 'pip install -U', or re-run the install script from the README).",
            )

        if method is InstallMethod.GIT_CLONE:
            command = ["sh", "-c", f"curl -LsSf {self.INSTALL_SCRIPT_URL} | sh"]
        else:
            command = self.UPGRADE_COMMANDS[method]

        try:
            result = subprocess.run(  # nosec B603 B607
                command,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return (True, "Update successful! Restart budjira to use the new version.")
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return (False, f"Update failed: {error_msg}")

        except subprocess.TimeoutExpired:
            return (False, "Update timed out. Please try again.")
        except Exception as e:
            return (False, f"Update failed: {e}")


def get_version_checker() -> VersionChecker:
    """Get version checker instance.

    Returns:
        VersionChecker instance
    """
    return VersionChecker()
