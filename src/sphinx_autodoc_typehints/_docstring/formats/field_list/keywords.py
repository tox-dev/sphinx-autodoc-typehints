"""Reads the keyword and argument of a reST field and names the keywords that document a parameter."""

from __future__ import annotations

__lazy_modules__ = ["typing"]

from typing import Final

PARAM_SYNONYMS: Final[tuple[str, ...]] = ("param ", "parameter ", "arg ", "argument ", "keyword ", "kwarg ", "kwparam ")
STAR_PREFIXES: Final[tuple[str, ...]] = ("", "\\*", "\\**", "\\*\\*")


def field_keyword_and_argument(line: str) -> tuple[str, str | None] | None:
    """Return the keyword of a field and its argument, `None` in place of either where the line has none."""
    # an indented field belongs to the block around it, such as a literal block or a note, not to the object
    if not line.startswith(":"):
        return None
    directive_and_name, closed, _ = line[1:].partition(":")
    if not closed:
        return None
    match directive_and_name.split(maxsplit=1):
        case [keyword, argument]:
            return keyword, argument
        case [keyword]:
            return keyword, None
        case _:
            return None


__all__ = [
    "PARAM_SYNONYMS",
    "STAR_PREFIXES",
    "field_keyword_and_argument",
]
