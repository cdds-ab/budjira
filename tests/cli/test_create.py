# mypy: disable-error-code="arg-type,call-arg"
"""Tests for create command."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.cli.create import app
from budjira.models.connection import Connection
from budjira.models.issue import Issue
from budjira.utils.errors import JiraAPIError, PermissionError
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def mock_connection() -> Connection:
    """Create mock connection."""
    return Connection(
        name="test-connection",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
    )


@pytest.fixture
def mock_created_issue() -> Issue:
    """Create mock created issue."""
    return Issue(
        key="TEST-456",
        summary="New test issue",
        description="Test description",
        issue_type="Bug",
        status="To Do",
        priority="High",
        assignee="John Doe",
        labels=["bug", "urgent"],
        project_key="TEST",
    )


class TestCreateCommand:
    """Test create command."""

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_non_interactive_minimal(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with minimal fields in non-interactive mode."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(
            app,
            ["New bug", "--type", "Bug", "--no-interactive"],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        assert "TEST-456" in result.stdout
        mock_client.create_issue.assert_called_once_with(
            project_key="TEST",
            summary="New bug",
            issue_type="Bug",
            description=None,
            priority=None,
            assignee=None,
            labels=[],
        )

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_non_interactive_full(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with all fields in non-interactive mode."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--description",
                "Detailed description",
                "--priority",
                "High",
                "--assignee",
                "jdoe",
                "--label",
                "bug",
                "--label",
                "urgent",
                "--no-interactive",
                "--skip-dor",
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        assert "TEST-456" in result.stdout
        mock_client.create_issue.assert_called_once_with(
            project_key="TEST",
            summary="New bug",
            issue_type="Bug",
            description="Detailed description",
            priority="High",
            assignee="jdoe",
            labels=["bug", "urgent"],
        )

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_project_override(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with project override."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--project",
                "OTHER",
                "--no-interactive",
            ],
        )

        # Verify
        assert result.exit_code == 0
        call_args = mock_client.create_issue.call_args[1]
        assert call_args["project_key"] == "OTHER"

    @patch("budjira.cli.create.Prompt")
    @patch("budjira.cli.create.Confirm")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_interactive_minimal(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_confirm: Mock,
        mock_prompt: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create in interactive mode with minimal input."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Mock prompts
        mock_prompt.ask.side_effect = ["New bug", "Task"]
        mock_confirm.ask.return_value = False  # No to all optional fields

        # Run command with --interactive (default)
        result = runner.invoke(app, [])

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        mock_client.create_issue.assert_called_once()
        call_args = mock_client.create_issue.call_args[1]
        assert call_args["summary"] == "New bug"
        assert call_args["issue_type"] == "Task"

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.Prompt")
    @patch("budjira.cli.create.Confirm")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_interactive_full(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_confirm: Mock,
        mock_prompt: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create in interactive mode with all optional fields."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Mock prompts
        mock_prompt.ask.side_effect = [
            "New bug",  # summary
            "Bug",  # issue_type
            "Detailed description",  # description
            "High",  # priority
            "jdoe",  # assignee
            "bug, urgent",  # labels
        ]
        mock_confirm.ask.return_value = True  # Yes to all optional fields

        # Run command
        result = runner.invoke(app, [])

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        mock_client.create_issue.assert_called_once()
        call_args = mock_client.create_issue.call_args[1]
        assert call_args["description"] == "Detailed description"
        assert call_args["priority"] == "High"
        assert call_args["assignee"] == "jdoe"
        assert call_args["labels"] == ["bug", "urgent"]

    @patch("budjira.cli.create.get_active_connection")
    def test_create_no_connection(
        self,
        mock_get_active_connection: Mock,
    ) -> None:
        """Test create without connection configured."""
        # Setup mocks
        from budjira.utils.errors import BudjiraError

        mock_get_active_connection.side_effect = BudjiraError("No active connection configured")

        # Run command
        result = runner.invoke(app, ["Test", "--type", "Bug", "--no-interactive"])

        # Verify
        assert result.exit_code == 1
        assert "No active connection" in result.stdout

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_missing_summary(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test create without summary in non-interactive mode."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        # Run command without summary
        result = runner.invoke(app, ["--type", "Bug", "--no-interactive"])

        # Verify
        assert result.exit_code == 1
        assert "Summary is required" in result.stdout

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_missing_type(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test create without issue type in non-interactive mode."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        # Run command without type
        result = runner.invoke(app, ["Test summary", "--no-interactive"])

        # Verify
        assert result.exit_code == 1
        assert "Issue type is required" in result.stdout

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_api_error(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test create with API error."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.side_effect = JiraAPIError("Invalid issue data")
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["Test", "--type", "Bug", "--no-interactive"])

        # Verify
        assert result.exit_code == 1
        assert "Invalid issue data" in result.stdout

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_permission_error(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test create with permission error."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.side_effect = PermissionError("Access denied")
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["Test", "--type", "Bug", "--no-interactive"])

        # Verify
        assert result.exit_code == 1
        assert "Access denied" in result.stdout

    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_displays_issue_url(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test that created issue URL is displayed."""
        # Setup mocks
        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(app, ["Test", "--type", "Bug", "--no-interactive"])

        # Verify
        assert result.exit_code == 0
        assert f"{mock_connection.url}/browse/TEST-456" in result.stdout


class TestCreateWithDoR:
    """Test create command with DoR integration."""

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_dor_description(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with DoR-formatted description."""
        from budjira.models.dor import DEFAULT_STORY_TEMPLATE, DorTemplateConfig

        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = True
        mock_settings.global_config.dor_validation_level = "off"
        mock_settings.dor_templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # DoR-formatted description
        dor_description = """## Context

User needs authentication

## User Story
As a user
I want to log in
So that I can access my account

## Acceptance Criteria
- [ ] Login form exists
- [ ] Password is hashed
"""

        # Run command with DoR description
        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--description",
                dor_description,
                "--no-interactive",
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        mock_client.create_issue.assert_called_once()
        call_args = mock_client.create_issue.call_args[1]
        assert call_args["description"] == dor_description

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_skip_dor_flag(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with --skip-dor flag."""
        from budjira.models.dor import DEFAULT_STORY_TEMPLATE, DorTemplateConfig

        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = True
        mock_settings.dor_templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command with --skip-dor
        result = runner.invoke(
            app,
            ["New story", "--type", "Story", "--skip-dor", "--no-interactive"],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        # DoR template should not be used
        mock_client.create_issue.assert_called_once()

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_dor_disabled(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create when DoR is disabled in config."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command
        result = runner.invoke(
            app,
            ["New story", "--type", "Story", "--no-interactive"],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        mock_client.create_issue.assert_called_once()

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_issue_type_without_dor_template(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with issue type that has no DoR template."""
        from budjira.models.dor import DEFAULT_STORY_TEMPLATE, DorTemplateConfig

        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = True
        # Only Story template exists
        mock_settings.dor_templates = DorTemplateConfig(templates={"Story": DEFAULT_STORY_TEMPLATE})
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Run command with Task (no DoR template for Task)
        result = runner.invoke(
            app,
            ["New task", "--type", "Task", "--no-interactive"],
        )

        # Verify
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        # DoR template should not be used for Task
        mock_client.create_issue.assert_called_once()

    @patch("budjira.cli.create.validate_description")
    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_dor_validation_strict_mode(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_validate: Mock,
        mock_connection: Connection,
    ) -> None:
        """Test create with DoR validation in strict mode."""
        from budjira.models.dor import (
            DEFAULT_STORY_TEMPLATE,
            DorTemplateConfig,
            ValidationLevel,
            ValidationResult,
        )

        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = True
        mock_settings.dor_templates = DorTemplateConfig(
            templates={"Story": DEFAULT_STORY_TEMPLATE},
            default_validation_level=ValidationLevel.STRICT,
        )
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        # Mock validation failure
        validation_result = ValidationResult(
            valid=False,
            errors=["Missing required section 'Context'"],
            warnings=[],
            missing_sections=["Context"],
            empty_sections=[],
        )
        mock_validate.return_value = validation_result

        # Run command with invalid description
        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--description",
                "Invalid description without DoR sections",
                "--no-interactive",
            ],
        )

        # Verify - should fail in strict mode
        assert result.exit_code == 1
        assert "DoR validation failed" in result.stdout or "Missing required section" in result.stdout

    @patch("budjira.cli.create.validate_description")
    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_dor_validation_warn_mode(
        self,
        mock_get_active_connection: Mock,
        mock_jira_client_class: Mock,
        mock_get_settings: Mock,
        mock_validate: Mock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with DoR validation in warn mode."""
        from budjira.models.dor import (
            DEFAULT_STORY_TEMPLATE,
            DorTemplateConfig,
            ValidationLevel,
            ValidationResult,
        )

        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = True
        mock_settings.dor_templates = DorTemplateConfig(
            templates={"Story": DEFAULT_STORY_TEMPLATE},
            default_validation_level=ValidationLevel.WARN,
        )
        mock_get_settings.return_value = mock_settings

        mock_get_active_connection.return_value = mock_connection

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Mock validation failure
        validation_result = ValidationResult(
            valid=False,
            errors=[],
            warnings=["Missing required section 'Context'"],
            missing_sections=["Context"],
            empty_sections=[],
        )
        mock_validate.return_value = validation_result

        # Run command with invalid description
        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--description",
                "Invalid description without DoR sections",
                "--no-interactive",
            ],
        )

        # Verify - should succeed in warn mode
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        mock_client.create_issue.assert_called_once()
