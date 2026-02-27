# mypy: disable-error-code="arg-type"
"""Tests for MetadataCache."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from budjira.config.metadata_cache import MetadataCache

if TYPE_CHECKING:
    from pathlib import Path
from budjira.models.connection import Connection
from budjira.models.project_metadata import (
    IssueTypeMetadata,
    ProjectMetadata,
)


def _make_connection(name: str = "test-conn") -> Connection:
    """Create a test connection."""
    return Connection(
        name=name,
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
        cache_ttl_hours=24,
    )


def _make_metadata(project_key: str = "TEST", hours_ago: int = 0) -> ProjectMetadata:
    """Create test metadata, optionally aged."""
    fetched_at = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
    return ProjectMetadata(
        project_key=project_key,
        project_name="Test Project",
        issue_types=[
            IssueTypeMetadata(id="1", name="Bug"),
            IssueTypeMetadata(id="2", name="Story"),
        ],
        priorities=["High", "Medium", "Low"],
        components=["Backend", "Frontend"],
        fetched_at=fetched_at,
    )


class TestMetadataCache:
    """Test MetadataCache operations."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading metadata."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()
        metadata = _make_metadata()

        cache.save(conn, metadata)
        loaded = cache.load(conn)

        assert loaded is not None
        assert loaded.project_key == "TEST"
        assert loaded.project_name == "Test Project"
        assert len(loaded.issue_types) == 2
        assert loaded.priorities == ["High", "Medium", "Low"]
        assert loaded.components == ["Backend", "Frontend"]

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Test loading when no cache exists."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()

        assert cache.load(conn) is None

    def test_load_corrupt_file(self, tmp_path: Path) -> None:
        """Test loading corrupt cache file returns None."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()

        cache_path = tmp_path / "test_conn_metadata.json"
        cache_path.write_text("not valid json{{{", encoding="utf-8")

        assert cache.load(conn) is None

    def test_clear_existing(self, tmp_path: Path) -> None:
        """Test clearing existing cache."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()
        metadata = _make_metadata()

        cache.save(conn, metadata)
        assert cache.clear(conn) is True
        assert cache.load(conn) is None

    def test_clear_nonexistent(self, tmp_path: Path) -> None:
        """Test clearing when no cache exists."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()

        assert cache.clear(conn) is False

    def test_is_valid_fresh(self, tmp_path: Path) -> None:
        """Test that fresh cache is valid."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()
        metadata = _make_metadata(hours_ago=0)

        cache.save(conn, metadata)
        assert cache.is_valid(conn) is True

    def test_is_valid_stale(self, tmp_path: Path) -> None:
        """Test that stale cache is invalid."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()
        metadata = _make_metadata(hours_ago=25)

        cache.save(conn, metadata)
        assert cache.is_valid(conn) is False

    def test_is_valid_no_cache(self, tmp_path: Path) -> None:
        """Test that missing cache is invalid."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection()

        assert cache.is_valid(conn) is False

    def test_cache_path_sanitization(self, tmp_path: Path) -> None:
        """Test that connection names with special chars are sanitized."""
        cache = MetadataCache(tmp_path)
        conn = _make_connection(name="my project!@#$")
        metadata = _make_metadata()

        cache.save(conn, metadata)

        # Should create a safe filename
        files = list(tmp_path.glob("*_metadata.json"))
        assert len(files) == 1
        assert "!" not in files[0].name

    def test_creates_cache_dir(self, tmp_path: Path) -> None:
        """Test that cache directory is created if missing."""
        cache_dir = tmp_path / "deep" / "nested" / "cache"
        cache = MetadataCache(cache_dir)

        assert cache_dir.exists()

        conn = _make_connection()
        metadata = _make_metadata()
        cache.save(conn, metadata)

        assert cache.load(conn) is not None
