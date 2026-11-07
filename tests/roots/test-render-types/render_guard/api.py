"""Functions naming the aliases through a TYPE_CHECKING import."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._types import Bounded, Plain, Wrapped


def plain(value: Plain | None) -> None:
    """
    Accept an alias.

    Parameters
    ----------
    value
        an argument.
    """


def wrapped(value: Wrapped[int]) -> None:
    """
    Use a generic alias.

    Parameters
    ----------
    value
        a sequence of them.
    """


def bounded(value: Bounded) -> None:
    """
    Take an alias with a bounded type parameter.

    Parameters
    ----------
    value
        a list of them.
    """
