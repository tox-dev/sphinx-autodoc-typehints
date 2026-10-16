from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from docutils import nodes
from docutils.parsers.rst import Directive
from pytest import CaptureFixture, MarkDecorator, mark, param

from _docstring.conftest import INT
from sphinx_autodoc_typehints._docstring.formats.field_list.rtype import (
    SphinxDirectivePlaceholder,
    node_line_no,
    safe_parse,
)

if TYPE_CHECKING:
    from io import StringIO

    from conftest import BuildText, MakeModule
    from sphinx.testing.util import SphinxTestApp

    from _docstring.conftest import Process

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="dummy")


def _with_line(node: nodes.Element, line: int) -> nodes.Element:
    node.line = line
    return node


@mark.parametrize(
    ("node", "expected"),
    [
        param(_with_line(nodes.paragraph(), 3), 3, id="own-line"),
        param(nodes.section("", nodes.title(), _with_line(nodes.paragraph(), 5)), None, id="past-the-first-child"),
        param(nodes.section("", _with_line(nodes.paragraph(), 5), nodes.paragraph()), 5, id="first-child"),
        param(nodes.section(), None, id="no-line"),
    ],
)
def test_node_line_no(node: nodes.Element, expected: int | None) -> None:
    assert node_line_no(node) == expected


def test_safe_parse_stands_in_for_a_directive_only_sphinx_knows(app: SphinxTestApp) -> None:
    doc = safe_parse(
        dedent("""\
            Summary.

            .. versionadded:: 1.0

            .. note:: careful"""),
        app.env,
    )
    assert [(type(node), node.line) for node in doc.children] == [
        (nodes.paragraph, 1),
        (SphinxDirectivePlaceholder, 3),
        (nodes.note, 5),
    ]


def test_safe_parse_runs_no_directive_only_sphinx_knows(
    app: SphinxTestApp, build_text: BuildText, make_module: MakeModule
) -> None:
    executions: list[str] = []

    class Tracking(Directive):
        has_content = True

        def run(self) -> list[nodes.Node]:
            executions.append(self.content[0])
            return []

    app.add_directive("tracking-directive", Tracking)
    make_module(
        "rtype_tracked",
        dedent("""\
            def tracked(x: int) -> int:
                \"""
                Do something.

                :param x: A number.

                .. tracking-directive::

                    unique-id-123
                \"""
                return x
        """),
    )
    build_text(".. autofunction:: rtype_tracked.tracked")
    assert executions == ["unique-id-123"]


def test_safe_parse_of_a_broken_docstring_stays_quiet(process: Process, capsys: CaptureFixture[str]) -> None:
    def broken() -> int: ...

    lines = ["Behaves like this:", "- a list item", "    an unexpected indent"]
    assert (process("function", "mod.broken", broken, lines), capsys.readouterr().err) == (
        ["Behaves like this:", "- a list item", "    an unexpected indent", "", f":rtype: {INT}"],
        "",
    )


@mark.sphinx("text", testroot="intersphinx-external-role")
def test_safe_parse_keeps_the_intersphinx_roles(app: SphinxTestApp, warning: StringIO) -> None:
    app.build()
    assert (warning.getvalue(), (Path(app.outdir) / "index.txt").read_text().count("the demo docs")) == ("", 2)


@mark.sphinx("text", testroot="intersphinx-missing-inventory")
def test_safe_parse_leaves_reporting_to_the_real_parse(app: SphinxTestApp, warning: StringIO) -> None:
    app.build()
    assert warning.getvalue().count("inventory for external cross-reference not found") == 1
