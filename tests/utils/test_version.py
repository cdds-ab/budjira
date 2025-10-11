"""Tests for version checking."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from budjira.utils.version import VersionChecker

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_settings(temp_cache_dir: Path) -> MagicMock:
    """Mock settings."""
    settings = MagicMock()
    settings.data_dir = temp_cache_dir
    settings.global_config.update_check_interval_hours = 24
    return settings


@pytest.fixture
def version_checker(mock_settings: MagicMock) -> VersionChecker:
    """Create version checker with mocked settings."""
    with patch("budjira.utils.version.get_settings", return_value=mock_settings):
        return VersionChecker()


class TestVersionChecker:
    """Test VersionChecker class."""

    def test_is_newer_version(self, version_checker: VersionChecker) -> None:
        """Test version comparison."""
        version_checker.current_version = "0.1.0"

        assert version_checker._is_newer_version("0.2.0") is True
        assert version_checker._is_newer_version("1.0.0") is True
        assert version_checker._is_newer_version("0.1.1") is True
        assert version_checker._is_newer_version("0.1.0") is False
        assert version_checker._is_newer_version("0.0.9") is False

    def test_is_newer_version_with_different_lengths(self, version_checker: VersionChecker) -> None:
        """Test version comparison with different part lengths."""
        version_checker.current_version = "0.1"

        assert version_checker._is_newer_version("0.1.0") is False
        assert version_checker._is_newer_version("0.2") is True

    def test_cache_save_and_load(self, version_checker: VersionChecker) -> None:
        """Test saving and loading cache."""
        version_checker._save_cache(
            latest_version="0.2.0",
            release_url="https://github.com/test/releases/tag/v0.2.0",
            release_notes="Test release notes",
        )

        cached = version_checker._load_cache()

        assert cached is not None
        assert cached["latest_version"] == "0.2.0"
        assert cached["release_url"] == "https://github.com/test/releases/tag/v0.2.0"
        assert cached["release_notes"] == "Test release notes"

    def test_cache_expired(self, version_checker: VersionChecker) -> None:
        """Test that expired cache returns None."""
        # Create expired cache
        cache_data = {
            "checked_at": (datetime.now() - timedelta(hours=25)).isoformat(),
            "current_version": "0.1.0",
            "latest_version": "0.2.0",
            "release_url": "https://test.com",
            "release_notes": "Test",
        }

        version_checker.cache_file.write_text(json.dumps(cache_data))

        cached = version_checker._load_cache()
        assert cached is None

    def test_cache_valid(self, version_checker: VersionChecker) -> None:
        """Test that valid cache is loaded."""
        # Create valid cache
        cache_data = {
            "checked_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "current_version": "0.1.0",
            "latest_version": "0.2.0",
            "release_url": "https://test.com",
            "release_notes": "Test",
        }

        version_checker.cache_file.write_text(json.dumps(cache_data))

        cached = version_checker._load_cache()
        assert cached is not None
        assert cached["latest_version"] == "0.2.0"

    def test_check_for_updates_with_cache(self, version_checker: VersionChecker) -> None:
        """Test checking for updates with valid cache."""
        version_checker.current_version = "0.1.0"

        # Create valid cache
        cache_data = {
            "checked_at": datetime.now().isoformat(),
            "current_version": "0.1.0",
            "latest_version": "0.2.0",
            "release_url": "https://test.com",
            "release_notes": "Test notes",
        }

        version_checker.cache_file.write_text(json.dumps(cache_data))

        update_available, latest, url, notes = version_checker.check_for_updates(force=False)

        assert update_available is True
        assert latest == "0.2.0"
        assert url == "https://test.com"
        assert notes == "Test notes"

    def test_check_for_updates_force(self, version_checker: VersionChecker) -> None:
        """Test checking for updates with force (bypasses cache)."""
        version_checker.current_version = "0.1.0"

        # Create valid cache with old version
        cache_data = {
            "checked_at": datetime.now().isoformat(),
            "current_version": "0.1.0",
            "latest_version": "0.2.0",
            "release_url": "https://old.com",
            "release_notes": "Old notes",
        }

        version_checker.cache_file.write_text(json.dumps(cache_data))

        # Mock GitHub API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v0.3.0",
            "html_url": "https://new.com",
            "body": "New notes",
        }

        with patch("requests.get", return_value=mock_response):
            update_available, latest, url, notes = version_checker.check_for_updates(force=True)

            assert update_available is True
            assert latest == "0.3.0"
            assert url == "https://new.com"
            assert notes == "New notes"

    def test_check_for_updates_network_error(self, version_checker: VersionChecker) -> None:
        """Test checking for updates with network error."""
        import requests

        version_checker.current_version = "0.1.0"

        with patch("budjira.utils.version.requests.get", side_effect=requests.RequestException("Network error")):
            update_available, latest, url, notes = version_checker.check_for_updates(force=True)

            assert update_available is False
            assert latest is None
            assert url is None
            assert notes is None

    def test_check_for_updates_no_update_needed(self, version_checker: VersionChecker) -> None:
        """Test checking when no update is needed."""
        version_checker.current_version = "1.0.0"

        # Mock GitHub API with same version
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
            "html_url": "https://test.com",
            "body": "Current version",
        }

        with patch("requests.get", return_value=mock_response):
            update_available, latest, _url, _notes = version_checker.check_for_updates(force=True)

            assert update_available is False
            assert latest == "1.0.0"

    def test_perform_update_success(self, version_checker: VersionChecker) -> None:
        """Test successful update."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Update successful"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            success, message = version_checker.perform_update()

            assert success is True
            assert "successful" in message.lower()

    def test_perform_update_failure(self, version_checker: VersionChecker) -> None:
        """Test failed update."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Update failed"

        with patch("subprocess.run", return_value=mock_result):
            success, message = version_checker.perform_update()

            assert success is False
            assert "failed" in message.lower()

    def test_perform_update_timeout(self, version_checker: VersionChecker) -> None:
        """Test update timeout."""
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 120)):
            success, message = version_checker.perform_update()

            assert success is False
            assert "timed out" in message.lower()
