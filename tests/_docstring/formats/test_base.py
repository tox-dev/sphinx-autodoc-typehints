from __future__ import annotations

from enum import Enum
from inspect import Parameter
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

from sphinx_autodoc_typehints._docstring.formats.base import format_default, last_paragraph_end

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


@mark.parametrize(
    ("defaults", "annotated", "expected"),
    [
        param("comma", True, ", default: :sphinx_autodoc_typehints_value:`1`", id="comma-after-a-type"),
        param("braces", True, " (default: :sphinx_autodoc_typehints_value:`1`)", id="braces-after-a-type"),
        param("braces-after", True, " (default: :sphinx_autodoc_typehints_value:`1`)", id="braces-after-after-a-type"),
        param("comma", False, "default: :sphinx_autodoc_typehints_value:`1`", id="comma-alone"),
        param("braces", False, "default: :sphinx_autodoc_typehints_value:`1`", id="braces-alone"),
        param("braces-after", False, " (default: :sphinx_autodoc_typehints_value:`1`)", id="braces-after-alone"),
        param("optional", True, ", optional", id="optional-after-a-type"),
        param("optional", False, " (optional)", id="optional-alone"),
    ],
)
def test_format_default_by_style(app: SphinxTestApp, defaults: str, annotated: bool, expected: str) -> None:
    app.config.typehints_defaults = defaults
    assert format_default(app, 1, annotated=annotated) == expected


def test_format_default_without_a_default(app: SphinxTestApp) -> None:
    app.config.typehints_defaults = "comma"
    assert format_default(app, Parameter.empty, annotated=True) is None


class _Mode(Enum):
    FAST = 1


class _MultiLineRepr:
    def __repr__(self) -> str:
        return dedent("""\
            MultiLine(
              a=1,
            )""")


@mark.parametrize(
    ("default", "expected"),
    [
        param(object(), "<object object>", id="sentinel"),
        param(_Mode.FAST, "_Mode.FAST", id="enum-member"),
        param(frozenset({"gamma", "alpha", "beta"}), "frozenset({'alpha', 'beta', 'gamma'})", id="frozenset"),
        param(_MultiLineRepr(), "MultiLine(   a=1, )", id="multi-line-repr"),
        param("x\\y", r"'x\\\\y'", id="backslash"),
    ],
)
def test_format_default_describes_it_like_the_signature(app: SphinxTestApp, default: object, expected: str) -> None:
    app.config.typehints_defaults = "comma"
    assert format_default(app, default, annotated=True) == f", default: :sphinx_autodoc_typehints_value:`{expected}`"


@mark.parametrize(
    ("lines", "expected"),
    [
        param([":param a: the a"], 0, id="one-line"),
        param([":param a: the a, for example::", "", "    a = 5"], 0, id="literal-block"),
        param([":param a: one of:", "", "    - x", "    - y"], 0, id="bullet-list"),
        param([":param a: one of:", "", "    1. x", "    2. y"], 0, id="enumerated-list"),
        param([":param a: the a", "", "    .. note:: careful"], 0, id="directive"),
        param([":param a: the a", "    more", "", "        quoted"], 1, id="deeper-indented-block"),
        param([":param a: the a", "", "    second paragraph"], 2, id="last-plain-paragraph"),
        param([":param a: the a", "    more", ":param b: the b"], 1, id="before-the-next-field"),
    ],
)
def test_last_paragraph_end(lines: list[str], expected: int) -> None:
    assert last_paragraph_end(lines, 0) == expected
