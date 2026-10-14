from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Generic

from typing_extensions import ParamSpec, TypeVar, TypeVarTuple

if TYPE_CHECKING:
    from collections.abc import Callable, Sized


def bounded[T: Path](value: T) -> T:
    """Take a bounded type parameter."""
    return value


def constrained[T: (int, str)](value: T) -> T:
    """Take a constrained type parameter."""
    return value


def variadic[*Ts, **P](*args: *Ts) -> None:
    """Take variadic type parameters."""


def forward[**P](call: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
    """
    Call with the arguments it takes.

    :param args: positional
    :param kwargs: by keyword
    """


class Stack[T]:
    """A stack."""

    def __init__(self, item: T) -> None:
        """Make a stack."""

    def peek(self) -> T:
        """Look at the top."""
        raise NotImplementedError


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

    def first(self) -> D:
        """Return the first."""
        raise NotImplementedError


L = TypeVar("L")


def loose(value: L) -> L:  # ruff:ignore[non-pep695-generic-function]  # no signature declares L
    """Use a type variable no signature declares."""
    return value


def plain(value: int) -> int:
    """Not generic."""
    return value
