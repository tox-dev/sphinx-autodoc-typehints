from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        pytest.param(
            "GoogleAttributes",
            """\
class dummy_module.GoogleAttributes

   Class docstring.

   count

      the count

      Type:
         int
""",
            id="attribute-typed-from-annotation",
        ),
        pytest.param(
            "NumpyParameterShadowedByAttribute",
            """\
class dummy_module.NumpyParameterShadowedByAttribute(count)

   Class docstring.

   Parameters:
      **count** ("int") -- the count
""",
            id="parameter-not-typed-as-attribute",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
def test_napoleon_class_annotation_lookup(
    app: SphinxTestApp, write_rst: Callable[[str], None], cls: str, expected: str
) -> None:
    write_rst(f".. autoclass:: dummy_module.{cls}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text() == expected


@pytest.mark.sphinx(
    "doctest",
    testroot="dummy",
    confoverrides={"extensions": ["sphinx.ext.autodoc", "sphinx.ext.doctest", "sphinx_autodoc_typehints"]},
)
def test_doctest_failure_reports_the_example_line(app: SphinxTestApp, write_rst: Callable[[str], None]) -> None:
    write_rst("Title\n=====\n\nPara.\n\n>>> 1 + 1\n3\n")
    app.build()

    assert 'File "index.rst", line 6, in default' in (Path(app.outdir) / "output.txt").read_text()


@pytest.mark.sphinx("text", testroot="dummy")
def test_overloads_stay_visible_to_an_app_without_the_extension(
    app: SphinxTestApp, write_rst: Callable[[str], None], make_app: Callable[..., SphinxTestApp]
) -> None:
    write_rst(".. automethod:: dummy_module.ClassWithOverloadedMethods.convert")
    app.build()
    plain = make_app(
        "text", srcdir=Path(app.srcdir), confoverrides={"extensions": ["sphinx.ext.autodoc"]}, freshenv=True
    )
    plain.build()

    assert (Path(plain.outdir) / "index.txt").read_text().splitlines()[:2] == [
        "ClassWithOverloadedMethods.convert(value: int) -> int",
        "ClassWithOverloadedMethods.convert(value: str) -> str",
    ]


@pytest.mark.sphinx("latex", testroot="dummy")
def test_admonition_line_counts_within_its_own_file(app: SphinxTestApp, warning: StringIO) -> None:
    (Path(app.srcdir) / "included.txt").write_text("a\n\nb\n\nc\n")
    (Path(app.srcdir) / "index.rst").write_text(
        "Index\n=====\n\n.. include:: included.txt\n\n.. note::\n\n   .. tabularcolumns:: |L|L|\n\n"
        "   +---------+-----+\n   | ::      | b   |\n   |         |     |\n   |   code  |     |\n   +---------+-----+\n"
    )
    app.build()

    assert re.findall(r"index\.rst:(\d+): WARNING: colspec", warning.getvalue()) == ["6"]
