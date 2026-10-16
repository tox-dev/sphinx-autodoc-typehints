from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="dummy")
def test_overloads_stay_visible_to_an_app_without_the_extension(
    build_text: BuildText, app: SphinxTestApp, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text(".. automethod:: dummy_module.ClassWithOverloadedMethods.convert")
    plain = make_app("text", srcdir=app.srcdir, confoverrides={"extensions": ["sphinx.ext.autodoc"]}, freshenv=True)
    plain.build()

    assert (Path(plain.outdir) / "index.txt").read_text() == dedent("""\
        ClassWithOverloadedMethods.convert(value: int) -> int
        ClassWithOverloadedMethods.convert(value: str) -> str

           Convert value.
        """)


@mark.parametrize(
    ("method", "expected"),
    [
        param(
            "sphinx.pycode.ModuleAnalyzer.analyze",
            dedent("""\
                ModuleAnalyzer.analyze()

                   Analyze the source code.

                   Return type:
                      "None"
            """),
            id="patch-built-on-install",
        ),
        param(
            "sphinx.domains.python.PyObject.get_signatures",
            dedent("""\
                PyObject.get_signatures()

                   Retrieve the signatures to document from the directive arguments.

                   By default, signatures are given as arguments, one per line.

                   Return type:
                      "list"["str"]
            """),
            id="patch-of-a-base-class",
        ),
    ],
)
@mark.sphinx("text", testroot="dummy")
def test_patched_method_documents_as_the_original(
    build_text: BuildText, app: SphinxTestApp, method: str, expected: str
) -> None:
    assert (build_text(f".. automethod:: {method}"), app.warning.getvalue()) == (expected, "")


@mark.sphinx("text", testroot="dummy")
def test_patched_class_lists_no_member_autodoc_would_not(build_text: BuildText) -> None:
    text = build_text(
        dedent("""\
            .. autoclass:: sphinx.domains.python.PyObject
               :members:
               :private-members:""")
    )
    assert ("handle_signature(" in text, "get_signatures(" in text) == (True, False)


@mark.sphinx("text", testroot="headers")
def test_autodoc_finds_an_attribute_a_base_annotates_with_a_guarded_name(build_text: BuildText) -> None:
    # documenting the base runs the guard binding Callable, which autodoc reads looking for the attribute
    assert build_text(
        dedent("""\
            .. autoclass:: header_module.Engined

            .. autoattribute:: header_module.SubEngined.engine""")
    ) == dedent("""\
        class header_module.Engined

           Holds engines.

        SubEngined.engine: Engine[str]

           The engine.
        """)
