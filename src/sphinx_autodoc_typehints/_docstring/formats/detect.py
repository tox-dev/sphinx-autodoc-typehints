"""Tells a numpydoc docstring from a plain field list."""

from __future__ import annotations

from .field_list import FieldListFormat
from .numpydoc import is_numpydoc_section


def detect_format(lines: list[str]) -> FieldListFormat:
    return FieldListFormat(numpydoc_pending=any(is_numpydoc_section(lines, index) for index in range(len(lines))))


__all__ = [
    "detect_format",
]
