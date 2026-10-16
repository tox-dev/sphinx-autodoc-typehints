"""A submodule with its own type under the package alias's name."""

from __future__ import annotations

Count = str


def consume(value: Count) -> None:
    """Consume a value.

    :param value: the value
    """
