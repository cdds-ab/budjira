"""Tests for settings management."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl and Path fields during validation

from pathlib import Path
from unittest.mock import patch

import pytest
from budjira.config.settings import Settings
from budjira.models.config import GlobalConfig, LogLevel
from budjira.models.connection import Connection
from budjira.models.custom_field import CustomFieldConfig, CustomFieldType


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    """Create settings with temporary directories."""
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"

    with (
        patch("budjira.config.settings.xdg_config_home", return_value=config_dir),
        patch("budjira.config.settings.xdg_data_home", return_value=data_dir),
    ):
        settings = Settings()
        # Reset singleton state
        import budjira.config.settings

        budjira.config.settings._settings = None
        return settings


@pytest.fixture
def test_connection() -> Connection:
    """Create a test connection."""
    return Connection(
        name="Test Connection",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
    )


class TestSettings:
    """Test Settings class."""

    def test_initialization_creates_directories(self, temp_settings: Settings) -> None:
        """Test that initialization creates all required directories."""
        assert temp_settings.config_dir.exists()
        assert temp_settings.data_dir.exists()
        assert temp_settings.credentials_dir.exists()
        assert temp_settings.cache_dir.exists()
        assert temp_settings.logs_dir.exists()

    def test_credentials_dir_has_restricted_permissions(self, temp_settings: Settings) -> None:
        """Test that credentials directory has owner-only permissions."""
        # Check that directory exists and has 700 permissions
        assert temp_settings.credentials_dir.exists()
        mode = oct(temp_settings.credentials_dir.stat().st_mode)[-3:]
        assert mode == "700"

    def test_load_default_global_config(self, temp_settings: Settings) -> None:
        """Test loading global config creates default if not exists."""
        config = temp_settings.global_config

        assert isinstance(config, GlobalConfig)
        assert config.log_level == LogLevel.INFO
        assert temp_settings.config_file.exists()

    def test_save_and_load_global_config(self, temp_settings: Settings) -> None:
        """Test saving and loading global config."""
        custom_config = GlobalConfig(
            log_level=LogLevel.DEBUG,
            check_updates=False,
            max_search_results=100,
        )

        temp_settings.save_global_config(custom_config)

        # Load again
        loaded = temp_settings.load_global_config()

        assert loaded.log_level == LogLevel.DEBUG
        assert loaded.check_updates is False
        assert loaded.max_search_results == 100

    def test_load_empty_connections(self, temp_settings: Settings) -> None:
        """Test loading connections when file doesn't exist."""
        connections = temp_settings.connections

        assert len(connections.connections) == 0

    def test_save_and_load_connections(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test saving and loading connections."""
        temp_settings.add_connection(test_connection)

        # Load again
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        conn = loaded.connections[0]
        assert conn.name == test_connection.name
        assert str(conn.url) == str(test_connection.url)
        assert conn.email == test_connection.email
        assert conn.project_key == test_connection.project_key

    def test_add_connection(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test adding a connection."""
        temp_settings.add_connection(test_connection)

        connections = temp_settings.connections
        assert len(connections.connections) == 1
        assert connections.connections[0].name == test_connection.name

    def test_add_duplicate_connection_raises_error(self, temp_settings: Settings) -> None:
        """Test that adding duplicate connection raises error."""
        conn1 = Connection(
            name="Test",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )
        temp_settings.add_connection(conn1)

        # Try to add another with same name
        conn2 = Connection(
            name="Test",  # Same name!
            url="https://different.atlassian.net",
            email="different@example.com",
            project_key="DIFF",
        )

        with pytest.raises(ValueError, match="already exists"):
            temp_settings.add_connection(conn2)

    def test_remove_connection(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test removing a connection."""
        temp_settings.add_connection(test_connection)
        assert len(temp_settings.connections.connections) == 1

        removed = temp_settings.remove_connection(test_connection.name)
        assert removed is True

        connections = temp_settings.load_connections()
        assert len(connections.connections) == 0

    def test_remove_nonexistent_connection(self, temp_settings: Settings) -> None:
        """Test removing a connection that doesn't exist."""
        removed = temp_settings.remove_connection("NonExistent")
        assert removed is False

    def test_update_connection(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test updating a connection."""
        temp_settings.add_connection(test_connection)

        # Update connection
        test_connection.name = "Test Connection"  # Keep same name
        test_connection.cache_enabled = True

        updated = temp_settings.update_connection(test_connection)
        assert updated is True

        connections = temp_settings.load_connections()
        conn = connections.connections[0]
        assert conn.cache_enabled is True

    def test_get_log_file(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test getting log file path for connection."""
        log_file = temp_settings.get_log_file(test_connection)

        assert log_file.parent == temp_settings.logs_dir
        assert log_file.suffix == ".log"
        assert "Test_Connection" in log_file.name

    def test_get_cache_file(self, temp_settings: Settings, test_connection: Connection) -> None:
        """Test getting cache file path for connection."""
        cache_file = temp_settings.get_cache_file(test_connection)

        assert cache_file.parent == temp_settings.cache_dir
        assert cache_file.suffix == ".db"
        assert "Test_Connection" in cache_file.name

    def test_singleton_pattern(self, tmp_path: Path) -> None:
        """Test that get_settings returns same instance."""
        from budjira.config.settings import get_settings

        config_dir = tmp_path / "config"
        data_dir = tmp_path / "data"

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=config_dir),
            patch("budjira.config.settings.xdg_data_home", return_value=data_dir),
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

    def test_tempo_enabled_persistence(self, temp_settings: Settings) -> None:
        """Test that tempo_enabled field is correctly saved and loaded (Bug #4 regression test)."""
        # Create connection with Tempo enabled
        connection = Connection(
            name="Test Tempo",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            tempo_enabled=True,
        )

        # Save connection
        temp_settings.add_connection(connection)

        # Load connections again to verify persistence
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]
        assert loaded_conn.tempo_enabled is True, "tempo_enabled should be persisted to TOML"

    def test_tempo_disabled_by_default(self, temp_settings: Settings) -> None:
        """Test that tempo_enabled defaults to False when not specified."""
        connection = Connection(
            name="Test Default",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]
        assert loaded_conn.tempo_enabled is False, "tempo_enabled should default to False"

    def test_custom_fields_persistence(self, temp_settings: Settings) -> None:
        """Test that custom_fields are correctly saved and loaded."""
        custom_fields = {
            "affected_system": CustomFieldConfig(
                field_id="customfield_10001",
                type=CustomFieldType.SELECT,
                required=True,
                default="Infrastructure",
                options=["Infrastructure", "Application", "Database"],
                label="Affected System",
            ),
            "environment": CustomFieldConfig(
                field_id="customfield_10002",
                type=CustomFieldType.TEXT,
                required=False,
            ),
        }

        connection = Connection(
            name="Test Custom Fields",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            custom_fields=custom_fields,
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]

        assert len(loaded_conn.custom_fields) == 2

        # Check affected_system field
        assert "affected_system" in loaded_conn.custom_fields
        af = loaded_conn.custom_fields["affected_system"]
        assert af.field_id == "customfield_10001"
        assert af.type == CustomFieldType.SELECT
        assert af.required is True
        assert af.default == "Infrastructure"
        assert af.options == ["Infrastructure", "Application", "Database"]
        assert af.label == "Affected System"

        # Check environment field
        assert "environment" in loaded_conn.custom_fields
        env = loaded_conn.custom_fields["environment"]
        assert env.field_id == "customfield_10002"
        assert env.type == CustomFieldType.TEXT
        assert env.required is False

    def test_custom_fields_empty_by_default(self, temp_settings: Settings) -> None:
        """Test that custom_fields defaults to empty dict when not specified."""
        connection = Connection(
            name="Test No Custom Fields",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]
        assert loaded_conn.custom_fields == {}

    def test_ai_prompt_persistence(self, temp_settings: Settings) -> None:
        """Test that ai_prompt is correctly saved and loaded."""
        ai_prompt = """## Project Workflow

This project uses specific issue types:
- Change: For production changes
- Service Request: For service requests

Always include the affected system field when creating issues.
"""

        connection = Connection(
            name="Test AI Prompt",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            ai_prompt=ai_prompt,
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]
        assert loaded_conn.ai_prompt == ai_prompt
        assert "Change" in loaded_conn.ai_prompt
        assert "Service Request" in loaded_conn.ai_prompt

    def test_ai_prompt_none_by_default(self, temp_settings: Settings) -> None:
        """Test that ai_prompt defaults to None when not specified."""
        connection = Connection(
            name="Test No AI Prompt",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]
        assert loaded_conn.ai_prompt is None

    def test_both_custom_fields_and_ai_prompt(self, temp_settings: Settings) -> None:
        """Test that both custom_fields and ai_prompt work together."""
        custom_fields = {
            "priority_level": CustomFieldConfig(
                field_id="customfield_10003",
                type=CustomFieldType.SELECT,
                options=["P1", "P2", "P3"],
            ),
        }
        ai_prompt = "Use priority_level for all issues."

        connection = Connection(
            name="Test Both Features",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            custom_fields=custom_fields,
            ai_prompt=ai_prompt,
        )

        temp_settings.add_connection(connection)
        loaded = temp_settings.load_connections()

        assert len(loaded.connections) == 1
        loaded_conn = loaded.connections[0]

        # Check custom_fields
        assert len(loaded_conn.custom_fields) == 1
        assert "priority_level" in loaded_conn.custom_fields
        assert loaded_conn.custom_fields["priority_level"].options == ["P1", "P2", "P3"]

        # Check ai_prompt
        assert loaded_conn.ai_prompt == ai_prompt
