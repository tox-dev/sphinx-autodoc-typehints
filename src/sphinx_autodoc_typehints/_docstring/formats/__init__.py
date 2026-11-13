"""
The docstring styles the extension edits.

It reads reST field lists, the sections numpydoc renders, which it first converts to a field list, and the combined
fields napoleon writes from Google and NumPy docstrings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING  # simplint: ignore[init-module-content]  # type-only relay avoids cycles

if TYPE_CHECKING:
    from .. import Documented as Documented
    from .. import Hint as Hint
    from .. import WrittenTypeAlias as WrittenTypeAlias

from .field_list import place_rtype
from .napoleon import mark_numpy_returns, note_attributes_before_napoleon

__all__ = [
    "mark_numpy_returns",
    "note_attributes_before_napoleon",
    "place_rtype",
]
