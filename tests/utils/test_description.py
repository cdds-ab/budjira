"""Tests for description dialect resolution and rendering."""

# mypy: disable-error-code="arg-type"
# Pydantic models accept strings for HttpUrl fields during validation

from budjira.models.connection import Connection
from budjira.utils.description import (
    DESCRIPTION_DIALECTS,
    DescriptionDialectOption,
    render_description,
    resolve_description_dialect,
)

WIKI_SOURCE = "{panel:bgColor=#eae6ff}\nh3. Steps\n# first\n# second\n{panel}"


def _connection(dialect: str = "markdown") -> Connection:
    return Connection(
        name="Test",
        url="https://test.atlassian.net",
        email="test@example.com",
        project_key="TEST",
        description_dialect=dialect,
    )


class TestRenderDescription:
    """render_description is the single place that decides about conversion."""

    def test_markdown_is_converted_to_wiki_markup(self) -> None:
        assert render_description("## Title\n- [ ] todo", "markdown") == "h2. Title\n* (x) todo"

    def test_wiki_is_passed_through_unchanged(self) -> None:
        assert render_description(WIKI_SOURCE, "wiki") == WIKI_SOURCE

    def test_empty_text_is_returned_unchanged(self) -> None:
        assert render_description("", "markdown") == ""


class TestResolveDescriptionDialect:
    """The CLI override wins over the connection, the connection over the default."""

    def test_connection_setting_is_used_without_override(self) -> None:
        assert resolve_description_dialect(None, _connection("wiki")) == "wiki"

    def test_default_connection_resolves_to_markdown(self) -> None:
        assert resolve_description_dialect(None, _connection()) == "markdown"

    def test_override_beats_connection_setting(self) -> None:
        assert resolve_description_dialect(DescriptionDialectOption.WIKI, _connection("markdown")) == "wiki"

    def test_override_can_force_markdown_on_a_wiki_connection(self) -> None:
        assert resolve_description_dialect(DescriptionDialectOption.MARKDOWN, _connection("wiki")) == "markdown"


def test_cli_choices_match_the_model_dialects() -> None:
    """The CLI must not offer a dialect the model rejects, or hide one it accepts."""
    assert {option.value for option in DescriptionDialectOption} == set(DESCRIPTION_DIALECTS)
