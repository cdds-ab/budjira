#!/usr/bin/env python3
"""Pre-commit hook to remind about documentation updates.

This script analyzes staged files and commit messages to determine
if documentation updates might be needed. It provides helpful reminders
but does not block commits (exits with 0).

Usage:
    Called automatically by pre-commit hook
    Manual: python scripts/check_documentation_updates.py
"""

from __future__ import annotations

import re
import subprocess
import sys


def run_command(cmd: list[str]) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout.strip()
    except Exception as e:
        return 1, str(e)


def get_staged_files() -> list[str]:
    """Get list of staged files."""
    returncode, output = run_command(["git", "diff", "--cached", "--name-only"])
    if returncode == 0 and output:
        return output.splitlines()
    return []


def get_commit_message_type() -> str | None:
    """Extract commit type from commit message if available.

    Returns:
        Commit type (feat/fix/docs/etc.) or None if not available
    """
    # Try to get from COMMIT_EDITMSG if it exists
    from pathlib import Path

    commit_msg_file = Path(".git/COMMIT_EDITMSG")
    try:
        if commit_msg_file.exists():
            with commit_msg_file.open() as f:
                first_line = f.readline().strip()
                match = re.match(r"^(\w+)(?:\([^)]+\))?:", first_line)
                if match:
                    return match.group(1)
    except Exception:
        pass

    return None


def main() -> int:
    """Check for documentation update needs and print reminders."""
    staged_files = get_staged_files()

    if not staged_files:
        # No staged files, nothing to check
        return 0

    reminders: list[str] = []

    # Check: CLI commands changed?
    cli_changed = any("budjira/cli/" in f for f in staged_files)
    if cli_changed:
        reminders.append("⚠️  CLI commands changed")
        reminders.append("   → Update AI usage prompt:")
        reminders.append("     1. Edit budjira/cli/ai.py template")
        reminders.append("     2. Run: uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md")
        reminders.append("     3. Commit with: docs: update AI usage prompt")
        reminders.append("")

    # Check: Models changed?
    models_changed = any("budjira/models/" in f for f in staged_files)
    if models_changed:
        reminders.append("INFO: Models changed")
        reminders.append("   → Consider updating AI usage prompt if user-facing")
        reminders.append("")

    # Check: Tests changed?
    tests_changed = any("tests/" in f for f in staged_files)
    if tests_changed:
        reminders.append("INFO: Tests changed")
        reminders.append("   → Update coverage statistics in .claude/context.md")
        reminders.append("     Run: uv run pytest --cov")
        reminders.append("")

    # Check: Core/backend changed?
    core_changed = any("budjira/core/" in f for f in staged_files)
    if core_changed:
        reminders.append("INFO: Core logic changed")
        reminders.append("   → Consider updating .claude/context.md if significant")
        reminders.append("")

    # Check commit type
    commit_type = get_commit_message_type()

    if commit_type == "feat":
        reminders.append("🎉 New feature detected (feat:)")
        reminders.append("   → Update .claude/context.md:")
        reminders.append("     - Implementierte Features section")
        reminders.append("     - Test statistics")
        reminders.append("     - Roadmap status")
        reminders.append("   → Update README.md if user-facing feature")
        reminders.append("   → Update CLAUDE.md if architectural change")
        reminders.append("")

    elif commit_type == "fix":
        reminders.append("🐛 Bug fix detected (fix:)")
        reminders.append("   → Update .claude/context.md if significant fix")
        reminders.append("")

    # Check: README changed?
    readme_changed = any("README.md" in f for f in staged_files)
    if readme_changed:
        reminders.append("✅ README.md updated")
        reminders.append("")

    # Check: Context updated?
    context_changed = any("context.md" in f for f in staged_files)
    if context_changed:
        reminders.append("✅ context.md updated")
        reminders.append("")

    # Check: AI prompt updated?
    ai_prompt_changed = any("ai-usage-prompt.md" in f for f in staged_files)
    if ai_prompt_changed:
        reminders.append("✅ AI usage prompt updated")
        reminders.append("")

    # Print reminders if any
    if reminders:
        print()
        print("=" * 70)
        print("📋 Documentation Update Reminders")
        print("=" * 70)
        print()
        for reminder in reminders:
            print(reminder)
        print("=" * 70)
        print("INFO: These are reminders only - commit will proceed")
        print("=" * 70)
        print()

    # Always exit 0 (warnings only, don't block commit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
