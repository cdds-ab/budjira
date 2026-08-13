"""Tests for the AI prompt freshness hook."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_ai_prompt.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_ai_prompt", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBaseline:
    """The hook must compare against the built-in template, not a local overlay (#105)."""

    def test_baseline_is_generated_from_the_defaults(self) -> None:
        """Without --defaults the baseline inherits the developer's stale template."""
        module = _load_script()

        assert "--defaults" in module.GENERATE_COMMAND

    def test_reminder_names_the_same_command_it_checks(self) -> None:
        """A reminder that regenerates differently than the check is how drift survives."""
        module = _load_script()

        for argument in module.GENERATE_COMMAND[2:]:
            assert argument in module.REGEN_COMMAND
