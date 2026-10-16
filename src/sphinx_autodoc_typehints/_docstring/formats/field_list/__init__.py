"""Editing of the reST field list in a docstring, the form numpydoc's sections convert to."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._docstring.formats.field_list.edit",
    "sphinx_autodoc_typehints._docstring.formats.field_list.keywords",
]

from sphinx_autodoc_typehints._docstring.formats.field_list.edit import FieldListFormat, write_rtype
from sphinx_autodoc_typehints._docstring.formats.field_list.keywords import STAR_PREFIXES, field_keyword_and_argument

__all__ = [
    "STAR_PREFIXES",
    "FieldListFormat",
    "field_keyword_and_argument",
    "write_rtype",
]
