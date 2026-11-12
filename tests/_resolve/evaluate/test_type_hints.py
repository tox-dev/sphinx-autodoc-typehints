from __future__ import annotations

from decimal import Decimal
from textwrap import dedent
from types import GenericAlias, ModuleType
from typing import TYPE_CHECKING
from warnings import catch_warnings, simplefilter

from pytest import MonkeyPatch, mark, param
from sphinx import addnodes
from sphinx.pycode import ModuleAnalyzer

from sphinx_autodoc_typehints._resolve.evaluate.type_hints import type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp


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
            '**kind** ("Engine"["ItemT"]) -- held engine',
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
    resolve_module: Callable[[str], ModuleType], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(ModuleAnalyzer, "cache", {})
    with catch_warnings():
        simplefilter("ignore", SyntaxWarning)
        module = resolve_module(
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


def test_type_hints_of_a_class_with_an_unhashable_metaclass(resolve_module: Callable[[str], ModuleType]) -> None:
    module = resolve_module(
        dedent("""\
            class Meta(type):
                def __eq__(cls, other):
                    return cls is other

            class Engine(metaclass=Meta):
                def __class_getitem__(cls, item):
                    return cls

            class Holder:
                kind: Engine[int]
        """)
    )

    assert type_hints(module.Holder, None, None) == {"kind": GenericAlias(module.Engine, int)}
