"""Global configuration model."""

from enum import Enum

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


class GlobalConfig(BaseModel):
    """Global budjira configuration.

    These settings apply across all connections and can be overridden
    via environment variables or command-line flags.
    """

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Default logging level",
    )
    check_updates: bool = Field(
        default=True,
        description="Check for updates on startup",
    )
    update_check_interval_hours: int = Field(
        default=24,
        description="Hours between update checks",
        ge=1,
        le=168,
    )
    default_output_format: OutputFormat = Field(
        default=OutputFormat.TABLE,
        description="Default output format for search results",
    )
    max_search_results: int = Field(
        default=50,
        description="Maximum number of search results to display",
        ge=1,
        le=1000,
    )
    cache_enabled_by_default: bool = Field(
        default=False,
        description="Enable caching for new connections by default",
    )
    editor: str = Field(
        default="vim",
        description="Default text editor for issue creation/editing",
    )
    timezone: str = Field(
        default="UTC",
        description="Default timezone for time logging",
    )
    active_connection: str | None = Field(
        default=None,
        description="Name of the currently active connection",
    )

    model_config = {"use_enum_values": True, "validate_assignment": True}
