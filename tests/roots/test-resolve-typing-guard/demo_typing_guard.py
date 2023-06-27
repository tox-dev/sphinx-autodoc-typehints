"""Module demonstrating imports that are type guarded"""
from __future__ import annotations

import typing
from builtins import ValueError  # handle does not have __module__
from functools import cmp_to_key  # has __module__ but cannot get module as is builtin
from typing import TYPE_CHECKING

from demo_typing_guard_dummy import AnotherClass

if TYPE_CHECKING:
    from decimal import Decimal
    from typing import Sequence


if typing.TYPE_CHECKING:
    from typing import AnyStr


if TYPE_CHECKING:  # bad import
    from functools import missing  # noqa: F401


def a(f: Decimal, s: AnyStr) -> Sequence[AnyStr | Decimal]:
    """
    Do.

    :param f: first
    :param s: second
    :return: result
    """
    return [f, s]


class SomeClass:
    """This class do something."""

    def create(self, item: Decimal) -> None:
        """
        Create something.

        :param item: the item in question
        """

    if TYPE_CHECKING:  # Classes doesn't have `__globals__` attribute

        def guarded(self, item: Decimal) -> None:
            """
            Guarded method.

            :param item: some item
            """


__all__ = [
    "a",
    "ValueError",
    "cmp_to_key",
    "SomeClass",
    "AnotherClass",
]
