from __future__ import annotations

from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Final, Protocol

from pytest import MarkDecorator, fixture, mark, param

if TYPE_CHECKING:
    from io import StringIO

    from conftest import BuildText, MakeModule
    from sphinx.testing.util import SphinxTestApp

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


class Document(Protocol):
    def __call__(self, docstring: str) -> str: ...


@fixture(name="document")
def document_fixture(make_module: MakeModule, build_text: BuildText) -> Document:
    def build(docstring: str) -> str:
        source = 'def documented(x: int) -> int:\n    """\n' + indent(dedent(docstring), "    ") + '    """\n'
        make_module("rtype_placed", source)
        return build_text(".. autofunction:: rtype_placed.documented")

    return build


def test_rtype_joins_the_params_before_a_table(document: Document) -> None:
    assert document("""\
        Summary.

        :param x: the x

        =  =
        a  b
        =  =
        """) == dedent("""\
        rtype_placed.documented(x)

           Summary.

           Parameters:
              **x** ("int") -- the x

           Return type:
              "int"

           +---+---+
           | a | b |
           +---+---+
        """)


def test_rtype_joins_a_param_followed_by_a_block_without_a_blank_line(document: Document) -> None:
    assert document("""\
        Summary.

        :param x: the x
        * one
        """) == dedent("""\
        rtype_placed.documented(x)

           Summary.

           Parameters:
              **x** ("int") -- the x

           Return type:
              "int"

           * one
        """)


def test_rtype_joins_the_first_list_of_params(document: Document) -> None:
    assert document("""\
        Summary.

        :raises ValueError: bad

        Text.

        :param x: the x
        """) == dedent("""\
        rtype_placed.documented(x)

           Summary.

           Raises:
              **ValueError** -- bad

           Text.

           Parameters:
              **x** ("int") -- the x

           Return type:
              "int"
        """)


def test_rtype_joins_a_field_list_without_params(document: Document) -> None:
    assert document("""\
        Summary.

        :raises ValueError: bad

        .. note:: careful
        """) == dedent("""\
        rtype_placed.documented(x)

           Summary.

           Raises:
              **ValueError** -- bad

           Return type:
              "int"

           Note:

             careful
        """)


@mark.parametrize(
    "block",
    [
        param("* one\n* two", id="bullets"),
        param(".. note:: careful", id="note"),
        param(">>> 1 + 1\n2", id="doctest"),
        param("term\n    definition", id="definition-list"),
        param(".. rubric:: Examples\n\nUsage.", id="rubric"),
    ],
)
def test_rtype_ends_a_docstring_without_a_field_list(document: Document, block: str) -> None:
    text = document(f"Summary.\n\n{block}\n")
    assert text.rstrip().endswith('Return type:\n      "int"')


def test_rtype_ends_a_docstring_after_a_section(document: Document) -> None:
    text = document("""\
        Summary.

        Title
        =====

        Body.
        """)
    assert text.rstrip().endswith('Body.\n\n   Return type:\n      "int"')


def test_rtype_leaves_no_marker_after_a_section_with_params(document: Document) -> None:
    text = document("""\
        Summary.

        :param x: the x

        Title
        =====

        Body.
        """)
    assert (text.index("Return type:") < text.index("Title"), "sphinx_autodoc_typehints_rtype" in text) == (True, False)


def test_rtype_keeps_the_line_of_a_warning_after_the_params(document: Document, warning: StringIO) -> None:
    document("""\
        Summary.

        :param x: the x

        .. nonexistent-directive:: arg
        """)
    assert "docstring of rtype_placed.documented:6: ERROR: Unknown directive type" in warning.getvalue()


@mark.sphinx("text", testroot="intersphinx-external-role")
def test_rtype_keeps_the_intersphinx_roles(app: SphinxTestApp, warning: StringIO) -> None:
    app.build()
    assert (warning.getvalue(), (Path(app.outdir) / "index.txt").read_text().count("the demo docs")) == ("", 2)


@mark.sphinx("text", testroot="intersphinx-missing-inventory")
def test_rtype_reports_a_missing_inventory_once(app: SphinxTestApp, warning: StringIO) -> None:
    app.build()
    assert warning.getvalue().count("inventory for external cross-reference not found") == 1


def test_rtype_leaves_the_fields_written_after_it_in_place(make_module: MakeModule, build_text: BuildText) -> None:
    make_module(
        "rtype_override",
        dedent('''\
            from typing import override


            class Base:
                def run(self) -> int:
                    return 1


            class Child(Base):
                @override
                def run(self) -> int:
                    """
                    Summary.

                    :raises ValueError: bad

                    Text.
                    """
                    return 2
        '''),
    )
    text = build_text(".. automethod:: rtype_override.Child.run")
    assert text.index("Return type:") < text.index("Text.") < text.index("Overrides:")
