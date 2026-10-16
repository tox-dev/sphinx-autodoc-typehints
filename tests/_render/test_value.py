from __future__ import annotations

from pathlib import Path
from re import findall
from textwrap import dedent
from typing import TYPE_CHECKING

from pytest import mark, param

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import BuildText, MakeModule
    from sphinx.testing.util import SphinxTestApp


def _values(html: str) -> list[tuple[str, list[tuple[str, str]]]]:
    return [
        (code_class, findall(r'(?:<span class="(\w+)">)?<span class="pre">([^<]*)</span>', inner))
        for code_class, inner in findall(
            r'<span class="highlight sphinx_autodoc_typehints-value">(?:<a [^>]*>)?<code class="([^"]*)">(.*?)</code>',
            html,
        )
    ]


@mark.parametrize(
    ("signature", "expected"),
    [
        param('mode: Literal["fill"]', [("s1", "'fill'")], id="str"),
        param('mode: Literal[b"raw"]', [("sa", "b"), ("s1", "'raw'")], id="bytes"),
        param("mode: Literal[-2.5]", [("o", "-"), ("mf", "2.5")], id="number"),
        param("mode: int = 1", [("mi", "1")], id="default"),
        param("mode: str = '\\\\'", [("s1", "'"), ("se", "\\\\"), ("s1", "'")], id="default-backslash"),
        param("mode: object = ODD", [("n", "odd"), ("", "?")], id="default-not-python-stays-plain"),
    ],
)
@mark.sphinx("html", testroot="render-types", confoverrides={"typehints_defaults": "comma"})
def test_value_takes_the_pygments_token_classes(
    build_text: BuildText, make_module: MakeModule, signature: str, expected: list[tuple[str, str]]
) -> None:
    make_module(
        "values",
        dedent(f"""\
            from typing import Literal


            class _Odd:
                def __repr__(self) -> str:
                    return "odd?"


            ODD = _Odd()


            def paint({signature}) -> int:
                \"\"\"Paint.

                :param mode: the mode
                \"\"\"
            """),
    )
    html = build_text(".. autofunction:: values.paint\n")
    assert _values(html) == [("docutils literal notranslate", expected)]


@mark.parametrize(
    ("value", "role"),
    [
        param("None", "py-obj", id="None"),
        param("True", "py-data", id="True"),
    ],
)
@mark.sphinx("html", testroot="render-types")
def test_value_constant_stays_a_reference(
    build_text: BuildText, make_module: MakeModule, value: str, role: str
) -> None:
    make_module(
        "constants",
        dedent(f"""\
            from typing import Literal


            def paint(mode: Literal[{value}]) -> int:
                \"\"\"Paint.

                :param mode: the mode
                \"\"\"
            """),
    )
    html = build_text(".. autofunction:: constants.paint\n")
    assert _values(html) == [(f"xref py {role} docutils literal notranslate", [("kc", value)])]


@mark.sphinx("html", testroot="render-types")
def test_value_stylesheet_is_served(app: SphinxTestApp, build_text: BuildText) -> None:
    assert app.config.html_static_path == []
    html = build_text("Values\n======\n")
    stylesheet = Path(app.outdir) / "_static" / "sphinx_autodoc_typehints.css"
    assert (stylesheet.is_file(), 'href="_static/sphinx_autodoc_typehints.css' in html) == (True, True)


@mark.sphinx("html", testroot="render-types")
def test_value_stylesheet_keeps_incremental_config_stable(
    app: SphinxTestApp, build_text: BuildText, make_app: Callable[..., SphinxTestApp]
) -> None:
    build_text("Values\n======\n")
    rebuilt = make_app("html", srcdir=app.srcdir)
    rebuilt.build()

    assert "html_static_path" not in rebuilt.status.getvalue()


@mark.parametrize(
    "signature",
    [
        param("mode: int | None) -> int", id="union"),
        param("mode: int) -> None", id="return"),
    ],
)
@mark.sphinx("html", testroot="render-types")
def test_value_none_type_is_a_colored_reference(build_text: BuildText, make_module: MakeModule, signature: str) -> None:
    make_module(
        "none_types",
        dedent(f"""\
            def paint({signature}:
                \"\"\"Paint.

                :param mode: the mode
                \"\"\"
            """),
    )
    html = build_text(".. autofunction:: none_types.paint\n")
    assert _values(html) == [("xref py py-obj docutils literal notranslate", [("kc", "None")])]
