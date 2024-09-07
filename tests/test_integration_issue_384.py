from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Any, NewType, TypeVar

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from io import StringIO

    from sphinx.testing.util import SphinxTestApp

T = TypeVar("T")
W = NewType("W", str)


def expected(expected: str, **options: dict[str, Any]) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.EXPECTED = expected
        val.OPTIONS = options
        return val

    return dec


def warns(pattern: str) -> Callable[[T], T]:
    def dec(val: T) -> T:
        val.WARNING = pattern
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

    regexp = getattr(val, "WARNING", None)
    value = warning.getvalue().strip()
    if regexp:
        msg = f"Regex pattern did not match.\n Regex: {regexp!r}\n Input: {value!r}"
        assert re.search(regexp, value), msg
    else:
        assert not value

    result = (Path(app.srcdir) / "_build/text/index.txt").read_text()

    expected = val.EXPECTED
    try:
        assert result.strip() == dedent(expected).strip()
    except Exception:
        indented = indent(f'"""\n{result}\n"""', " " * 4)
        print(f"@expected(\n{indented}\n)\n")  # noqa: T201
        raise
