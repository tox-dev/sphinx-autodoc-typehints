"""Annotations subscripting a class that drops the arguments, imported only for type checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, overload

from attrs import define

if TYPE_CHECKING:
    from engines import Engine

PAIRS = [(1, 2), (3, 4)]


def compare(kind: Engine[Any] | None, spare: Engine[str] | Engine[bytes]) -> Engine[int]:
    """
    Compare.

    :param kind: optional engine of anything
    :param spare: fallback engine of text or bytes
    """
    raise NotImplementedError


def quoted(kind: "Engine[int]") -> None:  # ruff:ignore[quoted-annotation]  # a quoted annotation under test
    """
    Quoted.

    :param kind: engine named in a string
    """


@overload
def pick(kind: Engine[int]) -> int: ...
@overload
def pick(kind: Engine[str]) -> str: ...
def pick(kind: Any) -> Any:
    """Pick."""
    return kind


class Column:
    """
    A column.

    :ivar kind: column engine
    :ivar other: optional text engine
    :ivar limited: capped count
    """

    kind: Engine[Any]

    def __init__(self) -> None:
        self.other: Engine[str] | None = None
        self.limited: Annotated[int, max(PAIRS, key=lambda pair: pair[0] - pair[1])] = 1


def sliced(kind: Engine[int, 1:2]) -> None:
    """
    Sliced.

    :param kind: engine subscripted with a slice
    """


def reassigned(kind: Missing[int]) -> None:  # ruff:ignore[undefined-name]  # the source no longer evaluates
    """
    Reassigned.

    :param kind: engine whose source no longer evaluates
    """


reassigned.__annotations__ = {"kind": "Engine[int]"}


Engines = list["Engine"]


def aliased(kind: Engines) -> None:
    """
    Aliased.

    :param kind: engines behind an alias
    """


@dataclass
class Record:
    """
    A record.

    :param kind: record engine
    """

    kind: Engine[int]


@define
class Entry:
    """
    An entry.

    :param kind: entry engine
    """

    kind: Engine[int]


class Switched:
    """
    Switched.

    :ivar kind: engine that differs per branch
    :ivar same: engine both branches agree on
    """

    if PAIRS:
        kind: Engine[int]
        same: Engine[int]
    else:
        kind: Engine[str]
        same: Engine[int]


class Commented:
    """A class whose method types its parameter in a comment."""

    kind: Engine[int]

    def bind(self, kind):  # ruff:ignore[missing-type-function-argument, missing-return-type-undocumented-public-function]  # typed by the comment
        # type: (Engine[str]) -> None
        """
        Bind.

        :param kind: engine to bind
        """


class Holder[T]:
    """
    A holder.

    :ivar kind: held engine
    """

    kind: Engine[T]
