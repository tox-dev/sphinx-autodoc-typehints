"""Support for docstrings the numpydoc extension rendered, which hold sections in place of fields."""

from __future__ import annotations

__lazy_modules__ = ["sphinx_autodoc_typehints._docstring.formats.numpydoc.convert"]

from sphinx_autodoc_typehints._docstring.formats.numpydoc.convert import convert_to_field_list, is_numpydoc_section

__all__ = [
    "convert_to_field_list",
    "is_numpydoc_section",
]
