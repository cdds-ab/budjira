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


class TestConnectAdd:
    """Test connect add command."""

    def test_add_stores_description_dialect(self, tmp_path: Path) -> None:
        """The dialect can be set when creating a connection."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "WikiHouse",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                    "--description-dialect",
                    "wiki",
                ],
                input="store\ntoken\n",
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("WikiHouse")
            assert stored is not None
            assert stored.description_dialect == "wiki"

    def test_add_keeps_description_dialect_of_existing_connection(self, tmp_path: Path) -> None:
        """Updating a connection without the option must not reset the dialect."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="WikiHouse",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                    description_dialect="wiki",
                )
            )

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "WikiHouse",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                ],
                input="y\nstore\ntoken\n",
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("WikiHouse")
            assert stored is not None
            assert stored.description_dialect == "wiki"

    def test_add_preserves_configuration_of_existing_connection(self, tmp_path: Path) -> None:
        """Updating a connection must not reset fields the command never asked for (#108)."""
        from budjira.models.custom_field import CustomFieldConfig, CustomFieldType

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="Configured",
                    url="https://test.atlassian.net",
                    email="old@example.com",
                    project_key="OLD",
                    tempo_enabled=True,
                    cache_enabled=True,
                    cache_ttl_hours=48,
                    board_id=42,
                    ai_prompt="house rules",
                    custom_fields={
                        "system": CustomFieldConfig(field_id="customfield_10001", type=CustomFieldType.SELECT)
                    },
                )
            )

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "Configured",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "new@example.com",
                    "--project",
                    "NEW",
                ],
                input="y\nstore\ntoken\n",
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("Configured")
            assert stored is not None
            # What was given changes ...
            assert stored.email == "new@example.com"
            assert stored.project_key == "NEW"
            # ... everything else survives
            assert stored.tempo_enabled is True
            assert stored.cache_enabled is True
            assert stored.cache_ttl_hours == 48
            assert stored.board_id == 42
            assert stored.ai_prompt == "house rules"
            assert stored.custom_fields["system"].field_id == "customfield_10001"


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

    def test_list_shows_description_dialect(self, tmp_path: Path) -> None:
        """The listing tells which connection deviates from the Markdown default."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="WikiHouse",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                    description_dialect="wiki",
                )
            )

            result = runner.invoke(app, ["connect", "list"])

            assert result.exit_code == 0
            assert "wiki" in result.stdout


class TestConnectShow:
    """Test connect show command."""

    def test_show_includes_description_dialect(self, tmp_path: Path) -> None:
        """The detail view names the dialect descriptions are sent in."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
        ):
            import budjira.config.settings

            budjira.config.settings._settings = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="WikiHouse",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                    description_dialect="wiki",
                )
            )

            result = runner.invoke(app, ["connect", "show", "WikiHouse"])

            assert result.exit_code == 0
            assert "Description" in result.stdout
            assert "wiki" in result.stdout

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

    def test_test_connection_expired_token(self, tmp_path: Path) -> None:
        """Test that expired/invalid tokens are detected (not silently ignored).

        Regression test for #68: server_info() succeeds without auth on many
        Jira instances, so we must use current_user() to validate the token.
        """
        mock_jira_instance = MagicMock()
        mock_jira_instance.current_user.side_effect = Exception("401 Client Error: Unauthorized")

        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_get_settings,
            patch("jira.JIRA", return_value=mock_jira_instance),
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

            conn = Connection(
                name="Expired Token",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            credential_store.store(conn, "expired-token")

            result = runner.invoke(app, ["connect", "test", "Expired Token"])

            assert result.exit_code == 1
            assert "Connection failed" in result.stdout
            assert "expired" in result.stdout.lower() or "Unauthorized" in result.stdout


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


class TestConnectAddSecretRefs:
    """Test connect add with secret references (#124)."""

    def test_add_with_api_token_ref_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--api-token-ref stores the reference, never a credential file."""
        monkeypatch.setenv("ADD_PROBE_TOKEN", "secret-value")
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "RefHouse",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                    "--api-token-ref",
                    "env:ADD_PROBE_TOKEN",
                ],
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("RefHouse")
            assert stored is not None
            assert stored.api_token_ref == "env:ADD_PROBE_TOKEN"
            assert not get_credential_store().has_credentials(stored)

    def test_add_ref_probe_failure_declined_aborts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A broken reference that the user does not confirm aborts before saving."""
        monkeypatch.delenv("ADD_PROBE_TOKEN", raising=False)
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "RefHouse",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                    "--api-token-ref",
                    "env:ADD_PROBE_TOKEN",
                ],
                input="n\n",
            )

            assert result.exit_code != 0

            from budjira.config import get_settings

            assert get_settings().connections.find_by_name("RefHouse") is None

    def test_add_store_token_flag_warns_and_stores(self, tmp_path: Path) -> None:
        """--store-token keeps the deprecated path working, with a warning."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "StoreHouse",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                    "--store-token",
                ],
                input="raw-token\n",
            )

            assert result.exit_code == 0
            assert "deprecated" in result.stdout.lower()
            stored = settings.load_connections().find_by_name("StoreHouse")
            assert stored is not None
            assert stored.api_token_ref is None
            assert get_credential_store().retrieve(stored) == "raw-token"

    def test_add_ref_supersedes_stored_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting a verified reference on an existing connection removes the stored file."""
        monkeypatch.setenv("ADD_PROBE_TOKEN", "secret-value")
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
            patch("budjira.cli.connect._auto_sync_metadata"),
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings

            conn = Connection(
                name="Legacy",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "old-token")
            assert credential_store.has_credentials(conn)

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "Legacy",
                    "--url",
                    "https://test.atlassian.net",
                    "--email",
                    "test@example.com",
                    "--project",
                    "TEST",
                    "--api-token-ref",
                    "env:ADD_PROBE_TOKEN",
                ],
                input="y\n",
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("Legacy")
            assert stored is not None
            assert stored.api_token_ref == "env:ADD_PROBE_TOKEN"
            assert not credential_store.has_credentials(stored)


class TestConnectShowSecretRefs:
    """Test connect show token source display (#124)."""

    def test_show_displays_ref_verbatim(self, tmp_path: Path) -> None:
        """The reference is printed verbatim, never a resolved value."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="RefHouse",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                    api_token_ref="pass:acme/jira-token",
                )
            )

            result = runner.invoke(app, ["connect", "show", "RefHouse"])

            assert result.exit_code == 0
            assert "pass:acme/jira-token" in result.stdout

    def test_show_marks_stored_deprecated(self, tmp_path: Path) -> None:
        """A stored token is flagged as deprecated."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="Legacy",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            get_credential_store().store(conn, "old-token")

            result = runner.invoke(app, ["connect", "show", "Legacy"])

            assert result.exit_code == 0
            assert "stored (deprecated)" in result.stdout


class TestConnectListTokenColumn:
    """Test the API token column in connect list (#124)."""

    def test_list_marks_stored_deprecated(self, tmp_path: Path) -> None:
        """Stored tokens are flagged, references shown verbatim."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="Legacy",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
            )
            settings.add_connection(conn)
            get_credential_store().store(conn, "old-token")
            settings.add_connection(
                Connection(
                    name="RefHouse",
                    url="https://ref.atlassian.net",
                    email="ref@example.com",
                    project_key="REF",
                    api_token_ref="pass:acme/jira-token",
                )
            )

            result = runner.invoke(app, ["connect", "list"])

            assert result.exit_code == 0
            assert "stored (deprecated)" in result.stdout
            assert "pass:acme/jira-token" in result.stdout


class TestConnectRemoveTempoOrphan:
    """Test that remove also deletes the Tempo credential file (#124)."""

    def test_remove_also_removes_tempo_token(self, tmp_path: Path) -> None:
        """connect remove must not leave an orphaned live Tempo token behind."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="WithTempo",
                url="https://test.atlassian.net",
                email="test@example.com",
                project_key="TEST",
                tempo_enabled=True,
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "jira-token")
            credential_store.store_credential(conn.get_tempo_credential_key(), "tempo-token")

            result = runner.invoke(app, ["connect", "remove", "WithTempo", "--force"])

            assert result.exit_code == 0
            assert "Removed Tempo token" in result.stdout
            assert credential_store.get_credential(conn.get_tempo_credential_key()) is None


class TestTempoSetupSecretRef:
    """Test tempo-setup with --tempo-token-ref (#124)."""

    def test_tempo_setup_with_ref(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A verified reference enables Tempo without storing a token."""
        monkeypatch.setenv("TEMPO_PROBE_TOKEN", "tempo-secret")
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="RefHouse",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                )
            )

            result = runner.invoke(
                app,
                [
                    "connect",
                    "tempo-setup",
                    "--connection",
                    "RefHouse",
                    "--tempo-token-ref",
                    "env:TEMPO_PROBE_TOKEN",
                ],
            )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("RefHouse")
            assert stored is not None
            assert stored.tempo_enabled is True
            assert stored.tempo_token_ref == "env:TEMPO_PROBE_TOKEN"
            assert get_credential_store().get_credential(stored.get_tempo_credential_key()) is None


class TestConnectMigrate:
    """Test connect migrate command (#124)."""

    def _setup(self, tmp_path: Path):
        """Standard tmp-dir settings/credential store context."""
        return (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings"),
        )

    def test_migrate_to_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """env target migrates only when the variable already holds the stored token."""
        monkeypatch.setenv("ACME_JIRA_TOKEN", "jira-token-123")
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "jira-token-123")

            result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "env:ACME_JIRA_TOKEN"])

            assert result.exit_code == 0
            assert "migrated to" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "env:ACME_JIRA_TOKEN"
            assert not credential_store.has_credentials(stored)

    def test_migrate_to_pass_verified(self, tmp_path: Path) -> None:
        """pass target: insert, verify same value, then switch and delete."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "jira-token-123")

            run_results = [
                MagicMock(returncode=1, stderr="Error: acme/jira-token is not in the password store.\n"),
                MagicMock(returncode=0, stderr=""),  # pass insert
                MagicMock(returncode=0, stdout="jira-token-123\n"),  # verification pass show
            ]
            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", side_effect=run_results) as mock_run,
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 0
            insert_call = mock_run.call_args_list[1]
            assert insert_call[0][0][:3] == ["pass", "insert", "--multiline"]
            assert insert_call[1]["input"] == "jira-token-123\n"
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "pass:acme/jira-token"
            assert not credential_store.has_credentials(stored)

    def test_migrate_pass_existing_entry_requires_force(self, tmp_path: Path) -> None:
        """An existing pass entry blocks migration unless --force is given."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "jira-token-123")

            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", return_value=MagicMock(returncode=0)),
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 0
            assert "already exists" in result.stdout
            assert "Nothing migrated" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref is None
            assert credential_store.has_credentials(stored)

    def test_migrate_pass_verification_mismatch_keeps_file(self, tmp_path: Path) -> None:
        """If the new reference resolves to a different value, keep the stored token."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store(conn, "jira-token-123")

            run_results = [
                MagicMock(returncode=1, stderr="Error: acme/jira-token is not in the password store.\n"),
                MagicMock(returncode=0, stderr=""),  # insert ok
                MagicMock(returncode=0, stdout="different-token\n"),  # verification mismatch
            ]
            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", side_effect=run_results),
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 0
            assert "different value" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref is None
            assert credential_store.has_credentials(stored)

    def test_migrate_all_with_pass_prefix(self, tmp_path: Path) -> None:
        """--all uses --to as a prefix, one entry per connection."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            credential_store = get_credential_store()
            for name in ("Site A", "site-b"):
                conn = Connection(
                    name=name,
                    url="https://x.atlassian.net",
                    email="u@example.com",
                    project_key="XX",
                )
                settings.add_connection(conn)
                credential_store.store(conn, f"token-{name}")

            inserted: dict[str, str] = {}

            def fake_run(args, **kwargs):
                if args[:2] == ["pass", "insert"]:
                    entry = args[4]  # pass insert --multiline --force <entry>
                    inserted[entry] = kwargs["input"]
                    return MagicMock(returncode=0, stderr="")
                if args[:2] == ["pass", "show"]:
                    entry = args[2]
                    if entry in inserted:
                        return MagicMock(returncode=0, stdout=inserted[entry])
                    return MagicMock(returncode=1, stderr=f"Error: {entry} is not in the password store.\n")
                return MagicMock(returncode=1, stderr="")

            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", side_effect=fake_run),
            ):
                result = runner.invoke(app, ["connect", "migrate", "--all", "--to", "pass:budjira"])

            assert result.exit_code == 0
            loaded = settings.load_connections()
            site_a = loaded.find_by_name("Site A")
            site_b = loaded.find_by_name("site-b")
            assert site_a is not None
            assert site_b is not None
            assert site_a.api_token_ref == "pass:budjira/site-a"
            assert site_b.api_token_ref == "pass:budjira/site-b"

    def test_migrate_tempo_token(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--tempo-to migrates the Tempo credential once the variable matches."""
        monkeypatch.setenv("ACME_TEMPO_TOKEN", "tempo-token-9")
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
                tempo_enabled=True,
            )
            settings.add_connection(conn)
            credential_store = get_credential_store()
            credential_store.store_credential(conn.get_tempo_credential_key(), "tempo-token-9")

            result = runner.invoke(app, ["connect", "migrate", "acme", "--tempo-to", "env:ACME_TEMPO_TOKEN"])

            assert result.exit_code == 0
            assert "migrated to" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.tempo_token_ref == "env:ACME_TEMPO_TOKEN"
            assert credential_store.get_credential(stored.get_tempo_credential_key()) is None

    def test_migrate_nothing_stored(self, tmp_path: Path) -> None:
        """A connection without stored tokens reports nothing to migrate."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.settings

            budjira.config.settings._settings = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="acme",
                    url="https://acme.atlassian.net",
                    email="user@example.com",
                    project_key="ACME",
                )
            )

            result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "env:ACME_TOKEN"])

            assert result.exit_code == 0
            assert "nothing to migrate" in result.stdout
            assert "Nothing migrated" in result.stdout

    def test_migrate_requires_target(self, tmp_path: Path) -> None:
        """Neither --to nor --tempo-to is an error."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(app, ["connect", "migrate", "acme"])

            assert result.exit_code == 1
            assert "Nothing to do" in result.stdout

    def test_migrate_rejects_file_scheme(self, tmp_path: Path) -> None:
        """file: targets are not a migration destination."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_credential_store, get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            conn = Connection(
                name="acme",
                url="https://acme.atlassian.net",
                email="user@example.com",
                project_key="ACME",
            )
            settings.add_connection(conn)
            get_credential_store().store(conn, "jira-token-123")

            result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "file:/tmp/token"])

            assert result.exit_code == 1
            assert "not 'file:'" in result.stdout


class TestConnectMigrateSafety:
    """Sparring-driven safety properties of connect migrate (#124)."""

    def _setup(self, tmp_path: Path):
        """Standard tmp-dir settings/credential store context."""
        return (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings"),
        )

    def _make_settings(self, tmp_path: Path, mock_cred_get_settings, *, tempo: bool = False):
        """Wire tmp settings, one 'acme' connection with stored token(s)."""
        import budjira.config.credentials
        import budjira.config.settings

        budjira.config.settings._settings = None
        budjira.config.credentials._credential_store = None

        from budjira.config import get_credential_store, get_settings

        settings = get_settings()
        mock_cred_get_settings.return_value = settings
        conn = Connection(
            name="acme",
            url="https://acme.atlassian.net",
            email="user@example.com",
            project_key="ACME",
            tempo_enabled=tempo,
        )
        settings.add_connection(conn)
        credential_store = get_credential_store()
        credential_store.store(conn, "jira-token-123")
        if tempo:
            credential_store.store_credential(conn.get_tempo_credential_key(), "tempo-token-9")
        return settings, credential_store

    def test_migrate_env_unset_keeps_file(self, tmp_path: Path) -> None:
        """Unset env var: export line printed, but file and config stay untouched."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)

            result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "env:ACME_JIRA_TOKEN"])

            assert result.exit_code == 0
            assert "is not set" in result.stdout
            assert "export ACME_JIRA_TOKEN='jira-token-123'" in result.stdout
            assert "Nothing migrated" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref is None
            assert credential_store.has_credentials(stored)

    def test_migrate_env_mismatch_keeps_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A variable holding a DIFFERENT value must not silently take over."""
        monkeypatch.setenv("ACME_JIRA_TOKEN", "someone-elses-token")
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)

            result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "env:ACME_JIRA_TOKEN"])

            assert result.exit_code == 0
            assert "different value" in result.stdout
            assert "Nothing migrated" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref is None
            assert credential_store.has_credentials(stored)

    def test_migrate_pass_gpg_failure_blocks_insert(self, tmp_path: Path) -> None:
        """A decryption failure is not 'entry absent' - insert must not run."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)

            gpg_failure = MagicMock(returncode=2, stderr="gpg: decryption failed: No secret key\n")
            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", return_value=gpg_failure) as mock_run,
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 0
            assert "cannot inspect pass entry" in result.stdout
            assert "Nothing migrated" in result.stdout
            # exactly one call: the existence check; no insert, no verification
            assert mock_run.call_count == 1
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref is None
            assert credential_store.has_credentials(stored)

    def test_migrate_pass_binary_missing(self, tmp_path: Path) -> None:
        """No pass binary: clean error, no traceback."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            self._make_settings(tmp_path, mock_cred_get_settings)

            with patch("budjira.cli.connect.shutil.which", return_value=None):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 1
            assert "'pass' executable not found" in result.stdout
            assert "Traceback" not in result.stdout

    def test_migrate_same_target_rejected(self, tmp_path: Path) -> None:
        """--to == --tempo-to would map both tokens onto one secret."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            self._make_settings(tmp_path, mock_cred_get_settings, tempo=True)

            result = runner.invoke(
                app,
                ["connect", "migrate", "acme", "--to", "pass:acme/token", "--tempo-to", "pass:acme/token"],
            )

            assert result.exit_code == 1
            assert "must differ" in result.stdout

    def test_migrate_all_tempo_gets_own_entry(self, tmp_path: Path) -> None:
        """--all with one prefix must not map API and Tempo tokens together."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, _ = self._make_settings(tmp_path, mock_cred_get_settings, tempo=True)

            inserted: dict[str, str] = {}

            def fake_run(args, **kwargs):
                if args[:2] == ["pass", "insert"]:
                    inserted[args[4]] = kwargs["input"]
                    return MagicMock(returncode=0, stderr="")
                if args[:2] == ["pass", "show"]:
                    entry = args[2]
                    if entry in inserted:
                        return MagicMock(returncode=0, stdout=inserted[entry])
                    return MagicMock(returncode=1, stderr=f"Error: {entry} is not in the password store.\n")
                return MagicMock(returncode=1, stderr="")

            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", side_effect=fake_run),
            ):
                result = runner.invoke(
                    app,
                    ["connect", "migrate", "--all", "--to", "pass:budjira", "--tempo-to", "pass:budjira"],
                )

            assert result.exit_code == 0
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "pass:budjira/acme"
            assert stored.tempo_token_ref == "pass:budjira/acme/tempo"
            assert inserted["budjira/acme"] == "jira-token-123\n"
            assert inserted["budjira/acme/tempo"] == "tempo-token-9\n"

    def test_migrate_skips_connection_with_existing_ref(self, tmp_path: Path) -> None:
        """A reference already set (e.g. shared) must never be re-pointed."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)
            conn = settings.connections.find_by_name("acme")
            assert conn is not None
            conn.api_token_ref = "pass:shared/atlassian-token"
            settings.update_connection(conn)

            with patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:budjira/acme"])

            assert result.exit_code == 0
            assert "already uses reference" in result.stdout
            assert "Nothing migrated" in result.stdout
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "pass:shared/atlassian-token"
            assert credential_store.has_credentials(stored)


class TestConnectAddFlagConflict:
    """--api-token-ref and --store-token are mutually exclusive (#124)."""

    def test_ref_and_store_token_rejected(self, tmp_path: Path) -> None:
        """Both flags together are a usage error, not a silent choice."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
        ):
            import budjira.config.settings

            budjira.config.settings._settings = None

            result = runner.invoke(
                app,
                [
                    "connect",
                    "add",
                    "--name",
                    "x",
                    "--url",
                    "https://x.atlassian.net",
                    "--email",
                    "u@example.com",
                    "--project",
                    "XX",
                    "--api-token-ref",
                    "env:X_TOKEN",
                    "--store-token",
                ],
            )

            assert result.exit_code == 1
            assert "cannot be used together" in result.stdout


class TestConnectTestSecretRef:
    """A broken reference must surface as a clean error at consumption points (#124)."""

    def test_test_connection_broken_ref(self, tmp_path: Path) -> None:
        """connect test with an unresolvable ref: exit 1, names the ref, no traceback."""
        with (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings") as mock_cred_get_settings,
        ):
            import budjira.config.credentials
            import budjira.config.settings

            budjira.config.settings._settings = None
            budjira.config.credentials._credential_store = None

            from budjira.config import get_settings

            settings = get_settings()
            mock_cred_get_settings.return_value = settings
            settings.add_connection(
                Connection(
                    name="BrokenRef",
                    url="https://test.atlassian.net",
                    email="test@example.com",
                    project_key="TEST",
                    api_token_ref="env:DEFINITELY_UNSET_BUDJIRA_TEST_VAR",
                )
            )

            result = runner.invoke(app, ["connect", "test", "BrokenRef"])

            assert result.exit_code == 1
            assert "env:DEFINITELY_UNSET_BUDJIRA_TEST_VAR" in result.stdout
            assert "Traceback" not in result.stdout


class TestConnectMigrateExistingEntry:
    """Existing pass entries: same value needs no --force (#128)."""

    def _setup(self, tmp_path: Path):
        """Standard tmp-dir settings/credential store context."""
        return (
            patch("budjira.config.settings.xdg_config_home", return_value=tmp_path / "config"),
            patch("budjira.config.settings.xdg_data_home", return_value=tmp_path / "data"),
            patch("budjira.config.credentials.get_settings"),
        )

    def _make_settings(self, tmp_path: Path, mock_cred_get_settings):
        """Wire tmp settings, one 'acme' connection with a stored token."""
        import budjira.config.credentials
        import budjira.config.settings

        budjira.config.settings._settings = None
        budjira.config.credentials._credential_store = None

        from budjira.config import get_credential_store, get_settings

        settings = get_settings()
        mock_cred_get_settings.return_value = settings
        conn = Connection(
            name="acme",
            url="https://acme.atlassian.net",
            email="user@example.com",
            project_key="ACME",
        )
        settings.add_connection(conn)
        credential_store = get_credential_store()
        credential_store.store(conn, "jira-token-123")
        return settings, credential_store

    def test_existing_entry_same_value_needs_no_force(self, tmp_path: Path) -> None:
        """Same value: no insert, no --force - migrate straight through."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)

            same_value = MagicMock(returncode=0, stdout="jira-token-123\n")
            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", return_value=same_value) as mock_run,
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token"])

            assert result.exit_code == 0
            assert "already holds this token" in result.stdout
            assert "migrated to" in result.stdout
            # only existence check + verification - never an insert
            for call in mock_run.call_args_list:
                assert call[0][0][:2] == ["pass", "show"]
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "pass:acme/jira-token"
            assert not credential_store.has_credentials(stored)

    def test_existing_entry_different_value_force_overwrites(self, tmp_path: Path) -> None:
        """Different value + --force: overwrite, verify, migrate."""
        xdg_config, xdg_data, cred_settings = self._setup(tmp_path)
        with xdg_config, xdg_data, cred_settings as mock_cred_get_settings:
            settings, credential_store = self._make_settings(tmp_path, mock_cred_get_settings)

            run_results = [
                MagicMock(returncode=0, stdout="old-token\n"),  # existence: different value
                MagicMock(returncode=0, stderr=""),  # insert
                MagicMock(returncode=0, stdout="jira-token-123\n"),  # verification
            ]
            with (
                patch("budjira.cli.connect.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.config.secret_ref.shutil.which", return_value="/usr/bin/pass"),
                patch("budjira.cli.connect.subprocess.run", side_effect=run_results) as mock_run,
            ):
                result = runner.invoke(app, ["connect", "migrate", "acme", "--to", "pass:acme/jira-token", "--force"])

            assert result.exit_code == 0
            assert "migrated to" in result.stdout
            assert mock_run.call_args_list[1][0][0][:2] == ["pass", "insert"]
            stored = settings.load_connections().find_by_name("acme")
            assert stored is not None
            assert stored.api_token_ref == "pass:acme/jira-token"
            assert not credential_store.has_credentials(stored)
