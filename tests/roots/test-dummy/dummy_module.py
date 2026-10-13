from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple, overload

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
