from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from operator import attrgetter
from sys import version_info
from textwrap import dedent
from types import GenericAlias, ModuleType
from typing import TYPE_CHECKING, Union, get_args, get_origin
from warnings import catch_warnings, simplefilter

from pytest import MonkeyPatch, mark, param
from sphinx import addnodes
from sphinx.pycode import ModuleAnalyzer

from sphinx_autodoc_typehints._resolve import get_all_type_hints
from sphinx_autodoc_typehints._resolve.evaluate import type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

    from _resolve.conftest import MakeSubclassOfAGuardedBase


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. autofunction:: dropped_module.compare",
            '* **kind** ("Engine"["Any"] | "None") -- optional engine of anything',
            id="parameter",
        ),
        param(
            ".. autofunction:: dropped_module.compare",
            '* **spare** ("Engine"["str"] | "Engine"["bytes"]) -- fallback engine of text or bytes',
            id="union-the-dropped-arguments-told-apart",
        ),
        param(".. autofunction:: dropped_module.compare", '"Engine"["int"]', id="return"),
        param(
            ".. autofunction:: dropped_module.quoted",
            '**kind** ("Engine"["int"]) -- engine named in a string',
            id="quoted",
        ),
        param(".. autofunction:: dropped_module.pick", '* **kind** ("Engine"["str"]) → "str"', id="overload"),
        param(
            ".. autoclass:: dropped_module.Column",
            '* **kind** ("Engine"["Any"]) -- column engine',
            id="class-body-ivar",
        ),
        param(
            ".. autoclass:: dropped_module.Column",
            '* **other** ("Engine"["str"] | "None") -- optional text engine',
            id="instance-ivar",
        ),
        param(
            ".. autoclass:: dropped_module.Column",
            '* **limited** ("int") -- capped count',
            id="instance-ivar-subscripting-in-a-nested-scope",
        ),
        param(
            ".. autoclass:: dropped_module.Record", '**kind** ("Engine"["int"]) -- record engine', id="dataclass-field"
        ),
        param(".. autoclass:: dropped_module.Entry", '**kind** ("Engine"["int"]) -- entry engine', id="attrs-field"),
        param(
            ".. autoclass:: dropped_module.Holder",
            '**kind** ("Engine"["T"]) -- held engine',
            id="class-body-ivar-of-a-type-parameter",
        ),
        param(
            ".. autoclass:: dropped_module.Switched",
            '* **same** ("Engine"["int"]) -- engine both branches agree on',
            id="class-body-ivar-written-alike-in-each-branch",
        ),
        param(
            ".. autofunction:: dropped_module.sliced",
            '**kind** ("Engine") -- engine subscripted with a slice',
            id="slice-a-call-cannot-take",
        ),
        param(
            ".. autofunction:: dropped_module.reassigned",
            '**kind** ("Engine") -- engine whose source no longer evaluates',
            id="source-that-no-longer-evaluates",
        ),
        param(
            ".. autofunction:: dropped_module.aliased",
            '**kind** ("list"["Engine"]) -- engines behind an alias',
            id="alias-holding-a-forward-reference",
        ),
        param(
            ".. autoclass:: dropped_module.Switched",
            '* **kind** ("Engine") -- engine that differs per branch',
            id="branches-differ",
        ),
        param(
            ".. automethod:: dropped_module.Commented.bind",
            '**kind** ("Engine") -- engine to bind',
            id="method-typed-by-a-comment-beside-a-class-attribute",
        ),
    ],
)
@mark.sphinx("text", testroot="dropped-arguments")
@mark.usefixtures("wide_text_output")
def test_field_type_keeps_the_arguments_only_the_source_gives(build_text: BuildText, rst: str, expected: str) -> None:
    assert expected in [line.strip() for line in build_text(rst).splitlines()]


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. autofunction:: dropped_module.compare",
            "dropped_module.compare(kind: Engine[Any] | None, spare: Engine[str] | Engine[bytes]) -> Engine[int]",
            marks=mark.sphinx(confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True}),
            id="function",
        ),
        param(
            ".. autoclass:: dropped_module.Record",
            "class dropped_module.Record(kind: Engine[int])",
            marks=mark.sphinx(confoverrides={"typehints_use_signature": True}),
            id="generated-init-of-a-dataclass",
        ),
        param(
            ".. autoclass:: dropped_module.Entry",
            "class dropped_module.Entry(kind: Engine[int])",
            marks=mark.sphinx(confoverrides={"typehints_use_signature": True}),
            id="generated-init-of-an-attrs-class",
        ),
    ],
)
@mark.sphinx("text", testroot="dropped-arguments")
@mark.usefixtures("wide_text_output")
def test_kept_signature_keeps_the_arguments_a_subscription_drops(
    build_text: BuildText, rst: str, expected: str
) -> None:
    assert build_text(rst).splitlines()[0] == expected


@mark.sphinx(
    "text",
    testroot="dropped-arguments",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
def test_kept_signature_links_the_class_whose_subscription_drops_the_arguments(
    app: SphinxTestApp, build_text: BuildText
) -> None:
    build_text(".. autofunction:: dropped_module.quoted")

    signature = next(app.env.get_doctree("index").findall(addnodes.desc_signature))
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == ["engines.Engine", "int", "None"]


def test_type_hints_reads_a_module_with_syntax_warnings_analyzed_where_they_were_ignored(
    make_module: Callable[[str], ModuleType], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(ModuleAnalyzer, "cache", {})
    with catch_warnings():
        simplefilter("ignore", SyntaxWarning)
        module = make_module(
            dedent("""\
                class Engine:
                    def __class_getitem__(cls, item):
                        return cls

                PATTERN = "\\d"

                class Holder:
                    kind: Engine[int]
            """)
        )
        ModuleAnalyzer.for_module(module.__name__).analyze()
    assert type_hints(module.Holder, None, None) == {"kind": GenericAlias(module.Engine, int)}


def test_type_hints_of_a_base_ignores_the_guard_of_the_module_of_a_subclass(guarded_subclass: type) -> None:
    assert type_hints(guarded_subclass, None, None) == {"inherited": int, "own": Decimal}


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    ("declaration", "owner"),
    [
        param("def func(value: Decimal) -> None: ...", "func", id="function"),
        param(
            dedent("""\
                class Holder:
                    def method(self, value: Decimal) -> None: ...
            """),
            "Holder.method",
            id="method",
        ),
        param(
            dedent("""\
                class Holder:
                    value: Decimal
            """),
            "Holder",
            id="class",
        ),
        param(
            "def func(value: Decimal, other: Undefined) -> None: ...", "func", id="function-beside-an-undefined-name"
        ),
        param(
            dedent("""\
                class Holder:
                    value: Decimal
                    other: Undefined
            """),
            "Holder",
            id="class-beside-an-undefined-name",
        ),
    ],
)
def test_lazy_annotation_reads_the_guarded_type_over_its_runtime_fallback(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], declaration: str, owner: str, decimal_fallback: str
) -> None:
    module = make_module(f"{decimal_fallback}{declaration}")
    assert get_all_type_hints([], attrgetter(owner)(module), f"mod.{owner}", {})["value"] is Decimal


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_annotation_of_a_base_reads_the_guard_of_its_own_module(  # pragma: >=3.14 cover
    make_subclass_of_a_guarded_base: MakeSubclassOfAGuardedBase,
) -> None:
    child = make_subclass_of_a_guarded_base(
        "",
        dedent("""\
            from typing import TYPE_CHECKING
            from guarded_base import Base

            if TYPE_CHECKING:
                from fractions import Fraction
            else:
                Fraction = int

            class Child(Base):
                ratio: Fraction
        """),
    )
    assert get_all_type_hints([], child, "mod.Child", {}) == {"amount": Decimal, "ratio": Fraction}


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_annotation_keeps_the_values_of_a_base_without_source(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType], decimal_fallback: str
) -> None:
    module = make_module(
        decimal_fallback
        + dedent("""\
            Plain = type("Plain", (), {"__annotations__": {"count": int}})

            class Child(Plain):
                amount: Decimal
        """)
    )
    assert get_all_type_hints([], module.Child, "mod.Child", {}) == {"count": int, "amount": Decimal}


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_annotation_naming_no_shadowed_name_keeps_its_closure(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    decimal_fallback: str,
) -> None:
    module = make_module(
        decimal_fallback
        + dedent("""\
            def make():
                Local = int
                def func(value: Local) -> None: ...
                return func
        """)
    )
    hints = get_all_type_hints([], module.make(), "mod.func", {})
    assert (hints, logged_warnings()) == ({"value": int, "return": type(None)}, [])


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
@mark.parametrize(
    ("declaration", "owner"),
    [
        param("def func(*args: *Ts, value: Decimal) -> None: ...", "func", id="starred"),
        param("def func(check: Annotated[int, lambda v: v], value: Decimal) -> None: ...", "func", id="lambda-first"),
        param("def func(value: Decimal, check: Annotated[int, lambda v: v]) -> None: ...", "func", id="lambda-last"),
        param(
            dedent("""\
                class Holder:
                    check: Annotated[int, lambda v: v]
                    value: Decimal
            """),
            "Holder",
            id="class",
        ),
    ],
)
def test_lazy_annotation_beside_one_without_source_reads_the_guarded_type(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    declaration: str,
    owner: str,
    decimal_fallback: str,
) -> None:
    # a lambda prints by its repr, which does not parse, and *Ts parses only inside a tuple
    module = make_module(
        decimal_fallback
        + dedent("""\
            from typing import Annotated, TypeVarTuple

            Ts = TypeVarTuple("Ts")
        """)
        + declaration
    )
    hints = get_all_type_hints([], getattr(module, owner), f"mod.{owner}", {})
    assert (hints["value"], logged_warnings()) == (Decimal, [])


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_annotation_stringified_union_of_a_mocked_type_evaluates_as_union(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType],
) -> None:
    module = make_module(
        dedent("""\
            from __future__ import annotations
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from absent_buffers import Buffer
            else:
                Buffer = object

            def func(value: Buffer | str) -> None: ...
        """)
    )
    hint = get_all_type_hints(["absent_buffers"], module.func, "mod.func", {})["value"]
    assert (get_origin(hint), [str(arg) for arg in get_args(hint)]) == (Union, ["absent_buffers.Buffer", str(str)])


@mark.skipif(version_info < (3, 14), reason="annotations evaluate lazily from Python 3.14")
def test_lazy_annotation_neither_source_nor_runtime_evaluates_warns(  # pragma: >=3.14 cover
    make_module: Callable[[str], ModuleType],
    logged_warnings: Callable[[], list[tuple[str, ...]]],
    decimal_fallback: str,
) -> None:
    module = make_module(
        decimal_fallback
        + dedent("""\
            class Holder:
                value: Decimal
                other: Missing

            Holder.__annotations__ = {"value": float}
        """)
    )
    get_all_type_hints([], module.Holder, "mod.Holder", {})
    assert [warning[-1] for warning in logged_warnings()] == ["name 'Missing' is not defined"]
