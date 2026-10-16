from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

if TYPE_CHECKING:
    from conftest import BuildText


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
            id="attribute-typed-from-annotation",
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
@mark.sphinx("text", testroot="dummy")
def test_napoleon_class_annotation_lookup(build_text: BuildText, cls: str, expected: str) -> None:
    assert build_text(f".. autoclass:: dummy_module.{cls}") == expected


@mark.sphinx("text", testroot="dummy")
def test_patched_class_lists_no_member_autodoc_would_not(build_text: BuildText) -> None:
    text = build_text(
        dedent("""\
            .. autoclass:: sphinx.ext.napoleon.docstring.GoogleDocstring
               :members:
               :private-members:""")
    )
    assert ("lines()" in text, "_lookup_annotation(" in text) == (True, False)
