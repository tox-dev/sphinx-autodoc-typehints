from __future__ import annotations

from dataclasses import dataclass
from functools import singledispatch
from typing import TYPE_CHECKING, Annotated, NamedTuple, Self, TypedDict, TypeVar, Union, Unpack, overload

from typing_extensions import Doc, deprecated

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


class DocumentedTwiceWithUnderscore:
    r"""
    Class docstring.

    :param type\_: the type
    """

    def __init__(self, type_: str, count: int) -> None:
        """
        Constructor docstring.

        :param count: the count
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


def versioned(a: int) -> int:
    """
    Do it.

    :param a: the a

    .. versionadded:: 1.0
    """
    return a


ConfiguredAlias = Union[int, str]  # documented as data, not a type statement
"""An alias the configuration maps."""


def takes_configured_alias(x: ConfiguredAlias) -> None:
    """
    Take it.

    :param x: the x
    """


Bounded = TypeVar("Bounded", bound=int)


# a module-level type variable shows in full, as no signature declares it
def bounded(value: Bounded) -> Bounded:  # ruff:ignore[non-pep695-generic-function]
    """
    Take a bounded type parameter.

    :param value: the value
    """
    return value


def unresolvable(value: Undefined) -> None:  # ruff:ignore[undefined-name]  # ty: ignore[unresolved-reference]  # the case under test
    """
    Name something undefined.

    :param value: the value
    """


class _TwiceOptions(TypedDict):
    verbose: bool


class KeysTwice:
    """Class docstring."""

    def __init__(self, **kwargs: Unpack[_TwiceOptions]) -> None:
        """Constructor docstring."""


class OverloadedTwice:
    """Class docstring."""

    @overload
    def __init__(self, a: int) -> None: ...

    @overload
    def __init__(self, a: str) -> None: ...

    def __init__(self, a: int | str) -> None:
        """Constructor docstring."""


class DescribedTwice:
    """Class docstring."""

    def __init__(self, a: Annotated[int, Doc("the a")]) -> None:
        """Constructor docstring."""


@deprecated("use something else")
class DeprecatedTwice:
    """Class docstring."""

    def __init__(self, a: int) -> None:
        """
        Constructor docstring.

        :param a: the a
        """


@overload
def overloaded(value: int) -> DataClass: ...


@overload
def overloaded(value: str, *, strict=...) -> MyNamedTuple: ...  # ruff:ignore[missing-type-function-argument]  # left untyped on purpose


def overloaded(value, *, strict=False):
    """Overloaded function."""


@overload
def overloaded_opt_out(value: int) -> int: ...


@overload
def overloaded_opt_out(value: str) -> str: ...


def overloaded_opt_out(value: int | str) -> int | str:
    """
    :no-overloads:

    Opted out.
    """


@overload
def overloaded_generic[T: int](value: T) -> T: ...


@overload
def overloaded_generic[T: int](value: list[T]) -> T: ...


def overloaded_generic[T: int](value: T | list[T]) -> T:
    """Generic function."""


class ClassWithOverloadedInitOptingOut:
    """Class docstring."""

    @overload
    def __init__(self, value: int) -> None: ...

    @overload
    def __init__(self, value: str) -> None: ...

    def __init__(self, value: int | str) -> None:
        """
        :no-overloads:

        Constructor docstring.
        """


@overload
def overloaded_options(value: int) -> int: ...


@overload
def overloaded_options(value: str, *, flag: bool = ...) -> str: ...


def overloaded_options(value, **options):
    """Overloaded function taking options."""
