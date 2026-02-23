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


class WorkflowError(BudjiraError):
    """Raised when workflow operations fail."""

    pass


class ShadowTicketNotFoundError(WorkflowError):
    """Raised when a shadow ticket cannot be found in the booking instance."""

    pass


class ShadowTicketAmbiguousError(WorkflowError):
    """Raised when multiple shadow tickets match, making resolution ambiguous."""

    pass


class OverbookingError(WorkflowError):
    """Raised when booking would exceed the estimate and policy is BLOCK."""

    pass


class WorkflowConfigError(ConfigurationError):
    """Raised when workflow profile configuration is invalid."""

    pass
