"""Project administration service: list projects, create a project like another.

The jira library has no public API for project search, scheme lookup, project
creation with schemes, or agile board creation, so this service talks to the
REST endpoints through the library's authenticated session (the same approach
as ``CommentService.add_adf``).

Jira Cloud behaviour this module encodes:

* ``POST /rest/api/3/project`` rejects ``projectTemplateKey`` together with
  explicit schemes, so a project created ``--like`` another carries the schemes
  and no template; its board is added afterwards via a filter and
  ``POST /rest/agile/1.0/board``.
* Setting ``permissionScheme`` fails on the Jira Free plan, so it is never sent;
  the new project gets the default permission scheme.
"""

from __future__ import annotations

import json
from typing import Any

from jira.exceptions import JIRAError

from budjira.models.project import BoardType, ProjectSummary, ReferenceProject
from budjira.services.base import BaseJiraService
from budjira.utils.errors import (
    AuthenticationError,
    BudjiraError,
    JiraAPIError,
    PermissionError,
    ValidationError,
)

_BASES = {
    "api3": "{server}/rest/api/3/{path}",
    "agile": "{server}/rest/agile/1.0/{path}",
}

_PAGE_SIZE = 50


def build_project_payload(
    key: str,
    name: str,
    reference: ReferenceProject,
    *,
    lead_account_id: str,
) -> dict[str, Any]:
    """Build the ``POST /rest/api/3/project`` body for a project like ``reference``.

    Never sets ``projectTemplateKey`` (conflicts with explicit schemes) nor
    ``permissionScheme`` (rejected on the Jira Free plan).

    Args:
        key: New project key
        name: New project name
        reference: Project whose schemes are reused
        lead_account_id: Account ID of the project lead

    Returns:
        Request body
    """
    payload: dict[str, Any] = {
        "key": key,
        "name": name,
        "projectTypeKey": reference.project_type_key,
        "leadAccountId": lead_account_id,
        "assigneeType": "UNASSIGNED",
    }
    schemes: dict[str, str | int | None] = {
        "issueTypeScheme": reference.issue_type_scheme,
        "issueTypeScreenScheme": reference.issue_type_screen_scheme,
        "workflowScheme": reference.workflow_scheme,
    }
    for field, scheme_id in schemes.items():
        if scheme_id is not None:
            # Jira returns these IDs as strings but expects int64 on create.
            payload[field] = int(scheme_id)
    return payload


def build_filter_payload(key: str, project_id: str) -> dict[str, Any]:
    """Build the board filter, shared with the project so its members see the board.

    Args:
        key: Project key
        project_id: Project ID (share permissions need the ID)

    Returns:
        ``POST /rest/api/3/filter`` body
    """
    return {
        "name": f"Filter for {key} board",
        "jql": f"project = {key} ORDER BY Rank ASC",
        "sharePermissions": [{"type": "project", "project": {"id": project_id}}],
    }


def build_board_payload(key: str, filter_id: int | str, board_type: BoardType) -> dict[str, Any]:
    """Build the ``POST /rest/agile/1.0/board`` body.

    Args:
        key: Project key the board belongs to
        filter_id: Filter the board shows (a placeholder string in dry runs)
        board_type: kanban or scrum

    Returns:
        Request body
    """
    return {
        "name": f"{key} board",
        "type": board_type,
        "filterId": filter_id,
        "location": {"type": "project", "projectKeyOrId": key},
    }


def _error_details(error: JIRAError) -> tuple[list[str], dict[str, str]]:
    """Extract Jira's ``errorMessages`` and ``errors`` from an error response."""
    raw = error.response.text if error.response is not None else error.text
    try:
        body = json.loads(raw or "")
    except (TypeError, ValueError):
        return ([error.text] if error.text else []), {}
    if not isinstance(body, dict):
        return [str(body)], {}
    messages = [str(m) for m in body.get("errorMessages") or []]
    errors = {str(k): str(v) for k, v in (body.get("errors") or {}).items()}
    return messages, errors


def _describe(error: JIRAError) -> str:
    """One line with everything Jira said about a failed request."""
    messages, errors = _error_details(error)
    parts = messages + [f"{field}: {text}" for field, text in errors.items()]
    return "; ".join(parts) or (error.text or f"HTTP {error.status_code}")


class ProjectService(BaseJiraService):
    """List projects of an instance and create a project like an existing one."""

    def _rest(self, method: str, path: str, *, api: str = "api3", **kwargs: Any) -> Any:
        """Call a REST endpoint through the authenticated session.

        Raises:
            JIRAError: For any non-2xx response (whether the session raises or not)
        """
        url = self.client._get_url(path, base=_BASES[api])
        response = getattr(self.client._session, method)(url, **kwargs)
        if not response.ok:
            raise JIRAError(text=response.text, status_code=response.status_code, url=url, response=response)
        return response.json() if response.text else None

    def _call(self, operation: str, method: str, path: str, **kwargs: Any) -> Any:
        """``_rest`` with generic error translation (401/403/other)."""
        try:
            return self._rest(method, path, **kwargs)
        except JIRAError as e:
            raise self._generic_error(e, operation) from e

    @staticmethod
    def _generic_error(error: JIRAError, operation: str) -> BudjiraError:
        if error.status_code == 401:
            return AuthenticationError(
                f"{operation} failed: Jira rejected the credentials (HTTP 401). "
                "Check the connection's API token — it may be expired or revoked."
            )
        if error.status_code == 403:
            return PermissionError(f"{operation} failed: access denied. {_describe(error)}")
        return JiraAPIError(f"{operation} failed: {_describe(error)}")

    def list_projects(self) -> list[ProjectSummary]:
        """List every project the token can see, reading all pages.

        Returns:
            Projects with key, name, id, style and lead
        """
        self._log_operation("List projects")
        projects: list[ProjectSummary] = []
        start_at = 0
        while True:
            page = self._call(
                "List projects",
                "get",
                "project/search",
                params={"startAt": start_at, "maxResults": _PAGE_SIZE, "expand": "lead", "orderBy": "key"},
            )
            values = page.get("values") or []
            projects.extend(
                ProjectSummary(
                    key=p["key"],
                    name=p.get("name", ""),
                    id=str(p.get("id", "")),
                    style=p.get("style", ""),
                    lead=(p.get("lead") or {}).get("displayName"),
                )
                for p in values
            )
            if page.get("isLast", True) or not values:
                return projects
            start_at += len(values)

    def project_exists(self, key: str) -> bool:
        """Whether a project with this key is visible to the token."""
        page = self._call("Look up project", "get", "project/search", params={"keys": key})
        return any(p.get("key") == key for p in page.get("values") or [])

    def current_account_id(self) -> str:
        """Account ID of the authenticated user (becomes the project lead)."""
        return str(self._call("Read current user", "get", "myself")["accountId"])

    def get_reference(self, key: str) -> ReferenceProject:
        """Read the schemes of a company-managed reference project.

        Raises:
            ValidationError: Reference not found, or team-managed (no shareable schemes)
        """
        self._log_operation("Read reference project", project_key=key)
        try:
            project = self._rest("get", f"project/{key}")
        except JIRAError as e:
            if e.status_code == 404:
                raise ValidationError(
                    f"Reference project '{key}' not found or not visible. Run 'budjira project list' to see projects."
                ) from e
            raise self._generic_error(e, f"Read reference project '{key}'") from e

        if project.get("style") == "next-gen" or project.get("simplified"):
            raise ValidationError(
                f"Reference project '{key}' is team-managed; team-managed projects have no schemes to share. "
                "Use a company-managed project as reference."
            )

        project_id = str(project["id"])

        def first(endpoint: str, field: str) -> Any:
            page = self._call(
                f"Read {endpoint} of '{key}'", "get", f"{endpoint}/project", params={"projectId": project_id}
            )
            values = page.get("values") or []
            return (values[0].get(field) or {}).get("id") if values else None

        issue_type_scheme = first("issuetypescheme", "issueTypeScheme")
        screen_scheme = first("issuetypescreenscheme", "issueTypeScreenScheme")
        workflow_scheme = first("workflowscheme", "workflowScheme")

        return ReferenceProject(
            key=project["key"],
            id=project_id,
            project_type_key=project.get("projectTypeKey", "software"),
            issue_type_scheme=None if issue_type_scheme is None else str(issue_type_scheme),
            issue_type_screen_scheme=None if screen_scheme is None else str(screen_scheme),
            workflow_scheme=None if workflow_scheme is None else int(workflow_scheme),
        )

    def create_project(self, payload: dict[str, Any]) -> dict[str, str]:
        """Create a project.

        Returns:
            ``{"id": ..., "key": ...}`` of the new project

        Raises:
            ValidationError: Key not available, Free-plan restriction, other rejected input
            PermissionError: Token lacks the Administer Jira global permission
            AuthenticationError: Credentials rejected
            JiraAPIError: Any other failure
        """
        key = payload.get("key", "")
        self._log_operation("Create project", project_key=key)
        try:
            created = self._rest("post", "project", json=payload)
        except JIRAError as e:
            raise self._create_error(e, key) from e
        return {"id": str(created["id"]), "key": str(created["key"])}

    def _create_error(self, error: JIRAError, key: str) -> BudjiraError:
        messages, errors = _error_details(error)
        everything = " ".join(messages + list(errors.values())).lower()
        if error.status_code == 403:
            return PermissionError(
                f"Creating project '{key}' was refused: creating projects needs the 'Administer Jira' "
                f"global permission. {_describe(error)}"
            )
        if error.status_code == 400:
            if "projectKey" in errors:
                return ValidationError(f"Project key '{key}' is not available: {errors['projectKey']}")
            if "free plan" in everything:
                return ValidationError(
                    "Jira refused the project because of a Jira Free plan restriction "
                    f"({_describe(error)}). budjira never sets a permission scheme; "
                    "check whether the reference project's schemes are available on this plan."
                )
            return ValidationError(f"Jira rejected project '{key}': {_describe(error)}")
        return self._generic_error(error, f"Create project '{key}'")

    def create_filter(self, payload: dict[str, Any]) -> int:
        """Create a filter; returns its ID."""
        self._log_operation("Create filter", name=payload.get("name"))
        created = self._call("Create board filter", "post", "filter", json=payload)
        return int(created["id"])

    def create_board(self, payload: dict[str, Any]) -> int:
        """Create an agile board; returns its ID."""
        self._log_operation("Create board", name=payload.get("name"))
        created = self._call("Create board", "post", "board", api="agile", json=payload)
        return int(created["id"])
