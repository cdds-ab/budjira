"""Models for Jira project administration (listing and creating projects)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

BoardType = Literal["kanban", "scrum"]


class ProjectSummary(BaseModel):
    """One project of an instance, as listed by ``project list``."""

    key: str
    name: str
    id: str
    style: str
    lead: str | None = None

    @property
    def management(self) -> str:
        """Human label for Jira's ``style`` (classic / next-gen)."""
        return {"classic": "company-managed", "next-gen": "team-managed"}.get(self.style, self.style)


class ReferenceProject(BaseModel):
    """A company-managed project whose schemes a new project reuses (``--like``).

    Scheme IDs are kept as Jira returns them; ``None`` means the reference has no
    scheme of that kind assigned (Jira's default applies) and the new project
    will get the default too.
    """

    key: str
    id: str
    project_type_key: str
    issue_type_scheme: str | None = None
    issue_type_screen_scheme: str | None = None
    workflow_scheme: int | None = None
