from __future__ import annotations

from re import findall
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import fixture, mark, param

if TYPE_CHECKING:
    from io import StringIO

    from conftest import BuildText, MakeModule


@fixture(name="enum_module")
def enum_module_fixture(make_module: MakeModule) -> None:
    make_module(
        "literal_enum",
        dedent("""\
            from enum import Enum
            from typing import Literal


            class Color(Enum):
                \"\"\"A color.\"\"\"

                RED = 1


            def paint(color: Literal[Color.RED]) -> None:
                \"\"\"Paint.

                :param color: the color to paint with
                \"\"\"
            """),
    )


@mark.parametrize(
    ("options", "href"),
    [
        param("", "#literal_enum.Color", id="undocumented-member-links-its-enum"),
        param(":undoc-members:", "#literal_enum.Color.RED", id="documented-member-links-itself"),
    ],
)
@mark.sphinx("html", testroot="render-types", confoverrides={"nitpicky": True, "autodoc_typehints": "description"})
@mark.usefixtures("enum_module")
def test_enum_member_in_literal_links(build_text: BuildText, warning: StringIO, options: str, href: str) -> None:
    html = build_text(
        dedent(f"""\
            .. automodule:: literal_enum
               :members:
               {options}
            """)
    )
    links = findall(r'href="([^"]*)"[^>]*><code class="xref py py-attr[^>]*><span class="pre">Color.RED</span>', html)
    assert (links, "literal_enum.Color" in warning.getvalue()) == ([href], False)


@mark.sphinx("text", testroot="render-types", confoverrides={"nitpicky": True})
@mark.usefixtures("enum_module")
def test_enum_member_written_by_hand_still_warns(build_text: BuildText, warning: StringIO) -> None:
    build_text(
        dedent("""\
            .. py:class:: literal_enum.Color

            :py:attr:`literal_enum.Color.RED`
            """)
    )
    assert "py:attr reference target not found: literal_enum.Color.RED" in warning.getvalue()
