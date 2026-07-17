"""Tests for Markdown -> Jira wiki-markup conversion.

budjira uploads issue descriptions verbatim over REST API v2, where Jira Cloud
renders them with the legacy wiki-markup renderer. Authors write Markdown, so
without conversion headings, checkboxes and bullet lists render as garbage
(see issue #95). ``markdown_to_wiki`` bridges that gap until the client moves
to REST v3 + ADF (see epic #96).
"""

from budjira.utils.markdown_to_jira import markdown_to_wiki


class TestHeadings:
    def test_h1(self) -> None:
        assert markdown_to_wiki("# Title") == "h1. Title"

    def test_h2(self) -> None:
        assert markdown_to_wiki("## Description") == "h2. Description"

    def test_h6(self) -> None:
        assert markdown_to_wiki("###### Deep") == "h6. Deep"

    def test_hash_without_space_is_not_a_heading(self) -> None:
        # "#tag" is not a Markdown heading and must not become "h1."
        assert markdown_to_wiki("#tag stays literal") == "#tag stays literal"

    def test_more_than_six_hashes_is_not_a_heading(self) -> None:
        assert markdown_to_wiki("####### too deep") == "####### too deep"


class TestLists:
    def test_dash_bullet(self) -> None:
        assert markdown_to_wiki("- item") == "* item"

    def test_plus_bullet(self) -> None:
        assert markdown_to_wiki("+ item") == "* item"

    def test_asterisk_bullet_passthrough(self) -> None:
        assert markdown_to_wiki("* item") == "* item"

    def test_nested_bullet(self) -> None:
        assert markdown_to_wiki("  - nested") == "** nested"

    def test_ordered_list(self) -> None:
        assert markdown_to_wiki("1. first") == "# first"

    def test_ordered_list_multi_digit(self) -> None:
        assert markdown_to_wiki("10. tenth") == "# tenth"


class TestCheckboxes:
    def test_unchecked(self) -> None:
        assert markdown_to_wiki("- [ ] todo") == "* (x) todo"

    def test_checked_lower(self) -> None:
        assert markdown_to_wiki("- [x] done") == "* (/) done"

    def test_checked_upper(self) -> None:
        assert markdown_to_wiki("- [X] done") == "* (/) done"


class TestInline:
    def test_bold_double_star(self) -> None:
        assert markdown_to_wiki("a **bold** word") == "a *bold* word"

    def test_bold_double_underscore(self) -> None:
        assert markdown_to_wiki("a __bold__ word") == "a *bold* word"

    def test_inline_code(self) -> None:
        assert markdown_to_wiki("call `foo()` now") == "call {{foo()}} now"

    def test_link(self) -> None:
        assert markdown_to_wiki("see [docs](https://x.io)") == "see [docs|https://x.io]"

    def test_underscore_italic_passthrough(self) -> None:
        # Jira italic already uses underscores, so _italic_ needs no change.
        assert markdown_to_wiki("an _italic_ word") == "an _italic_ word"


class TestCodeFences:
    def test_fenced_block_with_language(self) -> None:
        md = "```python\nx = 1\n```"
        assert markdown_to_wiki(md) == "{code:python}\nx = 1\n{code}"

    def test_fenced_block_plain(self) -> None:
        md = "```\nplain\n```"
        assert markdown_to_wiki(md) == "{code}\nplain\n{code}"

    def test_no_inline_conversion_inside_fence(self) -> None:
        # Markdown-looking content inside a fence stays verbatim.
        md = "```\n# not a heading\n- **not bold**\n```"
        assert markdown_to_wiki(md) == "{code}\n# not a heading\n- **not bold**\n{code}"


class TestPassthrough:
    def test_empty_string(self) -> None:
        assert markdown_to_wiki("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert markdown_to_wiki("Just a sentence.") == "Just a sentence."

    def test_multiline_plain_text(self) -> None:
        assert markdown_to_wiki("line one\n\nline two") == "line one\n\nline two"


class TestRealisticDorDescription:
    def test_issue_95_example(self) -> None:
        md = "## Description\n\nSome text.\n\n## Acceptance Criteria\n\n- [ ] first\n- [x] second"
        expected = "h2. Description\n\nSome text.\n\nh2. Acceptance Criteria\n\n* (x) first\n* (/) second"
        assert markdown_to_wiki(md) == expected
