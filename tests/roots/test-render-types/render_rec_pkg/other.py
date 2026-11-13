"""The submodule defining a recursive alias."""

from __future__ import annotations

type RecType = int | list[RecType]
"""A recursive type alias."""  # simplint: ignore[string-statement-comment]  # autodoc reads this docstring
