"""
The docstring styles the extension edits.

It reads reST field lists, the sections numpydoc renders, which it first converts to a field list, and the combined
fields napoleon writes from Google and NumPy docstrings.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._docstring.formats.base",
    "sphinx_autodoc_typehints._docstring.formats.detect",
    "sphinx_autodoc_typehints._docstring.formats.field_list",
    "sphinx_autodoc_typehints._docstring.formats.napoleon",
]

from sphinx_autodoc_typehints._docstring.formats.base import format_default, last_paragraph_end
from sphinx_autodoc_typehints._docstring.formats.detect import detect_format
from sphinx_autodoc_typehints._docstring.formats.field_list import (
    STAR_PREFIXES,
    FieldListFormat,
    field_keyword_and_argument,
    write_rtype,
)
from sphinx_autodoc_typehints._docstring.formats.napoleon import (
    WRITTEN_BEFORE_NAPOLEON,
    add_combined_field_entry,
    mark_numpy_returns,
    note_attributes_before_napoleon,
    reads_as_type,
    take_over_napoleon_attr_annotations,
    type_combined_field_entry,
)

__all__ = [
    "STAR_PREFIXES",
    "WRITTEN_BEFORE_NAPOLEON",
    "FieldListFormat",
    "add_combined_field_entry",
    "detect_format",
    "field_keyword_and_argument",
    "format_default",
    "last_paragraph_end",
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "reads_as_type",
    "take_over_napoleon_attr_annotations",
    "type_combined_field_entry",
    "write_rtype",
]
