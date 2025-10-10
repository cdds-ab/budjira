"""Custom exceptions for budjira."""


class BudjiraError(Exception):
    """Base exception for all budjira errors."""

    pass


class ConnectionError(BudjiraError):
    """Raised when connection to Jira fails."""

    pass


class AuthenticationError(BudjiraError):
    """Raised when authentication fails."""

    pass


class PermissionError(BudjiraError):
    """Raised when user lacks required permissions."""

    pass


class ValidationError(BudjiraError):
    """Raised when input validation fails."""

    pass


class JiraAPIError(BudjiraError):
    """Raised when Jira API returns an unexpected error."""

    pass


class ConfigurationError(BudjiraError):
    """Raised when configuration is invalid or missing."""

    pass


class InvalidIssueError(ValidationError):
    """Raised when an issue key is invalid or not found."""

    pass


class CacheError(BudjiraError):
    """Raised when cache operations fail."""

    pass
