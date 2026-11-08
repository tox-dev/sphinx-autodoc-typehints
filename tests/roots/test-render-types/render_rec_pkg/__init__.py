"""A package using a recursive alias of its submodule."""

from __future__ import annotations  # simplint: ignore[SMP407]  # tests read the names from the package itself

from .other import RecType  # simplint: ignore[SMP407]  # tests read the names from the package itself


def some_func(some_param: RecType) -> None:  # simplint: ignore[SMP407]  # tests read the names from the package itself
    """
    Take the recursive alias.

    Parameters
    ----------
    some_param
        some description
    """


__all__ = [  # simplint: ignore[SMP407]  # tests read the names from the package itself
    "RecType",
    "some_func",
]
