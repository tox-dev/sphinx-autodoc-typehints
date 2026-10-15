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
         "int"
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


@pytest.mark.parametrize(
    ("use_ivar", "expected"),
    [
        pytest.param(
            False, '   location\n\n      the location\n\n      Type:\n         "list"["Path"]\n', id="attribute"
        ),
        pytest.param(True, '   Variables:\n      **location** ("list"["Path"]) -- the location\n', id="ivar"),
    ],
)
@pytest.mark.parametrize("cls", ["GoogleInitAttributes", "NumpyInitAttributes"])
@pytest.mark.sphinx("text", testroot="dummy")
def test_napoleon_attribute_from_init_rendered_as_field(
    app: SphinxTestApp, write_rst: Callable[[str], None], cls: str, use_ivar: bool, expected: str
) -> None:
    app.config.napoleon_use_ivar = use_ivar
    # documenting an attribute has autodoc add the __init__ annotations of the module's classes to theirs, where
    # napoleon reads them
    write_rst(f".. autoattribute:: dummy_module.GoogleAttributes.count\n\n.. autoclass:: dummy_module.{cls}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text().split("Class docstring.\n\n")[1] == expected


@pytest.mark.parametrize(
    ("use_ivar", "expected"),
    [
        pytest.param(
            False,
            """\
attributes_module.location

   the location

   Type:
      "list"["Path"]

attributes_module.level

   the level

   Type:
      "int"

attributes_module.written

   written by hand

   Type:
      str
""",
            id="attribute",
        ),
        pytest.param(
            True,
            """\
vartype location:
   "list"["Path"]

ivar location:
   the location

vartype level:
   "int"

ivar level:
   the level

ivar written:
   written by hand

vartype written:
   str
""",
            id="ivar",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
def test_napoleon_module_attributes_rendered_as_fields(
    app: SphinxTestApp, write_rst: Callable[[str], None], use_ivar: bool, expected: str
) -> None:
    app.config.napoleon_use_ivar = use_ivar
    write_rst(".. automodule:: attributes_module")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text().split("Module docstring.\n\n")[1] == expected


@pytest.mark.parametrize(
    ("directive", "use_ivar", "expected"),
    [
        pytest.param("autoclass:: dummy_module.GoogleAttributes", False, "   count\n\n      the count\n", id="class"),
        pytest.param(
            "autoclass:: dummy_module.GoogleAttributes",
            True,
            "   Variables:\n      **count** -- the count\n",
            id="class-ivar",
        ),
        pytest.param(
            "autoclass:: dummy_module.GoogleInitAttributes",
            False,
            "   location\n\n      the location\n",
            id="init-assignment",
        ),
        pytest.param(
            "automodule:: attributes_module",
            False,
            """\
attributes_module.location

   the location

attributes_module.level

   the level

attributes_module.written

   written by hand

   Type:
      str
""",
            id="module",
        ),
        pytest.param(
            "automodule:: attributes_module",
            True,
            """\
ivar location:
   the location

ivar level:
   the level

ivar written:
   written by hand

vartype written:
   str
""",
            id="module-ivar",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
def test_napoleon_attributes_without_attr_annotations_stay_untyped(
    app: SphinxTestApp, write_rst: Callable[[str], None], directive: str, use_ivar: bool, expected: str
) -> None:
    app.config.napoleon_attr_annotations = False
    app.config.napoleon_use_ivar = use_ivar
    write_rst(f".. {directive}")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text().split("docstring.\n\n")[1] == expected


@pytest.mark.sphinx("text", testroot="dummy")
def test_napoleon_without_attr_annotations_types_a_field_written_by_hand(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    app.config.napoleon_attr_annotations = False
    write_rst(".. autoclass:: dummy_module.GoogleAttributesBesideField")
    app.build()

    assert (Path(app.srcdir) / "_build/text/index.txt").read_text().split("Class docstring.\n\n")[1] == (
        '   Variables:\n      **written** ("str") -- written as a field\n\n   count\n\n      the count\n'
    )


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
