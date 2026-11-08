"""Globals whose annotations record each evaluation."""

from __future__ import annotations

from typing import Final

EVALUATIONS: Final[list[str]] = []


def counted(kind: type) -> type:
    EVALUATIONS.append(kind.__name__)
    return kind


FIRST: Final[counted(int)] = 1
"""The first."""

SECOND: Final[int] = 2
"""The second."""

THIRD: Final[int] = 3
"""The third."""
