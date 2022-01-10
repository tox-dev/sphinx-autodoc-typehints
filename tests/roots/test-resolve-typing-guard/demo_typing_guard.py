"""Module demonstrating imports that are type guarded"""
from __future__ import annotations

import typing
from builtins import ValueError  # handle does not have __module__
from functools import cmp_to_key  # has __module__ but cannot get module as is builtin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal
    from typing import Sequence

if typing.TYPE_CHECKING:
    from typing import AnyStr


def a(f: Decimal, s: AnyStr) -> Sequence[AnyStr | Decimal]:
    """
    Do.

    :param f: first
    :param s: second
    :return: result
    """
    return [f, s]


__all__ = [
    "a",
    "ValueError",
    "cmp_to_key",
]
