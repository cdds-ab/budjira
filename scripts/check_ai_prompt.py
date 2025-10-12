#!/usr/bin/env python3
"""Pre-commit hook to check if AI prompt documentation needs updating.

This script checks if CLI command files have been modified and reminds the
developer to review the AI prompt supplements file.

Exit codes:
    0: Success (warning only, doesn't block commit)
    1: Error in script execution
"""

import sys
from subprocess import run  # nosec B404 - Using subprocess for git commands (trusted)


def get_staged_files() -> list[str]:
    """Get list of staged files from git.

    Returns:
        List of staged file paths
    """
    result = run(  # nosec B603 B607 - Running git command with fixed args (safe)
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().split("\n") if result.stdout else []


def check_cli_changes(staged_files: list[str]) -> bool:
    """Check if any CLI command files were modified.

    Args:
        staged_files: List of staged file paths

    Returns:
        True if CLI files were modified, False otherwise
    """
    cli_patterns = [
        "budjira/cli/",
        "budjira/models/",
    ]

    for file_path in staged_files:
        if any(pattern in file_path for pattern in cli_patterns) and file_path.endswith(".py"):
            return True
    return False


def print_warning() -> None:
    """Print warning message about AI prompt updates."""
    print("\n" + "=" * 70)
    print("⚠️  CLI Command Changes Detected")
    print("=" * 70)
    print()
    print("Modified CLI files detected. Please consider updating:")
    print()
    print("  📝 .claude/ai-prompt-supplements.md")
    print()
    print("Check if the following need updates:")
    print("  • Common workflows still work")
    print("  • Examples reflect current syntax")
    print("  • Tips address new features")
    print("  • Edge cases cover new functionality")
    print()
    print("Preview the current AI guide:")
    print("  $ budjira ai usage-prompt | less")
    print()
    print("=" * 70)
    print()


def main() -> int:
    """Main entry point for the hook.

    Returns:
        Exit code (0 = success/warning, 1 = error)
    """
    try:
        staged_files = get_staged_files()

        if not staged_files:
            # No staged files, nothing to check
            return 0

        if check_cli_changes(staged_files):
            print_warning()
            # Return 0 to allow commit (warning only, not blocking)
            return 0

        # No CLI changes detected
        return 0

    except Exception as e:
        print(f"Error in AI prompt freshness check: {e}", file=sys.stderr)
        # Return 0 even on error to not block commits
        return 0


if __name__ == "__main__":
    sys.exit(main())
