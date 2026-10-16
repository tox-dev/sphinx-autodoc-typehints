from __future__ import annotations

from textwrap import dedent
from warnings import catch_warnings

from typing_extensions import deprecated


@deprecated("Use fresh() instead, *really*.")
def stale(value: int) -> int:
    """
    Do the stale thing.

    More words.
    """
    return value


@deprecated(
    dedent("""\
        Use Fresh.
        It is faster.""")
)
class Stale:
    """A stale class."""


# subclassing warns, and the tests turn warnings into errors
with catch_warnings(action="ignore", category=DeprecationWarning):

    class Child(Stale):  # ty: ignore[deprecated]  # the case under test
        """Not deprecated itself."""


@deprecated("Use fresh() instead.")
def noted(value: int) -> int:
    """
    Do the noted thing.

    .. deprecated:: 2.0
       Use fresh().
    """
    return value


@deprecated("Use fresh() instead.")
def shown(value: int) -> int:
    """
    Use it like this::

        shown(1)
    """
    return value
