from __future__ import annotations

from typing import Annotated, NotRequired, Required, TypedDict

from typing_extensions import Doc
from typing_extensions import TypedDict as ExtensionsTypedDict


class Movie(TypedDict, total=False):
    """A movie."""

    title: Required[str]
    year: int
    rating: NotRequired[float]
    note: Annotated[str, Doc("a note")]


class Closed(ExtensionsTypedDict, closed=True):
    """Closed."""

    name: str


class ClosedChild(Closed):
    """Inherits being closed."""


class Reopened(ExtensionsTypedDict, closed=False):
    """Says it is open."""


class Extra(ExtensionsTypedDict, extra_items=int):
    """
    Typed extra items.

    :Extra items: counts, documented by hand
    """


class ExtraUnstated(ExtensionsTypedDict, extra_items=int):
    """Typed extra items."""


class Plain:
    """Not a typed dict."""

    year: int
