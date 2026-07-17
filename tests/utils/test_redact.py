"""Tests for credential redaction in log output."""

import logging

import pytest
from budjira.utils.redact import REDACTED, install_redaction, redact


class TestRedact:
    """Unit tests for the redact() text scrubber."""

    def test_bearer_scheme_is_masked(self) -> None:
        assert redact("Authorization: Bearer abcdef123456") == f"Authorization: {REDACTED}"

    def test_bearer_value_is_masked_without_header_context(self) -> None:
        assert redact("sending Bearer abcdef123456 now") == f"sending Bearer {REDACTED} now"

    def test_github_token_scheme_is_masked(self) -> None:
        assert redact("token ghp_abcdefghijklmnopqrstuvwxyz123456") == f"token {REDACTED}"

    def test_github_pat_is_masked_anywhere(self) -> None:
        assert redact("using ghp_abcdefghijklmnopqrstuvwxyz123456 for auth") == f"using {REDACTED} for auth"

    def test_github_fine_grained_pat_is_masked(self) -> None:
        token = "github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz"
        assert redact(f"header {token}") == f"header {REDACTED}"

    def test_atlassian_api_token_is_masked(self) -> None:
        assert redact("ATATT3xFfGF0abcdefghijklmnop=AB12") == REDACTED

    def test_authorization_dict_repr_is_masked(self) -> None:
        text = "{'Authorization': 'Bearer abcdef123456', 'Content-Type': 'application/json'}"
        assert "abcdef123456" not in redact(text)
        assert "Content-Type" in redact(text)

    def test_plain_text_is_untouched(self) -> None:
        text = "the token count is high and the bearer of news arrived"
        assert redact(text) == text

    def test_redact_is_idempotent(self) -> None:
        once = redact("Bearer abcdef123456")
        assert redact(once) == once


class TestInstallRedaction:
    """Integration tests: redaction applies to emitted log records."""

    @pytest.fixture(autouse=True)
    def _install(self) -> None:
        install_redaction()

    def test_fstring_message_is_redacted(self, caplog: pytest.LogCaptureFixture) -> None:
        logger = logging.getLogger("test.redact.fstring")
        with caplog.at_level(logging.INFO):
            logger.info(f"auth header: Bearer {'abcdef123456'}")
        assert "abcdef123456" not in caplog.text
        assert REDACTED in caplog.text

    def test_percent_style_args_are_redacted(self, caplog: pytest.LogCaptureFixture) -> None:
        logger = logging.getLogger("test.redact.args")
        with caplog.at_level(logging.INFO):
            logger.info("auth header: %s", "Bearer abcdef123456")
        assert "abcdef123456" not in caplog.text
        assert REDACTED in caplog.text

    def test_clean_records_keep_their_args(self, caplog: pytest.LogCaptureFixture) -> None:
        logger = logging.getLogger("test.redact.clean")
        with caplog.at_level(logging.INFO):
            logger.info("fetched %d issues", 42)
        assert "fetched 42 issues" in caplog.text

    def test_install_is_idempotent(self, caplog: pytest.LogCaptureFixture) -> None:
        install_redaction()
        install_redaction()
        logger = logging.getLogger("test.redact.idempotent")
        with caplog.at_level(logging.INFO):
            logger.info("token ghp_abcdefghijklmnopqrstuvwxyz123456")
        assert caplog.text.count(REDACTED) == 1
