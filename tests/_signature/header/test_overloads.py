from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark, param
from sphinx import addnodes

if TYPE_CHECKING:
    from conftest import BuildText
    from docutils import nodes

    from _signature.conftest import BuildDoctree

pytestmark: Final[MarkDecorator] = mark.sphinx(
    "text", testroot="dummy", confoverrides={"typehints_use_signature": True}
)


@mark.parametrize(
    ("rst", "expected"),
    [
        param(
            ".. autofunction:: dummy_module.overloaded",
            dedent("""\
                dummy_module.overloaded(value: int) -> DataClass
                dummy_module.overloaded(value: str, *, strict=...) -> MyNamedTuple

                   Overloaded function.
                """),
            id="function",
        ),
        param(
            ".. automethod:: dummy_module.ClassWithOverloadedMethods.build",
            dedent("""\
                classmethod ClassWithOverloadedMethods.build(value: int) -> ClassWithOverloadedMethods
                classmethod ClassWithOverloadedMethods.build(value: str) -> ClassWithOverloadedMethods

                   Build one.
                """),
            id="classmethod",
        ),
        param(
            ".. automethod:: dummy_module.ClassWithOverloadedMethods.convert",
            dedent("""\
                ClassWithOverloadedMethods.convert(value: int) -> int
                ClassWithOverloadedMethods.convert(value: str) -> str

                   Convert value.
                """),
            id="method",
        ),
        param(
            ".. automethod:: dummy_module.ClassWithOverloadedMethods.parse",
            dedent("""\
                static ClassWithOverloadedMethods.parse(value: int) -> int
                static ClassWithOverloadedMethods.parse(value: str) -> str

                   Parse value.
                """),
            id="staticmethod",
        ),
        param(
            ".. autoclass:: dummy_module.ClassWithOverloadedInit",
            dedent("""\
                class dummy_module.ClassWithOverloadedInit(value: int)
                class dummy_module.ClassWithOverloadedInit(value: str)

                   Class docstring.
                """),
            id="constructor",
        ),
        param(
            ".. autofunction:: dummy_module.overloaded_generic",
            dedent("""\
                dummy_module.overloaded_generic[T: int](value: T) -> T
                dummy_module.overloaded_generic[T: int](value: list[T]) -> T

                   Generic function.
                """),
            id="type-params",
        ),
        param(
            ".. autofunction:: dummy_module.overloaded_opt_out",
            dedent("""\
                dummy_module.overloaded_opt_out(value: int | str)

                   Opted out.

                   Return type:
                      "int" | "str"
                """),
            id="no-overloads",
        ),
        param(
            ".. autofunction:: dummy_module.overloaded(value)",
            dedent("""\
                dummy_module.overloaded(value)

                   Overloaded function.

                   Overloads:
                      * **value** ("int") → "DataClass"

                      * **value** ("str"), *, **strict** = "..." → "MyNamedTuple"
                """),
            id="written-signature",
        ),
        param(
            dedent("""\
                .. autofunction:: dummy_module.overloaded(value)

                .. autofunction:: dummy_module.overloaded
                   :no-index:"""),
            dedent("""\
                dummy_module.overloaded(value)

                   Overloaded function.

                   Overloads:
                      * **value** ("int") → "DataClass"

                      * **value** ("str"), *, **strict** = "..." → "MyNamedTuple"

                dummy_module.overloaded(value: int) -> DataClass
                dummy_module.overloaded(value: str, *, strict=...) -> MyNamedTuple

                   Overloaded function.
                """),
            id="written-signature-keeps-to-its-own-entry",
        ),
        param(
            ".. autoclass:: dummy_module.ClassWithOverloadedInitOptingOut",
            dedent("""\
                class dummy_module.ClassWithOverloadedInitOptingOut(value: int | str)

                   Class docstring.

                   Constructor docstring.
                """),
            marks=mark.sphinx(confoverrides={"typehints_use_signature": True, "autoclass_content": "both"}),
            id="no-overloads-in-constructor-docstring",
        ),
        param(
            ".. autofunction:: dummy_module.ClassWithOverloadedInit",
            dedent("""\
                dummy_module.ClassWithOverloadedInit(self, value: int) -> None
                dummy_module.ClassWithOverloadedInit(self, value: str) -> None

                   Class docstring.
                """),
            id="class-as-a-function",
        ),
        param(
            ".. autoclass:: dummy_module.overloaded",
            dedent("""\
                class dummy_module.overloaded
                class dummy_module.overloaded(*, strict=...)

                   Overloaded function.
                """),
            id="function-as-a-class",
        ),
    ],
)
def test_overloads_rendered_in_signature(build_text: BuildText, rst: str, expected: str) -> None:
    assert build_text(rst) == expected


def test_overload_signature_cross_references_types(overloaded_doctree: nodes.document) -> None:
    second = list(overloaded_doctree.findall(addnodes.desc_signature))[1]
    assert [xref["reftarget"] for xref in second.findall(addnodes.pending_xref)] == ["str", "dummy_module.MyNamedTuple"]


def test_overload_signature_targets_only_the_first_line(overloaded_doctree: nodes.document) -> None:
    assert [signature["ids"] for signature in overloaded_doctree.findall(addnodes.desc_signature)] == [
        ["dummy_module.overloaded"],
        [],
    ]


@fixture(name="overloaded_doctree")
def overloaded_doctree_fixture(build_doctree: BuildDoctree) -> nodes.document:
    return build_doctree(".. autofunction:: dummy_module.overloaded")
