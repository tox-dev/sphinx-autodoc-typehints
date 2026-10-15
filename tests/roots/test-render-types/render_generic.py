"""Generic and recursive PEP 695 aliases."""

from __future__ import annotations

type Pair[Element] = tuple[Element, Element]
type RecType = int | list[RecType]
type RecPair[Element] = Element | list[RecPair[Element]]


class Undocumented:
    """A class no document describes."""


def pair_func(value: Pair[int]) -> None:
    """
    Take a pair.

    Parameters
    ----------
    value
        a pair
    """


def take_pair(value: Pair[Undocumented]) -> None:
    """
    Take a pair of an undocumented class.

    Parameters
    ----------
    value
        the pair
    """


def rec_func(some_param: RecType) -> None:
    """
    Take a recursive alias.

    Parameters
    ----------
    some_param
        some description
    """


def rec_pair_func(some_param: RecPair[int]) -> None:
    """
    Take a recursive generic alias.

    Parameters
    ----------
    some_param
        some description
    """
