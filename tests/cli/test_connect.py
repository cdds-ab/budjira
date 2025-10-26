"""Tests for connect command."""

from __future__ import annotations

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl and Path fields during validation
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from budjira.cli.main import app
from budjira.models.connection import Connection
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


@pytest.fixture
def mock_jira() -> MagicMock:
    """Mock JIRA client."""
    jira_mock = MagicMock()
    jira_mock.server_info.return_value = {
        "version": "9.0.0",
        "buildNumber": "12345",
        "serverTitle": "Test Jira",
    }
    jira_mock.current_user.return_value = "test@example.com"
    return jira_mock


class TestConnectList:
    """Test connect list command."""

    def test_list_no_connections(self, tmp_path: Path) -> None:
        """Test listing when no connections exist."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(app, ["connect", "list"])

            assert result.exit_code == 0
            assert "No connections configured" in result.stdout

    def test_list_with_connections(self, tmp_path: Path) -> None:
        """Test listing existing connections."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            # Add a connection
            conn = Connection(
                name="Test Connection",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)

            result = runner.invoke(app, ["connect", "list"])

            assert result.exit_code == 0
            # Connection name may be split across lines in table
            assert "Test" in result.stdout
            assert "Connection" in result.stdout
            assert "test.atlassian.net" in result.stdout or "https://tes" in result.stdout
            assert "TEST" in result.stdout


class TestConnectShow:
    """Test connect show command."""

    def test_show_by_name(self, tmp_path: Path) -> None:
        """Test showing connection by name."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings

            # Add a connection
            conn = Connection(
                name="My Connection",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)

            result = runner.invoke(app, ["connect", "show", "My Connection"])

            assert result.exit_code == 0
            assert "My Connection" in result.stdout
            assert "test.atlassian.net" in result.stdout
            assert "test@example.com" in result.stdout
            assert "TEST" in result.stdout

    def test_show_not_found(self, tmp_path: Path) -> None:
        """Test showing non-existent connection."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(app, ["connect", "show", "NonExistent"])

            assert result.exit_code == 1
            assert "not found" in result.stdout.lower()


class TestConnectRemove:
    """Test connect remove command."""

    def test_remove_with_force(self, tmp_path: Path) -> None:
        """Test removing connection with --force."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings

            # Add a connection
            conn = Connection(
                name="To Remove",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)

            result = runner.invoke(app, ["connect", "remove", "To Remove", "--force"])

            assert result.exit_code == 0
            assert "Removed connection" in result.stdout

            # Verify connection was removed
            assert settings.connections.find_by_name("To Remove") is None

    def test_remove_not_found(self, tmp_path: Path) -> None:
        """Test removing non-existent connection."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(app, ["connect", "remove", "NonExistent", "--force"])

            assert result.exit_code == 1
            assert "not found" in result.stdout.lower()


class TestConnectTest:
    """Test connect test command."""

    def test_test_connection_success(self, tmp_path: Path, mock_jira: MagicMock) -> None:
        """Test successful connection test."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
            patch("jira.JIRA", return_value=mock_jira),
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings
            credential_store = get_credential_store()

            # Add a connection with credentials
            conn = Connection(
                name="Test Conn",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            credential_store.store(conn, "test-token")

            result = runner.invoke(app, ["connect", "test", "Test Conn"])

            assert result.exit_code == 0
            assert "Connection successful" in result.stdout
            assert "9.0.0" in result.stdout

    def test_test_connection_missing_credentials(self, tmp_path: Path) -> None:
        """Test connection test with missing credentials."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings

            # Add connection without credentials
            conn = Connection(
                name="No Creds",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)

            result = runner.invoke(app, ["connect", "test", "No Creds"])

            assert result.exit_code == 1
            assert "No API token" in result.stdout

    def test_test_connection_failure(self, tmp_path: Path) -> None:
        """Test connection test with connection failure."""

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
            patch("jira.JIRA", side_effect=Exception("Connection refused")),
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings
            credential_store = get_credential_store()

            # Add connection with credentials
            conn = Connection(
                name="Fail Conn",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            credential_store.store(conn, "test-token")

            result = runner.invoke(app, ["connect", "test", "Fail Conn"])

            assert result.exit_code == 1
            assert "Connection failed" in result.stdout


class TestConnectTempoSetup:
    """Test connect tempo-setup command."""

    def test_tempo_setup_success_and_persistence(self, tmp_path: Path) -> None:
        """Test that tempo-setup enables Tempo and persists the flag (Bug #4 regression test)."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect.Prompt.ask", return_value="test-tempo-token"),
            patch("budjira.cli.connect.Confirm.ask", return_value=False),  # No existing token
            patch("budjira.tempo.client.TempoClient") as mock_tempo_client,
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            credential_store = get_credential_store()

            # Mock successful Tempo API call
            mock_tempo_instance = MagicMock()
            mock_tempo_instance.get_accounts.return_value = []
            mock_tempo_client.return_value = mock_tempo_instance

            # Add a connection
            conn = Connection(
                name="Test Tempo Setup",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
                tempo_enabled=False,  # Initially disabled
            )
            settings.add_connection(conn)

            # Verify tempo_enabled is initially False
            initial_conn = settings.connections.find_by_name("Test Tempo Setup")
            assert initial_conn is not None
            assert initial_conn.tempo_enabled is False

            # Run tempo-setup command
            result = runner.invoke(app, ["connect", "tempo-setup", "--connection", "Test Tempo Setup"])

            # Assert command succeeded
            assert result.exit_code == 0
            assert "Tempo API connection successful" in result.stdout
            assert "Enabled Tempo integration" in result.stdout

            # Verify tempo_enabled is now True in memory
            loaded_conn = settings.connections.find_by_name("Test Tempo Setup")
            assert loaded_conn is not None
            assert loaded_conn.tempo_enabled is True, "tempo_enabled should be True after tempo-setup"

            # CRITICAL: Reload settings from disk to verify persistence
            settings_reloaded = settings.load_connections()
            conn_reloaded = settings_reloaded.find_by_name("Test Tempo Setup")
            assert conn_reloaded is not None
            assert conn_reloaded.tempo_enabled is True, "tempo_enabled should persist to TOML file"

            # Verify Tempo token was stored
            tempo_key = conn.get_tempo_credential_key()
            assert credential_store.get_credential(tempo_key) is not None

    def test_tempo_setup_with_existing_token_replacement(self, tmp_path: Path) -> None:
        """Test tempo-setup when replacing existing token."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect.Prompt.ask", return_value="new-tempo-token"),
            patch("budjira.cli.connect.Confirm.ask", return_value=True),  # Confirm replacement
            patch("budjira.tempo.client.TempoClient") as mock_tempo_client,
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            credential_store = get_credential_store()

            # Mock successful Tempo API call
            mock_tempo_instance = MagicMock()
            mock_tempo_instance.get_accounts.return_value = []
            mock_tempo_client.return_value = mock_tempo_instance

            # Add a connection with existing Tempo token
            conn = Connection(
                name="Test Replace",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
                tempo_enabled=True,
            )
            settings.add_connection(conn)
            credential_store.store_credential(conn.get_tempo_credential_key(), "old-token")

            # Run tempo-setup command
            result = runner.invoke(app, ["connect", "tempo-setup", "--connection", "Test Replace"])

            # Assert command succeeded
            assert result.exit_code == 0
            assert "Tempo token already configured" in result.stdout
            assert "Tempo API connection successful" in result.stdout

    def test_tempo_setup_api_failure_abort(self, tmp_path: Path) -> None:
        """Test tempo-setup with API failure and user chooses not to save."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect.Prompt.ask", return_value="invalid-token"),
            patch("budjira.cli.connect.Confirm.ask", return_value=False),  # Don't save on failure
            patch("budjira.tempo.client.TempoClient") as mock_tempo_client,
        ):
            # Reset singletons
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            # Mock failed Tempo API call
            mock_tempo_instance = MagicMock()
            mock_tempo_instance.get_accounts.side_effect = Exception("401 Unauthorized")
            mock_tempo_client.return_value = mock_tempo_instance

            # Add a connection
            conn = Connection(
                name="Test Fail",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)

            # Run tempo-setup command
            result = runner.invoke(app, ["connect", "tempo-setup", "--connection", "Test Fail"])

            # Assert command failed
            assert result.exit_code == 1
            assert "Tempo API connection failed" in result.stdout

    def test_tempo_setup_no_connection(self, tmp_path: Path) -> None:
        """Test tempo-setup without specifying connection and no default."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            # Reset singleton
            import budjira.config.settings

            budjira.config.settings._settings = None

            # Run tempo-setup without connection
            result = runner.invoke(app, ["connect", "tempo-setup"])

            # Assert command failed
            assert result.exit_code == 1
            assert "No active connection" in result.stdout
