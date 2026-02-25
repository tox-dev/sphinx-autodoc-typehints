from __future__ import annotations

import attr
import attrs


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


@attrs.define
class ModernAttrs:
    """A class using modern attrs.define."""

    name: str
    age: int
