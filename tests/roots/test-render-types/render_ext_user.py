"""A module using the aliases of another package."""

from __future__ import annotations

from render_ext import ExtAlias, ExtPair


def ext_alias_func(value: ExtAlias) -> ExtAlias:
    """
    Take and return an alias of another package.

    Parameters
    ----------
    value
        the value
    """


def ext_pair_func(value: ExtPair[int]) -> None:
    """
    Take a generic alias of another package.

    Parameters
    ----------
    value
        a pair
    """


__all__ = [
    "ExtAlias",
    "ExtPair",
    "ext_alias_func",
    "ext_pair_func",
]
