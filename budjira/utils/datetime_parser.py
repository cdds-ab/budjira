"""Datetime parsing utilities for work log entries and time tracking."""

from __future__ import annotations

from datetime import datetime, timedelta

from budjira.utils.errors import ValidationError


def parse_datetime_string(datetime_str: str) -> datetime:
    """Parse a datetime string and return a datetime object.

    Supported formats:
    - ISO format: "2025-10-25T14:30:00" or "2025-10-25 14:30:00"
    - Date only: "2025-10-25" (time defaults to 00:00)
    - Relative: "today", "yesterday"

    Args:
        datetime_str: Datetime string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValidationError: If datetime string format is invalid or in the future

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
    assert result is not None
    if result > datetime.now():
        raise ValidationError(f"Datetime cannot be in the future: {result.strftime('%Y-%m-%d %H:%M')}")

    return result
