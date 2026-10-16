from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

from _docstring.conftest import INT
from sphinx_autodoc_typehints._docstring import note_attributes_before_napoleon, process_docstring

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText, MakeModule
    from sphinx.testing.util import SphinxTestApp


def _untyped(**options: bool) -> MarkDecorator:
    return mark.sphinx(confoverrides={"napoleon_attr_annotations": False, **options})


pytestmark: Final[list[MarkDecorator]] = [mark.sphinx("text", testroot="dummy"), _untyped()]


@mark.parametrize(
    ("directive", "expected"),
    [
        param(
            "autoclass:: dummy_module.GoogleAttributes",
            dedent("""\
                class dummy_module.GoogleAttributes

                   Class docstring.

                   count

                      the count
            """),
            id="class",
        ),
        param(
            "autoclass:: dummy_module.GoogleAttributes",
            dedent("""\
                class dummy_module.GoogleAttributes

                   Class docstring.

                   Variables:
                      **count** -- the count
            """),
            id="class-ivar",
            marks=_untyped(napoleon_use_ivar=True),
        ),
        param(
            "autoclass:: dummy_module.GoogleInitAttributes",
            dedent("""\
                class dummy_module.GoogleInitAttributes

                   Class docstring.

                   location

                      the location
            """),
            id="init-assignment",
        ),
        param(
            "automodule:: attributes_module",
            dedent("""\
                Module docstring.

                attributes_module.location

                   the location

                attributes_module.level

                   the level

                attributes_module.written

                   written by hand

                   Type:
                      str
            """),
            id="module",
        ),
        param(
            "automodule:: attributes_module",
            dedent("""\
                Module docstring.

                ivar location:
                   the location

                ivar level:
                   the level

                ivar written:
                   written by hand

                vartype written:
                   str
            """),
            id="module-ivar",
            marks=_untyped(napoleon_use_ivar=True),
        ),
        param(
            "autoclass:: dummy_module.GoogleAttributesBesideField",
            dedent("""\
                class dummy_module.GoogleAttributesBesideField

                   Class docstring.

                   Variables:
                      **written** ("str") -- written as a field

                   count

                      the count
            """),
            id="beside-a-field-written-by-hand",
        ),
    ],
)
def test_napoleon_attributes_without_attr_annotations(build_text: BuildText, directive: str, expected: str) -> None:
    assert build_text(f".. {directive}") == expected


def test_napoleon_attributes_noted_for_a_failed_docstring_stay_out_of_the_next(
    app: SphinxTestApp, make_app: Callable[..., SphinxTestApp], make_module: MakeModule
) -> None:
    ledger = make_module(
        "noted_ledger",
        dedent("""\
            class Ledger:
                def __init__(self) -> None:
                    self.amount: int = 0
        """),
    ).Ledger
    # the same list stands in for a later one python allocates where the failed docstring's list was freed
    lines = ["Ledger docstring."]
    note_attributes_before_napoleon(app, "class", "noted_ledger.Ledger", ledger, None, lines)
    typed = make_app(srcdir=app.srcdir)
    lines[:] = [".. attribute:: amount", "", "   how much", ""]
    note_attributes_before_napoleon(typed, "class", "noted_ledger.Ledger", ledger, None, lines)
    process_docstring(typed, "class", "noted_ledger.Ledger", ledger, None, lines)
    assert lines == [".. attribute:: amount", "", "   how much", "", f"   :type: {INT}", ""]


@mark.parametrize(
    ("cls", "expected"),
    [
        param(
            "GoogleAttributes",
            dedent("""\
                class dummy_module.GoogleAttributes

                   Class docstring.

                   count

                      the count

                      Type:
                         "int"
            """),
            id="attribute-typed-by-the-extension",
        ),
        param(
            "NumpyParameterShadowedByAttribute",
            dedent("""\
                class dummy_module.NumpyParameterShadowedByAttribute(count)

                   Class docstring.

                   Parameters:
                      **count** ("int") -- the count
            """),
            id="parameter-not-typed-as-attribute",
        ),
    ],
)
@mark.sphinx("text", testroot="dummy", confoverrides={})
def test_napoleon_attributes_typed_from_annotations(build_text: BuildText, cls: str, expected: str) -> None:
    assert build_text(f".. autoclass:: dummy_module.{cls}") == expected


@mark.sphinx("text", testroot="dummy", confoverrides={})
def test_napoleon_attr_annotations_turned_off_re_reads_the_document(
    app: SphinxTestApp, build_text: BuildText, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text(".. autoclass:: dummy_module.GoogleAttributes")
    untyped = make_app("text", srcdir=app.srcdir, confoverrides={"napoleon_attr_annotations": False})
    untyped.build()
    assert "Type:" not in (Path(untyped.outdir) / "index.txt").read_text()
