"""Datetime parsing utilities for work log entries and time tracking."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta

from budjira.utils.errors import ValidationError


def parse_datetime_string(datetime_str: str, allow_future: bool = False) -> datetime:
    """Parse a datetime string and return a datetime object.

    Supported formats:
    - ISO format: "2025-10-25T14:30:00" or "2025-10-25 14:30:00"
    - Date only: "2025-10-25" (time defaults to 00:00)
    - Relative: "today", "yesterday", "tomorrow"

    Args:
        datetime_str: Datetime string to parse
        allow_future: If True, accept dates in the future (e.g., sprint dates).
            Defaults to False so worklog timestamps stay in the past.

    Returns:
        Parsed datetime object

    Raises:
        ValidationError: If datetime string format is invalid, or in the future
            while ``allow_future`` is False

    Examples:
        >>> dt = parse_datetime_string("2025-10-25 14:30")
        >>> dt.hour
        14
        >>> dt = parse_datetime_string("2025-10-25")
        >>> dt.hour
        0
    """
    if not datetime_str or not datetime_str.strip():
        raise ValidationError("Datetime string cannot be empty")

    datetime_str = datetime_str.strip()

    # Handle relative dates
    result: datetime | None = None
    if datetime_str.lower() == "today":
        result = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif datetime_str.lower() == "yesterday":
        result = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif datetime_str.lower() == "tomorrow":
        result = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Try parsing ISO format variants
        formats = [
            "%Y-%m-%dT%H:%M:%S",  # ISO format with T
            "%Y-%m-%d %H:%M:%S",  # Space-separated with seconds
            "%Y-%m-%d %H:%M",  # Space-separated without seconds
            "%Y-%m-%d",  # Date only
        ]

        for fmt in formats:
            try:
                result = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue

        if result is None:
            raise ValidationError(
                f"Invalid datetime format: '{datetime_str}'. "
                f"Supported formats: YYYY-MM-DD HH:MM, YYYY-MM-DD, today, yesterday"
            )

    # Validate: not in the future
    # At this point, result is guaranteed to be a datetime (not None)
    assert result is not None  # nosec B101
    if not allow_future and result > datetime.now():
        raise ValidationError(f"Datetime cannot be in the future: {result.strftime('%Y-%m-%d %H:%M')}")

    return result


def parse_jira_timestamp(timestamp: str | None) -> datetime | None:
    """Parse a Jira REST API timestamp (e.g., "2026-08-20T10:00:00.000+0000").

    Jira returns timezone offsets without a colon ("+0000"), which Python's
    ``datetime.fromisoformat`` only accepts since 3.11. This normalizes the
    offset ("Z", "+0000" → "+00:00") before parsing.

    Args:
        timestamp: Jira timestamp string, or None

    Returns:
        Parsed datetime, or None if the input is None or unparseable

    Examples:
        >>> dt = parse_jira_timestamp("2026-08-20T10:00:00.000+0000")
        >>> dt.hour
        10
        >>> parse_jira_timestamp(None) is None
        True
    """
    if not timestamp:
        return None

    normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", timestamp.replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_month_range(month_str: str) -> tuple[date, date]:
    """Parse a YYYY-MM string into the first and last day of that month.

    Args:
        month_str: Month string (e.g., "2026-08")

    Returns:
        Tuple of (first day, last day) of the month

    Raises:
        ValidationError: If the format is invalid

    Examples:
        >>> parse_month_range("2026-02")
        (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28))
    """
    value = month_str.strip()
    try:
        first = date.fromisoformat(f"{value}-01")
    except ValueError:
        raise ValidationError(f"Invalid month format: '{month_str}'. Expected YYYY-MM (e.g., 2026-08).") from None
    last_day = calendar.monthrange(first.year, first.month)[1]
    return first, first.replace(day=last_day)
