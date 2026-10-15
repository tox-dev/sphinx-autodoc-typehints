"""
Numpydoc format handler for ``:Parameters:``/``:Returns:`` style docstrings.

Handles docstrings produced by the numpydoc extension, which uses bold parameter names and
colon-separated types under section headers. Converts these sections to standard Sphinx field
list syntax (``:param:``/``:type:``/``:returns:``) in-place, then delegates all injection
operations to `SphinxFieldListFormat`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from ._base import DocstringFormat, InsertIndexInfo
from ._sphinx import SphinxFieldListFormat

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_NUMPYDOC_SECTIONS = frozenset({":Parameters:", ":Other Parameters:", ":Returns:", ":Raises:", ":Yields:"})
_NUMPYDOC_BOLD_RE = re.compile(
    r"""
    ^
    \s{4}           # 4-space indent
    \*\*(.+?)\*\*   # **name** (captured)
    (?:             # optional type part
        \s*:\s*     #   colon separator
        (.+)        #   type (captured)
    )?
    $
    """,
    re.VERBOSE,
)
_NUMPYDOC_PLAIN_RE = re.compile(
    r"""
    ^
    \s{4}       # 4-space indent
    (\S.+?)     # non-whitespace start, content (captured)
    $
    """,
    re.VERBOSE,
)


@dataclass
class _NumpydocEntry:
    name: str
    type: str
    description: list[str]
    end: int


def _convert_numpydoc_to_sphinx_fields(lines: list[str]) -> None:  # ruff:ignore[complex-structure, too-many-branches]
    """Convert numpydoc-formatted sections in ``lines`` to Sphinx field list syntax in-place."""
    result: list[str] = []
    i = 0
    while i < len(lines):
        if not _is_numpydoc_section(lines, i):
            result.append(lines[i])
            i += 1
            continue

        section = lines[i].strip()[1:-1]
        i += 1
        if i < len(lines) and not lines[i].strip():
            i += 1

        entries = _parse_numpydoc_entries(lines, i)
        i = entries[-1].end if entries else i

        if section == "Parameters":
            for entry in entries:
                for name in entry.name.split(", "):
                    result.extend(_field(f":param {name}:", entry.description))
                    if entry.type:
                        result.append(f":type {name}: {entry.type}")
        elif section == "Other Parameters":
            result.extend(_other_parameters(entries))
        elif section == "Raises":
            for entry in entries:
                result.extend(_field(f":raises {entry.name or entry.type}:", entry.description))
        elif len(entries) == 1 and section == "Returns":
            result.extend(_single_return(entries[0]))
        elif len(entries) == 1:
            # the yielded type is documented here only, the return type is left out when a Yields section exists
            result.extend(_field(f":Yields: {_label(entries[0])}", entries[0].description))
        else:
            result.append(":returns:" if section == "Returns" else ":Yields:")
            for entry in entries:
                result.extend(_field(f"   * {_label(entry)}", entry.description, indent="     "))

    lines[:] = result


def _is_numpydoc_section(lines: list[str], index: int) -> bool:
    """
    Tell a section numpydoc wrote from a reST field list of the same name, such as docutils' own ``:Parameters:``.

    numpydoc names every parameter in bold, while a field list written by hand holds whatever list its author chose.
    """
    if (section := lines[index].strip()) not in _NUMPYDOC_SECTIONS:
        return False
    entry = next((line for line in lines[index + 1 :] if line.strip()), "")
    return bool(
        _NUMPYDOC_BOLD_RE.match(entry)
        or (section not in {":Parameters:", ":Other Parameters:"} and _NUMPYDOC_PLAIN_RE.match(entry))
    )


def _other_parameters(entries: list[_NumpydocEntry]) -> list[str]:
    """
    Convert Other Parameters into one field, the way napoleon writes it, so the section keeps its heading.

    Its entries then take their types from the annotations in parentheses after the name, as napoleon's do.
    """
    named = [replace(entry, name=name) for entry in entries for name in entry.name.split(", ")]
    if len(named) == 1:
        return _field(f":Other Parameters: {_label(named[0])}", named[0].description)
    converted = [":Other Parameters:"]
    for entry in named:
        converted.extend(_field(f"   * {_label(entry)}", entry.description, indent="     "))
    return converted


def _single_return(entry: _NumpydocEntry) -> list[str]:
    """
    Convert a Returns section holding one entry.

    A named one reads like an entry of a longer list. An unnamed one holds the type alone, which becomes the
    :rtype: an annotation replaces, so the type shows without one.
    """
    if entry.name:
        return _field(f":returns: {_label(entry)}", entry.description)
    converted = [f":rtype: {entry.type}"] if entry.type else []
    if entry.description:
        converted.extend(_field(":returns:", entry.description))
    return converted


def _parse_numpydoc_entries(lines: list[str], start: int) -> list[_NumpydocEntry]:
    entries: list[_NumpydocEntry] = []
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in _NUMPYDOC_SECTIONS:
            break
        if not stripped:
            i += 1
            continue

        if m := _NUMPYDOC_BOLD_RE.match(lines[i]):
            name, typ = m.group(1), m.group(2) or ""
        elif m := _NUMPYDOC_PLAIN_RE.match(lines[i]):
            name, typ = "", m.group(1).strip()
        else:
            break

        i += 1
        desc_lines: list[str] = []
        # numpydoc indents the blank lines inside a description too, so only an unindented one ends it
        while i < len(lines) and lines[i].startswith("        "):
            desc_lines.append(lines[i][8:].rstrip())
            i += 1
        # numpydoc stands in an empty comment for a missing description
        description = [] if [line for line in desc_lines if line] == [".."] else desc_lines
        entries.append(_NumpydocEntry(name=name, type=typ, description=description, end=i))

    return entries


def _field(head: str, description: list[str], indent: str = "   ") -> list[str]:
    first, *rest = description or [""]
    return [f"{head} {first}".rstrip(), *(f"{indent}{line}" if line else "" for line in rest)]


def _label(entry: _NumpydocEntry) -> str:
    if not entry.name:
        label = entry.type
    elif entry.type:
        label = f"**{entry.name}** ({entry.type})"
    else:
        label = f"**{entry.name}**"
    return f"{label} --" if entry.description else label


class NumpydocFormat(DocstringFormat):
    """Converts numpydoc sections to Sphinx field lists, then delegates to SphinxFieldListFormat."""

    def __init__(self) -> None:
        self._converted = False
        self._sphinx = SphinxFieldListFormat()

    @staticmethod
    def detect(lines: list[str]) -> bool:
        return any(_is_numpydoc_section(lines, index) for index in range(len(lines)))

    def _ensure_converted(self, lines: list[str]) -> None:
        if not self._converted:
            _convert_numpydoc_to_sphinx_fields(lines)
            self._converted = True

    def find_param(self, lines: list[str], arg_name: str) -> int | None:
        self._ensure_converted(lines)
        return self._sphinx.find_param(lines, arg_name)

    def inject_param_type(self, lines: list[str], arg_name: str, formatted_type: str, at: int) -> None:
        self._sphinx.inject_param_type(lines, arg_name, formatted_type, at)

    def add_undocumented_param(
        self,
        lines: list[str],
        arg_name: str,
        description: str = "",
        *,
        before: int | None = None,
        field: Literal["param", "keyword"] = "param",
    ) -> int:
        self._ensure_converted(lines)
        return self._sphinx.add_undocumented_param(lines, arg_name, description, before=before, field=field)

    def find_preexisting_type(self, lines: list[str], arg_name: str) -> tuple[str, bool]:
        return self._sphinx.find_preexisting_type(lines, arg_name)

    def has_return_description(self, lines: list[str]) -> bool:
        self._ensure_converted(lines)
        return self._sphinx.has_return_description(lines)

    def get_rtype_insert_info(self, app: Sphinx, lines: list[str]) -> InsertIndexInfo | None:
        self._ensure_converted(lines)
        return self._sphinx.get_rtype_insert_info(app, lines)

    def inject_rtype(
        self,
        lines: list[str],
        formatted_annotation: str,
        info: InsertIndexInfo,
        *,
        use_rtype: bool,
    ) -> None:
        self._sphinx.inject_rtype(lines, formatted_annotation, info, use_rtype=use_rtype)

    def append_default(
        self,
        lines: list[str],
        insert_index: int,
        type_annotation: str,
        formatted_default: str,
        *,
        after: bool,
    ) -> str:
        return self._sphinx.append_default(lines, insert_index, type_annotation, formatted_default, after=after)

    def get_arg_name_from_line(self, line: str) -> str | None:
        return self._sphinx.get_arg_name_from_line(line)
