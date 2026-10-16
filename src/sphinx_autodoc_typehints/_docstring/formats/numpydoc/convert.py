"""Turns numpydoc's sections, such as `:Parameters:`, into the reST field list the package edits."""

from __future__ import annotations

import re  # a from-import of compile would shadow the builtin
from dataclasses import dataclass, replace
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from sphinx_autodoc_typehints._types import frozendict

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_NUMPYDOC_SECTIONS: Final[frozenset[str]] = frozenset({
    ":Parameters:",
    ":Other Parameters:",
    ":Returns:",
    ":Raises:",
    ":Yields:",
})
_NUMPYDOC_BOLD_RE: Final[re.Pattern[str]] = re.compile(
    dedent(r"""
        ^
        \s{4}
        \*\*(.+?)\*\*
        (?:
            \s*:\s*
            (.+)
        )?
        $
    """),
    re.VERBOSE,
)
_NUMPYDOC_PLAIN_RE: Final[re.Pattern[str]] = re.compile(
    dedent(r"""
        ^
        \s{4}
        (\S.+?)
        $
    """),
    re.VERBOSE,
)


def convert_to_field_list(lines: list[str]) -> None:
    result: list[str] = []
    at = 0
    while at < len(lines):
        if not is_numpydoc_section(lines, at):
            result.append(lines[at])
            at += 1
            continue

        section = lines[at].strip()[1:-1]
        at += 1
        if at < len(lines) and not lines[at].strip():
            at += 1

        entries = _parse_numpydoc_entries(lines, at)
        at = entries[-1].end if entries else at
        result.extend(_SECTIONS[section](entries))

    lines[:] = result


def is_numpydoc_section(lines: list[str], index: int) -> bool:
    """
    Return whether the line at `index` heads a section numpydoc wrote, not a reST field list of the same name.

    numpydoc names every parameter in bold, while a field list written by hand, such as docutils' own `:Parameters:`,
    holds whatever list its author chose.
    """
    if (section := lines[index].strip()) not in _NUMPYDOC_SECTIONS:
        return False
    entry = next((line for line in lines[index + 1 :] if line.strip()), "")
    return bool(
        _NUMPYDOC_BOLD_RE.match(entry)
        or (section not in {":Parameters:", ":Other Parameters:"} and _NUMPYDOC_PLAIN_RE.match(entry))
    )


def _parse_numpydoc_entries(lines: list[str], start: int) -> list[_NumpydocEntry]:
    entries: list[_NumpydocEntry] = []
    at = start
    while at < len(lines):
        stripped = lines[at].strip()
        if stripped in _NUMPYDOC_SECTIONS:
            break
        if not stripped:
            at += 1
            continue

        if bold := _NUMPYDOC_BOLD_RE.match(lines[at]):
            name, entry_type = bold.group(1), bold.group(2) or ""
        elif plain := _NUMPYDOC_PLAIN_RE.match(lines[at]):
            name, entry_type = "", plain.group(1).strip()
        else:
            break

        at += 1
        desc_lines: list[str] = []
        # numpydoc indents the blank lines inside a description too, so only an unindented one ends it
        while at < len(lines) and lines[at].startswith("        "):
            desc_lines.append(lines[at][8:].rstrip())
            at += 1
        # numpydoc stands in an empty comment for a missing description
        description = [] if [line for line in desc_lines if line] == [".."] else desc_lines
        entries.append(_NumpydocEntry(name=name, type=entry_type, description=description, end=at))

    return entries


@dataclass(frozen=True, slots=True)
class _NumpydocEntry:
    name: str
    type: str
    description: list[str]
    end: int


def _parameters(entries: list[_NumpydocEntry]) -> list[str]:
    converted: list[str] = []
    for entry in entries:
        for name in entry.name.split(", "):
            converted.extend(_field(f":param {name}:", entry.description))
            if entry.type:
                converted.append(f":type {name}: {entry.type}")
    return converted


def _field(head: str, description: list[str], indent: str = "   ") -> list[str]:
    first, *rest = description or [""]
    return [f"{head} {first}".rstrip(), *(f"{indent}{line}" if line else "" for line in rest)]


# one field, as napoleon writes it, keeps the section's heading, and its entries take their types in parentheses
def _other_parameters(entries: list[_NumpydocEntry]) -> list[str]:
    named = [replace(entry, name=name) for entry in entries for name in entry.name.split(", ")]
    if len(named) == 1:
        return _field(f":Other Parameters: {_label(named[0])}", named[0].description)
    return _bullets(":Other Parameters:", named)


def _label(entry: _NumpydocEntry) -> str:
    if not entry.name:
        label = entry.type
    elif entry.type:
        label = f"**{entry.name}** ({entry.type})"
    else:
        label = f"**{entry.name}**"
    return f"{label} --" if entry.description else label


def _bullets(head: str, entries: list[_NumpydocEntry]) -> list[str]:
    return [
        head,
        *(line for entry in entries for line in _field(f"   * {_label(entry)}", entry.description, indent="     ")),
    ]


def _raises(entries: list[_NumpydocEntry]) -> list[str]:
    return [line for entry in entries for line in _field(f":raises {entry.name or entry.type}:", entry.description)]


def _returns(entries: list[_NumpydocEntry]) -> list[str]:
    if len(entries) != 1:
        return _bullets(":returns:", entries)
    # a single named entry reads like an entry of a longer list, an unnamed one holds the type alone, which becomes
    # the :rtype: an annotation replaces, so the type shows without one
    if (entry := entries[0]).name:
        return _field(f":returns: {_label(entry)}", entry.description)
    converted = [f":rtype: {entry.type}"] if entry.type else []
    if entry.description:
        converted.extend(_field(":returns:", entry.description))
    return converted


def _yields(entries: list[_NumpydocEntry]) -> list[str]:
    if len(entries) == 1:
        # only this field states the yielded type, as a docstring with a Yields section gets no return type
        return _field(f":Yields: {_label(entries[0])}", entries[0].description)
    return _bullets(":Yields:", entries)


# built once rather than for every docstring converted, after the converters it names
_SECTIONS: Final[Mapping[str, Callable[[list[_NumpydocEntry]], list[str]]]] = frozendict({
    "Parameters": _parameters,
    "Other Parameters": _other_parameters,
    "Raises": _raises,
    "Returns": _returns,
    "Yields": _yields,
})


__all__ = [
    "convert_to_field_list",
    "is_numpydoc_section",
]
