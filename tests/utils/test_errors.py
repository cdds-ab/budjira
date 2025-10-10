"""Test custom exceptions."""

import pytest
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    CacheError,
    ConfigurationError,
    ConnectionError,
    InvalidIssueError,
    JiraAPIError,
    PermissionError,
    ValidationError,
)


def test_base_exception() -> None:
    """Test base BudjiraError exception."""
    with pytest.raises(BudjiraError) as exc_info:
        raise BudjiraError("Test error")
    assert "Test error" in str(exc_info.value)


def test_connection_error() -> None:
    """Test ConnectionError exception."""
    with pytest.raises(ConnectionError) as exc_info:
        raise ConnectionError("Connection failed")
    assert "Connection failed" in str(exc_info.value)


def test_authentication_error() -> None:
    """Test AuthenticationError exception."""
    with pytest.raises(AuthenticationError):
        raise AuthenticationError("Auth failed")


def test_permission_error() -> None:
    """Test PermissionError exception."""
    with pytest.raises(PermissionError):
        raise PermissionError("Permission denied")


def test_validation_error() -> None:
    """Test ValidationError exception."""
    with pytest.raises(ValidationError):
        raise ValidationError("Validation failed")


def test_jira_api_error() -> None:
    """Test JiraAPIError exception."""
    with pytest.raises(JiraAPIError):
        raise JiraAPIError("API error")


def test_configuration_error() -> None:
    """Test ConfigurationError exception."""
    with pytest.raises(ConfigurationError):
        raise ConfigurationError("Config error")


def test_invalid_issue_error() -> None:
    """Test InvalidIssueError exception."""
    with pytest.raises(InvalidIssueError):
        raise InvalidIssueError("Invalid issue")


def test_cache_error() -> None:
    """Test CacheError exception."""
    with pytest.raises(CacheError):
        raise CacheError("Cache error")


def test_inheritance() -> None:
    """Test that all exceptions inherit from BudjiraError."""
    assert issubclass(ConnectionError, BudjiraError)
    assert issubclass(AuthenticationError, BudjiraError)
    assert issubclass(PermissionError, BudjiraError)
    assert issubclass(ValidationError, BudjiraError)
    assert issubclass(JiraAPIError, BudjiraError)
    assert issubclass(ConfigurationError, BudjiraError)
    assert issubclass(InvalidIssueError, BudjiraError)
    assert issubclass(InvalidIssueError, ValidationError)  # InvalidIssueError is a ValidationError
    assert issubclass(CacheError, BudjiraError)
