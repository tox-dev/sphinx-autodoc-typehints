"""
Module docstring.

Attributes:
    location: the location
    level: the level
    written (str): written by hand
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

location: list[Path] = []
level: Final[int] = 0
written: int = 0
