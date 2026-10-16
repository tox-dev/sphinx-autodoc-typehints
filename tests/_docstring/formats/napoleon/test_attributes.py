from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

if TYPE_CHECKING:
    from conftest import BuildText


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
