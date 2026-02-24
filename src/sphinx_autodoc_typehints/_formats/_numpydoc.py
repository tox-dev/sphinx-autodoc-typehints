"""
Numpydoc format handler for ``:Parameters:``/``:Returns:`` style docstrings.

Handles docstrings produced by the numpydoc extension, which uses bold parameter names and
colon-separated types under section headers. Converts these sections to standard Sphinx field
list syntax (``:param:``/``:type:``/``:returns:``) in-place, then delegates all injection
operations to `SphinxFieldListFormat`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
        while i < len(lines) and lines[i].startswith("        ") and lines[i].strip():
            desc_lines.append(lines[i].strip())
            i += 1
        entries.append(_NumpydocEntry(name=name, type=typ, description=desc_lines, end=i))

    return entries


def _convert_numpydoc_to_sphinx_fields(lines: list[str]) -> None:  # noqa: C901, PLR0912
    """Convert numpydoc-formatted sections in ``lines`` to Sphinx field list syntax in-place."""
    if not any(line.strip() in _NUMPYDOC_SECTIONS for line in lines):
        return

    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped not in _NUMPYDOC_SECTIONS:
            result.append(lines[i])
            i += 1
            continue

        section = stripped[1:-1]
        i += 1
        if i < len(lines) and not lines[i].strip():
            i += 1

        entries = _parse_numpydoc_entries(lines, i)
        i = entries[-1].end if entries else i

        if section in {"Parameters", "Other Parameters"}:
            for entry in entries:
                desc = " ".join(entry.description) if entry.description else ""
                result.append(f":param {entry.name}: {desc}".rstrip())
                if entry.type:
                    result.append(f":type {entry.name}: {entry.type}")
        elif section == "Returns":
            if len(entries) == 1:
                entry = entries[0]
                desc = " ".join(entry.description) if entry.description else ""
                if desc:
                    result.append(f":returns: {desc}")
            else:
                result.append(":returns:")
                for entry in entries:
                    desc = " ".join(entry.description) if entry.description else ""
                    label = f"**{entry.name}**" if entry.name else ""
                    type_part = f" ({entry.type})" if entry.type else ""
                    result.append(f"   * {label}{type_part} -- {desc}".rstrip())
        elif section == "Raises":
            for entry in entries:
                desc = " ".join(entry.description) if entry.description else ""
                exc_name = entry.name or entry.type
                result.append(f":raises {exc_name}: {desc}".rstrip())
        elif len(entries) == 1:
            entry = entries[0]
            desc = " ".join(entry.description) if entry.description else ""
            if desc:
                result.append(f":Yields: {desc}")
        else:
            result.append(":Yields:")
            for entry in entries:
                desc = " ".join(entry.description) if entry.description else ""
                label = f"**{entry.name}**" if entry.name else ""
                type_part = f" ({entry.type})" if entry.type else ""
                result.append(f"   * {label}{type_part} -- {desc}".rstrip())

    lines[:] = result


class NumpydocFormat(DocstringFormat):
    """Converts numpydoc sections to Sphinx field lists, then delegates to SphinxFieldListFormat."""

    def __init__(self) -> None:
        self._converted = False
        self._sphinx = SphinxFieldListFormat()

    @staticmethod
    def detect(lines: list[str]) -> bool:
        return any(line.strip() in _NUMPYDOC_SECTIONS for line in lines)

    def _ensure_converted(self, lines: list[str]) -> None:
        if not self._converted:
            _convert_numpydoc_to_sphinx_fields(lines)
            self._converted = True

    def find_param(self, lines: list[str], arg_name: str) -> int | None:
        self._ensure_converted(lines)
        return self._sphinx.find_param(lines, arg_name)

    def inject_param_type(self, lines: list[str], arg_name: str, formatted_type: str, at: int) -> None:
        self._sphinx.inject_param_type(lines, arg_name, formatted_type, at)

    def add_undocumented_param(self, lines: list[str], arg_name: str) -> int:
        self._ensure_converted(lines)
        return self._sphinx.add_undocumented_param(lines, arg_name)

    def find_preexisting_type(self, lines: list[str], arg_name: str) -> tuple[str, bool]:
        return self._sphinx.find_preexisting_type(lines, arg_name)

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
