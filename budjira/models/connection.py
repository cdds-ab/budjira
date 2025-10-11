"""Connection model for Jira instances."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Connection(BaseModel):
    """Represents a Jira connection configuration.

    Each connection is identified by a project root path, allowing multiple
    Jira instances/projects to be managed simultaneously.
    """

    name: str = Field(
        ...,
        description="Human-readable name for this connection",
        min_length=1,
    )
    url: HttpUrl = Field(
        ...,
        description="Jira instance URL (e.g., https://company.atlassian.net)",
    )
    email: str = Field(
        ...,
        description="Email address for authentication",
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
    project_key: str = Field(
        ...,
        description="Default Jira project key (e.g., PROJ)",
        min_length=1,
        max_length=10,
    )
    project_root: Path = Field(
        ...,
        description="Local project root path that identifies this connection",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this connection is currently active",
    )
    cache_enabled: bool = Field(
        default=False,
        description="Whether to cache issues for offline access",
    )
    cache_ttl_hours: int = Field(
        default=24,
        description="Cache time-to-live in hours",
        ge=1,
        le=168,  # Max 1 week
    )

    @field_validator("project_root", mode="before")
    @classmethod
    def resolve_project_root(cls, v: str | Path) -> Path:
        """Resolve project root to absolute path."""
        path = Path(v).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"Project root does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Project root must be a directory: {path}")
        return path

    @field_validator("project_key")
    @classmethod
    def validate_project_key(cls, v: str) -> str:
        """Validate project key format (uppercase alphanumeric)."""
        if not v.isupper():
            raise ValueError("Project key must be uppercase")
        if not v.replace("_", "").isalnum():
            raise ValueError("Project key must contain only alphanumeric characters and underscores")
        return v

    def get_credential_key(self) -> str:
        """Generate unique key for credential storage.

        Returns:
            String key based on project root path
        """
        # Use resolved absolute path to ensure uniqueness
        return f"budjira_{self.project_root.as_posix().replace('/', '_')}"

    model_config = {"frozen": False, "validate_assignment": True}


class ConnectionList(BaseModel):
    """List of all configured connections."""

    connections: list[Connection] = Field(
        default_factory=list,
        description="List of configured Jira connections",
    )

    def find_by_root(self, root: Path) -> Connection | None:
        """Find connection by project root path.

        Args:
            root: Project root path to search for

        Returns:
            Connection if found, None otherwise
        """
        resolved_root = root.expanduser().resolve()
        for conn in self.connections:
            if conn.project_root == resolved_root:
                return conn
        return None

    def find_by_name(self, name: str) -> Connection | None:
        """Find connection by name.

        Args:
            name: Connection name to search for

        Returns:
            Connection if found, None otherwise
        """
        for conn in self.connections:
            if conn.name == name:
                return conn
        return None

    def add(self, connection: Connection) -> None:
        """Add a new connection.

        Args:
            connection: Connection to add

        Raises:
            ValueError: If connection with same root already exists
        """
        if self.find_by_root(connection.project_root):
            raise ValueError(
                f"Connection for project root '{connection.project_root}' already exists. "
                f"Use a different project root or update the existing connection."
            )
        self.connections.append(connection)

    def remove(self, root: Path) -> bool:
        """Remove connection by project root.

        Args:
            root: Project root of connection to remove

        Returns:
            True if connection was removed, False if not found
        """
        conn = self.find_by_root(root)
        if conn:
            self.connections.remove(conn)
            return True
        return False

    def update(self, connection: Connection) -> bool:
        """Update existing connection.

        Args:
            connection: Connection with updated values

        Returns:
            True if connection was updated, False if not found
        """
        for i, conn in enumerate(self.connections):
            if conn.project_root == connection.project_root:
                self.connections[i] = connection
                return True
        return False
