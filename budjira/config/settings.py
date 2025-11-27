"""Configuration and settings management using XDG base directories."""

from __future__ import annotations

import sys
from pathlib import Path

import tomli_w
from xdg_base_dirs import xdg_config_home, xdg_data_home

# tomllib is only available in Python 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from budjira.models.ai_prompt import AiPromptTemplate, get_default_ai_prompt_template
from budjira.models.config import GlobalConfig
from budjira.models.connection import Connection, ConnectionList
from budjira.models.dor import DorTemplateConfig, get_default_templates


class Settings:
    """Manages budjira configuration using XDG base directory specification.

    Configuration structure:
    - ~/.config/budjira/config.toml - Global settings
    - ~/.config/budjira/connections.toml - Connection definitions
    - ~/.config/budjira/credentials/ - Per-connection credentials (secure)
    - ~/.local/share/budjira/cache/ - SQLite cache files
    - ~/.local/share/budjira/logs/ - Log files per connection
    """

    def __init__(self) -> None:
        """Initialize settings with XDG paths."""
        self.config_dir = Path(xdg_config_home()) / "budjira"
        self.data_dir = Path(xdg_data_home()) / "budjira"

        # Configuration files
        self.config_file = self.config_dir / "config.toml"
        self.connections_file = self.config_dir / "connections.toml"
        self.dor_templates_file = self.config_dir / "dor-templates.toml"
        self.ai_prompt_template_file = self.config_dir / "ai-prompt-template.toml"

        # Data directories
        self.credentials_dir = self.config_dir / "credentials"
        self.cache_dir = self.data_dir / "cache"
        self.logs_dir = self.data_dir / "logs"

        # Ensure all directories exist
        self._ensure_directories()

        # Load configuration
        self._global_config: GlobalConfig | None = None
        self._connections: ConnectionList | None = None
        self._dor_templates: DorTemplateConfig | None = None
        self._ai_prompt_template: AiPromptTemplate | None = None

    def _ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True, mode=0o700)  # Restrict access
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def global_config(self) -> GlobalConfig:
        """Get global configuration, loading from file if needed.

        Returns:
            Global configuration object
        """
        if self._global_config is None:
            self._global_config = self.load_global_config()
        return self._global_config

    @property
    def connections(self) -> ConnectionList:
        """Get connection list, loading from file if needed.

        Returns:
            Connection list object
        """
        if self._connections is None:
            self._connections = self.load_connections()
        return self._connections

    @property
    def dor_templates(self) -> DorTemplateConfig:
        """Get DoR templates, loading from file if needed.

        Returns:
            DoR template configuration object
        """
        if self._dor_templates is None:
            self._dor_templates = self.load_dor_templates()
        return self._dor_templates

    @property
    def ai_prompt_template(self) -> AiPromptTemplate:
        """Get AI prompt template, loading from file if needed.

        Returns:
            AI prompt template object
        """
        if self._ai_prompt_template is None:
            self._ai_prompt_template = self.load_ai_prompt_template()
        return self._ai_prompt_template

    def load_global_config(self) -> GlobalConfig:
        """Load global configuration from config.toml.

        Returns:
            Global configuration object (defaults if file doesn't exist)
        """
        if not self.config_file.exists():
            # Create default config
            config = GlobalConfig()
            self.save_global_config(config)
            return config

        with self.config_file.open("rb") as f:
            data = tomllib.load(f)

        return GlobalConfig(**data)

    def save_global_config(self, config: GlobalConfig) -> None:
        """Save global configuration to config.toml.

        Args:
            config: Global configuration to save
        """
        with self.config_file.open("wb") as f:
            tomli_w.dump(config.model_dump(exclude_none=True), f)

        self._global_config = config

    def load_connections(self) -> ConnectionList:
        """Load connections from connections.toml.

        Returns:
            Connection list object (empty if file doesn't exist)
        """
        if not self.connections_file.exists():
            return ConnectionList()

        with self.connections_file.open("rb") as f:
            data = tomllib.load(f)

        # Convert connection dicts to Connection objects
        connections = [Connection(**conn) for conn in data.get("connections", [])]
        return ConnectionList(connections=connections)

    def save_connections(self, connections: ConnectionList) -> None:
        """Save connections to connections.toml.

        Args:
            connections: Connection list to save
        """
        # Convert to dict format for TOML
        data = {
            "connections": [
                {
                    "name": conn.name,
                    "url": str(conn.url),
                    "email": conn.email,
                    "project_key": conn.project_key,
                    "is_active": conn.is_active,
                    "cache_enabled": conn.cache_enabled,
                    "cache_ttl_hours": conn.cache_ttl_hours,
                    "tempo_enabled": conn.tempo_enabled,
                }
                for conn in connections.connections
            ]
        }

        with self.connections_file.open("wb") as f:
            tomli_w.dump(data, f)

        self._connections = connections

    def add_connection(self, connection: Connection) -> None:
        """Add a new connection.

        Args:
            connection: Connection to add

        Raises:
            ValueError: If connection with same root already exists
        """
        connections = self.connections
        connections.add(connection)
        self.save_connections(connections)

    def remove_connection(self, name: str) -> bool:
        """Remove connection by name.

        Args:
            name: Name of connection to remove

        Returns:
            True if connection was removed, False if not found
        """
        connections = self.connections
        if connections.remove(name):
            self.save_connections(connections)
            return True
        return False

    def update_connection(self, connection: Connection) -> bool:
        """Update existing connection.

        Args:
            connection: Connection with updated values

        Returns:
            True if connection was updated, False if not found
        """
        connections = self.connections
        if connections.update(connection):
            self.save_connections(connections)
            return True
        return False

    def get_log_file(self, connection: Connection) -> Path:
        """Get log file path for a connection.

        Args:
            connection: Connection to get log file for

        Returns:
            Path to log file
        """
        # Use connection name as log filename (sanitized)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in connection.name)
        return self.logs_dir / f"{safe_name}.log"

    def get_cache_file(self, connection: Connection) -> Path:
        """Get cache database path for a connection.

        Args:
            connection: Connection to get cache file for

        Returns:
            Path to SQLite cache file
        """
        # Use connection name as cache filename (sanitized)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in connection.name)
        return self.cache_dir / f"{safe_name}.db"

    def load_dor_templates(self) -> DorTemplateConfig:
        """Load DoR templates from dor-templates.toml.

        Returns:
            DoR template configuration (defaults if file doesn't exist)
        """
        if not self.dor_templates_file.exists():
            # Create default templates
            config = get_default_templates()
            self.save_dor_templates(config)
            return config

        with self.dor_templates_file.open("rb") as f:
            data = tomllib.load(f)

        return DorTemplateConfig(**data)

    def save_dor_templates(self, config: DorTemplateConfig) -> None:
        """Save DoR templates to dor-templates.toml.

        Args:
            config: DoR template configuration to save
        """
        with self.dor_templates_file.open("wb") as f:
            tomli_w.dump(config.model_dump(exclude_none=True), f)

        self._dor_templates = config

    def load_ai_prompt_template(self) -> AiPromptTemplate:
        """Load AI prompt template from ai-prompt-template.toml.

        Returns:
            AI prompt template (default if file doesn't exist)
        """
        if not self.ai_prompt_template_file.exists():
            # Create default template
            template = get_default_ai_prompt_template()
            self.save_ai_prompt_template(template)
            return template

        with self.ai_prompt_template_file.open("rb") as f:
            data = tomllib.load(f)

        return AiPromptTemplate(**data)

    def save_ai_prompt_template(self, template: AiPromptTemplate) -> None:
        """Save AI prompt template to ai-prompt-template.toml.

        Args:
            template: AI prompt template to save
        """
        with self.ai_prompt_template_file.open("wb") as f:
            tomli_w.dump(template.model_dump(exclude_none=True), f)

        self._ai_prompt_template = template


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get global settings instance (singleton).

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
