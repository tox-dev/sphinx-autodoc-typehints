from __future__ import annotations

from ast import AsyncFunctionDef, FunctionDef, parse
from sys import version_info
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import fixture, mark, param

from sphinx_autodoc_typehints._resolve.source import (
    annotations_as_written,
    function_annotations,
    holds_values,
    names_read,
    parameters,
    parsed_source,
    source_annotations,
    written_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from sphinx_autodoc_typehints._types import Annotation


@mark.parametrize(
    ("owner", "expected"),
    [
        param(lambda module: module.func, {"count": "int", "return": "str"}, id="function"),
        param(lambda module: module.Holder, {}, id="class"),
        param(lambda _: len, {}, id="no-source"),
    ],
)
def test_written_annotations(
    written: ModuleType, owner: Callable[[ModuleType], Callable[..., object]], expected: dict[str, str]
) -> None:
    assert written_annotations(owner(written)) == expected


@fixture(name="written")
def written_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            from __future__ import annotations

            def func(count: int, label) -> str: ...

            class Holder:
                size: int
        """)
    )


@mark.parametrize(
    "owner",
    [
        param(
            lambda make: (
                make(
                    dedent("""\
                    LAMBDA = (0,
                        lambda: 0)[1]
                """)
                ).LAMBDA
            ),
            id="code-that-does-not-parse-alone",
        ),
        param(lambda _: property(), id="no-source"),
    ],
)
def test_parsed_source_without_a_tree(
    make_module: Callable[[str], ModuleType],
    owner: Callable[[Callable[[str], ModuleType]], Callable[..., object] | property],
) -> None:
    assert parsed_source(owner(make_module)) is None


@mark.parametrize(
    ("source", "expected"),
    [
        param(
            "def greet(name: str, greeting: str) -> str: ...",
            {"name": "str", "greeting": "str", "return": "str"},
            id="basic",
        ),
        param("def f(x: int): ...", {"x": "int"}, id="no_return"),
        param("async def fetch(url: str) -> str: ...", {"url": "str", "return": "str"}, id="async"),
        param("def f(self, x: int) -> None: ...", {"x": "int", "return": "None"}, id="skips_unannotated"),
    ],
)
def test_function_annotations(source: str, expected: dict[str, str]) -> None:
    assert isinstance(node := parse(source).body[0], FunctionDef | AsyncFunctionDef)
    assert function_annotations(node) == expected


def test_parameters_in_the_order_a_call_binds_them() -> None:
    node = parse("def f(first, /, second, *args, third, **kwargs): ...").body[0]
    assert isinstance(node, FunctionDef)
    assert [parameter.arg for parameter in parameters(node)] == ["first", "second", "args", "third", "kwargs"]


@mark.parametrize(
    ("module_name", "qualname", "expected"),
    [
        # the result leaves out an annotation the branches of an if statement write in two ways
        param(lambda module: module.__name__, "", {"count": "int", "same": "int"}, id="module"),
        param(lambda module: module.__name__, "Holder", {"size": "float"}, id="class"),
        param(lambda _: "sys", "", {}, id="module-without-source"),
    ],
)
def test_source_annotations(
    annotated_module: ModuleType,
    module_name: Callable[[ModuleType], str],
    qualname: str,
    expected: dict[str, str],
) -> None:
    assert source_annotations(module_name(annotated_module), qualname) == expected


@fixture(name="annotated_module")
def annotated_module_fixture(make_module: Callable[[str], ModuleType]) -> ModuleType:
    return make_module(
        dedent("""\
            import sys

            count: int

            if sys.platform == "nowhere":
                label: bytes
                same: int
            else:
                label: str
                same: int

            class Holder:
                size: float

            def func():
                local: int = 1
        """)
    )


@mark.parametrize(
    ("source", "expected"),
    [
        param("list[Decimal]", ["list", "Decimal"], id="subscription"),
        param("*Ts", ["Ts"], id="starred"),
        param("Annotated[int, <function <lambda> at 0x1>]", [], id="repr-of-a-value"),
    ],
)
def test_names_read(source: str, expected: list[str]) -> None:
    assert list(names_read(source)) == expected


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    ("owner", "expected"),
    [
        param("func", {"value": "Decimal", "return": "None"}, id="lazy"),
        param("guarded", {"value": "Path", "return": "None"}, id="lazy-unbound-at-runtime"),
        param("Stored", {"count": int}, id="stored-without-source"),
    ],
)
def test_annotations_as_written(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], owner: str, expected: dict[str, Annotation | str]
) -> None:
    module = make_module(
        dedent("""\
            from decimal import Decimal
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from pathlib import Path

            def func(value: Decimal) -> None: ...

            def guarded(value: Path) -> None: ...

            Stored = type("Stored", (), {"__annotations__": {"count": int}})
        """)
    )
    assert annotations_as_written(getattr(module, owner)) == expected


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    "owner",
    [
        param(lambda loaded: loaded.Holder, id="class"),
        param(lambda loaded: loaded, id="module"),
    ],
)
def test_annotations_as_written_reads_the_source_of_values_autodoc_stored(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], owner: Callable[[ModuleType], type | ModuleType]
) -> None:
    module = make_module(
        dedent("""\
            from decimal import Decimal

            amount: Decimal
            holder: Holder

            class Holder:
                amount: Decimal
                holder: Holder
        """)
    )
    target = owner(module)
    # autodoc adds the types type comments give by assigning the evaluated annotations, which drops __annotate__
    target.__annotations__ = {"amount": float}
    assert annotations_as_written(target) == {"amount": "Decimal", "holder": "Holder"}


@mark.parametrize(
    ("hints", "expected"),
    [
        param({"amount": float}, True, id="values"),
        param({"amount": "float"}, False, id="strings"),
        param(None, False, id="none"),
    ],
)
def test_holds_values(hints: dict[str, Annotation | str] | None, expected: bool) -> None:
    assert holds_values(type("Holder", (), {"__annotations__": hints})) is expected


def test_holds_values_of_a_function() -> None:
    def func() -> None: ...

    func.__annotations__ = {"amount": float}
    assert holds_values(func) is False
