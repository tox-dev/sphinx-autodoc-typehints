"""PEP 695 aliases in the signatures of a function and of a method."""

from __future__ import annotations

from collections.abc import Callable

type IntList = list[int]
type StringOrInt = str | int
type Callback = Callable[[Callback], None]


def invoke_callback(callback: Callback) -> None:
    """Invoke a callback.

    :param callback: callback to invoke
    """


def type_alias_func(value: IntList) -> StringOrInt:
    """
    Take and return aliases.

    Parameters
    ----------
    value
        List of integers
    """


class Foo[Element]:
    """A generic class."""

    def __init__(self, thing: Element) -> None:
        """
        Store the thing.

        Parameters
        ----------
        thing
            the thing
        """


class FooStringOrInt(Foo[StringOrInt]):
    """A subclass binding the type parameter to an alias."""

    def set(self, thing: StringOrInt) -> StringOrInt:
        """
        Set the thing.

        Parameters
        ----------
        thing
            the thing
        """
