from __future__ import annotations

from dataclasses import dataclass


def undocumented_function(x: int) -> str:
    """Hi"""

    return str(x)


def undocumented_function_with_defaults(x: int, y: str = "hello") -> str:
    """Hi"""

    return str(x) + y


@dataclass
class DataClass:
    """Class docstring."""

    x: int
