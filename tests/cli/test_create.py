# mypy: disable-error-code="arg-type,call-arg"
"""Tests for create command."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from budjira.cli.create import app
from budjira.models.connection import Connection
from budjira.models.custom_field import CustomFieldConfig, CustomFieldType
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
            "TEST-100",  # epic
        ]
        mock_confirm.ask.return_value = True  # Yes to all optional fields (including epic)

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
        # URL should not have double slashes
        assert "https://test.atlassian.net/browse/TEST-456" in result.stdout


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

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_issue_with_original_estimate(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with original estimate."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.dor_validation_level = "off"
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "Fix bug",
                "--type",
                "Bug",
                "--original-estimate",
                "2h",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        # Verify timetracking field was passed
        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "timetracking" in call_kwargs
        assert call_kwargs["timetracking"]["originalEstimate"] == "2h"

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_issue_with_remaining_estimate(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with remaining estimate."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.dor_validation_level = "off"
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New feature",
                "--type",
                "Story",
                "--remaining-estimate",
                "3h30m",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0

        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "timetracking" in call_kwargs
        assert call_kwargs["timetracking"]["remainingEstimate"] == "3h30m"

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_issue_with_both_estimates(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with both original and remaining estimate."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.dor_validation_level = "off"
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "Task with estimates",
                "--type",
                "Task",
                "--original-estimate",
                "8h",
                "--remaining-estimate",
                "5h",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0

        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "timetracking" in call_kwargs
        assert call_kwargs["timetracking"]["originalEstimate"] == "8h"
        assert call_kwargs["timetracking"]["remainingEstimate"] == "5h"

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_issue_without_estimates(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue without time estimates."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.dor_validation_level = "off"
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["Task without estimates", "--type", "Task", "--no-interactive"],
        )

        assert result.exit_code == 0

        # Verify timetracking field was NOT passed
        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "timetracking" not in call_kwargs


class TestCreateWithEpic:
    """Test create command with epic linking."""

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_epic_flag_success(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with --epic flag successfully links to epic."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        # Mock epic issue
        epic_issue = Issue(
            key="TEST-100",
            summary="Epic Title",
            issue_type="Epic",
            status="In Progress",
            project_key="TEST",
        )

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_client.get_issue.return_value = epic_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--epic",
                "TEST-100",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        assert "Linked to epic: TEST-100 (Epic Title)" in result.stdout
        assert "Epic" in result.stdout
        assert "TEST-100" in result.stdout

        # Verify link_to_epic was called
        mock_client.link_to_epic.assert_called_once_with("TEST-456", "TEST-100")
        mock_client.get_issue.assert_called_once_with("TEST-100")

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_epic_flag_link_fails(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue when epic link fails but issue creation succeeds."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_client.link_to_epic.side_effect = JiraAPIError("Epic not found")
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--epic",
                "TEST-999",
                "--no-interactive",
            ],
        )

        # Should succeed with warning
        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        assert "Warning: Failed to link to epic TEST-999" in result.stdout
        assert "Issue was created successfully but epic link failed" in result.stdout

        # Verify issue was created
        mock_client.create_issue.assert_called_once()
        # Verify link attempt was made
        mock_client.link_to_epic.assert_called_once_with("TEST-456", "TEST-999")

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_without_epic_flag(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue without --epic flag does not attempt linking."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            ["New story", "--type", "Story", "--no-interactive"],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        # Verify link_to_epic was NOT called
        mock_client.link_to_epic.assert_not_called()
        mock_client.get_issue.assert_not_called()

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_epic_and_other_fields(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with --epic and other fields."""
        mock_get_conn.return_value = mock_connection
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        epic_issue = Issue(
            key="TEST-100",
            summary="Epic Title",
            issue_type="Epic",
            status="In Progress",
            project_key="TEST",
        )

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_client.get_issue.return_value = epic_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New story",
                "--type",
                "Story",
                "--epic",
                "TEST-100",
                "--priority",
                "High",
                "--label",
                "feature",
                "--original-estimate",
                "2h",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout
        assert "Linked to epic: TEST-100" in result.stdout

        # Verify both create_issue and link_to_epic were called
        mock_client.create_issue.assert_called_once()
        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert call_kwargs["priority"] == "High"
        assert call_kwargs["labels"] == ["feature"]
        assert "timetracking" in call_kwargs

        mock_client.link_to_epic.assert_called_once_with("TEST-456", "TEST-100")


class TestCreateWithCustomFields:
    """Test create command with custom fields."""

    @pytest.fixture
    def mock_connection_with_custom_fields(self) -> Connection:
        """Create mock connection with custom fields configured."""
        custom_fields = {
            "affected_system": CustomFieldConfig(
                field_id="customfield_10001",
                type=CustomFieldType.SELECT,
                required=True,
                options=["Infrastructure", "Application", "Database"],
                label="Affected System",
            ),
            "environment": CustomFieldConfig(
                field_id="customfield_10002",
                type=CustomFieldType.TEXT,
                required=False,
                default="Production",
            ),
            "severity": CustomFieldConfig(
                field_id="customfield_10003",
                type=CustomFieldType.NUMBER,
                required=False,
            ),
        }
        return Connection(
            name="test-connection",
            url="https://test.atlassian.net",
            email="test@example.com",
            project_key="TEST",
            custom_fields=custom_fields,
        )

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_custom_field_flag(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with --custom flag."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "affected_system=Infrastructure",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        # Verify custom field was passed with correct Jira field ID
        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "customfield_10001" in call_kwargs
        assert call_kwargs["customfield_10001"] == {"value": "Infrastructure"}

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_multiple_custom_fields(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with multiple --custom flags."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "affected_system=Database",
                "--custom",
                "environment=Staging",
                "--custom",
                "severity=5",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert call_kwargs["customfield_10001"] == {"value": "Database"}
        assert call_kwargs["customfield_10002"] == "Staging"
        assert call_kwargs["customfield_10003"] == 5

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_custom_field_invalid_name(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
    ) -> None:
        """Test create with unknown custom field name."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "unknown_field=value",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1
        assert "Unknown custom field" in result.stdout
        assert "unknown_field" in result.stdout

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_custom_field_invalid_format(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
    ) -> None:
        """Test create with invalid custom field format (no equals sign)."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "invalid-format",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1
        assert "Invalid custom field format" in result.stdout
        assert "name=value" in result.stdout

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_custom_field_invalid_select_option(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
    ) -> None:
        """Test create with invalid option for select field."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "affected_system=InvalidOption",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1
        assert "Invalid" in result.stdout
        assert "InvalidOption" in result.stdout

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_missing_required_custom_field(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
    ) -> None:
        """Test create without required custom field in non-interactive mode."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1
        assert "Missing required custom field" in result.stdout
        assert "Affected System" in result.stdout

    @patch("budjira.cli.create.Prompt")
    @patch("budjira.cli.create.Confirm")
    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_custom_field_interactive_prompt(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_confirm: MagicMock,
        mock_prompt: MagicMock,
        mock_connection_with_custom_fields: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test that required custom fields are prompted in interactive mode."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        # Mock prompts
        mock_prompt.ask.side_effect = [
            "New bug",  # summary
            "Bug",  # issue_type
            "Infrastructure",  # affected_system (required custom field)
        ]
        mock_confirm.ask.return_value = False  # No to all optional prompts

        result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        # Verify custom field was passed
        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert "customfield_10001" in call_kwargs
        assert call_kwargs["customfield_10001"] == {"value": "Infrastructure"}

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_no_custom_fields_configured(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test create with --custom flag but no custom fields configured."""
        mock_get_conn.return_value = mock_connection  # Has no custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--custom",
                "some_field=value",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 1
        assert "Unknown custom field" in result.stdout

    @patch("budjira.cli.create.get_settings")
    @patch("budjira.cli.create.JiraClient")
    @patch("budjira.cli.create.get_active_connection")
    def test_create_with_custom_field_and_other_options(
        self,
        mock_get_conn: MagicMock,
        mock_jira_client_class: MagicMock,
        mock_get_settings: MagicMock,
        mock_connection_with_custom_fields: Connection,
        mock_created_issue: Issue,
    ) -> None:
        """Test creating issue with custom fields combined with other options."""
        mock_get_conn.return_value = mock_connection_with_custom_fields
        mock_settings = MagicMock()
        mock_settings.global_config.enforce_dor = False
        mock_get_settings.return_value = mock_settings

        mock_client = MagicMock()
        mock_client.create_issue.return_value = mock_created_issue
        mock_jira_client_class.from_connection.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "New bug",
                "--type",
                "Bug",
                "--priority",
                "High",
                "--label",
                "urgent",
                "--custom",
                "affected_system=Infrastructure",
                "--original-estimate",
                "2h",
                "--no-interactive",
            ],
        )

        assert result.exit_code == 0
        assert "Issue created successfully" in result.stdout

        call_kwargs = mock_client.create_issue.call_args.kwargs
        assert call_kwargs["priority"] == "High"
        assert call_kwargs["labels"] == ["urgent"]
        assert call_kwargs["customfield_10001"] == {"value": "Infrastructure"}
        assert "timetracking" in call_kwargs
