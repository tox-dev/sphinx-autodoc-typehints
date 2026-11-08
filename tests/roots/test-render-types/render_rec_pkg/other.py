"""The submodule defining a recursive alias."""

from __future__ import annotations

type RecType = int | list[RecType]
"""A recursive type alias."""  # simplint: ignore[SMP006]  # autodoc reads the doc of a type statement from this string
