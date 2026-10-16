"""Tells a numpydoc docstring from a plain field list."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._docstring.formats.field_list",
    "sphinx_autodoc_typehints._docstring.formats.numpydoc",
]

from sphinx_autodoc_typehints._docstring.formats.field_list import FieldListFormat
from sphinx_autodoc_typehints._docstring.formats.numpydoc import is_numpydoc_section


def detect_format(lines: list[str]) -> FieldListFormat:
    return FieldListFormat(numpydoc_pending=any(is_numpydoc_section(lines, index) for index in range(len(lines))))


__all__ = [
    "detect_format",
]
