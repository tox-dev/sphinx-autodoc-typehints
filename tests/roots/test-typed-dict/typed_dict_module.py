from __future__ import annotations

from typing import Annotated, ClassVar, Generic, Literal, NotRequired, Required, TypedDict, TypeVar, Unpack

from typing_extensions import Doc, ReadOnly
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
    """Inherits closed=True from its base."""


class Reopened(ExtensionsTypedDict, closed=False):
    """Says it is open."""


class Extra(ExtensionsTypedDict, extra_items=int):
    """
    Typed extra items.

    :Extra items: integer counts documented by hand
    """


class ExtraUnstated(ExtensionsTypedDict, extra_items=int):
    """Typed extra items."""


class ExtraLiteral(ExtensionsTypedDict, extra_items=Literal["a", "b"]):
    """Literal extra items."""


class Shape(ExtensionsTypedDict):
    """A shape."""

    size: ReadOnly[int | str]
    label: ReadOnly[NotRequired[str]]


class Square(Shape):
    """Narrows the keys of its base."""

    size: ReadOnly[int]
    label: ReadOnly[Required[str]]


class Outline(Shape):
    """Inherits the keys of its base as they are."""


class Tile(Square, Outline):
    """Reads the keys from the first base in the MRO declaring each."""


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


def draw(**kwargs: Unpack[Square]) -> None:
    """
    Draw.

    :keyword size: the size
    """


class Raising:
    """Metadata whose comparison raises."""

    __hash__ = None

    def __eq__(self, other: object) -> bool:
        msg = "cannot compare"
        raise TypeError(msg)


class Ambiguous:
    """Metadata comparing to a value without a truth value, as a numpy array does."""

    __hash__ = None

    def __eq__(self, other: object) -> Ambiguous:
        return self

    def __bool__(self) -> bool:
        msg = "the truth value is ambiguous"
        raise ValueError(msg)


class Measured(TypedDict):
    """Keys with metadata that breaks comparison."""

    width: Annotated[int, Raising()]
    height: Annotated[int, Ambiguous()]


class Box(Measured):
    """Inherits keys with metadata that breaks comparison."""

    depth: float


def pack(**kwargs: Unpack[Box]) -> None:
    """
    Pack.

    :keyword width: the width
    :keyword height: the height
    """


class Counted:
    """Metadata counting how often the annotations holding it run."""

    created: ClassVar[int] = 0

    def __init__(self) -> None:
        Counted.created += 1


class Root(TypedDict):
    """The base of a hierarchy of diamonds."""

    name: Annotated[str, Counted()]


Diamond = Root
for level in range(10):
    # each level is a diamond over the one below, so 2**level paths lead to a base
    Diamond = type(Root)(
        f"Diamond{level}",
        (type(Root)(f"Left{level}", (Diamond,), {}), type(Root)(f"Right{level}", (Diamond,), {})),
        {"__module__": __name__},
    )


def nest(**kwargs: Unpack[Diamond]) -> None:
    """
    Nest.

    :keyword name: the name
    """


class Unstated:
    """Leaves a TypedDict neither closed nor open, counting each lookup of that state."""

    asked: ClassVar[int] = 0

    def __get__(self, instance: object, owner: type) -> None:
        Unstated.asked += 1


Spread = Root
for level in range(10):
    # each level is a diamond over the one below, so 2**level paths lead to a base
    sides = [type(Root)(f"Spread{side}{level}", (Spread,), {}) for side in ("Left", "Right")]
    Spread = type(Root)("Spread", tuple(sides), {"__module__": __name__, "__doc__": "A diamond of diamonds."})
    for spread in (*sides, Spread):
        spread.__closed__ = Unstated()
