from __future__ import annotations

from typing import Annotated, Generic, NotRequired, Required, TypedDict, TypeVar, Unpack

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


class Options[T](TypedDict):
    """Generic over the type of its keys."""

    limit: T
    extra: NotRequired[list[T]]


class IntOptions(Options[int]):
    """Binds the type parameter of its base."""


U = TypeVar("U")


class LegacyOptions(TypedDict, Generic[U]):  # ruff:ignore[non-pep695-generic-class]  # the legacy form under test
    """Generic over the type of its keys the pre-PEP 695 way."""

    limit: U


class StrOptions(LegacyOptions[str]):
    """Binds the type parameter of its base."""


def configure(**kwargs: Unpack[Options[int]]) -> None:
    """
    Configure.

    :keyword limit: the limit
    """


def configure_legacy(**kwargs: Unpack[LegacyOptions[str]]) -> None:
    """
    Configure the pre-PEP 695 way.

    :keyword limit: the limit
    """
