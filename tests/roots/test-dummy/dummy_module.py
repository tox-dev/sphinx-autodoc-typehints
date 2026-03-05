from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path


def undocumented_function(x: int) -> str:
    """Hi"""

    return str(x)


def undocumented_function_with_defaults(x: int, y: str = "hello") -> str:
    """Hi"""

    return str(x) + y


class MyNamedTuple(NamedTuple):
    """A named tuple."""

    x: int
    y: str = "hello"


class MyNamedTupleWithPath(NamedTuple):
    """A named tuple with non-builtin types."""

    path: Path
    version: str


@dataclass
class DataClass:
    """Class docstring."""

    x: int
