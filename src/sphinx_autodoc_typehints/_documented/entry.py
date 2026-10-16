"""The autodoc event arguments naming a documented object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sphinx.application import Sphinx

    from .._types import Documented


@dataclass(frozen=True, slots=True)
class Entry:
    """What an autodoc event names; `obj` may be a property."""

    app: Sphinx
    what: str
    name: str
    obj: Documented

    @property
    def documents_init(self) -> bool:
        return self.what == "method" and self.name.endswith(".__init__")


__all__ = [
    "Entry",
]
