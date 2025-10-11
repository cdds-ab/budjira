"""Tests for global configuration model."""

from budjira.models.config import GlobalConfig, LogLevel, OutputFormat


class TestGlobalConfig:
    """Test GlobalConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = GlobalConfig()

        assert config.log_level == LogLevel.INFO
        assert config.check_updates is True
        assert config.update_check_interval_hours == 24
        assert config.default_output_format == OutputFormat.TABLE
        assert config.max_search_results == 50
        assert config.cache_enabled_by_default is False
        assert config.editor == "vim"
        assert config.timezone == "UTC"

    def test_custom_config(self) -> None:
        """Test creating custom configuration."""
        config = GlobalConfig(
            log_level=LogLevel.DEBUG,
            check_updates=False,
            update_check_interval_hours=48,
            default_output_format=OutputFormat.JSON,
            max_search_results=100,
            cache_enabled_by_default=True,
            editor="nano",
            timezone="Europe/Berlin",
        )

        assert config.log_level == LogLevel.DEBUG
        assert config.check_updates is False
        assert config.update_check_interval_hours == 48
        assert config.default_output_format == OutputFormat.JSON
        assert config.max_search_results == 100
        assert config.cache_enabled_by_default is True
        assert config.editor == "nano"
        assert config.timezone == "Europe/Berlin"

    def test_serialization(self) -> None:
        """Test config serialization to dict."""
        config = GlobalConfig(log_level=LogLevel.DEBUG)
        data = config.model_dump()

        assert data["log_level"] == "DEBUG"
        assert "check_updates" in data

    def test_deserialization(self) -> None:
        """Test config deserialization from dict."""
        data = {
            "log_level": "WARNING",
            "check_updates": False,
            "update_check_interval_hours": 72,
            "default_output_format": "csv",
            "max_search_results": 200,
            "cache_enabled_by_default": True,
            "editor": "emacs",
            "timezone": "US/Pacific",
        }

        config = GlobalConfig(**data)

        assert config.log_level == LogLevel.WARNING
        assert config.check_updates is False
        assert config.default_output_format == OutputFormat.CSV
