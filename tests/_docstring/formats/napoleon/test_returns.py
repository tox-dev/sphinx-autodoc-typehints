from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, fixture, mark, param

from sphinx_autodoc_typehints._docstring.formats.napoleon import mark_numpy_returns

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")

type Mark = Callable[[str, list[str]], list[str]]


@mark.parametrize(
    ("lines", "expected"),
    [
        param(
            ["Returns", "-------", "int", "    the count"],
            ["Returns", "-------", ":", "int", "    the count"],
            id="type-with-description",
        ),
        param(
            ["Returns", "-------", "The count of items.", "", "Notes"],
            ["Returns", "-------", ":", "    The count of items.", "", "Notes"],
            id="sentence",
        ),
        param(
            ["Returns", "-------", "dict[str, int]", "", "Notes"],
            ["Returns", "-------", ":", "dict[str, int]", "", "Notes"],
            id="type-alone",
        ),
        param(
            ["Returns:", "========", "", "Notes"],
            ["Returns:", "========", ":", "", "Notes"],
            id="empty-section",
        ),
        param(
            ["Summary.", "", "return", "~~~~~~", "The count."],
            ["Summary.", "", "return", "~~~~~~", ":", "    The count."],
            id="singular-header",
        ),
    ],
)
def test_mark_numpy_returns_shields_the_section(mark_returns: Mark, lines: list[str], expected: list[str]) -> None:
    assert mark_returns("function", lines) == expected


@fixture(name="mark_returns")
def mark_returns_fixture(app: SphinxTestApp) -> Mark:
    def run(what: str, lines: list[str]) -> list[str]:
        mark_numpy_returns(app, what, "mod.func", None, None, lines)
        return lines

    return run


@mark.parametrize(
    ("what", "lines"),
    [
        param("class", ["Returns", "-------", "The count."], id="not-a-function"),
        param("method", ["Returns", "-=-=-=-", "The count."], id="mixed-underline"),
        param("method", ["Returns", "The count.", "-------"], id="no-underline"),
        param("function", ["Returns", "-------"], id="header-ends-the-docstring"),
        param(
            "function",
            ["Returns", "-------", "The count."],
            marks=mark.sphinx(confoverrides={"napoleon_numpy_docstring": False}),
            id="numpy-style-off",
        ),
    ],
)
def test_mark_numpy_returns_leaves_the_docstring(mark_returns: Mark, what: str, lines: list[str]) -> None:
    assert mark_returns(what, lines.copy()) == lines
