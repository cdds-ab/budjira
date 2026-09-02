"""Connection model for Jira instances."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from budjira.models.custom_field import CustomFieldConfig  # noqa: TC001 - needed at runtime for Pydantic

# How the description field is treated on upload. Modelled as an open set of string
# values so a third dialect ("adf", once the client speaks REST v3 - epic #96) can be
# added without changing the config format: unknown values simply fail validation today
# and become valid the moment they are listed here.
DescriptionDialect = Literal["markdown", "wiki"]


class Connection(BaseModel):
    """Represents a Jira connection configuration.

    Each connection is identified by its unique name, allowing multiple
    Jira instances/projects to be managed simultaneously.
    """

    name: str = Field(
        ...,
        description="Unique name for this connection",
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
    tempo_enabled: bool = Field(
        default=False,
        description="Whether Tempo Timesheets integration is enabled for this connection",
    )
    description_dialect: DescriptionDialect = Field(
        default="markdown",
        description=(
            "Dialect descriptions are authored in: 'markdown' converts to Jira wiki markup on "
            "upload, 'wiki' sends the text unchanged"
        ),
    )
    custom_fields: dict[str, CustomFieldConfig] = Field(
        default_factory=dict,
        description="Custom field configurations mapped by friendly name",
    )
    board_id: int | None = Field(
        default=None,
        description="Default board ID for sprint operations",
    )
    ai_prompt: str | None = Field(
        default=None,
        description="Project-specific AI prompt to append to generated usage prompts",
    )
    api_token_ref: str | None = Field(
        default=None,
        description=(
            "Secret reference for the Jira API token (env:NAME, pass:entry, file:/path) instead of a stored token"
        ),
    )
    tempo_token_ref: str | None = Field(
        default=None,
        description=(
            "Secret reference for the Tempo API token (env:NAME, pass:entry, file:/path) instead of a stored token"
        ),
    )

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
            String key based on connection name
        """
        # Use name with prefix for credential storage
        return f"budjira_{self.name.lower().replace(' ', '_')}"

    def get_tempo_credential_key(self) -> str:
        """Generate unique key for Tempo token storage.

        Returns:
            String key for Tempo token based on connection name
        """
        return f"budjira_tempo_{self.name.lower().replace(' ', '_')}"

    model_config = {"frozen": False, "validate_assignment": True}


class ConnectionList(BaseModel):
    """List of all configured connections."""

    connections: list[Connection] = Field(
        default_factory=list,
        description="List of configured Jira connections",
    )

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
            ValueError: If connection with same name already exists
        """
        if self.find_by_name(connection.name):
            raise ValueError(
                f"Connection '{connection.name}' already exists. "
                f"Use a different name or update the existing connection."
            )
        self.connections.append(connection)

    def remove(self, name: str) -> bool:
        """Remove connection by name.

        Args:
            name: Name of connection to remove

        Returns:
            True if connection was removed, False if not found
        """
        conn = self.find_by_name(name)
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
            if conn.name == connection.name:
                self.connections[i] = connection
                return True
        return False
