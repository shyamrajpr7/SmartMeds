"""
General helper utilities for SmartMeds.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import List, Optional


def parse_time(time_str: str) -> time:
    """
    Parse a time string in HH:MM format.

    Args:
        time_str: Time string like '08:00' or '14:30'.

    Returns:
        A datetime.time object.

    Raises:
        ValueError: If the format is invalid.
    """
    try:
        dt = datetime.strptime(time_str.strip(), "%H:%M")
        return dt.time()
    except ValueError:
        raise ValueError(f"Invalid time format: '{time_str}'. Expected HH:MM.")


def parse_times(times_str: str, separator: str = ",") -> List[time]:
    """
    Parse a comma-separated list of time strings.

    Args:
        times_str: Comma-separated time strings like '08:00,12:00,20:00'.
        separator: Delimiter character.

    Returns:
        List of datetime.time objects.
    """
    return [parse_time(t) for t in times_str.split(separator) if t.strip()]


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format a datetime object, returning 'N/A' if None.

    Args:
        dt: Datetime to format, or None.
        fmt: strftime format string.

    Returns:
        Formatted string or 'N/A'.
    """
    if dt is None:
        return "N/A"
    return dt.strftime(fmt)


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Return the correct singular or plural form based on count.

    Args:
        count: The count to check.
        singular: Singular form of the word.
        plural: Plural form. Defaults to singular + 's'.

    Returns:
        Correctly pluralized string with count.
    """
    word = singular if count == 1 else (plural or singular + "s")
    return f"{count} {word}"


def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: The text to truncate.
        max_length: Maximum number of characters.
        suffix: String to append when truncated.

    Returns:
        Truncated string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def redact_uri(uri: str) -> str:
    """
    Hide the credentials embedded in a connection string.

    ``mongodb+srv://user:secret@host/db`` becomes
    ``mongodb+srv://user:***@host/db`` so connection strings can be logged or
    displayed safely.

    Args:
        uri: The connection string to redact.

    Returns:
        The connection string with the password replaced by ``***``.
    """
    if "@" not in uri or "://" not in uri:
        return uri
    prefix, _, host = uri.rpartition("@")
    scheme, _, userinfo = prefix.partition("://")
    user = userinfo.split(":", 1)[0]
    if not user:
        return f"{scheme}://***@{host}"
    return f"{scheme}://{user}:***@{host}"
