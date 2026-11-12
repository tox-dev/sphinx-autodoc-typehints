"""A package re-exporting the aliases a private module defines."""

from __future__ import annotations

from ._priv import ExtAlias, ExtPair

__all__ = [
    "ExtAlias",
    "ExtPair",
]
