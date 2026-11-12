"""Support for the reST napoleon writes from Google and NumPy style docstrings."""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

if TYPE_CHECKING:
    from .. import Documented as Documented
    from .. import Hint as Hint
    from .. import WrittenTypeAlias as WrittenTypeAlias

from .attributes import note_attributes_before_napoleon
from .returns import mark_numpy_returns

__all__ = [
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
]
