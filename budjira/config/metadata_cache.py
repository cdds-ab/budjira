"""Metadata cache for storing and retrieving project metadata as JSON."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from budjira.models.project_metadata import ProjectMetadata

if TYPE_CHECKING:
    from pathlib import Path

    from budjira.models.connection import Connection

logger = logging.getLogger(__name__)


class MetadataCache:
    """Cache for project metadata stored as JSON files.

    Storage location: {cache_dir}/{safe_name}_metadata.json
    Uses the connection's cache_ttl_hours for staleness checks.
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialize metadata cache.

        Args:
            cache_dir: Directory for cache files (e.g., ~/.local/share/budjira/cache/)
        """
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, connection: Connection) -> Path:
        """Get cache file path for a connection.

        Args:
            connection: Jira connection

        Returns:
            Path to the metadata JSON cache file
        """
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in connection.name)
        return self._cache_dir / f"{safe_name}_metadata.json"

    def load(self, connection: Connection) -> ProjectMetadata | None:
        """Load cached metadata for a connection.

        Args:
            connection: Jira connection

        Returns:
            ProjectMetadata if cache exists and is valid, None otherwise
        """
        cache_path = self._get_cache_path(connection)
        if not cache_path.exists():
            logger.debug(f"No metadata cache found for connection '{connection.name}'")
            return None

        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            metadata = ProjectMetadata(**data)
            logger.debug(f"Loaded metadata cache for connection '{connection.name}'")
            return metadata
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load metadata cache for '{connection.name}': {e}")
            return None

    def save(self, connection: Connection, metadata: ProjectMetadata) -> None:
        """Save metadata to cache.

        Args:
            connection: Jira connection
            metadata: Project metadata to cache
        """
        cache_path = self._get_cache_path(connection)
        cache_path.write_text(
            metadata.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved metadata cache for connection '{connection.name}'")

    def clear(self, connection: Connection) -> bool:
        """Clear cached metadata for a connection.

        Args:
            connection: Jira connection

        Returns:
            True if cache was deleted, False if it didn't exist
        """
        cache_path = self._get_cache_path(connection)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Cleared metadata cache for connection '{connection.name}'")
            return True
        return False

    def is_valid(self, connection: Connection) -> bool:
        """Check if cached metadata exists and is not stale.

        Args:
            connection: Jira connection (uses cache_ttl_hours for staleness)

        Returns:
            True if cache exists and is fresh
        """
        metadata = self.load(connection)
        if metadata is None:
            return False
        return not metadata.is_stale(connection.cache_ttl_hours)
