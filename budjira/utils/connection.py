"""Connection resolution utilities."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from budjira.config import get_settings
from budjira.utils.errors import BudjiraError

if TYPE_CHECKING:
    from budjira.models.connection import Connection


def get_active_connection(connection_name: str | None = None) -> Connection:
    """Get the active connection using multiple resolution strategies.

    Resolution order:
    1. Explicit connection name provided
    2. BUDJIRA_CONNECTION environment variable
    3. Active connection from global config
    4. Error if none found

    Args:
        connection_name: Explicit connection name (from --connection option)

    Returns:
        Active Connection object

    Raises:
        BudjiraError: If no connection can be resolved
    """
    settings = get_settings()

    # Strategy 1: Explicit connection name (highest priority)
    if connection_name:
        connection = settings.connections.find_by_name(connection_name)
        if not connection:
            raise BudjiraError(
                f"Connection '{connection_name}' not found. Run 'budjira connect list' to see available connections."
            )
        return connection

    # Strategy 2: Environment variable
    env_connection = os.getenv("BUDJIRA_CONNECTION")
    if env_connection:
        connection = settings.connections.find_by_name(env_connection)
        if not connection:
            raise BudjiraError(
                f"Connection '{env_connection}' (from BUDJIRA_CONNECTION env var) not found. "
                f"Run 'budjira connect list' to see available connections."
            )
        return connection

    # Strategy 3: Active connection from config
    if settings.global_config.active_connection:
        connection = settings.connections.find_by_name(settings.global_config.active_connection)
        if connection:
            return connection
        # Connection in config but doesn't exist anymore - clear it
        settings.global_config.active_connection = None
        settings.save_global_config(settings.global_config)

    # No connection found
    raise BudjiraError(
        "No active connection configured. "
        "Either:\n"
        "  1. Set BUDJIRA_CONNECTION environment variable: export BUDJIRA_CONNECTION=<name>\n"
        "  2. Use --connection option: budjira <command> --connection <name>\n"
        "  3. Run 'budjira connect add' to create a connection"
    )
