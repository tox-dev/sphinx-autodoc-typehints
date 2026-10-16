"""Aliases whose values need the names a TYPE_CHECKING block imports."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

type Plain = int | Sequence[str]
type Wrapped[Element] = Sequence[Element]
type Bounded[Element: Sequence[str]] = list[Element]
