"""A submodule with an alias visible only to type checkers."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    Count = str


def consume(value: Count) -> None:
    """Consume a value.

    :param value: the value
    """


@overload
def choose(value: Count) -> Count: ...


@overload
def choose(value: bytes) -> bytes: ...


def choose(value: Count | bytes) -> Count | bytes:
    """Choose a value.

    :param value: the value
    """
    return value
