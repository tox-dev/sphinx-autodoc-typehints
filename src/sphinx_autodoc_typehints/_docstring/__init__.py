"""
The `autodoc-process-docstring` side of the extension, which writes types into docstring fields.

In the layering it sits beside `_signature`, above `_documented`, and above the `_render` and `_resolve`
packages those two build on.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._docstring.deprecation",
    "sphinx_autodoc_typehints._docstring.formats",
    "sphinx_autodoc_typehints._docstring.handler",
]

from sphinx_autodoc_typehints._docstring.deprecation import DEPRECATED_DIRECTIVE, DeprecatedDirective
from sphinx_autodoc_typehints._docstring.formats import (
    mark_numpy_returns,
    note_attributes_before_napoleon,
    take_over_napoleon_attr_annotations,
)
from sphinx_autodoc_typehints._docstring.handler import process_docstring

__all__ = [
    "DEPRECATED_DIRECTIVE",
    "DeprecatedDirective",
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "process_docstring",
    "take_over_napoleon_attr_annotations",
]
