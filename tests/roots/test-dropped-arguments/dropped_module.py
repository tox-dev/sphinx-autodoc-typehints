"""Annotations subscripting a class that drops the arguments, imported only for type checking."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Annotated, Any, overload

import attrs

if TYPE_CHECKING:
    from engines import Engine

PAIRS = [(1, 2), (3, 4)]


def compare(kind: Engine[Any] | None, spare: Engine[str] | Engine[bytes]) -> Engine[int]:
    """
    Compare.

    :param kind: the kind
    :param spare: the spare
    """
    raise NotImplementedError


def quoted(kind: "Engine[int]") -> None:  # ruff:ignore[quoted-annotation]  # a quoted annotation under test
    """
    Quoted.

    :param kind: the kind
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

    :ivar kind: the kind
    :ivar other: the other
    :ivar limited: the limited
    """

    kind: Engine[Any]

    def __init__(self) -> None:
        self.other: Engine[str] | None = None
        self.limited: Annotated[int, max(PAIRS, key=lambda pair: pair[0] - pair[1])] = 1


def sliced(kind: Engine[int, 1:2]) -> None:
    """
    Sliced.

    :param kind: the kind
    """


def reassigned(kind: Missing[int]) -> None:  # ruff:ignore[undefined-name]  # the source no longer evaluates
    """
    Reassigned.

    :param kind: the kind
    """


reassigned.__annotations__ = {"kind": "Engine[int]"}


Engines = list["Engine"]


def aliased(kind: Engines) -> None:
    """
    Aliased.

    :param kind: the kind
    """


@dataclasses.dataclass
class Record:
    """
    A record.

    :param kind: the kind
    """

    kind: Engine[int]


@attrs.define
class Entry:
    """
    An entry.

    :param kind: the kind
    """

    kind: Engine[int]


class Switched:
    """
    Switched.

    :ivar kind: the kind
    :ivar same: the same
    """

    if PAIRS:
        kind: Engine[int]
        same: Engine[int]
    else:
        kind: Engine[str]
        same: Engine[int]
