"""Decide how an issue description is rendered for upload.

Jira renders the REST v2 ``description`` field with the legacy wiki-markup
renderer. Authors usually write Markdown, so budjira converts on upload
(issue #95) - but an instance whose house format is *already* wiki markup is
damaged by that conversion (issue #106): a leading ``#`` is a Markdown heading
and a wiki ordered-list marker at the same time, and the heading rule wins.

The dialect therefore belongs to the instance, not to the converter. This
module holds the two decisions in one place each: which dialect applies
(:func:`resolve_description_dialect` for descriptions,
:func:`resolve_comment_dialect` for comments) and what that means for the
payload (:func:`render_description`). The service layer only passes the
resolved dialect through - it never decides whether to convert.

Descriptions and comments have independent connection settings on purpose:
descriptions historically went through the converter (default ``markdown``),
comments were posted raw (default ``wiki``). An instance whose authors write
one dialect for both can now express that; an instance that differs per field
keeps the asymmetry configurable rather than reversed.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Final, get_args

from budjira.models.connection import DescriptionDialect
from budjira.utils.markdown_to_jira import markdown_to_wiki

if TYPE_CHECKING:
    from budjira.models.connection import Connection

DESCRIPTION_DIALECTS: Final[tuple[DescriptionDialect, ...]] = get_args(DescriptionDialect)


class DescriptionDialectOption(str, Enum):
    """CLI-facing spelling of the dialects (Typer needs an Enum to offer choices)."""

    MARKDOWN = "markdown"
    WIKI = "wiki"


def resolve_description_dialect(
    override: DescriptionDialectOption | None,
    connection: Connection,
) -> DescriptionDialect:
    """Resolve the dialect for a single write.

    Priority: explicit CLI override, then the connection setting, whose own
    default is ``markdown``.

    Args:
        override: Value of a ``--description-dialect`` option, if given.
        connection: The connection the write goes to.

    Returns:
        The dialect to hand to the service layer.
    """
    if override is not None:
        # The enum mirrors DescriptionDialect member for member; a test guards the drift.
        return override.value
    return connection.description_dialect


def resolve_comment_dialect(
    override: DescriptionDialectOption | None,
    connection: Connection,
) -> DescriptionDialect:
    """Resolve the dialect for a single comment write.

    Same priority as :func:`resolve_description_dialect` (CLI override, then
    connection setting), but the connection default is ``wiki`` - the
    historical raw behaviour for comments.

    Args:
        override: Value of a ``--dialect`` option on a comment command, if given.
        connection: The connection the write goes to.

    Returns:
        The dialect to hand to the service layer.
    """
    if override is not None:
        return override.value
    return connection.comment_dialect


def render_description(text: str, dialect: DescriptionDialect) -> str:
    """Render a description for upload according to its dialect.

    Args:
        text: The description as the author wrote it.
        dialect: ``markdown`` converts to wiki markup, ``wiki`` passes through.

    Returns:
        The string to send as the ``description`` field.
    """
    if dialect == "wiki":
        return text
    return markdown_to_wiki(text)
