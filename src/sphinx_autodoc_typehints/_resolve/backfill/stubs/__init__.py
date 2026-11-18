"""Finds the `.pyi` stub of an object, reads its annotations, and builds the namespace they evaluate in."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.find",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Documented as Documented

from .find import stub_path

__all__ = [
    "stub_path",
]
