from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from sys import version_info
from typing import TYPE_CHECKING, Any, Generic, Protocol, overload

from typing_extensions import ParamSpec, TypeVar, TypeVarTuple

if TYPE_CHECKING:
    from collections.abc import Callable, Sized


def bounded[ItemT: Path](value: ItemT) -> ItemT:
    """Take a bounded type parameter."""
    return value


def constrained[ItemT: (int, str)](value: ItemT) -> ItemT:
    """Take a constrained type parameter."""
    return value


def variadic[*Ts, **Params](*args: *Ts) -> None:
    """
    Take variadic type parameters.

    :param args: the values
    """


def forward[**Params](call: Callable[Params, None], *args: Params.args, **kwargs: Params.kwargs) -> None:
    """
    Call with the arguments it takes.

    :param args: positional
    :param kwargs: by keyword
    """


class Stack[ItemT]:
    """A stack."""

    def __init__(self, item: ItemT) -> None:
        """Make a stack."""

    def peek(self) -> ItemT:
        """Look at the top."""
        raise NotImplementedError


#: A stack ready to use.
default_stack: Stack[int] = Stack(0)  # simplint: ignore[missing-final]  # header tests render the annotation as written


class Sizes[ItemT: Sized]:
    """Bound by a type imported only for type checking."""


class Unknown[ItemT: Undefined]:  # ruff:ignore[undefined-name]  # the fixture renders a bound that does not resolve
    """Bound by a name defined nowhere."""


class Rejected[ItemT: Rejecting[int]]:
    """Bound by a subscript that raises."""


class Rejecting:
    """Rejects every argument, as a class validating its subscript does."""

    def __class_getitem__(cls, item: object) -> type[Rejecting]:
        msg = f"cannot take {item}"
        raise ValueError(msg)


type Pairs[KeyT] = dict[KeyT, KeyT]


def takes_pairs(value: Pairs) -> None:
    """
    Take pairs.

    :param value: the pairs
    """


type RejectedAlias = Rejecting[int]


def takes_rejected(value: RejectedAlias) -> None:
    """
    Take an alias whose value raises.

    :param value: the value
    """


DefaultT = TypeVar("DefaultT", default=int)
DP = ParamSpec("DP", default=[int, str])
# what ``*tuple[int, ...]`` evaluates to, a spelling a default can take only from 3.13 on
DTs = TypeVarTuple("DTs", default=next(iter(tuple[int, ...])))


def relay(*args: DP.args, **kwargs: DP.kwargs) -> None:
    """
    Relay the arguments.

    :param args: positional
    :param kwargs: keyword
    """


class Legacy(Generic[DefaultT, DP, *DTs]):
    """Generic the pre-PEP 695 way."""

    def first(self) -> DefaultT:
        """Return the first."""
        raise NotImplementedError


DPath = TypeVar("DPath", default=Path)
DPathP = ParamSpec("DPathP", default=[Path])
DPathTs = TypeVarTuple("DPathTs", default=next(iter(tuple[Path, ...])))


class PathDefaults(Generic[DPath, DPathP, *DPathTs]):
    """Generic over type parameters defaulting to an imported class."""


LeftT = TypeVar("LeftT")


def loose(value: LeftT) -> LeftT:  # ruff:ignore[non-pep695-generic-function]  # no signature declares LeftT
    """Use a type variable no signature declares."""
    return value


def plain(value: int) -> int:
    """Not generic."""
    return value


ErrorT = TypeVar("ErrorT")


class Box(Generic[ErrorT]):  # ruff:ignore[non-pep695-generic-class]  # the pre-PEP 695 way is the case under test
    """Generic the pre-PEP 695 way, with members its subclasses inherit."""

    def get(self, default: ErrorT) -> ErrorT:
        """
        Return the content.

        :param default: returned when empty
        """
        raise NotImplementedError


class IntBox(Box[int]):
    """Binds the type parameter of its base."""


class Listing[CellT](Box[list[CellT]]):
    """Fills the type parameter of its base with a list of its own type parameter."""


class IntListing(Listing[int]):
    """Picks int for a base that binds the type parameter of its own base."""


class IntStack(Stack[int]):
    """Binds the type parameter of a PEP 695 base."""


class Restack[ValueT](Stack[ValueT]):
    """Passes a type parameter of its own on to its base."""


class Pool[ItemT]:
    """
    Holds the members its subclasses inherit, one annotated in its body and one overloaded.

    :ivar size: the member count
    """

    size: ItemT

    @overload
    def take(self, key: ItemT) -> ItemT: ...
    @overload
    def take(self, key: bytes) -> bytes: ...
    def take(self, key: ItemT | bytes) -> ItemT | bytes:
        """Take one."""
        raise NotImplementedError


class IntPool(Pool[int]):
    """
    Fixes the type parameter of its PEP 695 base to int.

    :ivar size: how many it holds
    """


class Crate(Generic[ErrorT]):  # ruff:ignore[non-pep695-generic-class]  # the pre-PEP 695 way is the case under test
    """
    Holds the members its subclasses inherit the pre-PEP 695 way.

    :ivar size: the member count
    """

    size: ErrorT

    @overload
    def take(self, key: ErrorT) -> ErrorT: ...
    @overload
    def take(self, key: bytes) -> bytes: ...
    def take(self, key: ErrorT | bytes) -> ErrorT | bytes:
        """Take one."""
        raise NotImplementedError


class IntCrate(Crate[int]):
    """
    Fixes the type parameter of its pre-PEP 695 base to int.

    :ivar size: how many it holds
    """


class Readable(Protocol):
    """A protocol that is not runtime checkable."""

    def read(self) -> bytes: ...


class File(Readable):
    """Inherits its constructor from a protocol that is not runtime checkable."""


class Feed[ItemT](Protocol):
    """A generic protocol that is not runtime checkable."""

    def pull(self) -> ItemT: ...


class IntFeed(Feed[int]):
    """Gives int to the type parameter of a protocol that is not runtime checkable."""


class Sink[ItemT](ABC):
    """An abstract base class others register with."""

    def put(self) -> ItemT:
        """Put one."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None: ...


class Registered:
    """Counts as a subclass of the abstract base class without deriving from it."""


Sink.register(Registered)


class IntSink(Registered, Sink[int]):
    """Lists a base registered with its abstract base class before binding the type parameter of that class."""

    def close(self) -> None:
        """Close it."""


class Shelf[ItemT]:
    """Holds a member overloaded with a type parameter of its own."""

    @overload
    def take[TextT: str](self, key: TextT) -> list[TextT]: ...
    @overload
    def take(self, key: int) -> ItemT: ...
    def take(self, key: str | int) -> list[str] | ItemT:
        """Take one."""
        raise NotImplementedError


if version_info >= (4,):

    @overload
    def pick[KeyT: int](key: KeyT) -> list[KeyT]: ...
    @overload
    def pick(key: str) -> str: ...


def pick(key: int | str) -> list[int] | str:
    """Pick one, with overloads behind a version check no interpreter passes, so typing holds no record of them."""
    raise NotImplementedError


class Forwarding:
    """Forwards its annotations to the object it wraps."""

    @property
    def __annotations__(self) -> dict[str, Any]:  # ruff:ignore[bad-dunder-method-name]  # the case under test  # simplint: ignore[imprecise-annotation]  # the case under test
        return {}

    def unwrap(self) -> int:
        """Return the wrapped object."""
        raise NotImplementedError
