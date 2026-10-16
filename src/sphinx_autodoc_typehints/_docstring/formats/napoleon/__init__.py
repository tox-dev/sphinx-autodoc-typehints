"""Support for the reST napoleon writes from Google and NumPy style docstrings."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._docstring.formats.napoleon.attributes",
    "sphinx_autodoc_typehints._docstring.formats.napoleon.combined",
    "sphinx_autodoc_typehints._docstring.formats.napoleon.returns",
    "sphinx_autodoc_typehints._docstring.formats.napoleon.typed",
]

from sphinx_autodoc_typehints._docstring.formats.napoleon.attributes import (
    WRITTEN_BEFORE_NAPOLEON,
    note_attributes_before_napoleon,
    take_over_napoleon_attr_annotations,
)
from sphinx_autodoc_typehints._docstring.formats.napoleon.combined import (
    add_combined_field_entry,
    type_combined_field_entry,
)
from sphinx_autodoc_typehints._docstring.formats.napoleon.returns import mark_numpy_returns
from sphinx_autodoc_typehints._docstring.formats.napoleon.typed import reads_as_type

__all__ = [
    "WRITTEN_BEFORE_NAPOLEON",
    "add_combined_field_entry",
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "reads_as_type",
    "take_over_napoleon_attr_annotations",
    "type_combined_field_entry",
]
