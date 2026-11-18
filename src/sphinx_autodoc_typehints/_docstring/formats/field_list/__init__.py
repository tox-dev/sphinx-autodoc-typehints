"""Editing of the reST field list in a docstring, the form numpydoc's sections convert to."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.rtype",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from .rtype import place_rtype

__all__ = [
    "place_rtype",
]
