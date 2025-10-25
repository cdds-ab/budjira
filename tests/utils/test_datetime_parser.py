"""Tests for datetime parsing utilities."""

from datetime import datetime, timedelta

import pytest
from budjira.utils.datetime_parser import parse_datetime_string
from budjira.utils.errors import ValidationError


class TestParseDatetimeString:
    """Tests for parse_datetime_string function."""

    def test_parse_iso_format_with_t(self) -> None:
        """Test parsing ISO format with T separator."""
        result = parse_datetime_string("2024-10-25T14:30:00")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_space_separated_with_seconds(self) -> None:
        """Test parsing space-separated format with seconds."""
        result = parse_datetime_string("2024-10-25 14:30:45")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_parse_space_separated_without_seconds(self) -> None:
        """Test parsing space-separated format without seconds."""
        result = parse_datetime_string("2024-10-25 14:30")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_date_only(self) -> None:
        """Test parsing date only (time defaults to 00:00)."""
        result = parse_datetime_string("2024-10-25")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 25
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_relative_today(self) -> None:
        """Test parsing 'today' relative date."""
        result = parse_datetime_string("today")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.year == today.year
        assert result.month == today.month
        assert result.day == today.day
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_relative_yesterday(self) -> None:
        """Test parsing 'yesterday' relative date."""
        result = parse_datetime_string("yesterday")
        yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.year == yesterday.year
        assert result.month == yesterday.month
        assert result.day == yesterday.day
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_case_insensitive_today(self) -> None:
        """Test that 'today' is case-insensitive."""
        result = parse_datetime_string("TODAY")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == today.date()

    def test_parse_case_insensitive_yesterday(self) -> None:
        """Test that 'yesterday' is case-insensitive."""
        result = parse_datetime_string("YESTERDAY")
        yesterday = (datetime.now() - timedelta(days=1)).date()
        assert result.date() == yesterday

    def test_parse_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = parse_datetime_string("  2024-10-25 14:30  ")
        assert result.year == 2024
        assert result.hour == 14

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            parse_datetime_string("")

    def test_whitespace_only_raises_error(self) -> None:
        """Test that whitespace-only string raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            parse_datetime_string("   ")

    def test_invalid_format_raises_error(self) -> None:
        """Test that invalid format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid datetime format"):
            parse_datetime_string("invalid-date")

    def test_invalid_format_with_suggestion(self) -> None:
        """Test that error message includes format suggestions."""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            parse_datetime_string("25/10/2025")

    def test_future_date_raises_error(self) -> None:
        """Test that future datetime raises ValidationError."""
        future = datetime.now() + timedelta(days=1)
        future_str = future.strftime("%Y-%m-%d %H:%M")
        with pytest.raises(ValidationError, match="cannot be in the future"):
            parse_datetime_string(future_str)

    def test_future_date_only_raises_error(self) -> None:
        """Test that future date (without time) raises ValidationError."""
        future = datetime.now() + timedelta(days=10)
        future_str = future.strftime("%Y-%m-%d")
        with pytest.raises(ValidationError, match="cannot be in the future"):
            parse_datetime_string(future_str)

    def test_now_is_valid(self) -> None:
        """Test that current time is valid (not considered future)."""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        # Should not raise - parsing should succeed
        # (may be very slightly in past by time it parses, which is OK)
        result = parse_datetime_string(now_str)
        assert result <= datetime.now()

    def test_one_second_ago_is_valid(self) -> None:
        """Test that one second ago is valid."""
        past = datetime.now() - timedelta(seconds=1)
        past_str = past.strftime("%Y-%m-%d %H:%M:%S")
        result = parse_datetime_string(past_str)
        assert result <= datetime.now()
