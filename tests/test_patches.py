from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

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
