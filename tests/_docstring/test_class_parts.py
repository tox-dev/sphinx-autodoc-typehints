from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param
from sphinx.ext.autodoc import Options

from _docstring.conftest import INT
from sphinx_autodoc_typehints._docstring import process_docstring

if TYPE_CHECKING:
    from conftest import BuildText
    from sphinx.testing.util import SphinxTestApp

pytestmark: Final[MarkDecorator] = mark.sphinx(
    "text", testroot="dummy", confoverrides={"autoclass_content": "both", "always_document_param_types": True}
)


@mark.parametrize(
    ("class_doc_from", "expected"),
    [
        param(
            "class",
            dedent("""\
                class dummy_module.DocumentedTwice(first, second, third)

                   Class docstring.

                   Parameters:
                      * **first** ("int") -- the first

                      * **second** ("str")

                      * **third** ("bool")
            """),
            id="class",
        ),
        param(
            "both",
            dedent("""\
                class dummy_module.DocumentedTwice(first, second, third)

                   Class docstring.

                   Parameters:
                      **first** ("int") -- the first

                   Constructor docstring.

                   Parameters:
                      * **second** ("str") -- the second

                      * **third** ("bool")
            """),
            id="both",
            marks=mark.sphinx(confoverrides={"autoclass_content": "class", "always_document_param_types": True}),
        ),
    ],
)
def test_class_doc_from_option_picks_the_docstrings_listing_params(
    build_text: BuildText, class_doc_from: str, expected: str
) -> None:
    assert (
        build_text(
            dedent(f"""\
                .. autoclass:: dummy_module.DocumentedTwice
                   :class-doc-from: {class_doc_from}
            """)
        )
        == expected
    )


def test_class_docstring_part_does_not_pair_with_another_directive(app: SphinxTestApp) -> None:
    class DocumentedTwice:
        """Class docstring."""

        def __init__(self, first: int, second: str) -> None:
            """Constructor docstring."""

    first_pass, second_pass = (["Class docstring.", "", ":param first: the first"] for _ in range(2))
    process_docstring(app, "class", f"{__name__}.DocumentedTwice", DocumentedTwice, Options(), first_pass)
    process_docstring(app, "class", f"{__name__}.DocumentedTwice", DocumentedTwice, Options(), second_pass)
    assert second_pass == ["Class docstring.", "", f":type first: {INT}", ":param first: the first"]


@mark.parametrize(
    ("cls", "expected"),
    [
        param(
            "DocumentedTwice",
            dedent("""\
                class dummy_module.DocumentedTwice(first, second, third)

                   Class docstring.

                   Parameters:
                      **first** ("int") -- the first

                   Constructor docstring.

                   Parameters:
                      * **second** ("str") -- the second

                      * **third** ("bool")
            """),
            id="init",
        ),
        param(
            "DocumentedTwiceThroughNew",
            dedent("""\
                class dummy_module.DocumentedTwiceThroughNew(first, second, third)

                   Class docstring.

                   Parameters:
                      **first** ("int") -- the first

                   Constructor docstring.

                   Parameters:
                      * **second** ("str") -- the second

                      * **third** ("bool")
            """),
            id="new",
        ),
        param(
            "DocumentedTwiceAlias",
            dedent("""\
                dummy_module.DocumentedTwiceAlias

                   An alias.

                   Parameters:
                      * **first** ("int")

                      * **second** ("str")

                      * **third** ("bool")
            """),
            id="alias",
        ),
        param(
            "DocumentedTwiceWithUnderscore",
            dedent("""\
                class dummy_module.DocumentedTwiceWithUnderscore(type_, count)

                   Class docstring.

                   Parameters:
                      **type_** ("str") -- the type

                   Constructor docstring.

                   Parameters:
                      **count** ("int") -- the count
            """),
            id="escaped-param",
        ),
        param(
            "KeysTwice",
            dedent("""\
                class dummy_module.KeysTwice(**kwargs)

                   Class docstring.

                   Constructor docstring.

                   Parameters:
                      **kwargs** ("Unpack"["_TwiceOptions"])

                   Keyword Arguments:
                      **verbose** ("bool")
            """),
            id="unpacked-keys",
        ),
        param(
            "OverloadedTwice",
            dedent("""\
                class dummy_module.OverloadedTwice(a)

                   Class docstring.

                   Constructor docstring.

                   Overloads:
                      * **a** ("int")

                      * **a** ("str")

                   Parameters:
                      **a** ("int" | "str")
            """),
            id="overloads",
        ),
        param(
            "DescribedTwice",
            dedent("""\
                class dummy_module.DescribedTwice(a)

                   Class docstring.

                   Constructor docstring.

                   Parameters:
                      **a** ("int") -- the a
            """),
            id="doc-described",
        ),
        param(
            "DeprecatedTwice",
            dedent("""\
                class dummy_module.DeprecatedTwice(a)

                   Class docstring.

                   Deprecated: use something else

                   Constructor docstring.

                   Parameters:
                      **a** ("int") -- the a
            """),
            id="deprecated",
            marks=mark.sphinx(confoverrides={"autoclass_content": "both"}),
        ),
    ],
)
def test_class_and_constructor_docstrings_share_the_fields(build_text: BuildText, cls: str, expected: str) -> None:
    assert build_text(f".. autoclass:: dummy_module.{cls}") == expected
