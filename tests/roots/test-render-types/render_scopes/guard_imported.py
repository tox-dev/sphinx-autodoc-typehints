"""A submodule importing the package alias only for type checkers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from render_scopes import Count


def consume(value: Count) -> None:
    """Consume a value.

    :param value: the value
    """
