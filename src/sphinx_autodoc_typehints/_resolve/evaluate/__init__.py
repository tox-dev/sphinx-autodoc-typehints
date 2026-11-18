"""Evaluates annotations where a type checker would."""

from __future__ import annotations

__lazy_modules__ = [
    f"{__spec__.parent}.expression",  # ty: ignore[unresolved-attribute]  # imported modules have a spec
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Annotation as Annotation
    from .. import Documented as Documented
    from .. import Hint as Hint

from .expression import resolve_string_annotations

__all__ = [
    "resolve_string_annotations",
]
