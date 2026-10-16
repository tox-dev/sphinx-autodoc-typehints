"""Builds an entry's header: the overloads its signature lists, its type parameters, and the type of data."""

from __future__ import annotations

from .data_types import render_header_types
from .overloads import signature_overloads
from .type_params import add_type_params

__all__ = [
    "add_type_params",
    "render_header_types",
    "signature_overloads",
]
