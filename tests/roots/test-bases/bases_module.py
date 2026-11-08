from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeVar

from bases_dependency import Mocked

ItemT = TypeVar("ItemT")


class Plain: ...


class Child(Plain): ...


class Open[ItemT]: ...


class Pairs(Mapping[str, int]): ...


class Stack[BaseT]: ...


class Sub[BaseT](Stack[BaseT]): ...


class Reader(Protocol): ...


class FromMock(Mocked): ...


type Hidden = bytes | None


class UsesHidden(Stack[Hidden]): ...
