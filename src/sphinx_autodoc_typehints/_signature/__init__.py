"""
Keeps or strips the types in the signatures autodoc writes, and adds types to the headers the Python domain builds.

In the import layering the package sits beside `_docstring` and above the `_documented`, `_render` and
`_resolve` layers it calls.
"""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._signature.bases",
    "sphinx_autodoc_typehints._signature.handler",
    "sphinx_autodoc_typehints._signature.header",
]

from sphinx_autodoc_typehints._signature.bases import process_bases
from sphinx_autodoc_typehints._signature.handler import process_signature
from sphinx_autodoc_typehints._signature.header import add_type_params, render_header_types

__all__ = [
    "add_type_params",
    "process_bases",
    "process_signature",
    "render_header_types",
]
