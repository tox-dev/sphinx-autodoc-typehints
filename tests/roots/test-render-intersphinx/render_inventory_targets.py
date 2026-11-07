"""Objects an inventory lists whose reported path maps to no documented name."""

from __future__ import annotations

from types import UnionType
from typing import Final, Union


class Thing:
    """A class whose instances have a module but no qualified name."""


THING: Final[Thing] = Thing()
PublicThing = Thing
CompatThing = Thing
UnionClass = UnionType
UnionAlias = Union[bytes, memoryview]
