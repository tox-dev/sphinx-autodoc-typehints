"""A package re-exporting the aliases a private module defines."""

from __future__ import annotations  # simplint: ignore[SMP407]  # tests read the names from the package itself

from ._priv import ExtAlias, ExtPair  # simplint: ignore[SMP407]  # tests read the names from the package itself

__all__ = [  # simplint: ignore[SMP407]  # tests read the names from the package itself
    "ExtAlias",
    "ExtPair",
]
