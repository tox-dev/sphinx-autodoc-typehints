from __future__ import annotations

import attr  # attr.s and attr.ib are the classic spelling under test
from attrs import define


@attr.s
class ClassicAttrs:
    """A class using classic attr.s style."""

    name = attr.ib(type=str)
    age = attr.ib(type=int)
    untyped = attr.ib()


@attr.s(auto_attribs=True)
class AutoAttribs:
    """A class using auto_attribs=True."""

    name: str
    age: int


@define
class ModernAttrs:
    """A class using modern attrs.define."""

    name: str
    age: int


class Outer:
    """A class with nested attrs classes to test forward reference resolution."""

    class Foo:
        """Referenced by Bar."""

    @define
    class Bar:
        """An attrs class referencing a sibling nested class."""

        foo: Outer.Foo
