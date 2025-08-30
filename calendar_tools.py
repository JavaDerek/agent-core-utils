import calendar
import re
from datetime import date, datetime

import dateparser
from dateutil.relativedelta import relativedelta

MONTHS = {name.lower(): idx for idx, name in enumerate(calendar.month_name) if name}

NUM_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

def _word_to_int(word: str) -> int | None:
    if word.isdigit():
        return int(word)
    return NUM_WORDS.get(word.lower())

def get_current_date() -> date:
    """Return today's date."""
    return date.today()

def parse_relative_date(expression: str, *, base: date | None = None) -> date | None:
    """Return an absolute date for ``expression`` relative to ``base``."""
    base = base or get_current_date()
    text = expression.lower().strip()

    next_month = re.fullmatch(r"next\s+([a-z]+)", text)
    if next_month and next_month.group(1) in MONTHS:
        m = MONTHS[next_month.group(1)]
        year = base.year if base.month < m else base.year + 1
        return date(year, m, 1)

    last_month = re.fullmatch(r"last\s+([a-z]+)", text)
    if last_month and last_month.group(1) in MONTHS:
        m = MONTHS[last_month.group(1)]
        year = base.year if base.month > m else base.year - 1
        return date(year, m, 1)

    in_future = re.fullmatch(
        r"in\s+(\d+|[a-z]+)\s+(day|week|month|year)s?",
        text,
    )
    if in_future:
        num = _word_to_int(in_future.group(1))
        unit = in_future.group(2)
        if num is not None:
            return (base + relativedelta(**{unit + "s": num}))

    from_now = re.fullmatch(
        r"(\d+|[a-z]+)\s+(day|week|month|year)s?\s+from\s+now",
        text,
    )
    if from_now:
        num = _word_to_int(from_now.group(1))
        unit = from_now.group(2)
        if num is not None:
            return (base + relativedelta(**{unit + "s": num}))

    ago = re.fullmatch(r"(\d+|[a-z]+)\s+(day|week|month|year)s?\s+ago", text)
    if ago:
        num = _word_to_int(ago.group(1))
        unit = ago.group(2)
        if num is not None:
            return (base + relativedelta(**{unit + "s": -num}))

    dt = dateparser.parse(
        text, settings={"RELATIVE_BASE": datetime(base.year, base.month, base.day)}
    )
    if dt:
        return dt.date()
    return None

def resolve_relative_dates(text: str, *, base: date | None = None) -> str:
    """Replace recognized relative date phrases in ``text`` with ISO dates."""
    base = base or get_current_date()
    patterns = [
        r"next\s+[a-z]+",
        r"last\s+[a-z]+",
        r"(\d+|[a-z]+)\s+(?:day|week|month|year)s?\s+from\s+now",
        r"(\d+|[a-z]+)\s+(?:day|week|month|year)s?\s+ago",
        r"in\s+(\d+|[a-z]+)\s+(?:day|week|month|year)s?",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            phrase = match.group(0)
            resolved = parse_relative_date(phrase, base=base)
            if resolved:
                text = text.replace(phrase, resolved.isoformat())
    return text
