"""A package using a recursive alias of its submodule."""

from __future__ import annotations

from render_rec_pkg.other import RecType


def some_func(some_param: RecType) -> None:
    """
    Take the recursive alias.

    Parameters
    ----------
    some_param
        some description
    """


__all__ = [
    "RecType",
    "some_func",
]
