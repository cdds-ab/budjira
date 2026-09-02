"""Token resolution for connections.

Single entry point for every command that needs a token. Resolution order
for the Jira API token (Tempo analog with ``tempo_token_ref`` /
``*_TEMPO_TOKEN``):

1. ``connection.api_token_ref`` - secret reference (``env:`` / ``pass:`` / ``file:``)
2. ``BUDJIRA_<NAME>_API_TOKEN`` - per-connection environment variable
   (NAME = connection name uppercased, non-alphanumeric mapped to ``_``)
3. ``BUDJIRA_API_TOKEN`` - generic environment fallback
4. Stored token via CredentialStore (deprecated - warns once per process,
   suppressible via ``suppress_stored_token_warning`` in config.toml)

Several connections may share one reference or one environment variable -
rotation then means updating a single secret, not six files on disk.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from rich.console import Console

from budjira.config.credentials import get_credential_store
from budjira.config.secret_ref import resolve_secret_ref
from budjira.config.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from budjira.models.connection import Connection

_err_console = Console(stderr=True)

# Once-per-process flag for the stored-token deprecation warning. Tests reset
# this to assert the warning fires (again).
_stored_token_warning_shown = False


def _env_safe_name(connection_name: str) -> str:
    """Map a connection name to its environment variable infix."""
    return re.sub(r"[^A-Z0-9]", "_", connection_name.upper())


def per_connection_env_name(connection_name: str, kind: str = "API") -> str:
    """Environment variable name for a connection-specific token.

    Args:
        connection_name: Connection name (e.g. ``acme-corp``)
        kind: ``API`` for the Jira token, ``TEMPO`` for the Tempo token

    Returns:
        Variable name, e.g. ``BUDJIRA_ACME_CORP_API_TOKEN``
    """
    return f"BUDJIRA_{_env_safe_name(connection_name)}_{kind}_TOKEN"


def _env_value(name: str) -> str | None:
    """Read an environment variable, treating empty/whitespace as unset."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _warn_stored_token(connection: Connection) -> None:
    """Print the stored-token deprecation warning once per process."""
    global _stored_token_warning_shown
    if _stored_token_warning_shown:
        return
    if get_settings().global_config.suppress_stored_token_warning:
        return
    _stored_token_warning_shown = True
    _err_console.print(
        f"[yellow]⚠[/yellow] Connection '{connection.name}' uses a stored token (deprecated). "
        f"Migrate with: [cyan]budjira connect migrate {connection.name} --to pass:<entry>[/cyan] "
        "(suppress: suppress_stored_token_warning = true in config.toml)",
        highlight=False,
    )


def _resolve_token(
    connection: Connection,
    ref: str | None,
    kind: str,
    retrieve_stored: Callable[[Connection], str | None],
) -> str | None:
    """Resolve a token following the documented order.

    Args:
        connection: Connection to resolve for
        ref: The connection's secret reference for this token (or None)
        kind: ``API`` or ``TEMPO`` - selects the environment variable names
        retrieve_stored: Callable retrieving the stored (deprecated) token

    Returns:
        Resolved token, or None if no source yielded one

    Raises:
        SecretRefError: If a configured reference cannot be resolved
    """
    if ref:
        return resolve_secret_ref(ref)

    per_conn = _env_value(per_connection_env_name(connection.name, kind))
    if per_conn:
        return per_conn

    generic = _env_value(f"BUDJIRA_{kind}_TOKEN")
    if generic:
        return generic

    stored = retrieve_stored(connection)
    if stored:
        _warn_stored_token(connection)
    return stored


def resolve_api_token(connection: Connection) -> str | None:
    """Resolve the Jira API token for a connection.

    Returns:
        Resolved token, or None if no source (ref, env vars, store) yields one
    """
    return _resolve_token(
        connection,
        connection.api_token_ref,
        "API",
        lambda conn: get_credential_store().retrieve(conn),
    )


def resolve_tempo_token(connection: Connection) -> str | None:
    """Resolve the Tempo API token for a connection.

    Returns:
        Resolved token, or None if no source (ref, env vars, store) yields one
    """
    return _resolve_token(
        connection,
        connection.tempo_token_ref,
        "TEMPO",
        lambda conn: get_credential_store().get_credential(conn.get_tempo_credential_key()),
    )


def describe_api_token_source(connection: Connection) -> str:
    """Describe where the Jira API token comes from, for display commands.

    Never includes the token itself - references are shown verbatim.

    Returns:
        Human-readable source, e.g. ``pass:acme/token`` or ``stored (deprecated)``
    """
    return _describe_token_source(connection, connection.api_token_ref, "API")


def describe_tempo_token_source(connection: Connection) -> str:
    """Describe where the Tempo API token comes from, for display commands.

    Never includes the token itself - references are shown verbatim.
    """
    return _describe_token_source(connection, connection.tempo_token_ref, "TEMPO")


def _describe_token_source(connection: Connection, ref: str | None, kind: str) -> str:
    if ref:
        return ref
    if _env_value(per_connection_env_name(connection.name, kind)):
        return f"env {per_connection_env_name(connection.name, kind)}"
    if _env_value(f"BUDJIRA_{kind}_TOKEN"):
        return f"env BUDJIRA_{kind}_TOKEN"
    store = get_credential_store()
    if kind == "API" and store.has_credentials(connection):
        return "stored (deprecated)"
    if kind == "TEMPO" and store.get_credential(connection.get_tempo_credential_key()) is not None:
        return "stored (deprecated)"
    return "missing"
