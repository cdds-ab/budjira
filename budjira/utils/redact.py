"""Credential redaction for log output.

budjira never logs credentials on purpose, but a future debug statement or an
exception path that echoes request/session state must not leak live tokens
into terminal output. This module makes that property structural instead of
accidental: once installed, every ``logging.LogRecord`` is scrubbed at
creation time, so the guarantee holds for all loggers and all handlers —
including handlers added later that know nothing about redaction.

Install happens once at CLI startup via :func:`install_redaction`.
"""

import logging
import re
import threading

REDACTED = "***REDACTED***"

# Token-ish value: long enough to be a credential, no whitespace.
_VALUE = r"[A-Za-z0-9\-._~+/=]{8,}"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # HTTP auth schemes: "Bearer <token>" / "token <token>" (GitHub style)
    (re.compile(rf"(?i)\b(bearer|token)\s+{_VALUE}"), rf"\1 {REDACTED}"),
    # Header/dict style: Authorization: <anything up to quote/brace/newline>
    (
        re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?)[^\"'\r\n}]+"),
        rf"\1{REDACTED}",
    ),
    # GitHub personal access tokens (classic and fine-grained)
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), REDACTED),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), REDACTED),
    # Atlassian Cloud API tokens
    (re.compile(rf"\bATATT{_VALUE}\b"), REDACTED),
]

_install_lock = threading.Lock()
_installed = False


def redact(text: str) -> str:
    """Return ``text`` with credential-looking values masked."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def install_redaction() -> None:
    """Install credential redaction into the logging record factory.

    Idempotent and thread-safe. The factory sees every record before any
    handler does, so the redaction applies regardless of logging
    configuration.
    """
    global _installed
    with _install_lock:
        if _installed:
            return

        previous_factory = logging.getLogRecordFactory()

        def redacting_factory(*args: object, **kwargs: object) -> logging.LogRecord:
            record = previous_factory(*args, **kwargs)
            message = record.getMessage()
            redacted = redact(message)
            if redacted != message:
                record.msg = redacted
                record.args = ()
            return record

        logging.setLogRecordFactory(redacting_factory)
        _installed = True
