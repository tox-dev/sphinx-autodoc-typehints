"""Members whose headers show a type."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Annotated, Generic, TypedDict, TypeVar

if TYPE_CHECKING:
    from decimal import Decimal

U = TypeVar("U")

LIMIT: Annotated[int, "a cap"] = 3
"""The limit."""

RATE: Decimal | None = None
"""The rate."""


class Account:
    """An account."""

    balance: Decimal
    """The balance."""

    def __init__(self) -> None:
        self.owner: Annotated[str, "a name"] = ""
        """The owner."""

    @property
    def total(self) -> Annotated[int, "a sum"]:
        """The total."""
        return 0

    @cached_property
    def fee(self) -> Annotated[Decimal, "a charge"]:
        """The fee."""
        raise NotImplementedError

    @classmethod
    @property
    def kind(cls) -> Annotated[str, "a label"]:
        """The kind."""
        return "account"


class Proxy:
    """Hands out the property it wraps only when read from the class."""

    def __init__(self, wrapped: property) -> None:
        self.wrapped = wrapped
        self.__doc__ = wrapped.__doc__

    def __get__(self, instance: object, owner: type | None = None) -> object:
        return self.wrapped if instance is None else self.wrapped.__get__(instance, owner)


class Proxied:
    """Holds a proxied property."""

    @Proxy
    @property
    def size(self) -> Annotated[int, "a count"]:
        """The size."""
        return 0


class Vault:
    """Holds members autodoc reaches through their mangled names."""

    @property
    def __code(self) -> int:
        """The code."""
        return 0

    class __Lock:
        """A lock."""

        @property
        def pins(self) -> int:
            """The pins."""
            return 0


class Box[T]:
    """Holds a value."""

    value: T
    """The value."""

    label: tuple[T, ...] = ()
    """The label."""

    @property
    def first(self) -> T:
        """The first."""
        raise NotImplementedError


class IntBox(Box[int]):
    """Holds an integer."""


class Legacy(Generic[U]):  # ruff:ignore[non-pep695-generic-class]  # the legacy form under test
    """Holds items the legacy way."""

    items: list[U]
    """The items."""


class StrLegacy(Legacy[str]):
    """Holds strings the legacy way."""


Num = int | float

SCORE: Num = 1
"""The score."""

LOW: Num = 0
"""The lowest score."""


class Scored:
    """Something scored."""

    points: Num = 0
    """The points."""

    @property
    def best(self) -> Num:
        """The best."""
        return 0


class Totals(TypedDict):
    """Totals."""

    count: Num
    """The count."""
