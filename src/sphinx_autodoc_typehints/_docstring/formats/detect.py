"""Tells a numpydoc docstring from a plain field list."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.field_list.edit",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
    f"{__spec__.parent}.numpydoc.convert",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from .field_list.edit import FieldListFormat
from .numpydoc.convert import is_numpydoc_section


def detect_format(lines: list[str]) -> FieldListFormat:
    return FieldListFormat(numpydoc_pending=any(is_numpydoc_section(lines, index) for index in range(len(lines))))


__all__ = [
    "detect_format",
]
