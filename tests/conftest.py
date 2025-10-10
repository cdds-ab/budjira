"""Pytest configuration and fixtures."""

import pytest


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
