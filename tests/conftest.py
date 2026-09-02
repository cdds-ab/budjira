"""Pytest configuration and fixtures."""

import os

import pytest
from budjira.models.connection import Connection


@pytest.fixture(autouse=True)
def _clear_budjira_token_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Token env vars are authoritative for secret resolution (#124).

    A developer machine exporting BUDJIRA_API_TOKEN & co. must not change what
    a test exercises - clear every BUDJIRA_*_TOKEN variable. Tests set their
    own via monkeypatch after this fixture has run.
    """
    for var in list(os.environ):
        if var.startswith("BUDJIRA_") and var.endswith("_TOKEN"):
            monkeypatch.delenv(var, raising=False)


@pytest.fixture
def sample_jira_url() -> str:
    """Return a sample Jira URL for testing."""
    return "https://example.atlassian.net"


@pytest.fixture
def sample_project_key() -> str:
    """Return a sample project key for testing."""
    return "TEST"


@pytest.fixture
def sample_issue_key() -> str:
    """Return a sample issue key for testing."""
    return "TEST-123"


@pytest.fixture
def mock_connection() -> Connection:
    """Return a mock Jira connection for testing."""
    return Connection(
        name="test-connection",
        url="https://test.atlassian.net",  # type: ignore[arg-type]
        email="test@example.com",
        project_key="TEST",
        tempo_enabled=False,
    )
