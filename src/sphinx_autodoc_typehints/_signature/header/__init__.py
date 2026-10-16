"""Builds an entry's header: the overloads its signature lists, its type parameters, and the type of data."""

from __future__ import annotations

__lazy_modules__ = [
    "sphinx_autodoc_typehints._signature.header.data_types",
    "sphinx_autodoc_typehints._signature.header.overloads",
    "sphinx_autodoc_typehints._signature.header.type_params",
]

from sphinx_autodoc_typehints._signature.header.data_types import render_header_types
from sphinx_autodoc_typehints._signature.header.overloads import signature_overloads
from sphinx_autodoc_typehints._signature.header.type_params import add_type_params

__all__ = [
    "add_type_params",
    "render_header_types",
    "signature_overloads",
]
