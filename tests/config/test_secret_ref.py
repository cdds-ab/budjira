"""Tests for secret reference parsing and resolution."""

# mypy: disable-error-code="arg-type"

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from budjira.config.secret_ref import (
    PASS_TIMEOUT_SECONDS,
    parse_secret_ref,
    resolve_secret_ref,
)
from budjira.utils.errors import SecretRefError


class TestParseSecretRef:
    """Test parse_secret_ref."""

    def test_valid_schemes(self) -> None:
        """Each supported scheme parses into scheme and target."""
        assert parse_secret_ref("env:MY_TOKEN") == ("env", "MY_TOKEN")
        assert parse_secret_ref("pass:acme/jira-token") == ("pass", "acme/jira-token")
        assert parse_secret_ref("file:/run/secrets/token") == ("file", "/run/secrets/token")

    def test_file_target_keeps_colons(self) -> None:
        """Only the first colon separates scheme from target."""
        assert parse_secret_ref("file:C:\\secrets\\token.txt") == ("file", "C:\\secrets\\token.txt")

    def test_missing_scheme_raises(self) -> None:
        """A reference without scheme separator is rejected."""
        with pytest.raises(SecretRefError, match="missing scheme"):
            parse_secret_ref("just-a-token")

    def test_unknown_scheme_raises(self) -> None:
        """Unknown schemes are rejected with the supported list."""
        with pytest.raises(SecretRefError, match="unknown scheme 'op'"):
            parse_secret_ref("op://vault/item")

    def test_empty_target_raises(self) -> None:
        """A scheme without a target is rejected."""
        with pytest.raises(SecretRefError, match="empty target"):
            parse_secret_ref("env:")


class TestResolveEnv:
    """Test env: scheme resolution."""

    def test_resolves_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The variable's value is returned."""
        monkeypatch.setenv("MY_TOKEN", "secret-value")
        assert resolve_secret_ref("env:MY_TOKEN") == "secret-value"

    def test_trims_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Surrounding whitespace is trimmed."""
        monkeypatch.setenv("MY_TOKEN", "  secret-value\n")
        assert resolve_secret_ref("env:MY_TOKEN") == "secret-value"

    def test_unset_variable_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unset variable names the reference, not the value."""
        monkeypatch.delenv("MY_TOKEN", raising=False)
        with pytest.raises(SecretRefError, match="'MY_TOKEN' is not set"):
            resolve_secret_ref("env:MY_TOKEN")

    def test_empty_variable_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An empty variable is an error, not an empty token."""
        monkeypatch.setenv("MY_TOKEN", "   ")
        with pytest.raises(SecretRefError, match="'MY_TOKEN' is empty"):
            resolve_secret_ref("env:MY_TOKEN")


class TestResolveFile:
    """Test file: scheme resolution."""

    def test_resolves_first_line(self, tmp_path: Path) -> None:
        """Only the first line is used, trailing newline removed."""
        secret_file = tmp_path / "token"
        secret_file.write_text("secret-value\nextra-line\n")
        assert resolve_secret_ref(f"file:{secret_file}") == "secret-value"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """A missing file is a clear error."""
        with pytest.raises(SecretRefError, match="does not exist"):
            resolve_secret_ref(f"file:{tmp_path}/nope")

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        """An empty file is a clear error."""
        secret_file = tmp_path / "token"
        secret_file.write_text("")
        with pytest.raises(SecretRefError, match="is empty"):
            resolve_secret_ref(f"file:{secret_file}")

    def test_expands_user(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """A leading ~ is expanded."""
        monkeypatch.setenv("HOME", str(tmp_path))
        secret_file = tmp_path / "token"
        secret_file.write_text("secret-value\n")
        assert resolve_secret_ref("file:~/token") == "secret-value"


class TestResolvePass:
    """Test pass: scheme resolution."""

    def test_resolves_first_line(self) -> None:
        """pass output is trimmed to the first line (URL/username lines dropped)."""
        result = MagicMock(returncode=0, stdout="secret-value\nuser@example.com\nhttps://acme.atlassian.net\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result):
            assert resolve_secret_ref("pass:acme/jira-token") == "secret-value"

    def test_calls_pass_show(self) -> None:
        """The entry is passed to 'pass show' with capture and timeout."""
        result = MagicMock(returncode=0, stdout="secret-value\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result) as mock_run:
            resolve_secret_ref("pass:acme/jira-token")
        mock_run.assert_called_once_with(
            ["pass", "show", "acme/jira-token"],
            capture_output=True,
            text=True,
            timeout=PASS_TIMEOUT_SECONDS,
        )

    def test_missing_pass_binary_raises(self) -> None:
        """A missing pass executable is a clear error."""
        with patch("budjira.config.secret_ref.shutil.which", return_value=None):
            with pytest.raises(SecretRefError, match="'pass' executable not found"):
                resolve_secret_ref("pass:acme/jira-token")

    def test_nonzero_exit_raises_with_stderr(self) -> None:
        """A failing pass names the reference and pass's own error line."""
        result = MagicMock(returncode=1, stderr="Error: acme/jira-token is not in the password store.\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result):
            with pytest.raises(SecretRefError, match="pass failed - Error: acme/jira-token is not"):
                resolve_secret_ref("pass:acme/jira-token")

    def test_empty_entry_raises(self) -> None:
        """An empty pass entry is an error, not an empty token."""
        result = MagicMock(returncode=0, stdout="\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result):
            with pytest.raises(SecretRefError, match="pass entry 'acme/jira-token' is empty"):
                resolve_secret_ref("pass:acme/jira-token")

    def test_timeout_raises(self) -> None:
        """A hung pass (e.g. gpg-agent prompt) times out with guidance."""
        with patch(
            "budjira.config.secret_ref.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pass", timeout=PASS_TIMEOUT_SECONDS),
        ):
            with pytest.raises(SecretRefError, match="timed out"):
                resolve_secret_ref("pass:acme/jira-token")

    def test_directory_listing_raises(self) -> None:
        """'pass show <dir>' exits 0 with a tree listing - that is not a secret."""
        result = MagicMock(returncode=0, stdout="acme\n├── jira-token\n└── tempo-token\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result):
            with pytest.raises(SecretRefError, match="is a pass directory"):
                resolve_secret_ref("pass:acme")

    def test_multiline_entry_without_tree_is_fine(self) -> None:
        """A real multi-line entry (secret + URL lines) still resolves to line one."""
        result = MagicMock(returncode=0, stdout="secret-value\nhttps://acme.atlassian.net\nuser: fred\n")
        with patch("budjira.config.secret_ref.subprocess.run", return_value=result):
            assert resolve_secret_ref("pass:acme/jira-token") == "secret-value"
