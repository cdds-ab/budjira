"""Text editor utilities for multi-line input."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - Used for controlled editor execution
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from budjira.utils.errors import BudjiraError

if TYPE_CHECKING:
    from collections.abc import Callable


def open_editor(
    initial_content: str = "",
    file_extension: str = ".md",
    editor: str | None = None,
) -> str:
    """Open text editor for multi-line input.

    Args:
        initial_content: Pre-filled content to show in editor
        file_extension: File extension for syntax highlighting (default: .md)
        editor: Editor command to use (default: $EDITOR or vim)

    Returns:
        Edited content from the editor

    Raises:
        BudjiraError: If editor fails or user cancels
    """
    # Determine editor to use
    if editor is None:
        editor = os.environ.get("EDITOR", "vim")

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=file_extension,
        delete=False,
        encoding="utf-8",
    ) as tf:
        tf.write(initial_content)
        temp_path = Path(tf.name)

    try:
        # Open editor
        result = subprocess.run(  # nosec B603 - Using user-configured editor (expected)
            [editor, str(temp_path)],
            check=False,
        )

        if result.returncode != 0:
            raise BudjiraError(f"Editor exited with code {result.returncode}")

        # Read edited content
        content = temp_path.read_text(encoding="utf-8")

        # Check if content was changed (user might have canceled)
        if content.strip() == initial_content.strip():
            # Content unchanged - this is OK, maybe user just reviewed it
            pass

        return content

    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


def open_editor_with_validation(
    initial_content: str,
    validator: Callable[[str], tuple[bool, str]],
    max_attempts: int = 3,
    editor: str | None = None,
) -> str:
    """Open editor with validation loop.

    Allows user to re-edit if validation fails.

    Args:
        initial_content: Pre-filled content
        validator: Validation function that returns (valid, error_message)
        max_attempts: Maximum number of edit attempts
        editor: Editor command to use

    Returns:
        Validated content from editor

    Raises:
        BudjiraError: If validation fails after max attempts
    """
    content = initial_content

    for attempt in range(max_attempts):
        content = open_editor(content, editor=editor)

        # Validate
        valid, error_message = validator(content)

        if valid:
            return content

        # Show error and ask to retry
        print(f"\n{error_message}\n")

        if attempt < max_attempts - 1:
            response = input("Edit again? [Y/n]: ").strip().lower()
            if response in ("n", "no"):
                raise BudjiraError("Validation failed, user canceled")
        else:
            raise BudjiraError(f"Validation failed after {max_attempts} attempts")

    # Should not reach here
    raise BudjiraError("Validation loop ended unexpectedly")
