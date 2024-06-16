from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Any, Callable, Literal, NewType, TypeVar  # no type comments

import pytest

if TYPE_CHECKING:
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


ArrayLike = Literal["test"]


@expected(
    """\
mod.function(x)

   Function docstring.

   Parameters:
      **x** (ArrayLike) -- foo

   Returns:
      something

   Return type:
      bytes
""",
)
def function(x: ArrayLike) -> str:  # noqa: ARG001
    """
    Function docstring.

    :param x: foo
    :return: something
    :rtype: bytes
    """


AUTO_FUNCTION = ".. autofunction:: mod.{}"

LT_PY310 = sys.version_info < (3, 10)


prolog = """
.. |test_node_start| replace:: {test_node_start}
""".format(test_node_start="test_start")


epilog = """
.. |test_node_end| replace:: {test_node_end}
""".format(test_node_end="test_end")


# Config settings for each test run.
# Config Name: Sphinx Options as Dict.
configs = {
    "default_conf": {
        "autodoc_type_aliases": {
            "ArrayLike": "ArrayLike",
        }
    }
}


@pytest.mark.parametrize("val", [x for x in globals().values() if hasattr(x, "EXPECTED")])
@pytest.mark.parametrize("conf_run", list(configs.keys()))
@pytest.mark.sphinx("text", testroot="integration")
def test_integration(
    app: SphinxTestApp, status: StringIO, warning: StringIO, monkeypatch: pytest.MonkeyPatch, val: Any, conf_run: str
) -> None:
    template = AUTO_FUNCTION

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
    if LT_PY310:
        expected = expected.replace("NewType", "NewType()")
    try:
        assert result.strip() == dedent(expected).strip()
    except Exception:
        indented = indent(f'"""\n{result}\n"""', " " * 4)
        print(f"@expected(\n{indented}\n)\n")  # noqa: T201
        raise
