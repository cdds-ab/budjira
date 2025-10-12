"""Time parsing utilities for work log entries."""

from __future__ import annotations

import re

from budjira.utils.errors import ValidationError


def parse_time_string(time_str: str) -> int:
    """Parse a time string and return minutes.

    Supported formats:
    - 1h, 2h30m, 30m, 1.5h, 90m
    - Combinations like "2h 30m" (with or without space)

    Args:
        time_str: Time string to parse

    Returns:
        Total time in minutes

    Raises:
        ValidationError: If time string format is invalid

    Examples:
        >>> parse_time_string("1h")
        60
        >>> parse_time_string("30m")
        30
        >>> parse_time_string("2h30m")
        150
        >>> parse_time_string("1.5h")
        90
    """
    if not time_str or not time_str.strip():
        raise ValidationError("Time string cannot be empty")

    time_str = time_str.strip().lower().replace(" ", "")
    total_minutes = 0

    # Match hours (1h, 1.5h, etc.)
    hours_match = re.search(r"(\d+\.?\d*)h", time_str)
    if hours_match:
        hours = float(hours_match.group(1))
        total_minutes += int(hours * 60)

    # Match minutes (30m, etc.)
    minutes_match = re.search(r"(\d+)m", time_str)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        total_minutes += minutes

    if total_minutes == 0:
        raise ValidationError(f"Invalid time format: '{time_str}'. Use formats like: 1h, 30m, 2h30m, 1.5h")

    if total_minutes > 24 * 60:  # More than 24 hours
        raise ValidationError(
            f"Time duration too large: {total_minutes} minutes ({total_minutes / 60:.1f} hours). "
            f"Maximum is 24 hours per work log entry."
        )

    return total_minutes


def format_minutes(minutes: int) -> str:
    """Format minutes into human-readable string.

    Args:
        minutes: Number of minutes

    Returns:
        Formatted string (e.g., "2h 30m", "1h", "45m")

    Examples:
        >>> format_minutes(90)
        '1h 30m'
        >>> format_minutes(60)
        '1h'
        >>> format_minutes(45)
        '45m'
    """
    if minutes < 0:
        raise ValidationError("Minutes cannot be negative")

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0 and remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{remaining_minutes}m"
