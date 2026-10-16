"""
The `autodoc-process-docstring` side of the extension, which writes types into docstring fields.

In the layering it sits beside `_signature`, above `_documented`, and above the `_render` and `_resolve`
packages those two build on.
"""

from __future__ import annotations

from .deprecation import DEPRECATED_DIRECTIVE, DeprecatedDirective
from .formats import mark_numpy_returns, note_attributes_before_napoleon
from .handler import process_docstring

__all__ = [
    "DEPRECATED_DIRECTIVE",
    "DeprecatedDirective",
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "process_docstring",
]
