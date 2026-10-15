from __future__ import annotations

from pathlib import Path
from re import findall
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark

if TYPE_CHECKING:
    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx(
    "doctest",
    testroot="dummy",
    confoverrides={"extensions": ["sphinx.ext.autodoc", "sphinx.ext.doctest", "sphinx_autodoc_typehints"]},
)
def test_doctest_failure_reports_the_example_line(build_text: BuildText) -> None:
    assert 'File "index.rst", line 6, in default' in build_text(
        dedent("""\
            Title
            =====

            Para.

            >>> 1 + 1
            3
        """),
        output="output.txt",
    )


@mark.sphinx("latex", testroot="dummy")
def test_admonition_line_counts_within_its_own_file(app: SphinxTestApp) -> None:
    (Path(app.srcdir) / "included.txt").write_text(
        dedent("""\
            a

            b

            c
        """)
    )
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
            Index
            =====

            .. include:: included.txt

            .. note::

               .. tabularcolumns:: |L|L|

               +---------+-----+
               | ::      | b   |
               |         |     |
               |   code  |     |
               +---------+-----+
        """)
    )
    app.build()

    assert findall(r"index\.rst:(\d+): WARNING: colspec", app.warning.getvalue()) == ["6"]


@mark.sphinx("text", testroot="dummy")
def test_patched_text_indent_documents_as_the_original(build_text: BuildText, app: SphinxTestApp) -> None:
    assert (build_text(".. automethod:: docutils.parsers.rst.states.Text.indent"), app.warning.getvalue()) == (
        dedent("""\
            Text.indent(match, context, next_state)

               Definition list item.
        """),
        "",
    )
