#!/usr/bin/env python3
"""Pre-commit hook to regenerate AI prompt documentation.

This script checks if CLI command files have been modified and automatically
regenerates the .claude/ai-usage-prompt.md file to keep it in sync.

Exit codes:
    0: Success (prompt regenerated)
    1: Error in script execution
"""

import sys
from pathlib import Path
from subprocess import run  # nosec B404 - Using subprocess for git/budjira commands (trusted)


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

    # Don't regenerate if only the AI prompt itself changed
    non_prompt_changes = [f for f in staged_files if not f.endswith("ai-usage-prompt.md")]
    if not non_prompt_changes:
        return False

    for file_path in non_prompt_changes:
        if any(pattern in file_path for pattern in cli_patterns) and file_path.endswith(".py"):
            return True
    return False


def regenerate_ai_prompt() -> bool:
    """Regenerate the AI usage prompt file.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if .claude directory exists
        claude_dir = Path(".claude")
        if not claude_dir.exists():
            print("⚠️  .claude directory not found, skipping AI prompt regeneration")
            return True

        prompt_file = claude_dir / "ai-usage-prompt.md"

        print("\n" + "=" * 70)
        print("🔄 Regenerating AI usage prompt...")
        print("=" * 70)

        # Run budjira ai usage-prompt --plain
        result = run(  # nosec B603 B607 - Running controlled command (safe)
            ["uv", "run", "budjira", "-q", "ai", "usage-prompt", "--plain"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"❌ Failed to generate AI prompt: {result.stderr}")
            return False

        # Write to file (ensure newline at end)
        content = result.stdout
        if not content.endswith("\n"):
            content += "\n"
        prompt_file.write_text(content)

        # Stage the updated file
        run(  # nosec B603 B607 - Running git command (safe)
            ["git", "add", str(prompt_file)],
            check=True,
        )

        print(f"✅ Regenerated and staged {prompt_file}")
        print()
        print("The AI usage prompt has been automatically updated to reflect")
        print("the latest CLI commands and features.")
        print()
        print("Please review .claude/ai-prompt-supplements.md if you need to add:")
        print("  • Project-specific workflows")
        print("  • Custom examples")
        print("  • Important tips or caveats")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"❌ Error regenerating AI prompt: {e}")
        return False


def main() -> int:
    """Main entry point for the hook.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        staged_files = get_staged_files()

        if not staged_files:
            # No staged files, nothing to check
            return 0

        if check_cli_changes(staged_files) and not regenerate_ai_prompt():
            # Failed to regenerate, but don't block commit
            print("⚠️  AI prompt regeneration failed, but commit will proceed")
            return 0

        # Success
        return 0

    except Exception as e:
        print(f"Error in AI prompt regeneration: {e}", file=sys.stderr)
        # Return 0 even on error to not block commits
        return 0


if __name__ == "__main__":
    sys.exit(main())
