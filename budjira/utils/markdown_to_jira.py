"""Convert Markdown to Jira legacy wiki markup.

budjira talks to Jira over REST API v2 (jira-python's default), where the
``description`` field is a plain string that Jira Cloud renders with the
**legacy wiki-markup renderer** — not Markdown. Authors naturally write
Markdown, so headings, checkboxes and bullet lists render as garbage without
conversion (issue #95).

This module is a pragmatic, contained bridge: it converts the common Markdown
constructs used in issue descriptions to their wiki-markup equivalents on
upload. It is deliberately **not** a full Markdown parser. The correct
long-term fix is moving the client to REST v3 + ADF, tracked as epic #96.

Mapping summary:

===================  ===================
Markdown             Jira wiki markup
===================  ===================
``# H`` .. ``###### `` ``h1.`` .. ``h6.``
``- x`` / ``+ x``    ``* x`` (bullet)
``1. x``             ``# x`` (ordered)
``- [ ] x``          ``* (x) x`` (open)
``- [x] x``          ``* (/) x`` (done)
``**b**`` / ``__b__`` ``*b*`` (bold)
```` `c` ````        ``{{c}}`` (monospace)
``[t](u)``           ``[t|u]`` (link)
```` ```lang ````    ``{code:lang}`` fence
===================  ===================

Underscore italics (``_i_``) already match Jira's syntax and pass through
unchanged. Single-asterisk Markdown italics are intentionally left alone to
avoid clobbering bullet markers.
"""

import re

_FENCE_RE = re.compile(r"^```(.*)$")
_CHECKBOX_RE = re.compile(r"^(\s*)[-*+] \[([ xX])\] (.*)$")
_HEADING_RE = re.compile(r"^(#{1,6}) (.*)$")
_ORDERED_RE = re.compile(r"^(\s*)\d+\. (.*)$")
_BULLET_RE = re.compile(r"^(\s*)[-*+] (.*)$")

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_STAR_RE = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UNDERSCORE_RE = re.compile(r"__(.+?)__")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text: str) -> str:
    """Apply inline (span-level) Markdown -> wiki conversions."""
    text = _INLINE_CODE_RE.sub(r"{{\1}}", text)
    text = _BOLD_STAR_RE.sub(r"*\1*", text)
    text = _BOLD_UNDERSCORE_RE.sub(r"*\1*", text)
    text = _LINK_RE.sub(r"[\1|\2]", text)
    return text


def _convert_line(line: str) -> str:
    """Convert a single non-fenced line (block prefix + inline content)."""
    checkbox = _CHECKBOX_RE.match(line)
    if checkbox:
        indent, mark, rest = checkbox.groups()
        depth = len(indent) // 2 + 1
        icon = "(/)" if mark in "xX" else "(x)"
        return "*" * depth + f" {icon} " + _inline(rest)

    heading = _HEADING_RE.match(line)
    if heading:
        hashes, rest = heading.groups()
        return f"h{len(hashes)}. " + _inline(rest)

    ordered = _ORDERED_RE.match(line)
    if ordered:
        indent, rest = ordered.groups()
        depth = len(indent) // 2 + 1
        return "#" * depth + " " + _inline(rest)

    bullet = _BULLET_RE.match(line)
    if bullet:
        indent, rest = bullet.groups()
        depth = len(indent) // 2 + 1
        return "*" * depth + " " + _inline(rest)

    return _inline(line)


def markdown_to_wiki(text: str) -> str:
    """Convert a Markdown string to Jira legacy wiki markup.

    Content inside fenced code blocks (```` ``` ````) is emitted verbatim,
    wrapped in a ``{code}`` block. Empty input is returned unchanged.

    Args:
        text: Markdown source (e.g. an issue description).

    Returns:
        The equivalent Jira wiki-markup string.
    """
    if not text:
        return text

    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        fence = _FENCE_RE.match(line)
        if fence:
            if not in_fence:
                lang = fence.group(1).strip()
                out.append(f"{{code:{lang}}}" if lang else "{code}")
                in_fence = True
            else:
                out.append("{code}")
                in_fence = False
            continue

        if in_fence:
            out.append(line)
        else:
            out.append(_convert_line(line))

    return "\n".join(out)
