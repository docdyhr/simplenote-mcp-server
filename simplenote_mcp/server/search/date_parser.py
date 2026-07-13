"""Natural language date parser for search queries.

Parses human-friendly date expressions like "yesterday", "last week",
"3 days ago" into datetime objects. Falls back to dateutil for flexible
format parsing.
"""

import re
from datetime import datetime, timedelta

from dateutil import parser as dateutil_parser

# Relative date keywords mapped to timedelta
_RELATIVE_KEYWORDS: dict[str, timedelta] = {
    "today": timedelta(days=0),
    "yesterday": timedelta(days=1),
    "last_week": timedelta(weeks=1),
    "last_month": timedelta(days=30),
    "last_year": timedelta(days=365),
}

# Day name to weekday number (Monday=0, Sunday=6)
_DAY_NAMES: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# Patterns for "N <unit> ago"
_UNIT_TO_TIMEDELTA: dict[str, callable] = {
    "day": lambda n: timedelta(days=n),
    "days": lambda n: timedelta(days=n),
    "week": lambda n: timedelta(weeks=n),
    "weeks": lambda n: timedelta(weeks=n),
    "month": lambda n: timedelta(days=n * 30),
    "months": lambda n: timedelta(days=n * 30),
    "year": lambda n: timedelta(days=n * 365),
    "years": lambda n: timedelta(days=n * 365),
}

# Regex for "N unit(s) ago"
_AGO_PATTERN = re.compile(
    r"^(\d+)\s+(days?|weeks?|months?|years?)\s+ago$", re.IGNORECASE
)

# Regex for "last <dayname>"
_LAST_DAY_PATTERN = re.compile(
    r"^last\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
    re.IGNORECASE,
)


def parse_natural_date(text: str) -> datetime | None:
    """Parse a natural language date expression into a datetime.

    Supports:
        - Keywords: "today", "yesterday", "last_week", "last_month", "last_year"
        - Relative: "3 days ago", "2 weeks ago", "1 month ago"
        - Named days: "last monday", "last friday"
        - Falls back to dateutil.parser.parse() for other formats

    Args:
        text: The date expression to parse.

    Returns:
        A datetime object, or None if parsing fails.
    """
    if not text or not text.strip():
        return None

    normalized = text.strip().lower().replace("-", "_").replace(" ", "_")

    # Check simple relative keywords (today, yesterday, last_week, etc.)
    if normalized in _RELATIVE_KEYWORDS:
        delta = _RELATIVE_KEYWORDS[normalized]
        result = datetime.now() - delta
        return result.replace(hour=0, minute=0, second=0, microsecond=0)

    # Re-normalize with spaces for pattern matching. The tool schema
    # advertises underscored examples (e.g. "3_days_ago", "last_monday"),
    # matching the keyword style above — accept those alongside naturally
    # spaced input for the regex patterns below, which require whitespace.
    spaced = text.strip().lower().replace("_", " ")

    # Check "N unit(s) ago" pattern
    ago_match = _AGO_PATTERN.match(spaced)
    if ago_match:
        count = int(ago_match.group(1))
        unit = ago_match.group(2).lower()
        if unit in _UNIT_TO_TIMEDELTA:
            delta = _UNIT_TO_TIMEDELTA[unit](count)
            result = datetime.now() - delta
            return result.replace(hour=0, minute=0, second=0, microsecond=0)

    # Check "last <dayname>" pattern
    last_day_match = _LAST_DAY_PATTERN.match(spaced)
    if last_day_match:
        day_name = last_day_match.group(1).lower()
        if day_name in _DAY_NAMES:
            target_weekday = _DAY_NAMES[day_name]
            now = datetime.now()
            current_weekday = now.weekday()
            days_back = (current_weekday - target_weekday) % 7
            if days_back == 0:
                days_back = 7  # "last monday" on a Monday means 7 days ago
            result = now - timedelta(days=days_back)
            return result.replace(hour=0, minute=0, second=0, microsecond=0)

    # Fallback to dateutil for flexible parsing
    try:
        return dateutil_parser.parse(text, fuzzy=False)
    except (ValueError, OverflowError):
        return None
