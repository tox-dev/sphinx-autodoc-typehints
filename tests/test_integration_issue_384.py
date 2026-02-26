from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, NewType, TypeVar

import pytest
from conftest import normalize_sphinx_text

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")
W = NewType("W", str)


def expected(expected: str, **options: Any) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected  # ty: ignore[unresolved-attribute]
        val.OPTIONS = options  # ty: ignore[unresolved-attribute]
        return val

    return dec


@expected(
    """\
mod.function(x=5, y=10, z=15)

   Function docstring.

   Parameters:
      * **x** ("int") -- optional specifier line 2 (default: "5")

      * **y** ("int") --

        another optional line 4

        second paragraph for y (default: "10")

      * **z** ("int") -- yet another optional s line 6 (default: "15")

   Returns:
      something

   Return type:
      bytes

""",
)
def function(x: int = 5, y: int = 10, z: int = 15) -> str:
    """
    Function docstring.

    :param x: optional specifier
              line 2
    :param y: another optional
              line 4

              second paragraph for y

    :param z: yet another optional s
              line 6

    :return: something
    :rtype: bytes
    """


# Config settings for each test run.
# Config Name: Sphinx Options as Dict.
configs = {"default_conf": {"typehints_defaults": "braces-after"}}


@pytest.mark.parametrize("val", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.parametrize("conf_run", list(configs.keys()))
@pytest.mark.sphinx("text", testroot="integration")
def test_integration(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch, val: Any, conf_run: str
) -> None:
    template = ".. autofunction:: mod.{}"

    (Path(app.srcdir) / "index.rst").write_text(template.format(val.__name__))
    app.config.__dict__.update(configs[conf_run])
    app.config.__dict__.update(val.OPTIONS)
    monkeypatch.setitem(sys.modules, "mod", sys.modules[__name__])
    app.build()
    assert "build succeeded" in status.getvalue()  # Build succeeded

    assert not warning.getvalue().strip()

    result = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())

    expected = dedent(normalize_sphinx_text(val.EXPECTED)).strip()
    assert result.strip() == expected
