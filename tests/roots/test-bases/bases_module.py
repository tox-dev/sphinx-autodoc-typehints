from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeVar

from bases_dependency import Mocked

T = TypeVar("T")


class Plain: ...


class Child(Plain): ...


class Open[T]: ...


class Pairs(Mapping[str, int]): ...


class Stack[X]: ...


class Sub[X](Stack[X]): ...


class Reader(Protocol): ...


class FromMock(Mocked): ...


type Hidden = bytes | None


class UsesHidden(Stack[Hidden]): ...
