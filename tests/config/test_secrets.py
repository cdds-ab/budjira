"""Tests for token resolution order and the stored-token deprecation warning."""

# mypy: disable-error-code="arg-type"

from unittest.mock import MagicMock, patch

import pytest
from budjira.config import secrets
from budjira.config.secrets import (
    describe_api_token_source,
    describe_tempo_token_source,
    per_connection_env_name,
    resolve_api_token,
    resolve_tempo_token,
)
from budjira.models.connection import Connection
from budjira.utils.errors import SecretRefError


@pytest.fixture
def connection() -> Connection:
    """Connection without any secret references."""
    return Connection(
        name="acme-corp",
        url="https://acme.atlassian.net",
        email="user@example.com",
        project_key="ACME",
    )


@pytest.fixture
def ref_connection() -> Connection:
    """Connection with both secret references set."""
    return Connection(
        name="acme-corp",
        url="https://acme.atlassian.net",
        email="user@example.com",
        project_key="ACME",
        api_token_ref="pass:acme/jira-token",
        tempo_token_ref="env:ACME_TEMPO_TOKEN",
    )


@pytest.fixture(autouse=True)
def reset_warning_flag() -> None:
    """Reset the once-per-process warning flag before each test."""
    secrets._stored_token_warning_shown = False


@pytest.fixture
def mock_credential_store():
    """Patch the credential store used by secrets resolution.

    get_settings is patched too: the stored-token deprecation warning reads
    global_config, and tests must not touch the developer's real config
    (a host with suppress_stored_token_warning would change behavior).
    """
    store = MagicMock()
    store.retrieve.return_value = None
    store.get_credential.return_value = None
    store.has_credentials.return_value = False
    settings = MagicMock()
    settings.global_config.suppress_stored_token_warning = False
    with (
        patch("budjira.config.secrets.get_credential_store", return_value=store),
        patch("budjira.config.secrets.get_settings", return_value=settings),
    ):
        yield store


class TestPerConnectionEnvName:
    """Test per-connection environment variable naming."""

    def test_simple_name(self) -> None:
        assert per_connection_env_name("acme") == "BUDJIRA_ACME_API_TOKEN"

    def test_name_sanitized(self) -> None:
        assert per_connection_env_name("acme-corp prod") == "BUDJIRA_ACME_CORP_PROD_API_TOKEN"

    def test_tempo_kind(self) -> None:
        assert per_connection_env_name("acme", "TEMPO") == "BUDJIRA_ACME_TEMPO_TOKEN"


class TestResolveApiToken:
    """Test the API token resolution order."""

    def test_ref_wins_over_everything(
        self, connection: Connection, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock
    ) -> None:
        """A configured reference beats env vars and the store."""
        connection.api_token_ref = "env:REF_TOKEN"
        monkeypatch.setenv("REF_TOKEN", "from-ref")
        monkeypatch.setenv("BUDJIRA_ACME_CORP_API_TOKEN", "from-per-conn")
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "from-generic")
        mock_credential_store.retrieve.return_value = "from-store"

        assert resolve_api_token(connection) == "from-ref"

    def test_per_connection_env_beats_generic(
        self, connection: Connection, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock
    ) -> None:
        """The per-connection variable beats the generic fallback."""
        monkeypatch.setenv("BUDJIRA_ACME_CORP_API_TOKEN", "from-per-conn")
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "from-generic")

        assert resolve_api_token(connection) == "from-per-conn"

    def test_generic_env_beats_store(
        self, connection: Connection, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock
    ) -> None:
        """The generic variable beats the stored token."""
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "from-generic")
        mock_credential_store.retrieve.return_value = "from-store"

        assert resolve_api_token(connection) == "from-generic"

    def test_store_is_last_resort(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """Without ref or env vars, the stored token is used."""
        mock_credential_store.retrieve.return_value = "from-store"

        assert resolve_api_token(connection) == "from-store"

    def test_nothing_found_returns_none(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """No ref, no env, no store: None."""
        assert resolve_api_token(connection) is None

    def test_empty_env_treated_as_unset(
        self, connection: Connection, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock
    ) -> None:
        """An empty variable does not shadow the next source."""
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "  ")
        mock_credential_store.retrieve.return_value = "from-store"

        assert resolve_api_token(connection) == "from-store"

    def test_ref_error_propagates(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """A broken reference is a hard error, never a silent fallback."""
        connection.api_token_ref = "env:DEFINITELY_UNSET_BUDJIRA_TEST_TOKEN"

        with pytest.raises(SecretRefError, match="is not set"):
            resolve_api_token(connection)

    def test_shared_reference(self, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock) -> None:
        """Several connections may share one reference."""
        monkeypatch.setenv("SHARED_TOKEN", "shared-value")
        conn1 = Connection(
            name="site-a",
            url="https://a.atlassian.net",
            email="u@example.com",
            project_key="AAA",
            api_token_ref="env:SHARED_TOKEN",
        )
        conn2 = Connection(
            name="site-b",
            url="https://b.atlassian.net",
            email="u@example.com",
            project_key="BBB",
            api_token_ref="env:SHARED_TOKEN",
        )

        assert resolve_api_token(conn1) == "shared-value"
        assert resolve_api_token(conn2) == "shared-value"


class TestResolveTempoToken:
    """Test the Tempo token resolution order."""

    def test_ref_wins(self, ref_connection: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
        """tempo_token_ref resolves via its scheme."""
        monkeypatch.setenv("ACME_TEMPO_TOKEN", "from-ref")
        assert resolve_tempo_token(ref_connection) == "from-ref"

    def test_fallback_chain(self, connection: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
        """Per-connection var, then generic var."""
        monkeypatch.setenv("BUDJIRA_TEMPO_TOKEN", "from-generic")
        assert resolve_tempo_token(connection) == "from-generic"
        monkeypatch.setenv("BUDJIRA_ACME_CORP_TEMPO_TOKEN", "from-per-conn")
        assert resolve_tempo_token(connection) == "from-per-conn"

    def test_store_is_last_resort(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """Stored Tempo credential is the deprecated fallback."""
        mock_credential_store.get_credential.return_value = "from-store"
        assert resolve_tempo_token(connection) == "from-store"


class TestStoredTokenWarning:
    """Test the stored-token deprecation warning."""

    def test_warns_once_per_process(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """Two resolutions print exactly one warning."""
        mock_credential_store.retrieve.return_value = "from-store"
        console = MagicMock()
        with patch("budjira.config.secrets._err_console", console):
            resolve_api_token(connection)
            resolve_api_token(connection)

        assert console.print.call_count == 1
        message = console.print.call_args[0][0]
        assert "deprecated" in message
        assert "budjira connect migrate acme-corp" in message

    def test_suppressed_via_config(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """suppress_stored_token_warning in config.toml silences the warning."""
        mock_credential_store.retrieve.return_value = "from-store"
        settings = MagicMock()
        settings.global_config.suppress_stored_token_warning = True
        console = MagicMock()
        with (
            patch("budjira.config.secrets.get_settings", return_value=settings),
            patch("budjira.config.secrets._err_console", console),
        ):
            resolve_api_token(connection)

        console.print.assert_not_called()

    def test_no_warning_for_other_sources(
        self, connection: Connection, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock
    ) -> None:
        """References and env vars never trigger the warning."""
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "from-generic")
        console = MagicMock()
        with patch("budjira.config.secrets._err_console", console):
            resolve_api_token(connection)

        console.print.assert_not_called()


class TestDescribeTokenSource:
    """Test source description for display commands."""

    def test_ref_shown_verbatim(self, ref_connection: Connection) -> None:
        """The reference is printed, never the resolved value."""
        assert describe_api_token_source(ref_connection) == "pass:acme/jira-token"
        assert describe_tempo_token_source(ref_connection) == "env:ACME_TEMPO_TOKEN"

    def test_env_sources(self, connection: Connection, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env sources name the variable."""
        monkeypatch.setenv("BUDJIRA_API_TOKEN", "x")
        assert describe_api_token_source(connection) == "env BUDJIRA_API_TOKEN"
        monkeypatch.setenv("BUDJIRA_ACME_CORP_API_TOKEN", "x")
        assert describe_api_token_source(connection) == "env BUDJIRA_ACME_CORP_API_TOKEN"

    def test_stored_marked_deprecated(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """Stored tokens are flagged as deprecated."""
        mock_credential_store.has_credentials.return_value = True
        assert describe_api_token_source(connection) == "stored (deprecated)"

    def test_missing(self, connection: Connection, mock_credential_store: MagicMock) -> None:
        """No source at all shows as missing."""
        assert describe_api_token_source(connection) == "missing"
        assert describe_tempo_token_source(connection) == "missing"
