"""Version checking and update utilities."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from budjira import __version__
from budjira.config import get_settings


class VersionChecker:
    """Check for updates from GitHub Releases."""

    GITHUB_API_URL = "https://api.github.com/repos/cdds-ab/budjira/releases/latest"
    CACHE_FILENAME = "update_check.json"

    def __init__(self) -> None:
        """Initialize version checker."""
        self.settings = get_settings()
        self.cache_file = self.settings.data_dir / self.CACHE_FILENAME
        self.current_version = __version__

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
                return data

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
            response = requests.get(self.GITHUB_API_URL, timeout=10)
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

        except (requests.RequestException, KeyError, ValueError):
            # Network error or API change - return no update available
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

    def perform_update(self) -> tuple[bool, str]:
        """Perform self-update using install script.

        Returns:
            Tuple of (success, message)
        """
        install_script_url = "https://raw.githubusercontent.com/cdds-ab/budjira/master/install.sh"

        try:
            # Download and execute install script
            result = subprocess.run(
                ["sh", "-c", f"curl -LsSf {install_script_url} | sh"],
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
