"""Evaluates annotations where a type checker would."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Annotation as Annotation
    from .. import Documented as Documented
    from .. import Hint as Hint

from .expression import resolve_string_annotations

__all__ = [
    "resolve_string_annotations",
]
