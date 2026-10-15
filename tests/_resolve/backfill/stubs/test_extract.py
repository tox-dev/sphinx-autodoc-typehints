from __future__ import annotations

from ast import parse, unparse
from operator import attrgetter
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import FixtureRequest, mark, param

from sphinx_autodoc_typehints._resolve.backfill.stubs.extract import (
    find_ast_node,
    stub_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from _resolve.conftest import MakeStubbedModule


@mark.parametrize(
    ("source", "parts", "expected"),
    [
        param("def foo(x: int) -> str: ...", ["foo"], "def foo(x: int) -> str:", id="top_level_function"),
        param(
            dedent("""\
                class Outer:
                    class Inner:
                        def method(self) -> None: ...
            """),
            ["Outer", "Inner", "method"],
            "def method(self) -> None:",
            id="nested_class_method",
        ),
        param(
            dedent("""\
                class Foo:
                    x: int
            """),
            ["Foo"],
            "class Foo:",
            id="class",
        ),
        param("def foo(): ...", ["bar"], None, id="missing"),
    ],
)
def test_find_ast_node(source: str, parts: list[str], expected: str | None) -> None:
    node = find_ast_node(parse(source).body, parts)
    assert (None if node is None else unparse(node).splitlines()[0]) == expected


@mark.parametrize(
    ("fixture", "owner", "expected"),
    [
        param("stub_mod", attrgetter("greet"), {"name": "str", "greeting": "str", "return": "str"}, id="function"),
        param(
            "stub_mod", attrgetter("Calculator.Inner.process"), {"data": "bytes", "return": "bytes"}, id="nested_class"
        ),
        param("stub_mod", attrgetter("Converter.__new__"), {"output": "str", "return": "Converter"}, id="class_new"),
        param("stub_mod", attrgetter("Calculator"), {"value": "int"}, id="class"),
        param("stub_mod", attrgetter("fetch"), {"url": "str", "return": "str"}, id="async_function"),
        param(
            "stub_mod", attrgetter("transform"), {"value": "Sequence[int]", "return": "list[str]"}, id="typing_imports"
        ),
        param("stub_mod", attrgetter("version_gated"), {"value": "int", "return": "bytes"}, id="version-gated"),
        param(
            "stub_mod", attrgetter("overloaded"), {"value": "int | str", "return": "int | str"}, id="overloads-merged"
        ),
        param("stub_mod", attrgetter("extras_only"), {"value": "float", "return": "float"}, id="undecidable-condition"),
        param("stub_mod", attrgetter("Box.size.fget"), {"return": "int"}, id="property-with-setter-and-deleter"),
        param("stub_mod", lambda _: test_find_ast_node, {}, id="no-stub"),
        param(
            "native_pkg",
            attrgetter("warc.parse"),
            {"data": "bytes", "return": "Iterator[WarcRecord]"},
            id="native-submodule",
        ),
    ],
)
def test_stub_annotations(
    request: FixtureRequest,
    fixture: str,
    owner: Callable[[ModuleType], Callable[..., object]],
    expected: dict[str, str],
) -> None:
    assert stub_annotations(owner(request.getfixturevalue(fixture))) == expected


@mark.parametrize(
    ("stub", "owner", "expected"),
    [
        param(
            dedent("""\
                class Holder:
                    size: int
                    self.label: str
            """),
            "Holder",
            {"size": "int"},
            id="class-body-names-only",
        ),
        param(
            dedent("""\
                from typing import overload

                @overload
                def pick(value: int) -> int: ...
                @overload
                def pick(value: str) -> str: ...
                def pick(value: object) -> object: ...
            """),
            "pick",
            {"value": "object", "return": "object"},
            id="implementation-over-overloads",
        ),
        param(
            dedent("""\
                @overload
                def pick(value: int, extra: int) -> int: ...
                @overload
                def pick(value: str) -> str: ...
            """),
            "pick",
            {"value": "int | str", "return": "int | str"},
            id="overloads-sharing-some-parameters",
        ),
        param("pick: int", "pick", {}, id="variable-named-like-the-function"),
        param("def pick(value: int) -> int: ...", "Holder", {}, id="missing"),
        param(
            dedent("""\
                class Runner:
                    def __call__(self) -> None: ...

                runner: Runner
            """),
            "runner",
            {},
            id="callable-instance-without-a-qualname",
        ),
    ],
)
def test_stub_annotations_of_a_written_stub(
    make_stubbed_module: MakeStubbedModule, stub: str, owner: str, expected: dict[str, str]
) -> None:
    module = make_stubbed_module(
        dedent("""\
            class Holder: ...

            def pick(value): ...

            class Runner:
                def __call__(self) -> None: ...

            runner = Runner()
        """),
        stub,
    )
    assert stub_annotations(getattr(module, owner)) == expected
