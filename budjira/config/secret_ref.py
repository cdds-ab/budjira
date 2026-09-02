"""Secret references: resolve tokens from env vars, pass, or files.

A secret reference is a typed string ``<scheme>:<target>`` stored on the
connection (e.g. ``api_token_ref = "pass:acme/jira-token"``). Supported
schemes:

- ``env:NAME``    - environment variable
- ``pass:entry``  - ``pass show entry``, first line
- ``file:/path``  - file contents, first line

The resolved value is always trimmed to its first line: pass entries often
carry URL, username or recovery lines below the secret, and files end in a
trailing newline - both would leak into the token and fail far from the
cause.

Errors name the reference, never the resolved value.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - fixed 'pass' CLI invocation with controlled args (trusted)
from pathlib import Path

from budjira.utils.errors import SecretRefError

SUPPORTED_SCHEMES = ("env", "pass", "file")

#: Timeout for the pass subprocess - a hung gpg-agent prompt must not block
#: the CLI forever.
PASS_TIMEOUT_SECONDS = 30


def parse_secret_ref(ref: str) -> tuple[str, str]:
    """Split a secret reference into scheme and target.

    Args:
        ref: Secret reference string (e.g. ``pass:acme/jira-token``)

    Returns:
        Tuple of (scheme, target)

    Raises:
        SecretRefError: If the scheme is missing, unknown, or the target empty
    """
    scheme, sep, target = ref.partition(":")
    if not sep:
        raise SecretRefError(
            f"Invalid secret reference '{ref}': missing scheme. "
            f"Expected one of: {', '.join(s + ':' for s in SUPPORTED_SCHEMES)}"
        )
    if scheme not in SUPPORTED_SCHEMES:
        raise SecretRefError(
            f"Invalid secret reference '{ref}': unknown scheme '{scheme}'. "
            f"Supported: {', '.join(s + ':' for s in SUPPORTED_SCHEMES)}"
        )
    if not target.strip():
        raise SecretRefError(f"Invalid secret reference '{ref}': empty target for scheme '{scheme}'")
    return scheme, target


def _first_line(text: str) -> str:
    """Normalize a resolved secret: first line only, trimmed."""
    return text.splitlines()[0].strip() if text.splitlines() else ""


def _resolve_env(ref: str, name: str) -> str:
    """Resolve an env:NAME reference."""
    value = os.environ.get(name)
    if value is None:
        raise SecretRefError(f"Secret reference '{ref}': environment variable '{name}' is not set")
    token = _first_line(value)
    if not token:
        raise SecretRefError(f"Secret reference '{ref}': environment variable '{name}' is empty")
    return token


def _resolve_file(ref: str, path_str: str) -> str:
    """Resolve a file:/path reference."""
    path = Path(path_str).expanduser()
    if not path.exists():
        raise SecretRefError(f"Secret reference '{ref}': file '{path}' does not exist")
    try:
        token = _first_line(path.read_text())
    except OSError as e:
        raise SecretRefError(f"Secret reference '{ref}': cannot read file '{path}': {e.strerror or e}") from e
    if not token:
        raise SecretRefError(f"Secret reference '{ref}': file '{path}' is empty")
    return token


def _resolve_pass(ref: str, entry: str) -> str:
    """Resolve a pass:entry reference via the pass CLI."""
    if shutil.which("pass") is None:
        raise SecretRefError(
            f"Secret reference '{ref}': 'pass' executable not found. "
            "Install pass (the standard Unix password manager) or use a different scheme."
        )
    try:
        result = subprocess.run(  # nosec B603 B607 - fixed 'pass show' args, entry from config
            ["pass", "show", entry],
            capture_output=True,
            text=True,
            timeout=PASS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        raise SecretRefError(
            f"Secret reference '{ref}': 'pass show' timed out after {PASS_TIMEOUT_SECONDS}s (is the GPG key unlocked?)"
        ) from e
    if result.returncode != 0:
        # stderr from pass/gpg describes the failure (e.g. entry not found, no
        # secret key) and never contains the secret itself.
        detail = result.stderr.strip().splitlines()[0] if result.stderr.strip() else "unknown error"
        raise SecretRefError(f"Secret reference '{ref}': pass failed - {detail[:200]}")
    lines = result.stdout.splitlines()
    if len(lines) > 1 and any(line.startswith(("├", "└", "│")) for line in lines[1:]):
        # 'pass show <dir>' exits 0 and prints a tree listing - the first line
        # is the directory name, not a secret.
        raise SecretRefError(f"Secret reference '{ref}': '{entry}' is a pass directory, not an entry")
    token = _first_line(result.stdout)
    if not token:
        raise SecretRefError(f"Secret reference '{ref}': pass entry '{entry}' is empty")
    return token


def resolve_secret_ref(ref: str) -> str:
    """Resolve a secret reference to its value.

    Args:
        ref: Secret reference string (``env:NAME``, ``pass:entry``, ``file:/path``)

    Returns:
        Resolved secret (first line, trimmed)

    Raises:
        SecretRefError: If the reference is invalid or cannot be resolved
    """
    scheme, target = parse_secret_ref(ref)
    if scheme == "env":
        return _resolve_env(ref, target)
    if scheme == "pass":
        return _resolve_pass(ref, target)
    return _resolve_file(ref, target)
