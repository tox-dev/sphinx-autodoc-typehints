from __future__ import annotations

from dataclasses import dataclass
from functools import singledispatch
from typing import TYPE_CHECKING, Annotated, NamedTuple, Self, TypedDict, TypeVar, Union, Unpack, overload

from typing_extensions import Doc, deprecated

if TYPE_CHECKING:
    from pathlib import Path


def undocumented_function(value: int) -> str:
    """Hi"""

    return str(value)


def undocumented_function_with_defaults(value: int, other: str = "hello") -> str:
    """Hi"""

    return str(value) + other


class MyNamedTuple(NamedTuple):
    """A named tuple."""

    value: int
    other: str = "hello"


class MyNamedTupleWithPath(NamedTuple):
    """A named tuple with non-builtin types."""

    path: Path
    version: str


@dataclass(frozen=True, slots=True)  # simplint: ignore[SMP703]  # the docs assert the positional constructor signature
class DataClass:
    """Class docstring."""

    value: int


class GoogleAttributes:
    """
    Class docstring.

    Attributes:
        count: the count
    """

    count: int


class GoogleAttributesBesideField:
    """
    Class docstring.

    :ivar written: written as a field

    Attributes:
        count: the count
    """

    count: int
    written: str


class GoogleInitAttributes:
    """
    Class docstring.

    Attributes:
        location: the location
    """

    def __init__(self) -> None:
        self.location: list[Path] = []


class NumpyInitAttributes:
    """
    Class docstring.

    Attributes
    ----------
    location
        the location
    """

    def __init__(self) -> None:
        self.location: list[Path] = []


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


#: An alias.
DocumentedTwiceAlias = DocumentedTwice


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
def dispatch(arg: object, flag: bool = False) -> str:  # simplint: ignore[SMP602]  # the docs render object as written
    """
    Dispatch on the argument type.

    :param arg: the argument
    """
    return f"{arg}{flag}"


@dispatch.register
def _(arg: int, flag: bool = False) -> str:
    return f"{arg}{flag}"


def versioned(item: int) -> int:
    """
    Do it.

    :param item: the a

    .. versionadded:: 1.0
    """
    return item


ConfiguredAlias = Union[int, str]  # documented as data, not a type statement
"""An alias the configuration maps."""


def takes_configured_alias(value: ConfiguredAlias) -> None:
    """
    Take it.

    :param value: the x
    """


Bounded = TypeVar("Bounded", bound=int)


# a module-level type variable no signature declares
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
    def __init__(self, item: int) -> None: ...

    @overload
    def __init__(self, item: str) -> None: ...

    def __init__(self, item: int | str) -> None:
        """Constructor docstring."""


class DescribedTwice:
    """Class docstring."""

    def __init__(self, item: Annotated[int, Doc("the a")]) -> None:
        """Constructor docstring."""


@deprecated("use something else")
class DeprecatedTwice:
    """Class docstring."""

    def __init__(self, item: int) -> None:
        """
        Constructor docstring.

        :param item: the a
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
def overloaded_generic[ItemT: int](value: ItemT) -> ItemT: ...


@overload
def overloaded_generic[ItemT: int](value: list[ItemT]) -> ItemT: ...


def overloaded_generic[ItemT: int](value: ItemT | list[ItemT]) -> ItemT:
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
