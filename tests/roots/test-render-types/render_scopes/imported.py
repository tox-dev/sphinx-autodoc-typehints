"""A submodule importing the package alias."""

from __future__ import annotations

from . import Count


def consume(value: Count) -> None:
    """Consume a value.

    :param value: the value
    """


__all__ = [
    "Count",
]
