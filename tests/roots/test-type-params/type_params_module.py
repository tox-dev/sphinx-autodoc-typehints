from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Generic

from typing_extensions import ParamSpec, TypeVar, TypeVarTuple

if TYPE_CHECKING:
    from collections.abc import Sized


def bounded[T: Path](value: T) -> T:
    """Take a bounded type parameter."""
    return value


def constrained[T: (int, str)](value: T) -> T:
    """Take a constrained type parameter."""
    return value


def variadic[*Ts, **P](*args: *Ts) -> None:
    """Take variadic type parameters."""


class Stack[T]:
    """A stack."""

    def __init__(self, item: T) -> None:
        """Make a stack."""


class Sizes[T: Sized]:
    """Bound by a type imported only for type checking."""


class Unknown[T: Undefined]:  # ruff:ignore[undefined-name]
    """Bound by a name defined nowhere."""


type Pairs[K] = dict[K, K]

D = TypeVar("D", default=int)
DP = ParamSpec("DP", default=[int, str])
# what ``*tuple[int, ...]`` evaluates to, which a default can only be written as from 3.13 on
DTs = TypeVarTuple("DTs", default=next(iter(tuple[int, ...])))


class Legacy(Generic[D, DP, *DTs]):
    """Generic the pre-PEP 695 way."""


def plain(value: int) -> int:
    """Not generic."""
    return value
