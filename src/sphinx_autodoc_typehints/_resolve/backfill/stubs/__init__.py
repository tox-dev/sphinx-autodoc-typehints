"""Finds the `.pyi` stub of an object, reads its annotations, and builds the namespace they evaluate in."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import Documented as Documented

from .find import stub_path

__all__ = [
    "stub_path",
]
