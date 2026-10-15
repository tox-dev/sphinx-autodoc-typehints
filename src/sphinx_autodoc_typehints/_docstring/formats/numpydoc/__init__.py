"""Support for docstrings the numpydoc extension rendered, which hold sections in place of fields."""

from __future__ import annotations

from .convert import convert_to_field_list, is_numpydoc_section

__all__ = [
    "convert_to_field_list",
    "is_numpydoc_section",
]
