"""Tells whether a field entry states a type."""

from __future__ import annotations

import re
from typing import Final

_READS_AS_TYPE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\[[^\[\]]*\]")


def reads_as_type(entry: str) -> bool:
    """
    Tell whether the text before ` -- ` in `entry` reads as a type.

    Napoleon's emphasized `*int*`, a role, a literal and a single token once its brackets go read as one.
    """
    if (text := entry.split(" -- ", 1)[0]).startswith(("*", ":", "`")):
        return True
    while (unbracketed := _READS_AS_TYPE_PATTERN.sub("", text)) != text:
        text = unbracketed
    return " " not in text


__all__ = [
    "reads_as_type",
]
