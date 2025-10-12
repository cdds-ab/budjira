"""Tests for time parsing utilities."""

import pytest
from budjira.utils.errors import ValidationError
from budjira.utils.time_parser import format_minutes, parse_time_string


class TestParseTimeString:
    """Test time string parsing."""

    def test_parse_hours_only(self) -> None:
        """Test parsing hours only."""
        assert parse_time_string("1h") == 60
        assert parse_time_string("2h") == 120
        assert parse_time_string("5h") == 300

    def test_parse_minutes_only(self) -> None:
        """Test parsing minutes only."""
        assert parse_time_string("30m") == 30
        assert parse_time_string("45m") == 45
        assert parse_time_string("90m") == 90

    def test_parse_hours_and_minutes(self) -> None:
        """Test parsing hours and minutes combined."""
        assert parse_time_string("1h30m") == 90
        assert parse_time_string("2h15m") == 135
        assert parse_time_string("0h45m") == 45

    def test_parse_decimal_hours(self) -> None:
        """Test parsing decimal hours."""
        assert parse_time_string("1.5h") == 90
        assert parse_time_string("2.5h") == 150
        assert parse_time_string("0.5h") == 30

    def test_parse_with_spaces(self) -> None:
        """Test parsing with spaces."""
        assert parse_time_string("1h 30m") == 90
        assert parse_time_string("2h 15m") == 135
        assert parse_time_string("  1h  ") == 60

    def test_parse_case_insensitive(self) -> None:
        """Test case insensitive parsing."""
        assert parse_time_string("1H") == 60
        assert parse_time_string("30M") == 30
        assert parse_time_string("1H30M") == 90

    def test_parse_empty_string(self) -> None:
        """Test empty string raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            parse_time_string("")

        with pytest.raises(ValidationError, match="cannot be empty"):
            parse_time_string("   ")

    def test_parse_invalid_format(self) -> None:
        """Test invalid format raises error."""
        with pytest.raises(ValidationError, match="Invalid time format"):
            parse_time_string("abc")

        with pytest.raises(ValidationError, match="Invalid time format"):
            parse_time_string("123")

        with pytest.raises(ValidationError, match="Invalid time format"):
            parse_time_string("hello")

    def test_parse_too_large(self) -> None:
        """Test time duration exceeding 24 hours."""
        with pytest.raises(ValidationError, match="Time duration too large"):
            parse_time_string("25h")

        with pytest.raises(ValidationError, match="Time duration too large"):
            parse_time_string("1500m")


class TestFormatMinutes:
    """Test minute formatting."""

    def test_format_hours_and_minutes(self) -> None:
        """Test formatting with hours and minutes."""
        assert format_minutes(90) == "1h 30m"
        assert format_minutes(135) == "2h 15m"
        assert format_minutes(185) == "3h 5m"

    def test_format_hours_only(self) -> None:
        """Test formatting exact hours."""
        assert format_minutes(60) == "1h"
        assert format_minutes(120) == "2h"
        assert format_minutes(180) == "3h"

    def test_format_minutes_only(self) -> None:
        """Test formatting less than an hour."""
        assert format_minutes(30) == "30m"
        assert format_minutes(45) == "45m"
        assert format_minutes(15) == "15m"

    def test_format_zero(self) -> None:
        """Test formatting zero minutes."""
        assert format_minutes(0) == "0m"

    def test_format_negative(self) -> None:
        """Test negative minutes raise error."""
        with pytest.raises(ValidationError, match="cannot be negative"):
            format_minutes(-1)

        with pytest.raises(ValidationError, match="cannot be negative"):
            format_minutes(-60)
