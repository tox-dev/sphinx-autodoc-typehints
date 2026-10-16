"""
The docstring styles the extension edits.

It reads reST field lists, the sections numpydoc renders, which it first converts to a field list, and the combined
fields napoleon writes from Google and NumPy docstrings.
"""

from __future__ import annotations

from .base import format_default, last_paragraph_end
from .detect import detect_format
from .field_list import (
    STAR_PREFIXES,
    FieldListFormat,
    field_keyword_and_argument,
    place_rtype,
    write_rtype,
)
from .napoleon import (
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
    "place_rtype",
    "reads_as_type",
    "take_over_napoleon_attr_annotations",
    "type_combined_field_entry",
    "write_rtype",
]
