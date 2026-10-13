from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FunctionType


def call(callback: FunctionType) -> None:
    """
    Call it.

    :param callback: the callback
    """
