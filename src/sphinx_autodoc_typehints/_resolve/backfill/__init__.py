"""Annotations for code that has none at runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

if TYPE_CHECKING:
    from .. import Documented as Documented

from .stubs import stub_path

__all__ = [
    "stub_path",
]
