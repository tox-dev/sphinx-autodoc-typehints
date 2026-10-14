"""Members whose headers show a type."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from decimal import Decimal

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
