"""Annotations for code that has none at runtime."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.stubs",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Documented as Documented

from .stubs import stub_path

__all__ = [
    "stub_path",
]
