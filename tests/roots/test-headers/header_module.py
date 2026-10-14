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
