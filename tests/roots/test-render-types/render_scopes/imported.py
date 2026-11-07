"""A submodule importing the package alias."""

from __future__ import annotations

from render_scopes import Count

__all__ = ["Count"]


def consume(value: Count) -> None:
    """Consume a value.

    :param value: the value
    """
