# mypy: disable-error-code="attr-defined,union-attr"
"""Tests for the project administration service (list / create --like)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from budjira.models.project import ProjectSummary, ReferenceProject
from budjira.services.projects import (
    ProjectService,
    build_board_payload,
    build_filter_payload,
    build_project_payload,
)
from budjira.utils.errors import AuthenticationError, JiraAPIError, ValidationError
from budjira.utils.errors import PermissionError as BudjiraPermissionError

API3 = "{server}/rest/api/3/{path}"
AGILE = "{server}/rest/agile/1.0/{path}"


def _response(payload: Any = None, *, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response."""
    response = MagicMock()
    response.ok = status_code < 400
    response.status_code = status_code
    response.text = "" if payload is None else json.dumps(payload)
    response.json.return_value = payload
    return response


def _client() -> MagicMock:
    """Mock JIRA client whose _get_url renders a readable URL."""
    client = MagicMock()
    client._get_url.side_effect = lambda path, base: base.format(server="https://x.atlassian.net", path=path)
    return client


def _routes(client: MagicMock, method: str, routes: dict[str, MagicMock]) -> None:
    """Answer session calls of one HTTP method by URL suffix (path without query)."""

    def handler(url: str, **_: Any) -> MagicMock:
        for suffix, response in routes.items():
            if url.endswith(suffix):
                return response
        raise AssertionError(f"unexpected {method.upper()} {url}")

    getattr(client._session, method).side_effect = handler


def _project_json(
    key: str = "CDDSINT",
    pid: str = "10000",
    style: str = "classic",
    lead: str | None = "Fred Thiele",
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": pid,
        "key": key,
        "name": f"{key} name",
        "style": style,
        "simplified": style == "next-gen",
        "projectTypeKey": "software",
    }
    if lead is not None:
        data["lead"] = {"displayName": lead, "accountId": "acc-1"}
    return data


def _reference() -> ReferenceProject:
    return ReferenceProject(
        key="CDDSINT",
        id="10000",
        project_type_key="software",
        issue_type_scheme="10603",
        issue_type_screen_scheme="10236",
        workflow_scheme=10237,
    )


class TestListProjects:
    """project/search is paginated; every page must be read."""

    def test_reads_all_pages(self) -> None:
        client = _client()
        pages = [
            _response({"startAt": 0, "isLast": False, "values": [_project_json("AAA", "1")]}),
            _response({"startAt": 1, "isLast": True, "values": [_project_json("BBB", "2", style="next-gen")]}),
        ]
        client._session.get.side_effect = pages

        projects = ProjectService(client).list_projects()

        assert projects == [
            ProjectSummary(key="AAA", name="AAA name", id="1", style="classic", lead="Fred Thiele"),
            ProjectSummary(key="BBB", name="BBB name", id="2", style="next-gen", lead="Fred Thiele"),
        ]
        first, second = client._session.get.call_args_list
        assert first.kwargs["params"]["startAt"] == 0
        assert first.kwargs["params"]["expand"] == "lead"
        assert second.kwargs["params"]["startAt"] == 1

    def test_missing_lead_is_none(self) -> None:
        client = _client()
        client._session.get.return_value = _response(
            {"startAt": 0, "isLast": True, "values": [_project_json(lead=None)]}
        )

        (project,) = ProjectService(client).list_projects()

        assert project.lead is None

    def test_management_label(self) -> None:
        assert ProjectSummary(key="A", name="a", id="1", style="classic").management == "company-managed"
        assert ProjectSummary(key="A", name="a", id="1", style="next-gen").management == "team-managed"

    def test_unauthorized_is_reported_as_authentication_error(self) -> None:
        client = _client()
        client._session.get.return_value = _response({"errorMessages": ["Unauthorized"]}, status_code=401)

        with pytest.raises(AuthenticationError):
            ProjectService(client).list_projects()


class TestProjectExists:
    def test_exists(self) -> None:
        client = _client()
        client._session.get.return_value = _response({"isLast": True, "values": [_project_json("APX")]})

        assert ProjectService(client).project_exists("APX") is True
        assert client._session.get.call_args.kwargs["params"]["keys"] == "APX"

    def test_absent(self) -> None:
        client = _client()
        client._session.get.return_value = _response({"isLast": True, "values": []})

        assert ProjectService(client).project_exists("APX") is False


class TestGetReference:
    """--like reads the three schemes a company-managed project is assigned."""

    def test_collects_schemes(self) -> None:
        client = _client()
        _routes(
            client,
            "get",
            {
                "/project/CDDSINT": _response(_project_json()),
                "/issuetypescheme/project": _response(
                    {"values": [{"issueTypeScheme": {"id": "10603"}, "projectIds": ["10000"]}]}
                ),
                "/issuetypescreenscheme/project": _response(
                    {"values": [{"issueTypeScreenScheme": {"id": "10236"}, "projectIds": ["10000"]}]}
                ),
                "/workflowscheme/project": _response(
                    {"values": [{"workflowScheme": {"id": 10237}, "projectIds": ["10000"]}]}
                ),
            },
        )

        reference = ProjectService(client).get_reference("CDDSINT")

        assert reference == _reference()
        scheme_calls = [c for c in client._session.get.call_args_list if c.args[0].endswith("scheme/project")]
        assert {tuple(c.kwargs["params"].items()) for c in scheme_calls} == {(("projectId", "10000"),)}

    def test_unassigned_scheme_is_none(self) -> None:
        client = _client()
        _routes(
            client,
            "get",
            {
                "/project/CDDSINT": _response(_project_json()),
                "/issuetypescheme/project": _response({"values": []}),
                "/issuetypescreenscheme/project": _response({"values": []}),
                "/workflowscheme/project": _response({"values": []}),
            },
        )

        reference = ProjectService(client).get_reference("CDDSINT")

        assert reference.issue_type_scheme is None
        assert reference.issue_type_screen_scheme is None
        assert reference.workflow_scheme is None

    def test_team_managed_reference_is_rejected(self) -> None:
        client = _client()
        _routes(client, "get", {"/project/PEX": _response(_project_json("PEX", style="next-gen"))})

        with pytest.raises(ValidationError, match="team-managed"):
            ProjectService(client).get_reference("PEX")

    def test_unknown_reference(self) -> None:
        client = _client()
        _routes(client, "get", {"/project/NOPE": _response({"errorMessages": ["No project"]}, status_code=404)})

        with pytest.raises(ValidationError, match="NOPE"):
            ProjectService(client).get_reference("NOPE")


class TestPayloads:
    def test_project_payload_reuses_reference_schemes(self) -> None:
        payload = build_project_payload("APX", "Apodeixis", _reference(), lead_account_id="acc-1")

        assert payload == {
            "key": "APX",
            "name": "Apodeixis",
            "projectTypeKey": "software",
            "leadAccountId": "acc-1",
            "assigneeType": "UNASSIGNED",
            "issueTypeScheme": 10603,
            "issueTypeScreenScheme": 10236,
            "workflowScheme": 10237,
        }

    def test_project_payload_never_sets_template_or_permission_scheme(self) -> None:
        payload = build_project_payload("APX", "Apodeixis", _reference(), lead_account_id="acc-1")

        assert "projectTemplateKey" not in payload
        assert "permissionScheme" not in payload

    def test_project_payload_omits_unassigned_schemes(self) -> None:
        reference = _reference().model_copy(update={"workflow_scheme": None, "issue_type_screen_scheme": None})

        payload = build_project_payload("APX", "Apodeixis", reference, lead_account_id="acc-1")

        assert "workflowScheme" not in payload
        assert "issueTypeScreenScheme" not in payload
        assert payload["issueTypeScheme"] == 10603

    def test_filter_payload_is_shared_with_the_project(self) -> None:
        assert build_filter_payload("APX", "10400") == {
            "name": "Filter for APX board",
            "jql": "project = APX ORDER BY Rank ASC",
            "sharePermissions": [{"type": "project", "project": {"id": "10400"}}],
        }

    def test_board_payload(self) -> None:
        assert build_board_payload("APX", 10500, "kanban") == {
            "name": "APX board",
            "type": "kanban",
            "filterId": 10500,
            "location": {"type": "project", "projectKeyOrId": "APX"},
        }


class TestCurrentAccountId:
    def test_reads_myself(self) -> None:
        client = _client()
        client._session.get.return_value = _response({"accountId": "acc-1", "displayName": "Fred"})

        assert ProjectService(client).current_account_id() == "acc-1"
        assert client._session.get.call_args.args[0].endswith("/rest/api/3/myself")


class TestCreateProject:
    def test_posts_payload_and_returns_identifiers(self) -> None:
        client = _client()
        client._session.post.return_value = _response({"id": 10400, "key": "APX", "self": "..."}, status_code=201)
        payload = {"key": "APX", "name": "Apodeixis"}

        created = ProjectService(client).create_project(payload)

        assert created == {"id": "10400", "key": "APX"}
        url = client._session.post.call_args.args[0]
        assert url == "https://x.atlassian.net/rest/api/3/project"
        assert client._session.post.call_args.kwargs["json"] == payload

    def test_key_taken(self) -> None:
        client = _client()
        client._session.post.return_value = _response(
            {"errorMessages": [], "errors": {"projectKey": "A project with that project key already exists."}},
            status_code=400,
        )

        with pytest.raises(ValidationError, match=r"'APX' is not available.*already exists"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})

    def test_missing_admin_permission(self) -> None:
        client = _client()
        client._session.post.return_value = _response({"errorMessages": ["Forbidden"]}, status_code=403)

        with pytest.raises(BudjiraPermissionError, match="Administer Jira"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})

    def test_free_plan_permission_scheme_restriction(self) -> None:
        client = _client()
        client._session.post.return_value = _response(
            {"errorMessages": ["Changing permission schemes is not allowed on the Jira free plan."]},
            status_code=400,
        )

        with pytest.raises(ValidationError, match="Free plan"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})

    def test_other_400_lists_all_messages(self) -> None:
        client = _client()
        client._session.post.return_value = _response(
            {"errorMessages": ["Bad thing"], "errors": {"workflowScheme": "Invalid workflow scheme"}},
            status_code=400,
        )

        with pytest.raises(ValidationError, match=r"Bad thing.*workflowScheme: Invalid workflow scheme"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})

    def test_server_error(self) -> None:
        client = _client()
        client._session.post.return_value = _response({"errorMessages": ["boom"]}, status_code=500)

        with pytest.raises(JiraAPIError, match="boom"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})

    def test_session_raising_jira_error_is_translated(self) -> None:
        """The jira library's session may raise instead of returning a non-ok response."""
        from jira.exceptions import JIRAError

        client = _client()
        response = _response(
            {"errors": {"projectKey": "A project with that project key already exists."}}, status_code=400
        )
        client._session.post.side_effect = JIRAError(status_code=400, text="x", response=response)

        with pytest.raises(ValidationError, match="already exists"):
            ProjectService(client).create_project({"key": "APX", "name": "Apodeixis"})


class TestCreateBoard:
    def test_creates_filter_then_board(self) -> None:
        client = _client()
        _routes(
            client,
            "post",
            {
                "/rest/api/3/filter": _response({"id": "10500", "name": "Filter for APX board"}),
                "/rest/agile/1.0/board": _response({"id": 300, "name": "APX board", "type": "kanban"}, status_code=201),
            },
        )
        service = ProjectService(client)

        filter_id = service.create_filter(build_filter_payload("APX", "10400"))
        board_id = service.create_board(build_board_payload("APX", filter_id, "kanban"))

        assert filter_id == 10500
        assert board_id == 300
        board_call = client._session.post.call_args_list[1]
        assert board_call.kwargs["json"]["filterId"] == 10500

    def test_board_failure_is_reported(self) -> None:
        client = _client()
        client._session.post.return_value = _response({"errorMessages": ["no board for you"]}, status_code=400)

        with pytest.raises(JiraAPIError, match="no board for you"):
            ProjectService(client).create_board(build_board_payload("APX", 10500, "kanban"))
