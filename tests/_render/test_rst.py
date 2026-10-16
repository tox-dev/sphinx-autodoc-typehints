from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark

from sphinx_autodoc_typehints._render import parse, unescape

if TYPE_CHECKING:
    from sphinx.testing.util import SphinxTestApp


@mark.sphinx("text", testroot="dummy")
def test_parse(app: SphinxTestApp) -> None:
    assert parse("``int``", app.env).pformat() == dedent("""\
        <document source="">
            <paragraph>
                <literal>
                    int
    """)


def test_unescape() -> None:
    assert unescape("a\x00*b\x00`") == "a*b`"
