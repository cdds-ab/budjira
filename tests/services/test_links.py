# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for link service."""

from unittest.mock import MagicMock

import pytest
from budjira.services.links import LinkService
from budjira.utils.errors import InvalidIssueError, JiraAPIError
from budjira.utils.errors import PermissionError as BudjiraPermissionError
from jira.exceptions import JIRAError


class TestGetLinkTypes:
    """Test get_link_types method."""

    def test_get_link_types_success(self) -> None:
        """Test getting link types successfully."""
        mock_client = MagicMock()

        # Mock link types response
        link_type1 = MagicMock()
        link_type1.id = "10000"
        link_type1.name = "Relates"
        link_type1.inward = "relates to"
        link_type1.outward = "relates to"

        link_type2 = MagicMock()
        link_type2.id = "10001"
        link_type2.name = "Blocks"
        link_type2.inward = "is blocked by"
        link_type2.outward = "blocks"

        mock_client.issue_link_types.return_value = [link_type1, link_type2]

        service = LinkService(mock_client)
        link_types = service.get_link_types()

        assert len(link_types) == 2
        assert "Relates" in link_types
        assert "Blocks" in link_types
        assert link_types["Relates"]["id"] == "10000"
        assert link_types["Blocks"]["inward"] == "is blocked by"

        mock_client.issue_link_types.assert_called_once()

    def test_get_link_types_cached(self) -> None:
        """Test that link types are cached."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.id = "10000"
        link_type.name = "Relates"
        link_type.inward = "relates to"
        link_type.outward = "relates to"

        mock_client.issue_link_types.return_value = [link_type]

        service = LinkService(mock_client)

        # First call
        link_types1 = service.get_link_types()
        # Second call
        link_types2 = service.get_link_types()

        assert link_types1 == link_types2
        # Should only call API once (cached)
        mock_client.issue_link_types.assert_called_once()

    def test_get_link_types_api_error(self) -> None:
        """Test handling API error when getting link types."""
        mock_client = MagicMock()

        mock_client.issue_link_types.side_effect = JIRAError(status_code=500, text="Server error")

        service = LinkService(mock_client)

        with pytest.raises(JiraAPIError, match="Failed to fetch issue link types"):
            service.get_link_types()


class TestCreateLink:
    """Test create_link method."""

    def test_create_link_success(self) -> None:
        """Test creating a link successfully."""
        mock_client = MagicMock()

        # Mock link types
        link_type = MagicMock()
        link_type.id = "10000"
        link_type.name = "Relates"
        link_type.inward = "relates to"
        link_type.outward = "relates to"

        mock_client.issue_link_types.return_value = [link_type]
        mock_client.create_issue_link.return_value = None

        service = LinkService(mock_client)
        service.create_link("Relates", "PROJ-123", "PROJ-456")

        mock_client.create_issue_link.assert_called_once()
        call_args = mock_client.create_issue_link.call_args
        assert call_args[1]["type"] == "Relates"
        assert call_args[1]["outwardIssue"] == "PROJ-456"
        assert call_args[1]["inwardIssue"] == "PROJ-123"

    def test_create_link_with_comment(self) -> None:
        """Test creating a link with comment."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.id = "10000"
        link_type.name = "Relates"
        mock_client.issue_link_types.return_value = [link_type]

        service = LinkService(mock_client)
        service.create_link("Relates", "PROJ-100", "PROJ-200", comment="Test comment")

        call_args = mock_client.create_issue_link.call_args
        assert call_args[1]["comment"] == {"body": "Test comment"}

    def test_create_link_invalid_type(self) -> None:
        """Test creating link with invalid type."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.name = "Relates"
        mock_client.issue_link_types.return_value = [link_type]

        service = LinkService(mock_client)

        with pytest.raises(ValueError, match="Invalid link type 'InvalidType'"):
            service.create_link("InvalidType", "PROJ-100", "PROJ-200")

    def test_create_link_issue_not_found(self) -> None:
        """Test creating link when issue not found."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.name = "Relates"
        mock_client.issue_link_types.return_value = [link_type]

        mock_client.create_issue_link.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = LinkService(mock_client)

        with pytest.raises(InvalidIssueError):
            service.create_link("Relates", "PROJ-999", "PROJ-1000")

    def test_create_link_permission_denied(self) -> None:
        """Test creating link with insufficient permissions."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.name = "Blocks"
        mock_client.issue_link_types.return_value = [link_type]

        mock_client.create_issue_link.side_effect = JIRAError(status_code=403, text="Permission denied")

        service = LinkService(mock_client)

        with pytest.raises(BudjiraPermissionError):
            service.create_link("Blocks", "PROJ-100", "PROJ-200")

    def test_create_link_api_error(self) -> None:
        """Test creating link with API error."""
        mock_client = MagicMock()

        link_type = MagicMock()
        link_type.name = "Relates"
        mock_client.issue_link_types.return_value = [link_type]

        mock_client.create_issue_link.side_effect = JIRAError(status_code=400, text="Bad request")

        service = LinkService(mock_client)

        with pytest.raises(JiraAPIError):
            service.create_link("Relates", "PROJ-100", "PROJ-200")


class TestGetIssueLinks:
    """Test get_issue_links method."""

    def test_get_issue_links_success(self) -> None:
        """Test getting issue links successfully."""
        mock_client = MagicMock()

        # Mock issue with links
        mock_issue = MagicMock()
        mock_issue.key = "PROJ-123"

        link1 = MagicMock()
        link1.id = "10001"
        link1.type.name = "Relates"
        link1.outwardIssue.key = "PROJ-456"
        link1.outwardIssue.fields.summary = "Related issue"
        delattr(link1, "inwardIssue")

        mock_issue.fields.issuelinks = [link1]
        mock_client.issue.return_value = mock_issue

        service = LinkService(mock_client)
        links = service.get_issue_links("PROJ-123")

        assert len(links) == 1
        assert links[0].issue_key == "PROJ-456"
        assert links[0].direction == "outward"

        mock_client.issue.assert_called_once_with("PROJ-123", fields="issuelinks")

    def test_get_issue_links_no_links(self) -> None:
        """Test getting issue with no links."""
        mock_client = MagicMock()

        mock_issue = MagicMock()
        mock_issue.fields.issuelinks = []
        mock_client.issue.return_value = mock_issue

        service = LinkService(mock_client)
        links = service.get_issue_links("PROJ-999")

        assert links == []

    def test_get_issue_links_issue_not_found(self) -> None:
        """Test getting links for non-existent issue."""
        mock_client = MagicMock()

        mock_client.issue.side_effect = JIRAError(status_code=404, text="Issue not found")

        service = LinkService(mock_client)

        with pytest.raises(InvalidIssueError):
            service.get_issue_links("PROJ-9999")


class TestDeleteLink:
    """Test delete_link method."""

    def test_delete_link_success(self) -> None:
        """Test deleting a link successfully."""
        mock_client = MagicMock()

        service = LinkService(mock_client)
        service.delete_link("10001")

        mock_client.delete_issue_link.assert_called_once_with("10001")

    def test_delete_link_not_found(self) -> None:
        """Test deleting non-existent link."""
        mock_client = MagicMock()

        mock_client.delete_issue_link.side_effect = JIRAError(status_code=404, text="Link not found")

        service = LinkService(mock_client)

        with pytest.raises(InvalidIssueError, match="Issue link '10001' not found"):
            service.delete_link("10001")
