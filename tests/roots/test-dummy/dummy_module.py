from __future__ import annotations

from dataclasses import dataclass
from functools import singledispatch
from typing import TYPE_CHECKING, NamedTuple, Self, overload

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


class GoogleAttributes:
    """
    Class docstring.

    Attributes:
        count: the count
    """

    count: int


class NumpyParameterShadowedByAttribute:
    """
    Class docstring.

    Parameters
    ----------
    count
        the count
    """

    count: str

    def __init__(self, count: int) -> None: ...


class ClassWithOverloadedMethods:
    """Class docstring."""

    @overload
    @classmethod
    def build(cls, value: int) -> ClassWithOverloadedMethods: ...

    @overload
    @classmethod
    def build(cls, value: str) -> ClassWithOverloadedMethods: ...

    @classmethod
    def build(cls, value: int | str) -> ClassWithOverloadedMethods:
        """Build one."""

    @overload
    def convert(self, value: int) -> int: ...

    @overload
    def convert(self, value: str) -> str: ...

    def convert(self, value: int | str) -> int | str:
        """Convert value."""

    @overload
    @staticmethod
    def parse(value: int) -> int: ...

    @overload
    @staticmethod
    def parse(value: str) -> str: ...

    @staticmethod
    def parse(value: int | str) -> int | str:
        """Parse value."""


class ClassWithOverloadedInit:
    """Class docstring."""

    @overload
    def __init__(self, value: int) -> None: ...

    @overload
    def __init__(self, value: str) -> None: ...

    def __init__(self, value: int | str) -> None: ...


class DocumentedTwice:
    """
    Class docstring.

    :param first: the first
    """

    def __init__(self, first: int, second: str, third: bool) -> None:
        """
        Constructor docstring.

        :param second: the second
        """


class DocumentedTwiceThroughNew:
    """
    Class docstring.

    :param first: the first
    """

    def __new__(cls, first: int, second: str, third: bool) -> Self:
        """
        Constructor docstring.

        :param second: the second
        """


@singledispatch
def dispatch(arg: object, flag: bool = False) -> str:
    """
    Dispatch on the argument type.

    :param arg: the argument
    """
    return f"{arg}{flag}"


@dispatch.register
def _(arg: int, flag: bool = False) -> str:
    return f"{arg}{flag}"
