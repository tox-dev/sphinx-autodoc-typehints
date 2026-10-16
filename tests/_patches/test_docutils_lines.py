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


@mark.sphinx("text", testroot="dummy")
def test_definition_list_warning_names_its_first_line(app: SphinxTestApp) -> None:
    (Path(app.srcdir) / "index.rst").write_text(
        dedent("""\
            .. _dup:

            Index
            =====

            .. toctree::

               other
        """)
    )
    (Path(app.srcdir) / "other.rst").write_text(
        dedent("""\
            Other
            =====

            .. _dup:

            term
               definition
        """)
    )
    app.build()

    assert findall(r"other\.rst:(\d+): WARNING: duplicate label", app.warning.getvalue()) == ["6"]
