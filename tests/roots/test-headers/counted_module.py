"""Globals whose annotations record each evaluation."""

from __future__ import annotations

EVALUATIONS: list[str] = []


def counted(kind: type) -> type:
    EVALUATIONS.append(kind.__name__)
    return kind


FIRST: counted(int) = 1
"""The first."""

SECOND: int = 2
"""The second."""

THIRD: int = 3
"""The third."""
