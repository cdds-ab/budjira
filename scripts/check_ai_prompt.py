#!/usr/bin/env python3
"""Pre-commit hook: warn when the AI usage prompt is out of date.

This hook NEVER writes or stages files. Regenerating ``.claude/ai-usage-prompt.md``
from inside a hook is unsafe: pre-commit stashes unstaged changes for the
duration of a commit, and a hook that rewrites a file which also has stashed
unstaged changes makes pre-commit's stash *restore* fail -- it cannot re-apply
its patch and silently strands the developer's work in a backup patch under
``~/.cache/pre-commit/``. That is exactly the "wild stasher" data-loss this
project hit.

So this hook only DETECTS staleness and prints an actionable reminder.
Regeneration stays an explicit, manual step:

    uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md

Exit code: always 0 (non-blocking reminder -- never aborts the commit).
"""

import sys
from pathlib import Path
from subprocess import run  # nosec B404 - subprocess for git/budjira commands (trusted)

PROMPT_FILE = Path(".claude/ai-usage-prompt.md")
REGEN_COMMAND = "uv run budjira -q ai usage-prompt --plain > .claude/ai-usage-prompt.md"


def get_staged_files() -> list[str]:
    """Return the list of staged file paths."""
    result = run(  # nosec B603 B607 - fixed git args (safe)
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().split("\n") if result.stdout else []


def check_cli_changes(staged_files: list[str]) -> bool:
    """Return True if a staged change can affect the generated AI prompt."""
    cli_patterns = ("budjira/cli/", "budjira/models/")

    # Ignore a change that only touches the prompt itself.
    non_prompt_changes = [f for f in staged_files if not f.endswith("ai-usage-prompt.md")]
    return any(f.endswith(".py") and any(p in f for p in cli_patterns) for f in non_prompt_changes)


def generate_expected_prompt() -> str | None:
    """Generate the current prompt in memory. Returns None if generation fails."""
    result = run(  # nosec B603 B607 - controlled command (safe)
        ["uv", "run", "budjira", "-q", "ai", "usage-prompt", "--plain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    content = result.stdout
    return content if content.endswith("\n") else content + "\n"


def print_reminder() -> None:
    """Print an actionable reminder that the prompt may be stale."""
    print("\n" + "=" * 70)
    print("[i] AI usage prompt may be out of date")
    print("=" * 70)
    print("CLI/model files changed but .claude/ai-usage-prompt.md differs from")
    print("the generated output. Regenerate and stage it in a separate commit:")
    print()
    print(f"    {REGEN_COMMAND}")
    print()
    print("This hook intentionally does NOT write the file itself (doing so from")
    print("a hook corrupts pre-commit's stash on partial commits).")
    print("=" * 70 + "\n")


def main() -> int:
    """Detect staleness and remind; never modify files, never block the commit."""
    try:
        staged_files = get_staged_files()
        if not staged_files or not check_cli_changes(staged_files):
            return 0

        if not PROMPT_FILE.exists():
            return 0

        expected = generate_expected_prompt()
        if expected is None:
            # Generation failed -- stay silent rather than nag with a false positive.
            return 0

        if PROMPT_FILE.read_text() != expected:
            print_reminder()

        return 0
    except Exception as e:
        # A reminder hook must never break a commit.
        print(f"AI prompt freshness check skipped: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
