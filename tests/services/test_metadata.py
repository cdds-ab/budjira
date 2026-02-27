"""Tests for MetadataService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from budjira.services.metadata import MetadataService
from budjira.utils.errors import JiraAPIError


@pytest.fixture
def mock_jira_client() -> MagicMock:
    """Create a mock JIRA client."""
    return MagicMock()


@pytest.fixture
def metadata_service(mock_jira_client: MagicMock) -> MetadataService:
    """Create a MetadataService with mocked client."""
    return MetadataService(mock_jira_client)


class TestGetProjects:
    """Test get_projects method."""

    def test_returns_project_list(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test fetching project list."""
        mock_project = MagicMock()
        mock_project.key = "TEST"
        mock_project.name = "Test Project"
        mock_jira_client.projects.return_value = [mock_project]

        result = metadata_service.get_projects()

        assert result == [{"key": "TEST", "name": "Test Project"}]

    def test_raises_on_error(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test that API errors are wrapped."""
        mock_jira_client.projects.side_effect = Exception("Network error")

        with pytest.raises(JiraAPIError, match="Failed to fetch projects"):
            metadata_service.get_projects()


class TestGetIssueTypes:
    """Test get_issue_types method."""

    def test_returns_type_names(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test fetching issue type names."""
        mock_type = MagicMock()
        mock_type.name = "Bug"
        mock_jira_client.issue_types.return_value = [mock_type]

        result = metadata_service.get_issue_types()
        assert result == ["Bug"]


class TestGetPriorities:
    """Test get_priorities method."""

    def test_returns_priority_names(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test fetching priority names."""
        p1 = MagicMock()
        p1.name = "FK1"
        p2 = MagicMock()
        p2.name = "FK2"
        mock_jira_client.priorities.return_value = [p1, p2]

        result = metadata_service.get_priorities()
        assert result == ["FK1", "FK2"]


class TestFetchProjectMetadata:
    """Test fetch_project_metadata method."""

    def test_fetches_complete_metadata(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test fetching complete project metadata."""
        # Mock createmeta response
        mock_jira_client.createmeta.return_value = {
            "projects": [
                {
                    "key": "TEST",
                    "issuetypes": [
                        {
                            "id": "10001",
                            "name": "Bug",
                            "description": "A bug",
                            "subtask": False,
                            "fields": {
                                "summary": {
                                    "name": "Summary",
                                    "required": True,
                                    "schema": {"type": "string"},
                                },
                                "priority": {
                                    "name": "Priority",
                                    "required": True,
                                    "schema": {"type": "priority"},
                                    "allowedValues": [
                                        {"name": "High"},
                                        {"name": "Low"},
                                    ],
                                },
                            },
                        },
                        {
                            "id": "10002",
                            "name": "Story",
                            "subtask": False,
                            "fields": {},
                        },
                    ],
                }
            ]
        }

        # Mock priorities
        p1 = MagicMock()
        p1.name = "High"
        p2 = MagicMock()
        p2.name = "Low"
        mock_jira_client.priorities.return_value = [p1, p2]

        # Mock project info
        mock_project = MagicMock()
        mock_project.name = "Test Project"
        comp1 = MagicMock()
        comp1.name = "Backend"
        mock_project.components = [comp1]
        mock_jira_client.project.return_value = mock_project

        result = metadata_service.fetch_project_metadata("TEST")

        assert result.project_key == "TEST"
        assert result.project_name == "Test Project"
        assert len(result.issue_types) == 2
        assert result.issue_types[0].name == "Bug"
        assert len(result.issue_types[0].fields) == 2
        assert result.priorities == ["High", "Low"]
        assert result.components == ["Backend"]

    def test_handles_createmeta_failure(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test graceful handling when createmeta fails."""
        mock_jira_client.createmeta.side_effect = Exception("Not supported")

        # Priorities still work
        p1 = MagicMock()
        p1.name = "High"
        mock_jira_client.priorities.return_value = [p1]

        mock_project = MagicMock()
        mock_project.name = "Test"
        mock_project.components = []
        mock_jira_client.project.return_value = mock_project

        result = metadata_service.fetch_project_metadata("TEST")

        assert result.issue_types == []
        assert result.priorities == ["High"]

    def test_handles_project_info_failure(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test graceful handling when project info fetch fails."""
        mock_jira_client.createmeta.return_value = {"projects": []}

        p1 = MagicMock()
        p1.name = "High"
        mock_jira_client.priorities.return_value = [p1]

        mock_jira_client.project.side_effect = Exception("Not found")

        result = metadata_service.fetch_project_metadata("TEST")

        assert result.project_name == "TEST"  # Falls back to key
        assert result.components == []

    def test_raises_on_priority_failure(self, metadata_service: MetadataService, mock_jira_client: MagicMock) -> None:
        """Test that priority fetch failure raises JiraAPIError."""
        mock_jira_client.createmeta.return_value = {"projects": []}
        mock_jira_client.priorities.side_effect = Exception("API error")

        with pytest.raises(JiraAPIError):
            metadata_service.fetch_project_metadata("TEST")

    def test_parses_allowed_values_with_value_key(
        self, metadata_service: MetadataService, mock_jira_client: MagicMock
    ) -> None:
        """Test parsing allowedValues that use 'value' instead of 'name'."""
        mock_jira_client.createmeta.return_value = {
            "projects": [
                {
                    "key": "TEST",
                    "issuetypes": [
                        {
                            "id": "1",
                            "name": "Task",
                            "fields": {
                                "customfield_001": {
                                    "name": "Environment",
                                    "required": False,
                                    "schema": {"type": "option"},
                                    "allowedValues": [
                                        {"value": "Production"},
                                        {"value": "Staging"},
                                    ],
                                },
                            },
                        },
                    ],
                }
            ]
        }

        p1 = MagicMock()
        p1.name = "High"
        mock_jira_client.priorities.return_value = [p1]

        mock_project = MagicMock()
        mock_project.name = "Test"
        mock_project.components = []
        mock_jira_client.project.return_value = mock_project

        result = metadata_service.fetch_project_metadata("TEST")

        field = result.issue_types[0].fields[0]
        assert field.allowed_values == ["Production", "Staging"]
